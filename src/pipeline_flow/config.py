'''Fachada pública da configuração do pipeline.'''

from .domain import ConfigError, PipelineConfig, VIDEO_MODELS
from .services import load_config

__all__ = (
    'ConfigError',
    'PipelineConfig',
    'VIDEO_MODELS',
    'load_config',
)
