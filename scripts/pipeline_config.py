'''Wrapper compatível para pipeline_flow.config.'''

from pipeline_flow.adapters import read_dotenv
from pipeline_flow.config import ConfigError, PipelineConfig, VIDEO_MODELS, load_config

__all__ = (
    'ConfigError',
    'PipelineConfig',
    'VIDEO_MODELS',
    'load_config',
    'read_dotenv',
)
