'''Consultas somente leitura sobre os artefatos locais do pipeline.'''

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import quote

from pipeline_flow.domain import PipelineConfig
from pipeline_flow.domain import normalize_states
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services.migrar_estados import discover_revisions
from pipeline_flow.services.preparar_insumos import Workbook, read_json


class ReadModelError(ValueError):
    '''Falha ao consultar a visão local sem modificar sua origem.'''


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


class PipelineReadModel:
    '''Recompõe uma visão atual sem manter estado nem escrever em disco.'''

    def __init__(self, config: PipelineConfig):
        self.config = config

    def _display_path(self, value: str | Path | None) -> str | None:
        if not value:
            return None
        path = Path(value).resolve()
        roots = (
            ('preparados', self.config.output_dir),
            ('entregas', self.config.delivery_dir),
            ('projeto', self.config.root),
        )
        for label, root in roots:
            try:
                relative = path.relative_to(root.resolve())
            except ValueError:
                continue
            return f'{label}/{relative.as_posix()}'
        return path.name

    def _media_url(self, path: Path) -> str | None:
        allowed = {
            '.gif', '.jpeg', '.jpg', '.mkv',
            '.mov', '.mp4', '.png', '.webm', '.webp',
        }
        if path.suffix.lower() not in allowed:
            return None
        for scope, root in (
            ('preparados', self.config.output_dir),
            ('entregas', self.config.delivery_dir),
        ):
            try:
                relative = path.resolve().relative_to(root.resolve())
            except ValueError:
                continue
            return f'/media/{scope}/{quote(relative.as_posix())}'
        return None

    def _spreadsheet_rows(self) -> tuple[list[dict], list[dict]]:
        if not self.config.spreadsheet.is_file():
            return [], [{
                'origem': 'planilha',
                'erro': 'Planilha configurada não existe.',
            }]
        try:
            workbook = Workbook(self.config.spreadsheet, allow_legacy=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return [], [{'origem': 'planilha', 'erro': str(exc)}]
        rows = []
        errors = []
        for raw in workbook.raw_records():
            try:
                rows.append(normalize_states(raw))
            except ValueError as exc:
                rows.append(raw)
                errors.append({
                    'origem': 'planilha',
                    'linha': raw.get('_linha'),
                    'erro': str(exc),
                })
        return rows, errors

    def _rows_by_plan(self, rows: Iterable[dict]) -> dict[Path, dict]:
        indexed = {}
        for row in rows:
            value = row.get('plano_arquivo')
            if not value:
                continue
            try:
                indexed[Path(value).resolve()] = row
            except (OSError, TypeError, ValueError):
                continue
        return indexed

    def _media(self, clip: dict, state: dict, stage: str) -> dict | None:
        record = state.get(stage)
        if not isinstance(record, dict):
            return None
        result = {
            'status': record.get('status') or 'disponivel',
            'modelo': record.get('modelo'),
            'arquivo': self._display_path(record.get('arquivo')),
            'sha256': record.get('sha256'),
            'valido': False,
        }
        try:
            path = flow.media(record, clip)
            result.update(
                valido=True,
                bytes=path.stat().st_size,
                extensao=path.suffix.lower(),
                url=self._media_url(path),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result['erro'] = str(exc)
        return result

    def _event_count(self, clip: dict) -> int:
        path = clip['folder'] / 'logs' / 'eventos.jsonl'
        if not path.is_file():
            return 0
        try:
            with path.open(encoding='utf-8') as handle:
                return sum(bool(line.strip()) for line in handle)
        except OSError:
            return 0

    @staticmethod
    def _attempt(value: object) -> dict | None:
        if not isinstance(value, dict):
            return None
        return {
            field: value.get(field)
            for field in (
                'etapa',
                'status',
                'inicio',
                'submetida_em',
                'modelo',
            )
            if value.get(field) is not None
        }

    @staticmethod
    def _latest_image_review(history: object) -> dict | None:
        if not isinstance(history, list):
            return None
        for entry in reversed(history):
            if not isinstance(entry, dict) or entry.get('etapa') != 'revisar-imagem':
                continue
            return {
                field: entry.get(field)
                for field in (
                    'resultado',
                    'justificativa',
                    'imagem_sha256',
                    'revisao_sha256',
                    'fim',
                )
                if entry.get(field) not in (None, '')
            }
        return None

    @staticmethod
    def _next_action(clip: dict, state: dict, row: dict, approval_bound: bool) -> str:
        pipeline = clip['plan'].get('pipeline', {})
        carousel_plan = clip['plan'].get('carrossel')
        if state.get('tentativa'):
            return 'verificar_tentativa_interrompida'
        if pipeline.get('gerar_imagem') and not state.get('imagem'):
            return 'gerar_imagem'
        if (
            row.get('gerar_carrossel') == 'sim'
            and isinstance(carousel_plan, dict)
            and carousel_plan.get('ativo') is True
            and not state.get('carrossel')
        ):
            return 'gerar_carrossel'
        approval_ready = (
            row.get('aprovacao') == 'aprovada' and approval_bound
        )
        if (
            pipeline.get('aprovacao_necessaria')
            or pipeline.get('gerar_video')
        ) and not approval_ready:
            return 'revisar_e_aprovar_imagem'
        if pipeline.get('gerar_video') and not state.get('video'):
            return 'gerar_video'
        return 'concluido'

    def _clip(self, clip: dict, rows_by_plan: dict[Path, dict]) -> dict:
        plan_path = (clip['folder'] / 'plano_clipe.json').resolve()
        row = rows_by_plan.get(plan_path, {})
        errors = []
        try:
            state = flow.state_for(clip)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            state = {}
            errors.append(str(exc))
        image = self._media(clip, state, 'imagem')
        video = self._media(clip, state, 'video')
        approval_bound = False
        if image and image.get('valido'):
            try:
                frame = flow.media(state['imagem'], clip)
                approval_bound = flow.approval_is_bound(
                    clip,
                    state.get('aprovacao'),
                    frame,
                )
            except (OSError, ValueError, KeyError, TypeError):
                approval_bound = False
        plan = clip['plan']
        carousel_plan = plan.get('carrossel')
        carousel_requested = (
            row.get('gerar_carrossel') == 'sim'
            and isinstance(carousel_plan, dict)
            and carousel_plan.get('ativo') is True
        )
        carousel_content = None
        if carousel_requested:
            carousel_content = {
                field: carousel_plan.get(field) or ''
                for field in (
                    'texto',
                    'subtexto',
                    'cta',
                    'cta_destino',
                    'cta_palavra',
                )
            }
        return {
            'id': plan['id_clipe'],
            'producao_id': plan['producao_id'],
            'ordem': plan.get('ordem'),
            'papel': row.get('papel_na_producao') or plan.get('papel'),
            'produto_id': row.get('produto_id') or plan.get('produto_id'),
            'plano_status': plan.get('status'),
            'gera_video': bool(plan.get('pipeline', {}).get('gerar_video')),
            'metodo_video': plan.get('pipeline', {}).get('metodo_video'),
            'duracao_video_s': plan.get('pipeline', {}).get('duracao_video_s'),
            'aprovacao_necessaria': bool(
                plan.get('pipeline', {}).get('aprovacao_necessaria')
                or plan.get('pipeline', {}).get('gerar_video')
            ),
            'status': row.get('status'),
            'imagem_status': row.get('imagem_status'),
            'video_status': row.get('video_status'),
            'carrossel_status': row.get('carrossel_status'),
            'carrossel_solicitado': carousel_requested,
            'carrossel_conteudo': carousel_content,
            'decisao_humana': row.get('aprovacao') or '',
            'aprovacao_humana': row.get('aprovacao') == 'aprovada',
            'aprovacao_vinculada': approval_bound,
            'ultima_revisao_imagem': self._latest_image_review(
                state.get('historico')
            ),
            'imagem': image,
            'video': video,
            'carrossel': self._media(clip, state, 'carrossel'),
            'tentativa': self._attempt(state.get('tentativa')),
            'lock_ativo': (clip['folder'] / '.execucao.lock').is_file(),
            'eventos': self._event_count(clip),
            'proxima_acao': (
                'corrigir_estado_invalido'
                if errors
                else self._next_action(
                    clip,
                    state,
                    row,
                    approval_bound,
                )
            ),
            'pasta': self._display_path(clip['folder']),
            'erros': errors,
        }

    def _pending_clips(self, revision: Path, ready_ids: set[str]) -> list[dict]:
        try:
            summary = read_json(revision / 'plano_producao.json')
        except (OSError, ValueError, KeyError, TypeError):
            return []
        pending = []
        for item in summary.get('clipes', []):
            clip_id = item.get('id_clipe')
            if not clip_id or clip_id in ready_ids:
                continue
            try:
                plan = read_json(revision / clip_id / 'plano_clipe.json')
            except (OSError, ValueError, KeyError, TypeError):
                plan = item
            if plan.get('status') != 'pendente':
                continue
            pending.append({
                'id': clip_id,
                'producao_id': summary.get('producao_id'),
                'ordem': item.get('ordem'),
                'plano_status': 'pendente',
                'proxima_acao': 'corrigir_plano_pendente',
                'motivo': plan.get('motivo'),
                'erros': [],
            })
        return pending

    def _production(self, revision: Path, rows_by_plan: dict[Path, dict]) -> dict:
        errors = []
        try:
            summary = read_json(revision / 'plano_producao.json')
            production_id = summary['producao_id']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {
                'id': revision.parent.name,
                'revisao': revision.name,
                'ativa': False,
                'clipes': [],
                'erros': [str(exc)],
            }
        try:
            loaded = flow.load_clips(revision, skip_pending=True)
            clips = [self._clip(clip, rows_by_plan) for clip in loaded]
            clips += self._pending_clips(
                revision,
                {clip['id'] for clip in clips},
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            clips = []
            errors.append(str(exc))
        active = any(
            plan.parent.parent == revision.resolve()
            for plan in rows_by_plan
        )
        return {
            'id': production_id,
            'revisao': revision.name,
            'ativa': active,
            'pasta': self._display_path(revision),
            'clipes': sorted(
                clips,
                key=lambda item: (item.get('ordem') or 0, item['id']),
            ),
            'erros': errors,
        }

    def productions(self) -> dict:
        rows, errors = self._spreadsheet_rows()
        indexed = self._rows_by_plan(rows)
        revisions = discover_revisions(self.config.output_dir)
        productions = [self._production(path, indexed) for path in revisions]
        return {
            'gerado_em': datetime.now(timezone.utc).isoformat(),
            'planilha': {
                'arquivo': self._display_path(self.config.spreadsheet),
                'disponivel': self.config.spreadsheet.is_file(),
                'linhas': len(rows),
            },
            'producoes': productions,
            'erros': errors,
        }

    def production(self, production_id: str) -> dict:
        matches = [
            item
            for item in self.productions()['producoes']
            if item['id'] == production_id
        ]
        if not matches:
            raise ReadModelError('Produção não encontrada.')
        return {'id': production_id, 'revisoes': matches}

    def clips(self, production_id: str | None = None) -> list[dict]:
        items = []
        for production in self.productions()['producoes']:
            if production_id and production['id'] != production_id:
                continue
            for clip in production['clipes']:
                items.append({
                    **clip,
                    'revisao': production['revisao'],
                    'revisao_ativa': production['ativa'],
                })
        return items

    def deliveries(self) -> dict:
        index = self.config.delivery_dir / 'indice_entregas.json'
        if not index.is_file():
            return {'entregas': [], 'erros': []}
        try:
            entries = read_json(index)
            if not isinstance(entries, list):
                raise ReadModelError('Índice de entregas não é uma lista.')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {'entregas': [], 'erros': [str(exc)]}
        deliveries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            destination = Path(entry.get('entrega', '')).resolve()
            safe = _path_within(destination, self.config.delivery_dir)
            deliveries.append({
                'sequencia': entry.get('sequencia'),
                'tipo': entry.get('tipo'),
                'origem': self._display_path(entry.get('origem')),
                'entrega': self._display_path(destination),
                'disponivel': safe and destination.is_file(),
                'caminho_seguro': safe,
                'url': (
                    self._media_url(destination)
                    if safe and destination.is_file()
                    else None
                ),
            })
        return {'entregas': deliveries, 'erros': []}

    def logs(self, limit: int = 100) -> dict:
        limit = max(1, min(limit, 500))
        root = self.config.output_dir / 'flow'
        events = []
        errors = []
        if not root.is_dir():
            return {'eventos': [], 'erros': []}
        for path in sorted(root.rglob('eventos.jsonl')):
            if 'antigos' in path.relative_to(root).parts:
                continue
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except OSError as exc:
                errors.append({'arquivo': self._display_path(path), 'erro': str(exc)})
                continue
            for line in lines:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append({
                        'arquivo': self._display_path(path),
                        'erro': f'JSONL inválido: {exc.msg}',
                    })
                    continue
                if isinstance(event, dict):
                    events.append(event)
        events.sort(key=lambda item: str(
            item.get('timestamp')
            or item.get('inicio_em')
            or item.get('inicio')
            or item.get('em')
            or ''
        ))
        return {'eventos': events[-limit:], 'erros': errors}

    def dashboard(self) -> dict:
        view = self.productions()
        active = [item for item in view['producoes'] if item['ativa']]
        selected = active or view['producoes']
        clips = [clip for item in selected for clip in item['clipes']]
        actions = {}
        for clip in clips:
            action = clip.get('proxima_acao', 'desconhecida')
            actions[action] = actions.get(action, 0) + 1
        deliveries = self.deliveries()
        logs = self.logs(limit=20)
        production_errors = [
            {
                'origem': f'producao/{item["id"]}/{item["revisao"]}',
                'erro': error,
            }
            for item in selected
            for error in item['erros']
        ]
        return {
            'gerado_em': view['gerado_em'],
            'resumo': {
                'producoes': len({item['id'] for item in selected}),
                'revisoes': len(selected),
                'clipes': len(clips),
                'entregas': len(deliveries['entregas']),
                'erros': (
                    len(view['erros'])
                    + len(production_errors)
                    + len(deliveries['erros'])
                    + len(logs['erros'])
                ),
            },
            'proximas_acoes': actions,
            'producoes': selected,
            'ultimos_eventos': logs['eventos'],
            'erros': (
                view['erros']
                + production_errors
                + deliveries['erros']
                + logs['erros']
            ),
        }
