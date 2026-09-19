'''Serviços de aplicação para compor a configuração do pipeline.'''

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from pipeline_flow.adapters import (
    environment,
    legacy_gflow_root,
    read_dotenv,
    resolve_path,
)
from pipeline_flow.domain import PipelineConfig, positive_int, video_model


def _first(sources: tuple[Mapping[str, str], ...], *names: str) -> str:
    for source in sources:
        for name in names:
            value = source.get(name)
            if value is not None and str(value).strip():
                return str(value).strip()
    return ''


def load_config(
    root: Path,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> PipelineConfig:
    '''Carrega processo > .env > padrões seguros; a CLI sobrescreve depois.'''
    root = Path(root).resolve()
    sources = (
        environment(environ),
        read_dotenv(dotenv_path or root / '.env'),
    )

    gflow_value = _first(sources, 'GFLOW_ROOT')
    gflow_root = (
        resolve_path(gflow_value, root, root.parent / 'gflow-videos')
        if gflow_value
        else legacy_gflow_root(_first(sources, 'GFLOW_CLI_HOME'), root)
    )

    return PipelineConfig(
        root=root,
        spreadsheet=resolve_path(
            _first(sources, 'PIPELINE_SPREADSHEET'),
            root,
            root / 'entradas' / 'controle_pipeline_flow.xlsx',
        ),
        output_dir=resolve_path(
            _first(sources, 'PIPELINE_OUTPUT_DIR'),
            root,
            root / 'preparados',
        ),
        delivery_dir=resolve_path(
            _first(sources, 'PIPELINE_DELIVERY_DIR'),
            root,
            root / 'entregas_flow',
        ),
        gflow_root=gflow_root,
        project_id=_first(
            sources,
            'GFLOW_PROJECT_ID',
            'GFLOW_CLI_DEFAULT_PROJECT',
        ),
        video_model=video_model(_first(sources, 'GFLOW_VIDEO_MODEL')),
        timeout_seconds=positive_int(
            _first(sources, 'GFLOW_TIMEOUT_SECONDS'),
            1800,
            'GFLOW_TIMEOUT_SECONDS',
        ),
        web_host=_first(sources, 'WEB_HOST') or '127.0.0.1',
        web_port=positive_int(_first(sources, 'WEB_PORT'), 8765, 'WEB_PORT'),
    )
