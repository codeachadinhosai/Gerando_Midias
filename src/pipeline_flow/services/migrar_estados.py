'''Migra estados de execucao legados sem gerar ou substituir midia.'''

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

from pipeline_flow.config import load_config
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services.preparar_insumos import (
    Invalid,
    ROOT,
    Workbook,
    digest,
    now,
    read_json,
    require,
)


MIGRATION_EVENT_SCHEMA_VERSION = 1


def plan_execution_state_migration(clip, state):
    '''Valida o estado e devolve copia migrada, alteracoes e gate humano.'''
    require(isinstance(state, dict), 'Estado de execucao invalido.')
    flow.require_sha256(state.get('fingerprint'), 'fingerprint do estado')
    require(
        state['fingerprint'] == clip['fingerprint'],
        'Estado pertence a outros insumos; migracao bloqueada.',
    )
    migrated = copy.deepcopy(state)
    changes = []
    version = migrated.get('schema_version')
    if version is None:
        migrated['schema_version'] = flow.EXECUTION_SCHEMA_VERSION
        changes.append('estado_v2')
    else:
        require(
            version == flow.EXECUTION_SCHEMA_VERSION,
            'Versao do estado de execucao nao suportada.',
        )

    fingerprint, _, response_hash = flow.revision_identity(clip)
    for stage in ('imagem', 'video'):
        record = migrated.get(stage)
        if record is None:
            continue
        require(isinstance(record, dict), f'Registro de {stage} invalido.')
        if record.get('schema_version') is None:
            flow.media(record)
            migrated[stage] = {
                **record,
                'schema_version': flow.MEDIA_SCHEMA_VERSION,
                'revisao_sha256': response_hash,
                'fingerprint_sha256': fingerprint,
            }
            changes.append(f'{stage}_v2')
        else:
            flow.media(record, clip)

    requires_reapproval = False
    approval = migrated.get('aprovacao')
    if approval is not None:
        require(isinstance(approval, dict), 'Registro de aprovacao invalido.')
        if approval.get('schema_version') is None:
            archived = copy.deepcopy(approval)
            archived.update(
                resultado='revogada_por_migracao_v2',
                motivo='Aprovacao legada sem vinculo comprovavel com a revisao.',
            )
            approval_history = migrated.setdefault(
                'aprovacoes_historicas',
                [],
            )
            require(
                isinstance(approval_history, list),
                'Historico de aprovacoes invalido.',
            )
            approval_history.append(archived)
            migrated.pop('aprovacao')
            changes.append('aprovacao_legada_arquivada')
            requires_reapproval = True
        else:
            require(
                approval.get('schema_version') == flow.APPROVAL_SCHEMA_VERSION,
                'Versao do registro de aprovacao nao suportada.',
            )
            if migrated.get('imagem'):
                frame = flow.media(migrated['imagem'], clip)
            elif clip['plan'].get('frame_existente_ref_id'):
                frame = flow.existing(clip, 'frame_existente_ref_id')
            else:
                frame = None
            require(
                frame is not None
                and flow.approval_is_bound(clip, approval, frame),
                'Aprovacao versionada nao corresponde ao frame ou a revisao.',
            )

    attempt = migrated.get('tentativa')
    if attempt is not None:
        require(isinstance(attempt, dict), 'Registro de tentativa invalido.')
        attempt_version = attempt.get('schema_version')
        require(
            attempt_version in {None, flow.ATTEMPT_SCHEMA_VERSION},
            'Versao do registro de tentativa nao suportada.',
        )

    return migrated, changes, requires_reapproval


def _backup_state(path, source_hash):
    archive_dir = path.parent / 'logs' / 'migrations'
    archive_dir.mkdir(parents=True, exist_ok=True)
    backup = archive_dir / f'execucao.{source_hash[:12]}.json'
    if backup.exists():
        require(
            digest(backup) == source_hash,
            'Backup de migracao existente diverge do estado original.',
        )
    else:
        shutil.copy2(path, backup)
    return backup


def _revoke_spreadsheet_approval(sheet, clip):
    if sheet is None:
        return False
    wb = Workbook(sheet)
    plan_path = (clip['folder'] / 'plano_clipe.json').resolve()
    matches = [
        record
        for record in wb.records()
        if record.get('plano_arquivo')
        and Path(record['plano_arquivo']).resolve() == plan_path
    ]
    require(
        len(matches) <= 1,
        'Mais de uma linha da planilha aponta para o mesmo plano.',
    )
    if not matches or not matches[0].get('aprovacao'):
        return False
    wb.set(matches[0]['_linha'], 'aprovacao', '')
    wb.save()
    return True


