'''Vocabulário canônico dos estados operacionais persistidos na planilha.'''

from __future__ import annotations

from enum import Enum
import re
import unicodedata
from typing import Mapping


class StateError(ValueError):
    '''Estado operacional desconhecido ou usado no campo errado.'''


class TextState(str, Enum):
    def __str__(self) -> str:
        return self.value


class PipelineStatus(TextState):
    NEW = 'novo'
    CLASSIFYING = 'classificando'
    CLASSIFIED = 'classificado'
    WAITING_IMAGE = 'aguardando_imagem'
    IMAGE_GENERATED = 'imagem_gerada'
    WAITING_APPROVAL = 'aguardando_aprovacao'
    APPROVED = 'aprovada'
    READY_FOR_VIDEO = 'pronto_para_video'
    GENERATING_VIDEO = 'gerando_video'
    MATERIAL_VALIDATED = 'material_validado'
    COMPLETED = 'concluido'
    PENDING = 'pendente'
    ERROR = 'erro'


class ImageStatus(TextState):
    PENDING = 'pendente'
    GENERATING = 'gerando'
    GENERATED = 'gerada'
    NOT_REQUIRED = 'nao_necessaria'
    ERROR = 'erro'


class VideoStatus(TextState):
    PENDING = 'pendente'
    GENERATING = 'gerando'
    GENERATED = 'gerado'
    REUSED = 'reutilizado'
    NOT_REQUIRED = 'nao_necessario'
    ERROR = 'erro'


class CarouselStatus(TextState):
    PENDING = 'pendente'
    GENERATING = 'gerando'
    GENERATED = 'gerado'
    NOT_REQUESTED = 'nao_solicitado'
    ERROR = 'erro'


STATE_FIELDS = {
    'status': PipelineStatus,
    'imagem_status': ImageStatus,
    'video_status': VideoStatus,
    'carrossel_status': CarouselStatus,
}


def state_token(value: object) -> str:
    '''Converte grafias legadas com espaços e acentos para snake_case ASCII.'''
    text = unicodedata.normalize('NFKD', str(value or '').strip().lower())
    text = ''.join(character for character in text if not unicodedata.combining(character))
    return re.sub(r'[^a-z0-9]+', '_', text).strip('_')


def normalize_state(field: str, value: object, *, allow_empty: bool = True) -> str:
    '''Valida um estado e devolve sua representação canônica persistível.'''
    enum_type = STATE_FIELDS.get(field)
    if enum_type is None:
        raise StateError(f'Campo de estado desconhecido: {field}.')
    token = state_token(value)
    if not token and allow_empty:
        return ''
    try:
        return enum_type(token).value
    except ValueError as exc:
        allowed = ', '.join(item.value for item in enum_type)
        raise StateError(
            f'Estado inválido para {field}: {value!r}. Valores: {allowed}.'
        ) from exc


def normalize_states(record: Mapping[str, object]) -> dict[str, object]:
    '''Copia um registro normalizando somente seus campos operacionais.'''
    normalized = dict(record)
    for field in STATE_FIELDS:
        if field in normalized:
            normalized[field] = normalize_state(field, normalized[field])
    return normalized
