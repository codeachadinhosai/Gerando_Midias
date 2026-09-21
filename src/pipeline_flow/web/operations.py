# Operações locais e confirmadas expostas pela interface web.

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import uuid
import warnings

from PIL import Image, UnidentifiedImageError

from pipeline_flow.cli import create_ai_bundle
from pipeline_flow.domain import PipelineConfig
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services import gerar_carrossel as carousel
from pipeline_flow.services.preparar_insumos import (
    Invalid,
    Workbook,
    import_response,
    norm,
    prepare,
    read_json,
    signature,
    now,
)


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}
REVISION_PATTERN = re.compile(r'[0-9a-f]{16}')
CREDIT_CONFIRMATION = 'GERAR VIDEO'
ACTIVE_EXECUTION_STATES = {'queued', 'running'}


class OperationError(ValueError):
    pass


class OperationConflict(OperationError):
    pass


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _segment(value: str, field: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value or str()):
        raise OperationError(f'{field} inválido.')
    return value


class PipelineOperations:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._lock = threading.Lock()
        self._execution_lock = threading.Lock()
        self._executions: dict[str, dict] = {}

    @property
    def credit_lock_path(self) -> Path:
        return self.config.output_dir / '.locks' / 'video-credit.lock'

    def execution_catalog(self) -> dict:
        binary = self.config.gflow_root / '.venv/Scripts/gflow.exe'
        with self._execution_lock:
            executions = [
                dict(item)
                for item in sorted(
                    self._executions.values(),
                    key=lambda value: value['solicitada_em'],
                    reverse=True,
                )
            ]
        return {
            'execucoes': executions,
            'executor': {
                'disponivel': (
                    binary.is_file() and bool(self.config.project_id)
                ),
                'gflow_disponivel': binary.is_file(),
                'projeto_configurado': bool(self.config.project_id),
                'modelo': self.config.video_model,
                'timeout_segundos': self.config.timeout_seconds,
                'maximo_simultaneo': 1,
                'trava_credito_ativa': self.credit_lock_path.is_file(),
            },
        }

    def _update_execution(self, execution_id: str, **fields) -> None:
        with self._execution_lock:
            current = self._executions.get(execution_id)
            if current is not None:
                current.update(fields)

    def _safe_execution_error(self, exc: Exception) -> str:
        if isinstance(exc, subprocess.TimeoutExpired):
            return (
                'O Flow excedeu o tempo limite de '
                + str(self.config.timeout_seconds)
                + ' segundos. Confira a tentativa antes de reenviar.'
            )
        message = str(exc) or 'Falha sem detalhe seguro disponivel.'
        if self.config.project_id:
            message = message.replace(
                self.config.project_id,
                '<redigido>',
            )
        return message[:1000]

    def _video_preflight(
        self,
        clip: dict,
        expected_image_sha256: str,
    ) -> None:
        try:
            flow.require_sha256(
                expected_image_sha256,
                'imagem_sha256 esperada',
            )
            state = flow.state_for(clip)
            workbook = Workbook(self.config.spreadsheet)
            row = flow.row_for(workbook, clip)
            pipeline = clip['plan']['pipeline']
            if not pipeline.get('gerar_video'):
                raise OperationError('Este plano nao solicita geracao de video.')
            if state.get('video'):
                flow.media(state['video'], clip)
                raise OperationConflict('O video deste clipe ja foi concluido.')
            if state.get('tentativa'):
                raise OperationConflict(
                    'Existe uma tentativa incompleta; confira o acompanhamento antes de reenviar.'
                )
            if (clip['folder'] / '.execucao.lock').is_file():
                raise OperationConflict('O clipe possui uma operacao em andamento.')
            if self.credit_lock_path.is_file():
                raise OperationConflict(
                    'Outra geracao paga esta ativa ou requer revisao manual.'
                )
            if not state.get('imagem'):
                raise OperationError('O clipe nao possui imagem registrada para revisao.')
            frame = flow.media(state['imagem'], clip)
            if flow.digest(frame) != expected_image_sha256:
                raise OperationConflict(
                    'A imagem mudou desde que a tela foi carregada. Atualize os dados antes de liberar o video.'
                )
            if not (
                norm(row.get('aprovacao')) == 'aprovada'
                and flow.approval_is_bound(
                    clip,
                    state.get('aprovacao'),
                    frame,
                )
            ):
                raise OperationError(
                    'A imagem precisa estar aprovada e vinculada a este frame e revisao.'
                )
            binary = self.config.gflow_root / '.venv/Scripts/gflow.exe'
            if not binary.is_file():
                raise OperationError(
                    'gflow.exe nao foi encontrado na raiz configurada.'
                )
            if not self.config.project_id:
                raise OperationError(
                    'GFLOW_PROJECT_ID nao esta configurado.'
                )
        except OperationError:
            raise
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc

    def _run_video_execution(
        self,
        execution_id: str,
        clip: dict,
        args: SimpleNamespace,
    ) -> None:
        self._update_execution(
            execution_id,
            status='running',
            iniciada_em=now(),
        )
        try:
            result = flow.execute(clip, args)
        except Exception as exc:
            self._update_execution(
                execution_id,
                status='failed',
                concluida_em=now(),
                erro=self._safe_execution_error(exc),
            )
            return
        self._update_execution(
            execution_id,
            status='succeeded',
            concluida_em=now(),
            resultado=result,
        )

    def start_video(
        self,
        production: str,
        revision: str,
        clip_id: str,
        image_sha256: str,
        credit_confirmation: str,
    ) -> dict:
        values = {
            'Producao': production,
            'Revisao': revision,
            'Clipe': clip_id,
            'SHA-256 da imagem': image_sha256,
            'Confirmacao de credito': credit_confirmation,
        }
        if any(not isinstance(value, str) for value in values.values()):
            raise OperationError('Campos da liberacao de video devem ser textos.')
        if credit_confirmation != CREDIT_CONFIRMATION:
            raise OperationError(
                'Digite GERAR VIDEO para confirmar o possivel consumo de creditos.'
            )
        clip = self._active_clip(production, revision, clip_id)
        self._video_preflight(clip, image_sha256)
        execution_id = uuid.uuid4().hex
        job = {
            'id': execution_id,
            'producao_id': production,
            'revisao': revision,
            'id_clipe': clip_id,
            'status': 'queued',
            'modelo': self.config.video_model,
            'solicitada_em': now(),
        }
        with self._execution_lock:
            if any(
                item.get('status') in ACTIVE_EXECUTION_STATES
                for item in self._executions.values()
            ):
                raise OperationConflict(
                    'Ja existe uma geracao de video em andamento. Aguarde a conclusao antes de liberar outra.'
                )
            finished = [
                key
                for key, item in self._executions.items()
                if item.get('status') not in ACTIVE_EXECUTION_STATES
            ]
            while len(self._executions) >= 100 and finished:
                self._executions.pop(finished.pop(0), None)
            self._executions[execution_id] = job
        args = SimpleNamespace(
            acao='video',
            planilha=self.config.spreadsheet,
            gflow_raiz=self.config.gflow_root,
            projeto=self.config.project_id,
            modelo_video=self.config.video_model,
            timeout=self.config.timeout_seconds,
            delivery_dir=self.config.delivery_dir,
            expected_image_sha256=image_sha256,
            credit_lock_path=(
                self.config.output_dir / '.locks' / 'video-credit.lock'
            ),
        )
        thread = threading.Thread(
            target=self._run_video_execution,
            args=(execution_id, clip, args),
            name='pipeline-video-' + execution_id[:8],
            daemon=True,
        )
        try:
            thread.start()
        except RuntimeError as exc:
            self._update_execution(
                execution_id,
                status='failed',
                concluida_em=now(),
                erro='Nao foi possivel iniciar a tarefa local.',
            )
            raise OperationError(
                'Nao foi possivel iniciar a tarefa local.'
            ) from exc
        return dict(job)

    def _package(self, token: str) -> tuple[Path, dict]:
        parts = token.split('/')
        if len(parts) != 2:
            raise OperationError('Pacote inválido.')
        production = _segment(parts[0], 'Produção')
        revision = parts[1]
        if not REVISION_PATTERN.fullmatch(revision):
            raise OperationError('Revisão do pacote inválida.')
        root = self.config.output_dir / 'pacotes'
        package = (root / production / revision).resolve()
        if not _within(package, root) or not package.is_dir():
            raise OperationError('Pacote não encontrado.')
        try:
            manifest = read_json(package / 'manifesto.json')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(f'Manifesto inválido: {exc}') from exc
        if manifest.get('producao_id') != production:
            raise OperationError('Produção e manifesto divergem.')
        return package, manifest

    def _response(self, token: str) -> Path:
        root = self.config.responses_dir.resolve()
        candidate = (root / token).resolve()
        if (
            not _within(candidate, root)
            or candidate.suffix.lower() != '.json'
            or not candidate.is_file()
        ):
            raise OperationError('Resposta não encontrada.')
        return candidate

    def catalog(self) -> dict:
        packages = []
        package_root = self.config.output_dir / 'pacotes'
        for manifest_file in sorted(package_root.glob('*/*/manifesto.json')):
            if not _within(manifest_file, package_root):
                continue
            try:
                manifest = read_json(manifest_file)
                production = manifest['producao_id']
                revision = manifest_file.parent.name
                if not REVISION_PATTERN.fullmatch(revision):
                    continue
                packages.append({
                    'id': f'{production}/{revision}',
                    'producao_id': production,
                    'revisao': revision,
                    'pacote_sha256': manifest.get('pacote_sha256'),
                    'clipes': len(manifest.get('clipes', [])),
                })
            except (OSError, ValueError, KeyError, TypeError):
                continue
        responses = []
        root = self.config.responses_dir
        for response_file in sorted(root.rglob('*.json')) if root.exists() else []:
            if not _within(response_file, root):
                continue
            try:
                data = read_json(response_file)
                responses.append({
                    'id': response_file.relative_to(root).as_posix(),
                    'pacote_sha256': data.get('pacote_sha256'),
                    'producao_id': data.get('plano_producao', {}).get('producao_id'),
                })
            except (OSError, ValueError, KeyError, TypeError):
                continue
        latest = self.config.output_dir / 'pacotes_ia' / 'ULTIMO_PACOTE_IA.zip'
        return {
            'pacotes': packages,
            'respostas': responses,
            'limite_upload_bytes': MAX_UPLOAD_BYTES,
            'pacote_ia': {
                'disponivel': latest.is_file(),
                'bytes': latest.stat().st_size if latest.is_file() else 0,
                'url': '/api/operations/package-latest' if latest.is_file() else None,
            },
        }

    def prepare_packages(self) -> dict:
        roots = [
            self.config.root / 'entradas',
            self.config.root / 'referencia_gflow_original' / 'Fila Flow',
        ]
        with self._lock:
            report = prepare(
                self.config.root,
                self.config.spreadsheet,
                roots,
                output_dir=self.config.output_dir,
            )
            bundle = create_ai_bundle(report, self.config.output_dir)
        return {'preparacao': report, 'pacote_ia': bundle}

    def import_saved(self, package_id: str, response_id: str) -> dict:
        package, _ = self._package(package_id)
        response = self._response(response_id)
        with self._lock:
            return import_response(
                self.config.root,
                package,
                response,
                update_excel=True,
                output_dir=self.config.output_dir,
            )

    def import_uploaded(
        self, package_id: str, filename: str, content: bytes
    ) -> dict:
        package, manifest = self._package(package_id)
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise OperationError('Resposta vazia ou acima do limite de 50 MiB.')
        if Path(filename).name != filename or Path(filename).suffix.lower() != '.json':
            raise OperationError('Envie um arquivo JSON com nome simples.')
        try:
            data = json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OperationError(f'JSON inválido: {exc}') from exc
        if not isinstance(data, dict):
            raise OperationError('A resposta deve ser um objeto JSON.')
        root = self.config.responses_dir
        root.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(suffix='.json', dir=root)
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            temporary.write_bytes(content)
            with self._lock:
                result = import_response(
                    self.config.root,
                    package,
                    temporary,
                    update_excel=True,
                    output_dir=self.config.output_dir,
                )
                response_hash = signature(data)[:12]
                production = manifest['producao_id']
                revision = package.name
                destination = root / (
                    f'{production}_{revision}_{response_hash}_resposta_ia.json'
                )
                if destination.exists():
                    if destination.read_bytes() != content:
                        raise OperationError('Resposta existente diverge do upload.')
                    temporary.unlink()
                else:
                    os.replace(temporary, destination)
            return {**result, 'resposta_salva': str(destination)}
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _validate_image(filename: str, content: bytes) -> tuple[str, int, int]:
        suffix = Path(filename).suffix.lower()
        if Path(filename).name != filename or suffix not in IMAGE_SUFFIXES:
            raise OperationError('Formato de imagem não aceito.')
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise OperationError('Imagem vazia ou acima do limite de 50 MiB.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    'error', Image.DecompressionBombWarning
                )
                with Image.open(io.BytesIO(content)) as image:
                    width, height = image.size
                    image_format = (image.format or str()).lower()
                    image.verify()
        except (
            OSError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise OperationError('O arquivo enviado não é uma imagem válida.') from exc
        if (
            width <= 0
            or height <= 0
            or width * height > MAX_IMAGE_PIXELS
        ):
            raise OperationError('A imagem excede o limite seguro de pixels.')
        expected = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp'}
        if image_format != expected[suffix]:
            raise OperationError('A extensão não corresponde ao conteúdo da imagem.')
        return suffix, width, height

    def _active_clip(self, production: str, revision: str, clip_id: str) -> dict:
        production = _segment(production, 'Produção')
        clip_id = _segment(clip_id, 'Clipe')
        if not REVISION_PATTERN.fullmatch(revision):
            raise OperationError('Revisão inválida.')
        root = self.config.output_dir / 'flow'
        folder = (root / production / revision).resolve()
        expected_plan = (folder / clip_id / 'plano_clipe.json').resolve()
        if not _within(folder, root) or not expected_plan.is_file():
            raise OperationError('Clipe não encontrado.')
        try:
            records = Workbook(self.config.spreadsheet).records()
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc
        active = False
        for row in records:
            try:
                plan = Path(row.get('plano_arquivo') or str()).resolve()
            except (OSError, ValueError):
                continue
            if norm(row.get('classifica')) == 'sim' and plan == expected_plan:
                active = True
                break
        if not active:
            raise OperationError('Somente o clipe da revisão ativa pode ser alterado.')
        try:
            clips = flow.load_clips(folder)
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc
        match = next((item for item in clips if item['plan']['id_clipe'] == clip_id), None)
        if match is None:
            raise OperationError('Clipe não encontrado na revisão.')
        return match

    def register_image(
        self,
        production: str,
        revision: str,
        clip_id: str,
        filename: str,
        content: bytes,
    ) -> dict:
        _, width, height = self._validate_image(filename, content)
        clip = self._active_clip(production, revision, clip_id)
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix='.imagem-web-',
            suffix='-' + filename,
            dir=self.config.output_dir,
        )
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            temporary.write_bytes(content)
            args = SimpleNamespace(
                acao='registrar-imagem',
                arquivo=temporary,
                planilha=self.config.spreadsheet,
                delivery_dir=self.config.delivery_dir,
            )
            result = flow.execute(clip, args)
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc
        finally:
            if temporary.exists():
                temporary.unlink()
        return {
            'producao_id': production,
            'revisao': revision,
            'id_clipe': clip_id,
            'arquivo_origem': filename,
            'largura': width,
            'altura': height,
            'resultado': result,
        }

    def review_image(
        self,
        production: str,
        revision: str,
        clip_id: str,
        decision: str,
        image_sha256: str,
        reason: str = '',
    ) -> dict:
        values = {
            'Produção': production,
            'Revisão': revision,
            'Clipe': clip_id,
            'Decisão': decision,
            'SHA-256 da imagem': image_sha256,
            'Justificativa': reason,
        }
        if any(not isinstance(value, str) for value in values.values()):
            raise OperationError('Campos da revisão devem ser textos.')
        clip = self._active_clip(production, revision, clip_id)
        try:
            result = flow.record_human_image_review(
                clip,
                self.config.spreadsheet,
                decision,
                image_sha256,
                reason,
            )
        except flow.ImageReviewConflict as exc:
            raise OperationConflict(str(exc)) from exc
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc
        return {
            'producao_id': production,
            'revisao': revision,
            'id_clipe': clip_id,
            **result,
        }

    def generate_carousel(
        self,
        production: str,
        revision: str,
        clip_id: str,
        image_sha256: str,
        regenerate: bool = False,
    ) -> dict:
        values = {
            'Produção': production,
            'Revisão': revision,
            'Clipe': clip_id,
            'SHA-256 da imagem': image_sha256,
        }
        if any(not isinstance(value, str) for value in values.values()):
            raise OperationError('Campos do carrossel devem ser textos.')
        if not isinstance(regenerate, bool):
            raise OperationError('O indicador de regeneração deve ser booleano.')
        clip = self._active_clip(production, revision, clip_id)
        try:
            destination = carousel.generate(
                clip,
                self.config.spreadsheet,
                self.config.delivery_dir,
                expected_image_sha256=image_sha256,
                force=regenerate,
            )
        except carousel.CarouselConflict as exc:
            raise OperationConflict(str(exc)) from exc
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            raise OperationError(str(exc)) from exc
        try:
            relative = destination.resolve().relative_to(
                self.config.delivery_dir.resolve()
            ).as_posix()
        except ValueError as exc:
            raise OperationError('Card gerado fora da pasta de entregas.') from exc
        return {
            'producao_id': production,
            'revisao': revision,
            'id_clipe': clip_id,
            'arquivo': relative,
            'resultado': (
                'carrossel regenerado localmente; versão anterior preservada'
                if regenerate
                else 'carrossel gerado localmente sem consumo de créditos'
            ),
        }