def migrate_clip_state(clip, sheet=None, *, apply=False):
    '''Simula ou aplica uma migracao atomica sob o lock do clipe.'''
    folder = Path(clip['folder']).resolve()
    path = (folder / 'execucao.json').resolve()
    require(
        path.is_relative_to(folder),
        'execucao.json esta fora da pasta do clipe.',
    )
    require(path.is_file(), 'execucao.json ausente.')

    def planned():
        original = read_json(path)
        migrated, changes, requires_reapproval = (
            plan_execution_state_migration(clip, original)
        )
        return original, migrated, changes, requires_reapproval

    if not apply:
        _, _, changes, requires_reapproval = planned()
        return {
            'producao_id': clip['plan']['producao_id'],
            'id_clipe': clip['plan']['id_clipe'],
            'estado': 'pendente' if changes else 'atual',
            'alteracoes': changes,
            'reaprovacao_necessaria': requires_reapproval,
            'aplicada': False,
        }

    try:
        handle = flow.acquire_clip_lock(clip, 'migrar-estado')
    except flow.LockError as exc:
        raise Invalid(str(exc)) from exc
    active_error = None
    try:
        original, migrated, changes, requires_reapproval = planned()
        result = {
            'producao_id': clip['plan']['producao_id'],
            'id_clipe': clip['plan']['id_clipe'],
            'estado': 'atual',
            'alteracoes': changes,
            'reaprovacao_necessaria': requires_reapproval,
            'aplicada': False,
        }
        if not changes:
            return result
        source_hash = digest(path)
        backup = _backup_state(path, source_hash)
        approval_cleared = (
            _revoke_spreadsheet_approval(sheet, clip)
            if requires_reapproval
            else False
        )
        migration_history = migrated.setdefault(
            'historico_migracoes',
            [],
        )
        require(
            isinstance(migration_history, list),
            'Historico de migracoes invalido.',
        )
        migration_history.append(
            {
                'schema_version': MIGRATION_EVENT_SCHEMA_VERSION,
                'em': now(),
                'origem_sha256': source_hash,
                'backup': str(backup.resolve()),
                'alteracoes': changes,
                'reaprovacao_necessaria': requires_reapproval,
                'aprovacao_planilha_limpa': approval_cleared,
            }
        )
        flow.atomic(path, migrated)
        result.update(
            estado='migrado',
            aplicada=True,
            backup=str(backup.resolve()),
            aprovacao_planilha_limpa=approval_cleared,
        )
        return result
    except BaseException as exc:
        active_error = exc
        raise
    finally:
        try:
            flow.release_lock(handle)
        except flow.LockError as lock_error:
            if active_error is not None:
                active_error.add_note(
                    f'Falha adicional ao liberar lock: {lock_error}'
                )
            else:
                raise Invalid(str(lock_error)) from lock_error


def discover_revisions(output_dir):
    base = Path(output_dir).resolve() / 'flow'
    if not base.is_dir():
        return []
    return sorted(
        revision
        for production in base.iterdir()
        if production.is_dir()
        for revision in production.iterdir()
        if revision.is_dir()
        and (revision / 'plano_producao.json').is_file()
        and (revision / 'resposta_ia.json').is_file()
    )


def migrate_all(
    output_dir,
    sheet=None,
    *,
    apply=False,
    production_id=None,
    clip_id=None,
):
    items = []
    errors = []
    flow_root = Path(output_dir).resolve() / 'flow'
    preserved_history = (
        sum(
            'antigos' in path.relative_to(flow_root).parts
            for path in flow_root.rglob('execucao.json')
        )
        if flow_root.is_dir()
        else 0
    )
    for revision in discover_revisions(output_dir):
        if production_id and revision.parent.name != production_id:
            continue
        try:
            clips = flow.load_clips(revision, skip_pending=True)
        except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({'revisao': str(revision), 'erro': str(exc)})
            continue
        for clip in clips:
            if clip_id and clip['plan']['id_clipe'] != clip_id:
                continue
            if not (clip['folder'] / 'execucao.json').is_file():
                continue
            try:
                items.append(
                    migrate_clip_state(
                        clip,
                        sheet,
                        apply=apply,
                    )
                )
            except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(
                    {
                        'producao_id': clip['plan']['producao_id'],
                        'id_clipe': clip['plan']['id_clipe'],
                        'erro': str(exc),
                    }
                )
    return {
        'modo': 'aplicar' if apply else 'simular',
        'estados_analisados': len(items),
        'estados_pendentes': sum(
            item['estado'] == 'pendente'
            for item in items
        ),
        'estados_migrados': sum(
            item['estado'] == 'migrado'
            for item in items
        ),
        'estados_historicos_preservados': preserved_history,
        'itens': items,
        'erros': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=ROOT)
    parser.add_argument('--saida', type=Path)
    parser.add_argument('--planilha', type=Path)
    parser.add_argument('--producao')
    parser.add_argument('--clipe')
    parser.add_argument(
        '--aplicar',
        action='store_true',
        help='Aplica a migracao; sem esta opcao apenas simula.',
    )
    args = parser.parse_args()
    try:
        config = load_config(args.raiz)
        report = migrate_all(
            (args.saida or config.output_dir).resolve(),
            (args.planilha or config.spreadsheet).resolve(),
            apply=args.aplicar,
            production_id=args.producao,
            clip_id=args.clipe,
        )
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 2 if report['erros'] else 0
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps({'erro': str(exc)}, ensure_ascii=True),
            file=sys.stderr,
        )
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
