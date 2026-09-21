"""Executa insumos importados no ambiente gflow existente."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from pipeline_flow.config import VIDEO_MODELS, load_config
from pipeline_flow.domain import ImageStatus, PipelineStatus, VideoStatus
from pipeline_flow.services.execution_control import (
    LockError,
    acquire_lock,
    release_lock,
)
from pipeline_flow.services.operational_log import record_clip_event
from pipeline_flow.services.preparar_insumos import ROOT, Workbook, Invalid, digest, inside, norm, now, read_json, require, safe_id, signature, write_json


APPROVAL_SCHEMA_VERSION = 2
EXECUTION_SCHEMA_VERSION = 2
MEDIA_SCHEMA_VERSION = 2
ATTEMPT_SCHEMA_VERSION = 2
SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$')
IMAGE_OUTPUT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
VIDEO_OUTPUT_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv'}


class ImageReviewConflict(Invalid):
    # Sinaliza revisão obsoleta sem confundir com uma entrada inválida comum.
    pass


def require_sha256(value, field):
    require(
        isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None,
        f'{field} deve ser um SHA-256 hexadecimal valido.',
    )
    return value


def revision_identity(clip):
    fingerprint = require_sha256(clip.get('fingerprint'), 'fingerprint da revisao')
    package_hash = require_sha256(
        clip.get('flow', {}).get('pacote_sha256'),
        'pacote_sha256 da revisao',
    )
    response_hash = require_sha256(
        clip.get('revision_sha256'),
        'sha256 da resposta importada',
    )
    return fingerprint, package_hash, response_hash


def media_record(clip, path, **metadata):
    path = Path(path).resolve()
    require(path.is_file() and path.stat().st_size > 0, 'Midia ausente ou vazia.')
    fingerprint, _, response_hash = revision_identity(clip)
    return {
        **metadata,
        'schema_version': MEDIA_SCHEMA_VERSION,
        'arquivo': str(path),
        'sha256': digest(path),
        'revisao_sha256': response_hash,
        'fingerprint_sha256': fingerprint,
    }


def approval_record(clip, frame, approved_at):
    frame = Path(frame).resolve()
    require(frame.is_file() and frame.stat().st_size > 0, 'Frame ausente ou vazio.')
    fingerprint, package_hash, response_hash = revision_identity(clip)
    return {
        'schema_version': APPROVAL_SCHEMA_VERSION,
        'producao_id': str(clip['plan']['producao_id']),
        'id_clipe': str(clip['plan']['id_clipe']),
        'revisao_sha256': response_hash,
        'fingerprint_sha256': fingerprint,
        'pacote_sha256': package_hash,
        'imagem_arquivo': str(frame),
        'imagem_sha256': digest(frame),
        'aprovada_em': approved_at,
    }


def approval_is_bound(clip, approval, frame):
    if not isinstance(approval, dict) or approval.get('schema_version') != APPROVAL_SCHEMA_VERSION:
        return False
    try:
        frame = Path(frame).resolve()
        if not frame.is_file() or frame.stat().st_size <= 0:
            return False
        fingerprint, package_hash, response_hash = revision_identity(clip)
        require_sha256(approval.get('imagem_sha256'), 'imagem_sha256 da aprovacao')
        require_sha256(approval.get('revisao_sha256'), 'revisao_sha256 da aprovacao')
        require_sha256(approval.get('fingerprint_sha256'), 'fingerprint_sha256 da aprovacao')
        require_sha256(approval.get('pacote_sha256'), 'pacote_sha256 da aprovacao')
        frame_hash = digest(frame)
    except (Invalid, OSError, TypeError, ValueError):
        return False
    return (
        approval.get('producao_id') == str(clip['plan']['producao_id'])
        and approval.get('id_clipe') == str(clip['plan']['id_clipe'])
        and approval.get('revisao_sha256') == response_hash
        and approval.get('fingerprint_sha256') == fingerprint
        and approval.get('pacote_sha256') == package_hash
        and approval.get('imagem_arquivo') == str(frame)
        and approval.get('imagem_sha256') == frame_hash
    )


def video_release_frame(clip, state, row, expected_image_sha256=None):
    pipe = clip['plan']['pipeline']
    frame = None
    if state.get('imagem'):
        frame = media(state['imagem'], clip)
    elif pipe['metodo_video'] == 'i2v' or pipe['aprovacao_necessaria']:
        frame = existing(clip, 'frame_existente_ref_id')
    if expected_image_sha256 is not None:
        require_sha256(
            expected_image_sha256,
            'imagem_sha256 esperada',
        )
        require(
            frame is not None and digest(frame) == expected_image_sha256,
            'A imagem mudou desde a liberacao do video; atualize os dados e revise novamente.',
        )
    require(
        frame is not None
        and norm(row['aprovacao']) == 'aprovada'
        and approval_is_bound(clip, state.get('aprovacao'), frame),
        'Aprovacao ausente/revogada ou vinculada a outro frame ou revisao; execute aprovar apos revisao.',
    )
    return frame


def record_human_image_review(
    clip,
    sheet,
    decision,
    expected_image_sha256,
    reason='',
):
    # A ordem das gravações garante que falhas parciais não liberem o vídeo.
    decision = norm(decision)
    require(decision in {'aprovada', 'rejeitada'}, 'Decisao invalida.')
    expected_image_sha256 = require_sha256(
        expected_image_sha256,
        'imagem_sha256 esperada',
    )
    reason = ' '.join(str(reason or '').split())
    require(len(reason) <= 500, 'Justificativa deve ter no maximo 500 caracteres.')
    if decision == 'rejeitada':
        require(bool(reason), 'Justificativa obrigatoria para rejeitar a imagem.')
    else:
        reason = ''

    started_at = now()
    try:
        lock_handle = acquire_clip_lock(clip, 'revisar-imagem')
    except LockError as exc:
        raise Invalid(str(exc)) from exc

    try:
        state = state_for(clip)
        require(
            not state.get('video'),
            'Video ja registrado; preserve o ativo e importe uma nova revisao para mudar a decisao.',
        )
        require(state.get('imagem'), 'Imagem registrada ausente.')
        frame = media(state['imagem'], clip)
        current_image_sha256 = digest(frame)
        if current_image_sha256 != expected_image_sha256:
            raise ImageReviewConflict(
                'A imagem mudou desde que a tela foi carregada. Atualize os dados e revise novamente.'
            )

        wb = Workbook(sheet)
        row = row_for(wb, clip)
        decided_at = now()
        history = {
            'etapa': 'revisar-imagem',
            'inicio': started_at,
            'fim': decided_at,
            'resultado': decision,
            'imagem_sha256': current_image_sha256,
            'revisao_sha256': clip['revision_sha256'],
            'justificativa': reason,
        }

        if decision == 'rejeitada':
            state.pop('aprovacao', None)
            state.setdefault('historico', []).append(history)
            atomic(clip['folder'] / 'execucao.json', state)
            wb.set_human_approval(row['_linha'], decision)
            wb.set(row['_linha'], 'status', PipelineStatus.WAITING_APPROVAL)
            wb.set(row['_linha'], 'erro', reason)
            wb.set(row['_linha'], 'atualizado_em', decided_at)
            wb.save()
            message = 'imagem rejeitada; video permanece bloqueado'
        else:
            wb.set_human_approval(row['_linha'], decision)
            wb.set(
                row['_linha'],
                'status',
                PipelineStatus.READY_FOR_VIDEO
                if clip['plan']['pipeline'].get('gerar_video')
                else PipelineStatus.APPROVED,
            )
            wb.set(row['_linha'], 'erro', '')
            wb.set(row['_linha'], 'atualizado_em', decided_at)
            wb.save()
            state['aprovacao'] = approval_record(clip, frame, decided_at)
            state.setdefault('historico', []).append(history)
            atomic(clip['folder'] / 'execucao.json', state)
            message = 'imagem aprovada e vinculada ao frame'

        record_clip_event(
            clip,
            stage='revisar-imagem',
            method='decisao_humana_na_interface',
            command=None,
            result=decision,
            error='',
            started_at=started_at,
            timestamp=now(),
        )
        return {
            'resultado': message,
            'decisao': decision,
            'imagem_sha256': current_image_sha256,
            'revisao_sha256': clip['revision_sha256'],
            'decidida_em': decided_at,
        }
    except Exception as exc:
        try:
            record_clip_event(
                clip,
                stage='revisar-imagem',
                method='decisao_humana_na_interface',
                command=None,
                result='erro',
                error=str(exc),
                started_at=started_at,
                timestamp=now(),
            )
        except OSError as log_error:
            exc.add_note(
                f'Falha adicional ao registrar log operacional: {log_error}'
            )
        raise
    finally:
        try:
            release_lock(lock_handle)
        except LockError as lock_error:
            active_error = sys.exception()
            if active_error is not None:
                active_error.add_note(
                    f'Falha adicional ao liberar lock: {lock_error}'
                )
            else:
                raise Invalid(str(lock_error)) from lock_error


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    write_json(temporary, value)
    os.replace(temporary, path)


def export_delivery(clip, stage, record, delivery_dir=None):
    if stage == 'imagem' and record.get('modelo') == 'fornecida_pelo_usuario':
        return None
    if stage == 'video' and record.get('status') == 'reutilizado':
        return None
    source = media(record, clip).resolve()
    delivery_dir = Path(delivery_dir).resolve() if delivery_dir else ROOT / 'entregas_flow'
    index_path = delivery_dir / 'indice_entregas.json'
    delivery_dir.mkdir(parents=True, exist_ok=True)
    try:
        lock_handle = acquire_lock(
            delivery_dir / '.indice_entregas.lock',
            'exportar-entrega',
        )
    except LockError as exc:
        raise Invalid(str(exc)) from exc
    try:
        entries = read_json(index_path) if index_path.exists() else []
        require(isinstance(entries, list), 'Indice de entregas invalido.')
        return _ensure_delivery(
            clip, stage, record, source, delivery_dir, index_path, entries
        )
    finally:
        try:
            release_lock(lock_handle)
        except LockError as lock_error:
            active_error = sys.exception()
            if active_error is not None:
                active_error.add_note(
                    f'Falha adicional ao liberar lock de entregas: {lock_error}'
                )
            else:
                raise Invalid(str(lock_error)) from lock_error


def _ensure_delivery(clip, stage, record, source, delivery_dir, index_path, entries):
    for entry in entries:
        if entry.get('origem') == str(source):
            destination = Path(entry['entrega']).resolve()
            require(
                destination.is_relative_to(delivery_dir),
                'Indice de entregas aponta para fora da pasta autorizada.',
            )
            if not destination.is_file() or digest(destination) != record['sha256']:
                shutil.copy2(source, destination)
            return destination
    used = [int(p.name.split('_', 1)[0]) for p in delivery_dir.iterdir()
            if p.is_file() and p.name.split('_', 1)[0].isdigit()]
    used += [int(e['sequencia']) for e in entries if str(e.get('sequencia', '')).isdigit()]
    sequence = max(used, default=0) + 1
    clip_id = safe_id(clip['plan']['id_clipe'])
    destination = delivery_dir / f'{sequence:06d}_{clip_id}_{stage}{source.suffix.lower()}'
    shutil.copy2(source, destination)
    entries.append({'sequencia': sequence, 'tipo': stage, 'origem': str(source),
                    'entrega': str(destination.resolve())})
    atomic(index_path, entries)
    return destination


def load_clips(production, *, skip_pending=False):
    production = Path(production).resolve()
    summary = read_json(production / 'plano_producao.json')
    response = read_json(production / 'resposta_ia.json')
    revision_hash = signature(response)
    require_sha256(revision_hash, 'sha256 da resposta importada')
    require(
        production.name == revision_hash[:16],
        'Resposta importada alterada; importe uma nova revisao.',
    )
    require(
        summary == response.get('plano_producao'),
        'Plano da producao diverge da resposta importada.',
    )
    response_clips = {
        item.get('plano', {}).get('id_clipe'): item.get('plano')
        for item in response.get('clipes', [])
        if isinstance(item, dict)
    }
    clips, seen = [], set()
    for item in sorted(summary['clipes'], key=lambda x: x['ordem']):
        cid = safe_id(item['id_clipe'])
        require(cid not in seen, 'Clipe duplicado.')
        seen.add(cid)
        folder = inside(production, cid)
        plan = read_json(folder / 'plano_clipe.json')
        require(plan['id_clipe'] == cid and plan['producao_id'] == summary['producao_id'], 'Plano divergente.')
        require(
            response_clips.get(cid) == plan,
            'Plano do clipe diverge da resposta importada.',
        )
        if plan['status'] == 'pendente':
            require(skip_pending, 'Plano pendente ou ordem divergente.')
            continue
        require(plan['status'] == 'pronto', 'Status do plano nao suportado.')
        require(plan['ordem'] == item['ordem'], 'Ordem do plano divergente.')
        flow = read_json(folder / 'insumos_flow.json')
        require_sha256(flow.get('pacote_sha256'), 'pacote_sha256 dos insumos')
        refs = []
        for index, ref in enumerate(flow['referencias'], 1):
            path = inside(folder, ref['arquivo'])
            require(ref['ordem'] == index and digest(path) == ref['sha256'], 'Referencia alterada ou fora de ordem.')
            refs.append(path)
        pipe = plan['pipeline']
        require(pipe['aspecto'] == '9:16', 'Aspecto nao suportado.')
        if pipe['gerar_imagem']:
            require(pipe['metodo_imagem'] == 'i2i' and refs, 'Imagem requer i2i e referencias.')
        if pipe['gerar_video']:
            require(pipe['metodo_video'] in {'i2v', 'r2v'} and pipe['duracao_video_s'] == 8, 'Metodo/duracao nao suportados.')
            require(not pipe['gerar_imagem'] or pipe['aprovacao_necessaria'], 'Frame novo exige aprovacao.')
        prompts = {}
        for stage in ('imagem', 'video'):
            if pipe['gerar_' + stage]:
                prompts[stage] = (folder / ('prompt_' + stage + '.txt')).read_text(encoding='utf-8').strip()
                require(bool(prompts[stage]), 'Prompt vazio.')
        fingerprint = signature({'plano': plan, 'insumos': flow, 'prompts': prompts})
        require_sha256(fingerprint, 'fingerprint da revisao')
        clips.append(dict(
            folder=folder,
            plan=plan,
            flow=flow,
            refs=refs,
            prompts=prompts,
            fingerprint=fingerprint,
            revision_sha256=revision_hash,
        ))
    return clips


def state_for(clip):
    path = clip['folder'] / 'execucao.json'
    state = read_json(path) if path.exists() else {
        'schema_version': EXECUTION_SCHEMA_VERSION,
        'fingerprint': clip['fingerprint'],
    }
    require(isinstance(state, dict), 'Estado de execucao invalido.')
    require(
        state.get('schema_version') in {
            None,
            EXECUTION_SCHEMA_VERSION,
        },
        'Versao do estado de execucao nao suportada.',
    )
    require_sha256(state.get('fingerprint'), 'fingerprint do estado')
    require(state['fingerprint'] == clip['fingerprint'], 'Insumos alterados; importe nova revisao.')
    return state


def media(record, clip=None):
    require(isinstance(record, dict), 'Registro de midia invalido.')
    require_sha256(record.get('sha256'), 'sha256 da midia')
    if record.get('schema_version') is not None:
        require(record.get('schema_version') == MEDIA_SCHEMA_VERSION, 'Versao do registro de midia nao suportada.')
        require_sha256(record.get('revisao_sha256'), 'revisao_sha256 da midia')
        require_sha256(record.get('fingerprint_sha256'), 'fingerprint_sha256 da midia')
        if clip is not None:
            fingerprint, _, response_hash = revision_identity(clip)
            require(
                record['revisao_sha256'] == response_hash
                and record['fingerprint_sha256'] == fingerprint,
                'Midia pertence a outra revisao.',
            )
    path = Path(record['arquivo']).resolve()
    if clip is not None:
        require(
            path.is_relative_to(Path(clip['folder']).resolve()),
            'Midia registrada fora da pasta da revisao.',
        )
    require(path.is_file() and path.stat().st_size > 0 and digest(path) == record['sha256'], 'Midia ausente ou alterada.')
    return path


def existing(clip, key):
    refs = [r for r in clip['flow']['referencias'] if r['ref_id'] == clip['plan'].get(key)]
    require(len(refs) == 1, key + ': ativo deve constar nas referencias exportadas.')
    return inside(clip['folder'], refs[0]['arquivo'])


def row_for(wb, clip):
    matches = [r for r in wb.records() if r['plano_arquivo'] and Path(r['plano_arquivo']).resolve() == clip['folder'] / 'plano_clipe.json']
    require(len(matches) == 1, 'Importe esta revisao com --atualizar-excel antes de executar.')
    row = matches[0]
    require(norm(row['classifica']) == 'sim', 'Linha desativada.')
    require(row['producao_id'] == clip['plan']['producao_id'] and int(row['ordem']) == clip['plan']['ordem'], 'Linha alterada.')
    return row


def sync(
    sheet,
    clip,
    state,
    delivery_dir=None,
    *,
    revoke_unbound_approval=False,
):
    for stage in ('imagem', 'video'):
        if state.get(stage):
            export_delivery(clip, stage, state[stage], delivery_dir)
    wb = Workbook(sheet)
    row = row_for(wb, clip)
    fields = {'atualizado_em': now(), 'erro': ''}
    if state.get('imagem'):
        frame = media(state['imagem'], clip)
        fields.update(
            imagem_status=ImageStatus.GENERATED,
            imagem_arquivo=str(frame),
            status=PipelineStatus.WAITING_APPROVAL,
        )
        if (
            revoke_unbound_approval
            and not approval_is_bound(clip, state.get('aprovacao'), frame)
        ):
            fields['aprovacao'] = ''
    if state.get('video'):
        fields.update(
            video_status=state['video'].get('status', VideoStatus.GENERATED),
            video_arquivo=str(media(state['video'], clip)),
            status=PipelineStatus.COMPLETED,
        )
    for key, value in fields.items():
        wb.set(row['_linha'], key, value)
    wb.save()


def command(clip, stage, binary, project, model, output, frame=None):
    pipe = clip['plan']['pipeline']
    method = pipe['metodo_' + stage]
    cmd = [str(binary), 'image' if stage == 'imagem' else 'video', method]
    if method == 'i2v':
        require(frame is not None, 'Frame inicial ausente.')
        cmd += ['--initial-frame', str(frame)]
    cmd += [clip['prompts'][stage], '--aspect', pipe['aspecto'], '--model', model, '--project', project, '-o', str(output), '--json']
    if method in {'i2i', 'r2v'}:
        require(all(p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'} for p in clip['refs']), 'Referencias devem ser imagens.')
        if method == 'r2v':
            require(
                0 < len(clip['refs']) <= 7,
                'Omni Flash aceita de uma a sete referencias em r2v.',
            )
        for ref in clip['refs']:
            cmd += ['--ref', str(ref)]
    if stage == 'video':
        cmd += ['--duration', str(pipe['duracao_video_s'])]
    return cmd


def acquire_clip_lock(clip, operation):
    fingerprint, package_hash, response_hash = revision_identity(clip)
    return acquire_lock(
        clip['folder'] / '.execucao.lock',
        operation,
        context={
            'producao_id': str(clip['plan']['producao_id']),
            'id_clipe': str(clip['plan']['id_clipe']),
            'revisao_sha256': response_hash,
            'fingerprint_sha256': fingerprint,
            'pacote_sha256': package_hash,
        },
    )


def video_credit_lock_path(args):
    configured = getattr(args, 'credit_lock_path', None)
    if configured is not None:
        return Path(configured).resolve()
    return (
        Path(args.planilha).resolve().parent
        / 'backups'
        / '.video-credit.lock'
    )


def acquire_video_credit_lock(clip, args):
    fingerprint, package_hash, response_hash = revision_identity(clip)
    try:
        return acquire_lock(
            video_credit_lock_path(args),
            'video-pago',
            context={
                'producao_id': str(clip['plan']['producao_id']),
                'id_clipe': str(clip['plan']['id_clipe']),
                'revisao_sha256': response_hash,
                'fingerprint_sha256': fingerprint,
                'pacote_sha256': package_hash,
            },
            recover_stale=False,
        )
    except LockError as exc:
        raise Invalid(
            'Outra geracao paga esta ativa ou requer revisao manual: '
            + str(exc)
        ) from exc


def operation_idempotency_key(clip, stage, model, frame=None):
    fingerprint, package_hash, response_hash = revision_identity(clip)
    payload = {
        'producao_id': str(clip['plan']['producao_id']),
        'id_clipe': str(clip['plan']['id_clipe']),
        'etapa': stage,
        'modelo': model,
        'revisao_sha256': response_hash,
        'fingerprint_sha256': fingerprint,
        'pacote_sha256': package_hash,
        'frame_sha256': digest(frame) if frame is not None else None,
    }
    return signature(payload)


def _attempt_directory(clip, attempt):
    directory = Path(str(attempt.get('diretorio', ''))).resolve()
    folder = Path(clip['folder']).resolve()
    require(
        directory.is_relative_to(folder),
        'Diretorio da tentativa esta fora da pasta do clipe.',
    )
    return directory


def attempt_output_candidates(clip, attempt):
    stage = attempt.get('etapa')
    require(stage in {'imagem', 'video'}, 'Etapa da tentativa invalida.')
    directory = _attempt_directory(clip, attempt)
    extensions = (
        IMAGE_OUTPUT_EXTENSIONS
        if stage == 'imagem'
        else VIDEO_OUTPUT_EXTENSIONS
    )
    candidates = []
    declared = attempt.get('saida')
    if declared:
        declared_path = Path(str(declared)).resolve()
        require(
            declared_path.is_relative_to(directory),
            'Saida da tentativa esta fora do diretorio registrado.',
        )
        if declared_path.is_file():
            candidates.append(declared_path)
    if directory.is_dir():
        candidates.extend(
            path.resolve()
            for path in directory.glob(f'{stage}.*')
            if path.is_file() and path.suffix.lower() in extensions
        )
    return sorted(set(candidates), key=str)


def _attempt_model(attempt, stage):
    if attempt.get('modelo'):
        return str(attempt['modelo'])
    command_items = attempt.get('comando')
    if isinstance(command_items, list) and '--model' in command_items:
        index = command_items.index('--model') + 1
        if index < len(command_items):
            return str(command_items[index])
    return 'nano2' if stage == 'imagem' else 'desconhecido'


def recover_completed_attempt(clip, state, stage, args):
    attempt = state.get('tentativa')
    if not isinstance(attempt, dict):
        return None
    require(
        attempt.get('etapa') == stage,
        'Existe tentativa incompleta de outra etapa; confira execucao.json.',
    )
    model = _attempt_model(attempt, stage)
    frame = None
    pipe = clip['plan']['pipeline']
    if (
        stage == 'video'
        and (
            pipe['metodo_video'] == 'i2v'
            or pipe['aprovacao_necessaria']
        )
    ):
        frame = (
            media(state['imagem'], clip)
            if state.get('imagem')
            else existing(clip, 'frame_existente_ref_id')
        )
    if attempt.get('schema_version') is not None:
        require(
            attempt.get('schema_version') == ATTEMPT_SCHEMA_VERSION
            and attempt.get('revisao_sha256') == clip['revision_sha256']
            and attempt.get('fingerprint_sha256') == clip['fingerprint'],
            'Tentativa pertence a outra revisao.',
        )
        require_sha256(
            attempt.get('idempotency_key'),
            'idempotency_key da tentativa',
        )
        require(
            attempt['idempotency_key']
            == operation_idempotency_key(
                clip,
                stage,
                model,
                frame,
            ),
            'Chave idempotente da tentativa nao corresponde aos insumos atuais.',
        )
    candidates = attempt_output_candidates(clip, attempt)
    if not candidates:
        return None
    require(
        len(candidates) == 1 and candidates[0].stat().st_size > 0,
        'Saida da tentativa ausente ou ambigua; confira o Flow antes de repetir.',
    )
    idempotency_key = attempt.get('idempotency_key') or signature({
        'tentativa_legada': attempt,
        'arquivo': str(candidates[0]),
    })
    state[stage] = media_record(
        clip,
        candidates[0],
        modelo=model,
        em=now(),
        idempotency_key=idempotency_key,
        recuperada=True,
    )
    history_entry = dict(state.pop('tentativa'))
    history_entry.update(
        fim=now(),
        resultado='recuperada_sem_reenvio',
    )
    state.setdefault('historico', []).append(history_entry)
    atomic(clip['folder'] / 'execucao.json', state)
    sync(
        args.planilha,
        clip,
        state,
        getattr(args, 'delivery_dir', None),
        revoke_unbound_approval=stage == 'imagem',
    )
    return 'tentativa recuperada sem nova chamada ao Flow'


def execute(clip, args):
    folder = clip['folder']
    stage = args.acao
    pipe = clip['plan']['pipeline']
    started_at = now()
    event_command = None
    event_method = {
        'registrar-imagem': 'fornecida_pelo_usuario',
        'aprovar': 'vinculo_ao_frame',
    }.get(stage, str(pipe.get('metodo_' + stage, 'nao_aplicavel')))
    credit_lock_handle = None

    def completed(message):
        record_clip_event(
            clip,
            stage=stage,
            method=event_method,
            command=event_command,
            result=message,
            error='',
            started_at=started_at,
            timestamp=now(),
        )
        return message

    try:
        lock_handle = acquire_clip_lock(clip, stage)
    except LockError as exc:
        raise Invalid(str(exc)) from exc
    try:
        state = state_for(clip)
        wb = Workbook(args.planilha)
        row = row_for(wb, clip)
        if stage == 'registrar-imagem':
            source = Path(args.arquivo).resolve()
            require(source.is_file() and source.stat().st_size > 0, 'Imagem fornecida ausente ou vazia.')
            require(source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}, 'Formato de imagem fornecida nao aceito.')
            require(not state.get('video'), 'Video ja registrado; preserve o ativo e importe uma nova revisao para trocar a imagem.')
            run_dir = folder / 'gerados' / ('manual_' + uuid.uuid4().hex)
            run_dir.mkdir(parents=True)
            target = run_dir / ('imagem' + source.suffix.lower())
            shutil.copy2(source, target)
            state['imagem'] = media_record(
                clip,
                target,
                modelo='fornecida_pelo_usuario',
                em=now(),
            )
            state.pop('aprovacao', None)
            state.setdefault('historico', []).append({'etapa': 'registrar-imagem', 'inicio': now(), 'origem': str(source), 'diretorio': str(run_dir)})
            atomic(folder / 'execucao.json', state)
            sync(
                args.planilha,
                clip,
                state,
                getattr(args, 'delivery_dir', None),
                revoke_unbound_approval=True,
            )
            return completed('imagem fornecida registrada; revisar e vincular nova aprovacao')
        if stage == 'aprovar':
            frame = media(state['imagem'], clip) if state.get('imagem') else existing(clip, 'frame_existente_ref_id')
            require(norm(row['aprovacao']) == 'aprovada', 'Revise o frame e marque aprovacao=aprovada no Excel.')
            state['aprovacao'] = approval_record(clip, frame, now())
            atomic(folder / 'execucao.json', state)
            return completed('aprovacao vinculada ao frame')
        if state.get(stage):
            media(state[stage], clip)
            sync(
                args.planilha,
                clip,
                state,
                getattr(args, 'delivery_dir', None),
                revoke_unbound_approval=stage == 'imagem',
            )
            return completed('ja concluido; Excel sincronizado')
        if state.get('tentativa'):
            attempt = state['tentativa']
            require(
                isinstance(attempt, dict),
                'Registro de tentativa invalido; nao reenviar.',
            )
            event_command = attempt.get('comando')
            recovered = recover_completed_attempt(
                clip,
                state,
                stage,
                args,
            )
            if recovered:
                return completed(recovered)
            if attempt.get('status') == 'preparada':
                history_entry = dict(state.pop('tentativa'))
                history_entry.update(
                    fim=now(),
                    resultado='descartada_antes_do_envio',
                )
                state.setdefault('historico', []).append(history_entry)
                atomic(folder / 'execucao.json', state)
            else:
                key = attempt.get('idempotency_key', 'legada')
                raise Invalid(
                    'Tentativa sem conclusao confirmada e sem saida local; '
                    f'nao reenviar. Confira execucao.json, gflow.log e Flow. Chave: {key}.'
                )
        if not pipe['gerar_' + stage]:
            if stage == 'video' and pipe['usar_ativo_existente']:
                require(not clip['plan']['origem_clipe'].get('trecho'), 'Recorte de ativo ainda nao suportado.')
                asset = existing(clip, 'ativo_existente_ref_id')
                require(asset.suffix.lower() in {'.mp4', '.mov', '.webm', '.mkv'}, 'Ativo final nao e video.')
                event_method = 'reutilizar'
                state['video'] = media_record(clip, asset, status=VideoStatus.REUSED)
                atomic(folder / 'execucao.json', state)
                sync(args.planilha, clip, state, getattr(args, 'delivery_dir', None))
                return completed('ativo reutilizado')
            return completed('etapa nao solicitada')
        frame = None
        if stage == 'video':
            require(
                args.modelo_video == 'omni-flash',
                'Este projeto permite somente o modelo de video omni-flash.',
            )
            expected_image_sha256 = getattr(
                args,
                'expected_image_sha256',
                None,
            )
            frame = video_release_frame(
                clip, state, row, expected_image_sha256
            )
        binary = args.gflow_raiz / '.venv/Scripts/gflow.exe'
        require(binary.is_file(), 'gflow.exe nao encontrado.')
        require(args.projeto, 'Informe --projeto com o ID do projeto Flow existente.')
        run_dir = folder / 'gerados' / uuid.uuid4().hex
        output = run_dir / ('imagem.png' if stage == 'imagem' else 'video.mp4')
        model = 'nano2' if stage == 'imagem' else args.modelo_video
        if stage == 'video':
            state = state_for(clip)
            wb = Workbook(args.planilha)
            row = row_for(wb, clip)
            frame = video_release_frame(
                clip, state, row, expected_image_sha256
            )
        idempotency_key = operation_idempotency_key(
            clip,
            stage,
            model,
            frame,
        )
        cmd = command(clip, stage, binary, args.projeto, model, output, frame)
        event_command = cmd
        if stage == 'video':
            credit_lock_handle = acquire_video_credit_lock(clip, args)
        run_dir.mkdir(parents=True)
        state['tentativa'] = {
            'schema_version': ATTEMPT_SCHEMA_VERSION,
            'etapa': stage,
            'status': 'preparada',
            'inicio': now(),
            'comando_sha256': signature(cmd),
            'diretorio': str(run_dir),
            'saida': str(output),
            'modelo': model,
            'idempotency_key': idempotency_key,
            'revisao_sha256': clip['revision_sha256'],
            'fingerprint_sha256': clip['fingerprint'],
        }
        atomic(folder / 'execucao.json', state)
        env = os.environ.copy()
        env['GFLOW_CLI_HOME'] = str(args.gflow_raiz / 'data/flow_gflow')
        env['GFLOW_CLI_FLOW_HOST'] = 'flow.google.com'
        env['GFLOW_CLI_HEADLESS'] = 'false'
        env['GFLOW_CLI_OUTPUT_DIR'] = str(run_dir)
        with (run_dir / 'gflow.log').open('w', encoding='utf-8') as log:
            state['tentativa']['status'] = 'submetida'
            state['tentativa']['submetida_em'] = now()
            atomic(folder / 'execucao.json', state)
            result = subprocess.run(
                cmd,
                cwd=args.gflow_raiz,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=args.timeout,
                shell=False,
            )
        require(result.returncode == 0, f'gflow retornou {result.returncode}; consulte {run_dir}.')
        candidates = attempt_output_candidates(clip, state['tentativa'])
        require(len(candidates) == 1 and candidates[0].stat().st_size > 0, 'Saida ausente/ambigua; confira Flow antes de reenviar.')
        state[stage] = media_record(
            clip,
            candidates[0],
            modelo=model,
            em=now(),
            idempotency_key=idempotency_key,
        )
        history_entry = dict(state.pop('tentativa'))
        history_entry.update(fim=now(), resultado='concluida')
        state.setdefault('historico', []).append(history_entry)
        atomic(folder / 'execucao.json', state)
        sync(
            args.planilha,
            clip,
            state,
            getattr(args, 'delivery_dir', None),
            revoke_unbound_approval=stage == 'imagem',
        )
        return completed('gerado; revisar resultado visualmente')
    except Exception as exc:
        try:
            record_clip_event(
                clip,
                stage=stage,
                method=event_method,
                command=event_command,
                result='erro',
                error=str(exc),
                started_at=started_at,
                timestamp=now(),
            )
        except OSError as log_error:
            exc.add_note(f'Falha adicional ao registrar log operacional: {log_error}')
        raise
    finally:
        release_errors = []
        for handle in (credit_lock_handle, lock_handle):
            if handle is None:
                continue
            try:
                release_lock(handle)
            except LockError as lock_error:
                release_errors.append(lock_error)
        active_error = sys.exception()
        if active_error is not None:
            for release_error in release_errors:
                active_error.add_note(
                    f'Falha adicional ao liberar lock: {release_error}'
                )
        elif release_errors:
            raise Invalid(str(release_errors[0])) from release_errors[0]


def main():
    try:
        config = load_config(ROOT)
    except (OSError, ValueError) as exc:
        print(f'Erro de configuracao: {exc}', file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acao', choices=['listar', 'imagem', 'registrar-imagem', 'aprovar', 'video'])
    parser.add_argument('--producao', required=True, type=Path)
    parser.add_argument('--clipe')
    parser.add_argument('--arquivo', type=Path, help='Imagem fornecida pelo usuario para registrar no clipe.')
    parser.add_argument('--planilha', type=Path, default=config.spreadsheet)
    parser.add_argument('--gflow-raiz', type=Path, default=config.gflow_root)
    parser.add_argument('--projeto', default=config.project_id)
    parser.add_argument('--modelo-video', default=config.video_model, choices=VIDEO_MODELS)
    parser.add_argument('--timeout', type=int, default=config.timeout_seconds)
    parser.add_argument('--entregas', dest='delivery_dir', type=Path, default=config.delivery_dir)
    args = parser.parse_args()
    args.credit_lock_path = (
        config.output_dir / '.locks' / 'video-credit.lock'
    )
    if args.acao == 'registrar-imagem' and (not args.clipe or args.arquivo is None):
        parser.error('registrar-imagem exige --clipe ID_DO_CLIPE e --arquivo CAMINHO_DA_IMAGEM')
    args.gflow_raiz = args.gflow_raiz.resolve()
    args.delivery_dir = args.delivery_dir.resolve()
    try:
        clips = load_clips(args.producao)
        if args.clipe:
            clips = [c for c in clips if c['plan']['id_clipe'] == args.clipe]
        require(bool(clips), 'Nenhum clipe selecionado.')
        for clip in clips:
            result = {'id_clipe': clip['plan']['id_clipe'], 'pipeline': clip['plan']['pipeline'], 'estado': state_for(clip)} if args.acao == 'listar' else {'id_clipe': clip['plan']['id_clipe'], 'resultado': execute(clip, args)}
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (Invalid, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
