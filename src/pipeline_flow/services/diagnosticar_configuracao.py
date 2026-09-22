"""Diagnostica a configuracao local sem gerar midia ou alterar arquivos."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from pipeline_flow.config import PipelineConfig, load_config
from pipeline_flow.services.preparar_insumos import ROOT, Workbook

MINIMUM_PYTHON = (3, 11)
DEPENDENCIES = (
    ("fastapi", "fastapi", True),
    ("Pillow", "PIL", True),
    ("uvicorn", "uvicorn", True),
    ("openpyxl", "openpyxl", False),
)


def _check(
    checks: list[dict],
    identifier: str,
    status: str,
    message: str,
    scope: str = "local",
) -> None:
    checks.append(
        {
            "id": identifier,
            "status": status,
            "escopo": scope,
            "mensagem": message,
        }
    )


def _available_directory(path: Path, access: Callable[[Path, int], bool]) -> tuple[bool, Path]:
    candidate = path if path.exists() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate.is_dir() and access(candidate, os.W_OK), candidate


def _configuration_summary(config: PipelineConfig | None) -> dict:
    if config is None:
        return {}
    return {
        "planilha": str(config.spreadsheet),
        "saida": str(config.output_dir),
        "entregas": str(config.delivery_dir),
        "gflow_raiz": str(config.gflow_root),
        "projeto_configurado": bool(config.project_id),
        "modelo_video": config.video_model,
        "timeout_segundos": config.timeout_seconds,
        "web": f"{config.web_host}:{config.web_port}",
    }


def _finish(checks: list[dict], config: PipelineConfig | None) -> dict:
    local_ready = not any(
        item["status"] == "erro" and item["escopo"] == "local"
        for item in checks
    )
    flow_ready = local_ready and all(
        item["status"] == "ok"
        for item in checks
        if item["escopo"] == "flow"
    )
    if not local_ready:
        status = "erro"
    elif any(item["status"] == "aviso" for item in checks):
        status = "atencao"
    else:
        status = "pronto"
    return {
        "status": status,
        "somente_leitura": True,
        "pipeline_local_pronto": local_ready,
        "geracao_flow_pronta": flow_ready,
        "configuracao": _configuration_summary(config),
        "verificacoes": checks,
    }


def diagnose(
    root: Path,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
    module_available: Callable[[str], bool] | None = None,
    python_version: tuple[int, int, int] | None = None,
    os_name: str | None = None,
    access: Callable[[Path, int], bool] | None = None,
) -> dict:
    """Return a side-effect-free report for local and Flow readiness."""
    root = Path(root).resolve()
    checks: list[dict] = []
    module_available = module_available or (
        lambda name: importlib.util.find_spec(name) is not None
    )
    python_version = python_version or tuple(sys.version_info[:3])
    os_name = os_name or os.name
    access = access or os.access

    version_text = ".".join(str(part) for part in python_version)
    if python_version[:2] >= MINIMUM_PYTHON:
        _check(checks, "python", "ok", f"Python {version_text} atende ao minimo 3.11.")
    else:
        _check(checks, "python", "erro", f"Python {version_text} e anterior ao minimo 3.11.")

    if os_name == "nt":
        _check(checks, "sistema", "ok", "Windows detectado.")
    else:
        _check(
            checks,
            "sistema",
            "aviso",
            "O fluxo completo e suportado oficialmente em Windows.",
        )

    env_path = Path(dotenv_path) if dotenv_path is not None else root / ".env"
    if not env_path.is_absolute():
        env_path = root / env_path
    env_path = env_path.resolve()
    if env_path.is_file():
        _check(checks, "env", "ok", f"Arquivo .env encontrado em {env_path}.")
    else:
        _check(
            checks,
            "env",
            "aviso",
            f"Arquivo .env ausente em {env_path}; padroes seguros serao usados.",
        )

    for package, module, required in DEPENDENCIES:
        if module_available(module):
            _check(checks, f"dependencia_{module}", "ok", f"Dependencia {package} disponivel.")
        else:
            _check(
                checks,
                f"dependencia_{module}",
                "erro" if required else "aviso",
                (
                    f"Dependencia {package} ausente."
                    + (" Instale o projeto novamente." if required else " Instale o extra dev.")
                ),
            )

    try:
        config = load_config(root, environ=environ, dotenv_path=env_path)
    except (OSError, ValueError) as exc:
        _check(checks, "configuracao", "erro", f"Configuracao invalida: {exc}")
        return _finish(checks, None)

    _check(checks, "configuracao", "ok", "Configuracao carregada sem executar o pipeline.")

    if not config.spreadsheet.is_file():
        _check(
            checks,
            "planilha",
            "erro",
            f"Planilha operacional nao encontrada em {config.spreadsheet}.",
        )
    else:
        try:
            Workbook(config.spreadsheet, allow_legacy=True)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            _check(checks, "planilha", "erro", f"Planilha operacional invalida: {exc}")
        else:
            _check(
                checks,
                "planilha",
                "ok",
                f"Planilha operacional valida em {config.spreadsheet}.",
            )

    directories = (
        ("pasta_planilha", config.spreadsheet.parent, "pasta da planilha"),
        ("pasta_saida", config.output_dir, "pasta de preparados"),
        ("pasta_entregas", config.delivery_dir, "pasta de entregas"),
    )
    for identifier, path, label in directories:
        writable, checked = _available_directory(path, access)
        if writable:
            suffix = "" if path.exists() else f"; criacao depende de {checked}"
            _check(checks, identifier, "ok", f"{label.capitalize()} gravavel{suffix}.")
        else:
            _check(
                checks,
                identifier,
                "erro",
                f"{label.capitalize()} sem permissao de escrita aparente: {path}.",
            )

    if config.project_id:
        _check(
            checks,
            "projeto_flow",
            "ok",
            "Projeto Flow configurado; o identificador nao e exibido.",
            "flow",
        )
    else:
        _check(
            checks,
            "projeto_flow",
            "aviso",
            "GFLOW_PROJECT_ID ausente; geracao externa indisponivel.",
            "flow",
        )

    binary = config.gflow_root / ".venv" / "Scripts" / "gflow.exe"
    if binary.is_file():
        _check(checks, "gflow", "ok", f"gflow.exe encontrado em {binary}.", "flow")
    else:
        _check(
            checks,
            "gflow",
            "aviso",
            f"gflow.exe nao encontrado em {binary}; geracao externa indisponivel.",
            "flow",
        )

    if config.video_model == "omni-flash":
        _check(checks, "modelo_video", "ok", "Modelo de video definido como omni-flash.", "flow")
    else:
        _check(checks, "modelo_video", "erro", "Modelo de video invalido.", "flow")

    return _finish(checks, config)


def human_report(report: dict) -> str:
    labels = {"ok": "OK", "aviso": "AVISO", "erro": "ERRO"}
    lines = ["DIAGNOSTICO SEGURO DO PIPELINE", ""]
    for item in report["verificacoes"]:
        lines.append(f"[{labels[item['status']]}] {item['mensagem']}")
    lines.extend(
        [
            "",
            (
                "Pipeline local: PRONTO"
                if report["pipeline_local_pronto"]
                else "Pipeline local: CORRIGIR ERROS"
            ),
            (
                "Geracao no Flow: PRONTA"
                if report["geracao_flow_pronta"]
                else "Geracao no Flow: INDISPONIVEL"
            ),
            "Nenhuma midia foi gerada e nenhum comando externo foi executado.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=ROOT)
    parser.add_argument("--env", dest="dotenv_path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = diagnose(args.raiz, dotenv_path=args.dotenv_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(human_report(report))
    return 0 if report["pipeline_local_pronto"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
