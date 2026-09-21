'''Modelos e validações de configuração sem acesso a arquivos ou ambiente.'''

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .events import OperationalEvent
from .states import (
    CarouselStatus,
    ImageStatus,
    PipelineStatus,
    STATE_FIELDS,
    StateError,
    VideoStatus,
    normalize_state,
    normalize_states,
    state_token,
)

VIDEO_MODELS = (
    'omni-flash',
)


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


def positive_int(value: str, default: int, name: str) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f'{name} deve ser um inteiro positivo.') from exc
    if parsed <= 0:
        raise ConfigError(f'{name} deve ser um inteiro positivo.')
    return parsed


def video_model(value: str) -> str:
    model = value or 'omni-flash'
    if model not in VIDEO_MODELS:
        options = ', '.join(VIDEO_MODELS)
        raise ConfigError(f'GFLOW_VIDEO_MODEL inválido: {model}. Opções: {options}.')
    return model


__all__ = (
    'CarouselStatus',
    'ConfigError',
    'ImageStatus',
    'OperationalEvent',
    'PipelineConfig',
    'PipelineStatus',
    'STATE_FIELDS',
    'StateError',
    'VIDEO_MODELS',
    'VideoStatus',
    'normalize_state',
    'normalize_states',
    'positive_int',
    'state_token',
    'video_model',
)
