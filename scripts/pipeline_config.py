'''Configuração centralizada e carregamento conservador de arquivos .env.'''
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Mapping

VIDEO_MODELS = ('veo-fast', 'veo-lite', 'veo-quality', 'omni-flash', 'veo-lite-lp')
_ENV_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class ConfigError(ValueError):
    '''Configuração inválida ou ambígua.'''


@dataclass(frozen=True)
class PipelineConfig:
    root: Path
    spreadsheet: Path
    output_dir: Path
    delivery_dir: Path
    gflow_root: Path
    project_id: str
    video_model: str
    timeout_seconds: int
    web_host: str
    web_port: int

    @property
    def responses_dir(self) -> Path:
        return self.output_dir / 'respostas_ia'


def read_dotenv(path: Path) -> dict[str, str]:
    '''Lê KEY=VALUE sem interpolação, execução ou alteração de os.environ.'''
    path = Path(path)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        if '=' not in line:
            raise ConfigError(f'{path}:{line_number}: esperado NOME=VALOR.')
        name, value = line.split('=', 1)
        name = name.strip()
        if not _ENV_NAME.fullmatch(name):
            raise ConfigError(f'{path}:{line_number}: nome de variável inválido.')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in (chr(39), chr(34)):
            value = value[1:-1]
        values[name] = value
    return values


def _first(sources: tuple[Mapping[str, str], ...], *names: str) -> str:
    for source in sources:
        for name in names:
            value = source.get(name)
            if value is not None and str(value).strip():
                return str(value).strip()
    return ''


def _path(value: str, root: Path, default: Path) -> Path:
    candidate = Path(value).expanduser() if value else default
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _positive_int(value: str, default: int, name: str) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f'{name} deve ser um inteiro positivo.') from exc
    if parsed <= 0:
        raise ConfigError(f'{name} deve ser um inteiro positivo.')
    return parsed


def load_config(
    root: Path,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> PipelineConfig:
    '''Carrega processo > .env > padrões seguros; a CLI sobrescreve depois.'''
    root = Path(root).resolve()
    process = os.environ if environ is None else environ
    dotenv = read_dotenv(dotenv_path or root / '.env')
    sources = (process, dotenv)

    gflow_value = _first(sources, 'GFLOW_ROOT')
    if gflow_value:
        gflow_root = _path(gflow_value, root, root.parent / 'gflow-videos')
    else:
        cli_home = _first(sources, 'GFLOW_CLI_HOME')
        cli_home_path = _path(cli_home, root, root / 'unused') if cli_home else None
        gflow_root = (
            cli_home_path.parents[1]
            if cli_home_path is not None and len(cli_home_path.parents) >= 2
            else (root.parent / 'gflow-videos').resolve()
        )

    model = _first(sources, 'GFLOW_VIDEO_MODEL') or 'veo-fast'
    if model not in VIDEO_MODELS:
        options = ', '.join(VIDEO_MODELS)
        raise ConfigError(f'GFLOW_VIDEO_MODEL inválido: {model}. Opções: {options}.')

    return PipelineConfig(
        root=root,
        spreadsheet=_path(
            _first(sources, 'PIPELINE_SPREADSHEET'),
            root,
            root / 'entradas' / 'controle_pipeline_flow.xlsx',
        ),
        output_dir=_path(_first(sources, 'PIPELINE_OUTPUT_DIR'), root, root / 'preparados'),
        delivery_dir=_path(
            _first(sources, 'PIPELINE_DELIVERY_DIR'), root, root / 'entregas_flow'
        ),
        gflow_root=gflow_root,
        project_id=_first(sources, 'GFLOW_PROJECT_ID', 'GFLOW_CLI_DEFAULT_PROJECT'),
        video_model=model,
        timeout_seconds=_positive_int(
            _first(sources, 'GFLOW_TIMEOUT_SECONDS'), 1800, 'GFLOW_TIMEOUT_SECONDS'
        ),
        web_host=_first(sources, 'WEB_HOST') or '127.0.0.1',
        web_port=_positive_int(_first(sources, 'WEB_PORT'), 8765, 'WEB_PORT'),
    )
