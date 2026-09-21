"""Executa automaticamente todas as etapas deterministicas pendentes do pipeline Flow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import shutil
import zipfile
from datetime import datetime
from types import SimpleNamespace

from pipeline_flow.config import VIDEO_MODELS, load_config
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services import gerar_carrossel as carousel
from pipeline_flow.services.preparar_insumos import (
    ROOT,
    Invalid,
    Workbook,
    digest,
    import_response,
    norm,
    prepare,
    read_json,
    signature,
    write_json,
)


def matching_response(package: Path, responses_dir: Path) -> Path | None:
    manifest = read_json(package / "manifesto.json")
    expected = manifest["pacote_sha256"]
    matches = []
    if responses_dir.exists():
        for candidate in responses_dir.rglob("*.json"):
            try:
                if read_json(candidate).get("pacote_sha256") == expected:
                    matches.append(candidate)
            except (OSError, ValueError, TypeError):
                continue
    return max(matches, key=lambda path: path.stat().st_mtime_ns) if matches else None


def active_destination_for(sheet: Path, production_id: str) -> Path | None:
    destinations = set()
    for row in Workbook(sheet).records():
        if norm(row["classifica"]) != "sim" or row["producao_id"] != production_id or not row["plano_arquivo"]:
            continue
        plan = Path(row["plano_arquivo"]).resolve()
        if plan.is_file():
            destinations.add(plan.parent.parent)
    return next(iter(destinations)) if len(destinations) == 1 else None


def package_for_hash(
    production_id: str, package_hash: str, output_dir: Path | None = None
) -> Path | None:
    base = (Path(output_dir).resolve() if output_dir else ROOT / "preparados") / "pacotes" / production_id
    if not base.exists():
        return None
    for candidate in base.iterdir():
        manifest = candidate / "manifesto.json"
        try:
            if manifest.is_file() and read_json(manifest).get("pacote_sha256") == package_hash:
                return candidate
        except (OSError, ValueError):
            continue
    return None


def differs_only_in_approval(
    current_package: Path, active_destination: Path, output_dir: Path | None = None
) -> bool:
    response_file = active_destination / "resposta_ia.json"
    if not response_file.is_file():
        return False
    response = read_json(response_file)
    old_package = package_for_hash(
        response["plano_producao"]["producao_id"], response["pacote_sha256"], output_dir
    )
    if old_package is None:
        return False
    current = read_json(current_package / "manifesto.json")
    old = read_json(old_package / "manifesto.json")

    def comparable(manifest):
        result = []
        for item in manifest["clipes"]:
            entry = dict(item["entrada"])
            entry.pop("aprovacao", None)
            result.append((item["id_clipe"], item["linha"], entry, item.get("anexos")))
        return result

    return current["producao_id"] == old["producao_id"] and comparable(current) == comparable(old)

def imported_destination(response: Path, output_dir: Path | None = None) -> Path:
    data = read_json(response)
    production_id = data["plano_producao"]["producao_id"]
    base = Path(output_dir).resolve() if output_dir else ROOT / "preparados"
    return base / "flow" / production_id / signature(data)[:16]


def destination_is_active(sheet: Path, package: Path, destination: Path) -> bool:
    if not destination.is_dir():
        return False
    manifest = read_json(package / "manifesto.json")
    manifest = read_json(package / "manifesto.json")
    records = {record["_linha"]: record for record in Workbook(sheet).records()}
    for item in manifest["clipes"]:
        row = records.get(item["linha"], {})
        expected = destination / item["id_clipe"] / "plano_clipe.json"
        if not row.get("plano_arquivo") or Path(row["plano_arquivo"]).resolve() != expected.resolve():
            return False
    return True


def active_productions(sheet: Path, blocked_ids: set[str]) -> list[Path]:
    productions = set()
    for row in Workbook(sheet).records():
        if norm(row["classifica"]) != "sim" or not row["plano_arquivo"]:
            continue
        plan = Path(row["plano_arquivo"]).resolve()
        if not plan.is_file():
            continue
        try:
            data = read_json(plan)
        except (OSError, ValueError):
            continue
        if data.get("producao_id") not in blocked_ids:
            productions.add(plan.parent.parent)
    return sorted(productions, key=str)


def supplied_image(row: dict, state: dict) -> Path | None:
    if state.get("imagem") or not row.get("imagem_arquivo"):
        return None
    candidate = Path(row["imagem_arquivo"]).resolve()
    if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return candidate
    return None


def classification_message(package: Path) -> str:
    guide = ROOT / "entradas" / "GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md"
    text = guide.read_text(encoding="utf-8")
    match = re.search(r"## Mensagem pronta para colar no novo chat\s*```text\s*(.*?)\s*```", text, re.S)
    if not match:
        raise Invalid("Mensagem pronta para classificação ausente no guia.")
    message = match.group(1).strip()
    if "Ã" in message:
        message = message.encode("latin1").decode("utf-8")
    manifest = read_json(package / "manifesto.json")
    manifest = read_json(package / "manifesto.json")
    return message + "\n\nPacote real desta classificação (use exatamente este caminho):\n" + str(package) + "\n\nHash pacote_sha256:\n" + manifest["pacote_sha256"] + "\n\nDepois de salvar a resposta, execute novamente rodar_pipeline.py."

def executor_args(args, action: str, supplied: Path | None = None):
    return SimpleNamespace(
        acao=action,
        arquivo=supplied,
        planilha=args.planilha,
        gflow_raiz=args.gflow_raiz,
        projeto=args.projeto,
        modelo_video=args.modelo_video,
        timeout=args.timeout,
        delivery_dir=args.delivery_dir,
        credit_lock_path=args.output_dir / '.locks' / 'video-credit.lock',
    )


def run_clip(clip: dict, args) -> list[dict]:
    events = []
    state = flow.state_for(clip)
    row = flow.row_for(Workbook(args.planilha), clip)
    had_frame_at_start = bool(state.get("imagem")) or bool(clip["plan"].get("frame_existente_ref_id"))

    supplied = supplied_image(row, state)
    if supplied:
        result = flow.execute(clip, executor_args(args, "registrar-imagem", supplied))
        events.append({"etapa": "registrar-imagem", "resultado": result, "arquivo": str(supplied)})
        state = flow.state_for(clip)
    elif clip["plan"]["pipeline"]["gerar_imagem"] and not state.get("imagem"):
        result = flow.execute(clip, executor_args(args, "imagem"))
        events.append({"etapa": "imagem", "resultado": result})
        state = flow.state_for(clip)

    pipe = clip["plan"]["pipeline"]
    frame_available = bool(state.get("imagem")) or bool(clip["plan"].get("frame_existente_ref_id"))
    carousel_plan = clip["plan"].get("carrossel")
    if frame_available and isinstance(carousel_plan, dict) and carousel_plan.get("ativo"):
        state = flow.state_for(clip)
        frame = flow.media(state["imagem"], clip) if state.get("imagem") else flow.existing(clip, "frame_existente_ref_id")
        expected = signature({"imagem": digest(frame), "carrossel": carousel_plan})[:12]
        current = state.get("carrossel", {})
        if expected not in Path(current.get("arquivo", "")).name:
            output = carousel.generate(clip, args.planilha, args.delivery_dir)
            events.append({"etapa": "carrossel", "resultado": "gerado", "arquivo": str(output)})
        else:
            events.append({"etapa": "carrossel", "resultado": "ja concluido"})

    if pipe["aprovacao_necessaria"] and frame_available:
        frame = flow.media(state["imagem"], clip) if state.get("imagem") else flow.existing(clip, "frame_existente_ref_id")
        bound = flow.approval_is_bound(clip, state.get("aprovacao"), frame)
        if norm(row["aprovacao"]) == "aprovada" and not bound and had_frame_at_start:
            result = flow.execute(clip, executor_args(args, "aprovar"))
            events.append({"etapa": "aprovar", "resultado": result})
            state = flow.state_for(clip)
            bound = flow.approval_is_bound(clip, state.get("aprovacao"), frame)
        if not bound:
            events.append({"etapa": "video", "resultado": "aguardando revisao e aprovacao humana da imagem"})
            return events

    if pipe["gerar_video"] and norm(row["aprovacao"]) != "aprovada":
        events.append({"etapa": "video", "resultado": "bloqueado: aprovacao=aprovada nao foi registrada explicitamente"})
        return events

    if not state.get("video") and (pipe["gerar_video"] or pipe["usar_ativo_existente"]):
        result = flow.execute(clip, executor_args(args, "video"))
        events.append({"etapa": "video", "resultado": result})
    elif state.get("video"):
        flow.sync(args.planilha, clip, state)
        events.append({"etapa": "video", "resultado": "ja concluido; Excel sincronizado"})
    return events


def create_ai_bundle(preparation: dict, output_root: Path | None = None) -> dict | None:
    packages = preparation.get("pacotes", [])
    pending = preparation.get("pendencias", [])

    if not packages and not pending:
        return None

    output_root = Path(output_root).resolve() if output_root else ROOT / "preparados"
    output_dir = output_root / "pacotes_ia"
    history_dir = output_dir / "historico"

    output_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    history_zip = history_dir / f"pacote_ia_{timestamp}.zip"
    latest_zip = output_dir / "ULTIMO_PACOTE_IA.zip"

    readme = """PACOTE CONSOLIDADO PARA CLASSIFICACAO POR IA

