"""Executa insumos importados no ambiente gflow existente."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from preparar_insumos import ROOT, Workbook, Invalid, digest, inside, norm, now, read_json, require, safe_id, signature, write_json


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    write_json(temporary, value)
    os.replace(temporary, path)


def export_delivery(clip, stage, record):
    if stage == 'imagem' and record.get('modelo') == 'fornecida_pelo_usuario':
        return None
    if stage == 'video' and record.get('status') == 'reutilizado':
        return None
    source = media(record).resolve()
    delivery_dir = ROOT / 'entregas_flow'
    index_path = delivery_dir / 'indice_entregas.json'
    delivery_dir.mkdir(parents=True, exist_ok=True)
    entries = read_json(index_path) if index_path.exists() else []
    require(isinstance(entries, list), 'Indice de entregas invalido.')
    return _ensure_delivery(clip, stage, record, source, delivery_dir, index_path, entries)


def _ensure_delivery(clip, stage, record, source, delivery_dir, index_path, entries):
    for entry in entries:
        if entry.get('origem') == str(source):
            destination = Path(entry['entrega'])
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


def load_clips(production):
    production = Path(production).resolve()
    summary = read_json(production / 'plano_producao.json')
    clips, seen = [], set()
    for item in sorted(summary['clipes'], key=lambda x: x['ordem']):
        cid = safe_id(item['id_clipe'])
        require(cid not in seen, 'Clipe duplicado.')
        seen.add(cid)
        folder = inside(production, cid)
        plan = read_json(folder / 'plano_clipe.json')
        require(plan['id_clipe'] == cid and plan['producao_id'] == summary['producao_id'], 'Plano divergente.')
        require(plan['status'] == 'pronto' and plan['ordem'] == item['ordem'], 'Plano pendente ou ordem divergente.')
        flow = read_json(folder / 'insumos_flow.json')
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
        clips.append(dict(folder=folder, plan=plan, flow=flow, refs=refs, prompts=prompts, fingerprint=fingerprint))
    return clips


def state_for(clip):
    path = clip['folder'] / 'execucao.json'
    state = read_json(path) if path.exists() else {'fingerprint': clip['fingerprint']}
    require(state['fingerprint'] == clip['fingerprint'], 'Insumos alterados; importe nova revisao.')
    return state


def media(record):
    path = Path(record['arquivo'])
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


def sync(sheet, clip, state):
    for stage in ('imagem', 'video'):
        if state.get(stage):
            export_delivery(clip, stage, state[stage])
    wb = Workbook(sheet)
    row = row_for(wb, clip)
    fields = {'atualizado_em': now(), 'erro': ''}
    if state.get('imagem'):
        fields.update(imagem_status='gerada', imagem_arquivo=str(media(state['imagem'])), status='aguardando_aprovacao')
    if state.get('video'):
        fields.update(video_status=state['video'].get('status', 'gerado'), video_arquivo=str(media(state['video'])), status='concluido')
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
            cap = 7 if model == 'omni-flash' else 0 if model == 'veo-quality' else 3
            require(0 < len(clip['refs']) <= cap, 'Referencias incompativeis com modelo r2v.')
        for ref in clip['refs']:
            cmd += ['--ref', str(ref)]
    if stage == 'video':
        cmd += ['--duration', str(pipe['duracao_video_s'])]
    return cmd


def execute(clip, args):
    folder = clip['folder']
    lock = folder / '.execucao.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise Invalid('Execucao bloqueada; confira o processo antes de remover .execucao.lock.')
    os.close(fd)
    try:
        state = state_for(clip)
        wb = Workbook(args.planilha)
        row = row_for(wb, clip)
        stage, pipe = args.acao, clip['plan']['pipeline']
        if stage == 'registrar-imagem':
            source = Path(args.arquivo).resolve()
            require(source.is_file() and source.stat().st_size > 0, 'Imagem fornecida ausente ou vazia.')
            require(source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}, 'Formato de imagem fornecida nao aceito.')
            require(not state.get('video'), 'Video ja registrado; preserve o ativo e importe uma nova revisao para trocar a imagem.')
            run_dir = folder / 'gerados' / ('manual_' + uuid.uuid4().hex)
            run_dir.mkdir(parents=True)
            target = run_dir / ('imagem' + source.suffix.lower())
            shutil.copy2(source, target)
            state['imagem'] = {'arquivo': str(target), 'sha256': digest(target), 'modelo': 'fornecida_pelo_usuario', 'em': now()}
            state.pop('aprovacao', None)
            state.setdefault('historico', []).append({'etapa': 'registrar-imagem', 'inicio': now(), 'origem': str(source), 'diretorio': str(run_dir)})
            atomic(folder / 'execucao.json', state)
            sync(args.planilha, clip, state)
            return 'imagem fornecida registrada; revisar e vincular nova aprovacao'
        if stage == 'aprovar':
            frame = media(state['imagem']) if state.get('imagem') else existing(clip, 'frame_existente_ref_id')
            require(norm(row['aprovacao']) == 'aprovada', 'Revise o frame e marque aprovacao=aprovada no Excel.')
            state['aprovacao'] = {'sha256': digest(frame), 'arquivo': str(frame), 'em': now()}
            atomic(folder / 'execucao.json', state)
            return 'aprovacao vinculada ao frame'
        if state.get(stage):
            media(state[stage])
            sync(args.planilha, clip, state)
            return 'ja concluido; Excel sincronizado'
        require(not state.get('tentativa'), 'Tentativa sem conclusao confirmada. Confira execucao.json, log e Flow antes de repetir.')
        if not pipe['gerar_' + stage]:
            if stage == 'video' and pipe['usar_ativo_existente']:
                require(not clip['plan']['origem_clipe'].get('trecho'), 'Recorte de ativo ainda nao suportado.')
                asset = existing(clip, 'ativo_existente_ref_id')
                require(asset.suffix.lower() in {'.mp4', '.mov', '.webm', '.mkv'}, 'Ativo final nao e video.')
                state['video'] = {'arquivo': str(asset), 'sha256': digest(asset), 'status': 'reutilizado'}
                atomic(folder / 'execucao.json', state)
                sync(args.planilha, clip, state)
                return 'ativo reutilizado'
            return 'etapa nao solicitada'
        frame = None
        if stage == 'video':
            if pipe['metodo_video'] == 'i2v' or pipe['aprovacao_necessaria']:
                frame = media(state['imagem']) if state.get('imagem') else existing(clip, 'frame_existente_ref_id')
            if pipe['aprovacao_necessaria']:
                approval = state.get('aprovacao', {})
                require(norm(row['aprovacao']) == 'aprovada' and approval.get('sha256') == digest(frame) and approval.get('arquivo') == str(frame), 'Aprovacao ausente/revogada ou frame alterado; execute aprovar apos revisao.')
        binary = args.gflow_raiz / '.venv/Scripts/gflow.exe'
        require(binary.is_file(), 'gflow.exe nao encontrado.')
        require(args.projeto, 'Informe --projeto com o ID do projeto Flow existente.')
        run_dir = folder / 'gerados' / uuid.uuid4().hex
        output = run_dir / ('imagem.png' if stage == 'imagem' else 'video.mp4')
        model = 'nano2' if stage == 'imagem' else args.modelo_video
        cmd = command(clip, stage, binary, args.projeto, model, output, frame)
        run_dir.mkdir(parents=True)
        state['tentativa'] = {'etapa': stage, 'inicio': now(), 'comando': cmd, 'diretorio': str(run_dir)}
        atomic(folder / 'execucao.json', state)
        env = os.environ.copy()
        env['GFLOW_CLI_HOME'] = str(args.gflow_raiz / 'data/flow_gflow')
        env['GFLOW_CLI_FLOW_HOST'] = 'flow.google.com'
        env['GFLOW_CLI_HEADLESS'] = 'false'
        env['GFLOW_CLI_OUTPUT_DIR'] = str(run_dir)
        with (run_dir / 'gflow.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(cmd, cwd=args.gflow_raiz, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        require(result.returncode == 0, f'gflow retornou {result.returncode}; consulte {run_dir}.')
        candidates = [output] if output.is_file() else [p for p in run_dir.glob('imagem.*') if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}]
        require(len(candidates) == 1 and candidates[0].stat().st_size > 0, 'Saida ausente/ambigua; confira Flow antes de reenviar.')
        state[stage] = {'arquivo': str(candidates[0]), 'sha256': digest(candidates[0]), 'modelo': model, 'em': now()}
        state.setdefault('historico', []).append(state.pop('tentativa'))
        atomic(folder / 'execucao.json', state)
        sync(args.planilha, clip, state)
        return 'gerado; revisar resultado visualmente'
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acao', choices=['listar', 'imagem', 'registrar-imagem', 'aprovar', 'video'])
    parser.add_argument('--producao', required=True, type=Path)
    parser.add_argument('--clipe')
    parser.add_argument('--arquivo', type=Path, help='Imagem fornecida pelo usuario para registrar no clipe.')
    parser.add_argument('--planilha', type=Path, default=ROOT / 'entradas/controle_pipeline_flow.xlsx')
    parser.add_argument('--gflow-raiz', type=Path, default=ROOT.parent / 'gflow-videos')
    parser.add_argument('--projeto', default=os.environ.get('GFLOW_CLI_DEFAULT_PROJECT', ''))
    parser.add_argument('--modelo-video', default='veo-fast', choices=['veo-fast', 'veo-lite', 'veo-quality', 'omni-flash', 'veo-lite-lp'])
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    if args.acao == 'registrar-imagem' and (not args.clipe or args.arquivo is None):
        parser.error('registrar-imagem exige --clipe ID_DO_CLIPE e --arquivo CAMINHO_DA_IMAGEM')
    args.gflow_raiz = args.gflow_raiz.resolve()
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


