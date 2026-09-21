'''Backend web local e somente leitura do Pipeline Flow.'''

from .app import create_app
from .queries import PipelineReadModel

__all__ = ('PipelineReadModel', 'create_app')
