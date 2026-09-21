'''Lista ou gera todas as imagens pendentes das revisoes ativas.'''

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from pipeline_flow.config import load_config
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services.preparar_insumos import ROOT, Invalid, Workbook, norm


def active_productions(sheet: Path) -> list[Path]:
    productions: set[Path] = set()
    for row in Workbook(sheet).records():
        if norm(row['classifica']) != 'sim' or not row['plano_arquivo']:
            continue
        plan = Path(row['plano_arquivo']).resolve()
        if plan.is_file():
            productions.add(plan.parent.parent)
    return sorted(productions, key=str)


def executor_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        acao='imagem',
        planilha=args.planilha,
        gflow_raiz=args.gflow_raiz,
        projeto=args.projeto,
        modelo_video='omni-flash',
        timeout=args.timeout,
        delivery_dir=args.delivery_dir,
        credit_lock_path=args.output_dir / '.locks' / 'video-credit.lock',
    )


def run(args: argparse.Namespace) -> dict:
    productions = (
        [args.producao.resolve()]
        if args.producao is not None
        else active_productions(args.planilha)
    )
    report = {
        'modo': 'executar' if args.executar else 'simular',
        'producoes': [],
        'pendentes': 0,
        'geradas': 0,
        'ja_concluidas': 0,
        'ignoradas': 0,
        'erros': [],
    }

    selected_clip = args.clipe
    for production in productions:
        production_entry = {'producao': str(production), 'clipes': []}
        report['producoes'].append(production_entry)
        try:
            clips = flow.load_clips(production)
        except (Invalid, OSError, ValueError, KeyError) as exc:
            report['erros'].append(
                {'producao': str(production), 'erro': str(exc)}
            )
            continue

        if selected_clip:
            clips = [
                clip for clip in clips
                if clip['plan']['id_clipe'] == selected_clip
            ]

        for clip in clips:
            clip_id = clip['plan']['id_clipe']
            pipe = clip['plan']['pipeline']
            state = flow.state_for(clip)

            if not pipe['gerar_imagem']:
                report['ignoradas'] += 1
                production_entry['clipes'].append({
                    'id_clipe': clip_id,
                    'resultado': 'imagem nao solicitada no plano',
                })
                continue
            if state.get('imagem'):
                report['ja_concluidas'] += 1
                production_entry['clipes'].append({
                    'id_clipe': clip_id,
                    'resultado': 'imagem ja concluida',
                })
                continue

            report['pendentes'] += 1
            if not args.executar:
                production_entry['clipes'].append({
                    'id_clipe': clip_id,
                    'resultado': 'imagem pendente',
                })
                continue

            try:
                result = flow.execute(clip, executor_args(args))
                report['geradas'] += 1
                production_entry['clipes'].append({
                    'id_clipe': clip_id,
                    'resultado': result,
                })
            except (
                Invalid,
                OSError,
                ValueError,
                KeyError,
                subprocess.TimeoutExpired,
            ) as exc:
                report['erros'].append({
                    'producao': str(production),
                    'id_clipe': clip_id,
                    'erro': str(exc),
                })
                production_entry['clipes'].append({
                    'id_clipe': clip_id,
                    'resultado': 'erro',
                    'erro': str(exc),
                })

    if selected_clip and not any(
        item['clipes'] for item in report['producoes']
    ):
        report['erros'].append({
            'id_clipe': selected_clip,
            'erro': 'clipe nao encontrado',
        })
    return report


def main(prog: str | None = None) -> int:
    try:
        config = load_config(ROOT)
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {'erro': f'configuracao invalida: {exc}'},
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument('--planilha', type=Path, default=config.spreadsheet)
    parser.add_argument(
        '--saida', dest='output_dir', type=Path, default=config.output_dir
    )
    parser.add_argument(
        '--entregas',
        dest='delivery_dir',
        type=Path,
        default=config.delivery_dir,
    )
    parser.add_argument('--gflow-raiz', type=Path, default=config.gflow_root)
    parser.add_argument('--projeto', default=config.project_id)
    parser.add_argument('--timeout', type=int, default=config.timeout_seconds)
    parser.add_argument(
        '--producao', type=Path, help='Limita a uma revisao importada.'
    )
    parser.add_argument('--clipe', help='Limita a um ID de clipe.' )
    parser.add_argument(
        '--executar',
        action='store_true',
        help='Confirma chamadas ao Flow. Sem esta opcao, apenas simula.' ,
    )
    args = parser.parse_args()
    args.planilha = args.planilha.resolve()
    args.output_dir = args.output_dir.resolve()
    args.delivery_dir = args.delivery_dir.resolve()
    args.gflow_raiz = args.gflow_raiz.resolve()

    try:
        report = run(args)
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps({'erro': str(exc)}, ensure_ascii=True),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 2 if report['erros'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