Este ZIP foi criado automaticamente por rodar_pipeline.py.

Cada pasta de producao contem o pacote real preparado pelo sistema:
- manifesto.json
- CLASSIFICADOR_UNIVERSAL.txt
- CONTRATO_INSUMOS.md
- identidade.txt, quando aplicavel
- anexos reais
- demais arquivos preparados para a classificacao

A IA deve analisar cada producao separadamente.

Cada resposta deve continuar sendo salva separadamente em:
preparados/respostas_ia/

O pacote_sha256 de cada producao deve ser preservado exatamente.

Consulte pendencias.json para producoes/linhas que nao puderam ser
incluidas por arquivos ausentes ou ambiguos.

Nao gerar imagens ou videos durante a classificacao.
"""

    index = {
        "criado_em": timestamp,
        "pacotes": packages,
        "pendencias": pending,
    }

    with zipfile.ZipFile(
        history_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED
    ) as archive:

        archive.writestr(
            "LEIA_PRIMEIRO.txt",
            readme
        )

        archive.writestr(
            "indice.json",
            json.dumps(index, ensure_ascii=False, indent=2)
        )

        archive.writestr(
            "pendencias.json",
            json.dumps(pending, ensure_ascii=False, indent=2)
        )

        for item in packages:
            production_id = item["producao_id"]
            package = Path(item["pacote"]).resolve()

            if not package.is_dir():
                continue

            prefix = f"{production_id}/{package.name}"

            for path in package.rglob("*"):
                if not path.is_file():
                    continue

                relative = path.relative_to(package)

                archive.write(
                    path,
                    arcname=f"{prefix}/{relative.as_posix()}"
                )

            try:
                message = classification_message(package)
                archive.writestr(
                    f"{prefix}/MENSAGEM_CLASSIFICACAO.txt",
                    message
                )
            except (Invalid, OSError, ValueError, KeyError):
                pass

    shutil.copy2(history_zip, latest_zip)

    return {
        "arquivo": str(latest_zip),
        "historico": str(history_zip),
        "quantidade_pacotes": len(packages),
        "quantidade_pendencias": len(pending),
    }




def run(args) -> dict:
    report = {
        "configuracao": {
            "output_dir": str(args.output_dir),
            "responses_dir": str(args.respostas),
            "delivery_dir": str(args.delivery_dir),
        },
        "preparacao": None,
        "pacote_ia": None,
        "importacoes": [],
        "execucoes": [],
        "pendencias": [],
        "erros": []
    }
    blocked_ids = set()

    if not args.sem_preparar:
        preparation = prepare(ROOT, args.planilha, args.fontes, output_dir=args.output_dir)
        report["preparacao"] = preparation
        report["pacote_ia"] = create_ai_bundle(preparation, args.output_dir)
        for item in preparation.get("pacotes", []):
            package = Path(item["pacote"]).resolve()
            response = matching_response(package, args.respostas)
            if response is None:
                active = active_destination_for(args.planilha, item["producao_id"])
                if active is not None and differs_only_in_approval(
                    package, active, args.output_dir
                ):
                    report["importacoes"].append({
                        "producao_id": item["producao_id"],
                        "resultado": "plano importado continua valido; mudou somente a aprovacao",
                        "destino": str(active),
                    })
                    continue
                message = classification_message(package)
                message_dir = args.output_dir / "mensagens_classificacao"
                message_file = message_dir / (item["producao_id"] + "_" + package.name + ".txt")
                message_dir.mkdir(parents=True, exist_ok=True)
                message_file.write_text(message + "\n", encoding="utf-8")
                blocked_ids.add(item["producao_id"])
                report["pendencias"].append({
                    "producao_id": item["producao_id"],
                    "etapa": "classificacao",
                    "motivo": "pacote novo sem resposta_ia correspondente",
                    "pacote": str(package),
                    "mensagem_pronta": message,
                    "arquivo_mensagem": str(message_file),
                })
                continue
            destination = imported_destination(response, args.output_dir)
            if destination_is_active(args.planilha, package, destination):
                report["importacoes"].append({"producao_id": item["producao_id"], "resultado": "revisao ja importada", "destino": str(destination)})
                continue
            try:
                imported = import_response(
                    ROOT, package, response, update_excel=True, output_dir=args.output_dir
                )
                report["importacoes"].append({"producao_id": item["producao_id"], **imported})
                if imported.get("erro_excel"):
                    blocked_ids.add(item["producao_id"])
                    report["erros"].append({"producao_id": item["producao_id"], "erro": imported["erro_excel"]})
            except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
                blocked_ids.add(item["producao_id"])
                report["erros"].append({"producao_id": item["producao_id"], "erro": str(exc)})

    for production in active_productions(args.planilha, blocked_ids):
        try:
            clips = flow.load_clips(production)
        except (Invalid, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            report["erros"].append({"producao": str(production), "erro": str(exc)})
            continue
        for clip in clips:
            clip_id = clip["plan"]["id_clipe"]
            try:
                events = run_clip(clip, args)
                report["execucoes"].append({"producao": str(production), "id_clipe": clip_id, "eventos": events})
            except (Invalid, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
                report["erros"].append({"producao": str(production), "id_clipe": clip_id, "erro": str(exc)})

    write_json(args.output_dir / "ultima_execucao_automatica.json", report)
    return report

def human_next_action(report: dict) -> str:
    lines = [
        "",
        "=" * 72,
        "PRÓXIMA AÇÃO",
        "=" * 72,
    ]

    preparation = report.get("preparacao") or {}
    preparation_pending = preparation.get("pendencias", [])
    classification_pending = [
        item
        for item in report.get("pendencias", [])
        if item.get("etapa") == "classificacao"
    ]
    errors = report.get("erros", [])

    approval_pending = []

    for execution in report.get("execucoes", []):
        clip_id = execution.get("id_clipe", "")

        for event in execution.get("eventos", []):
            result = str(event.get("resultado", "")).lower()

            if (
                "aguardando revisao" in result
                or "aprovacao=aprovada" in result
                or "aprovação=aprovada" in result
            ):
                approval_pending.append(clip_id)

    # 1. Erros reais têm prioridade.
    if errors:
        lines.append("CORRIJA OS ERROS DO PIPELINE ANTES DE CONTINUAR.")
        lines.append("")

        for item in errors[:10]:
            production = item.get("producao_id") or item.get("producao") or ""
            error = item.get("erro", "")
            lines.append(f"- {production}: {error}")

        if len(errors) > 10:
            lines.append(f"- ... e mais {len(errors) - 10} erro(s).")

        return "\n".join(lines)

    # 2. Existe pacote aguardando classificação pela IA.
    if classification_pending:
        lines.append("ENVIE O PACOTE ABAIXO PARA A IA:")
        lines.append("")
        lines.append(
            r".\preparados\pacotes_ia\ULTIMO_PACOTE_IA.zip"
        )
        lines.append("")
        lines.append(
            "Peça para a IA analisar os pacotes prontos, examinar os anexos "
            "e gerar uma resposta_ia.json para cada produção/revisão."
        )
        lines.append("")
        lines.append(
            r"Depois salve as respostas em .\preparados\respostas_ia"
        )
        lines.append("")
        lines.append("E rode novamente:")
        lines.append("")
        lines.append(r"python .\scripts\rodar_pipeline.py")

        # Produções que ainda não puderam entrar no pacote.
        if preparation_pending:
            grouped = {}

            for item in preparation_pending:
                production = item.get("producao_id", "sem_producao")
                grouped.setdefault(production, []).append(item)

            lines.append("")
            lines.append("ATENÇÃO: também existem produções incompletas:")

            for production, items in grouped.items():
                lines.append(
                    f"- {production}: {len(items)} arquivo(s) "
                    "ausente(s) ou ambíguo(s)."
                )

            lines.append("")
            lines.append(
                "Essas pendências também estão registradas em pendencias.json "
                "dentro do ZIP."
            )

        return "\n".join(lines)

    # 3. Não depende da IA, mas existem arquivos faltando.
    if preparation_pending:
        lines.append("CORRIJA OS ARQUIVOS AUSENTES OU AMBÍGUOS:")
        lines.append("")

        grouped = {}

        for item in preparation_pending:
            production = item.get("producao_id", "sem_producao")
            grouped.setdefault(production, []).append(item)

        for production, items in grouped.items():
            lines.append(f"- {production}: {len(items)} pendência(s)")

            for item in items[:3]:
                lines.append(
                    f"    linha {item.get('linha')}: {item.get('erro')}"
                )

            if len(items) > 3:
                lines.append(
                    f"    ... e mais {len(items) - 3} pendência(s)."
                )

        lines.append("")
        lines.append("Depois rode novamente o pipeline.")

        return "\n".join(lines)

    # 4. Imagens aguardando decisão humana para vídeo.
    if approval_pending:
        unique = sorted(set(approval_pending))

        lines.append("REVISE AS IMAGENS GERADAS.")
        lines.append("")
        lines.append(
            "Se estiverem corretas e você quiser liberar o vídeo, "
            "marque aprovacao=aprovada no Excel para:"
        )

        for clip_id in unique:
            lines.append(f"- {clip_id}")

        lines.append("")
        lines.append("Depois salve o Excel e rode novamente o pipeline.")

        return "\n".join(lines)

    # 5. Nada pendente.
    lines.append("NENHUMA AÇÃO HUMANA PENDENTE.")
    lines.append("O pipeline terminou sem pendências conhecidas.")

    return "\n".join(lines)

def main(prog: str | None = None) -> int:
    try:
        config = load_config(ROOT)
    except (OSError, ValueError) as exc:
        print(json.dumps({'erro': f'configuracao invalida: {exc}'}, ensure_ascii=True), file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument("--planilha", type=Path, default=config.spreadsheet)
    parser.add_argument("--saida", dest="output_dir", type=Path, default=config.output_dir)
    parser.add_argument("--respostas", type=Path)
    parser.add_argument("--entregas", dest="delivery_dir", type=Path, default=config.delivery_dir)
    parser.add_argument("--fontes", nargs="+", type=Path, default=[ROOT / "entradas", ROOT / "referencia_gflow_original" / "Fila Flow"])
    parser.add_argument("--sem-preparar", action="store_true", help="Executa somente revisoes ja importadas.")
    parser.add_argument("--gflow-raiz", type=Path, default=config.gflow_root)
    parser.add_argument("--projeto", default=config.project_id)
    parser.add_argument("--modelo-video", default=config.video_model, choices=VIDEO_MODELS)
    parser.add_argument("--timeout", type=int, default=config.timeout_seconds)
    args = parser.parse_args()
    args.planilha = args.planilha.resolve()
    args.output_dir = args.output_dir.resolve()
    args.respostas = (
        args.respostas.resolve()
        if args.respostas is not None
        else args.output_dir / "respostas_ia"
    )
    args.delivery_dir = args.delivery_dir.resolve()
    args.gflow_raiz = args.gflow_raiz.resolve()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        print(human_next_action(result))
        return 2 if result["erros"] else 0
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"erro": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
