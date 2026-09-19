'''Adaptadores para ambiente do processo, arquivos .env e caminhos locais.'''

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Mapping

from pipeline_flow.domain import ConfigError

_ENV_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def environment(environ: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def read_dotenv(path: Path) -> dict[str, str]:
    '''Lê KEY=VALUE sem interpolação, execução ou alteração de os.environ.'''
    path = Path(path)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    for line_number, raw_line in enumerate(lines, 1):
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
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in (chr(39), chr(34))
        ):
            value = value[1:-1]
        values[name] = value
    return values


def resolve_path(value: str, root: Path, default: Path) -> Path:
    candidate = Path(value).expanduser() if value else default
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def legacy_gflow_root(cli_home: str, root: Path) -> Path:
    if not cli_home:
        return (root.parent / 'gflow-videos').resolve()
    home = resolve_path(cli_home, root, root / 'unused')
    return home.parents[1] if len(home.parents) >= 2 else (root.parent / 'gflow-videos').resolve()
