'''Modelo puro dos eventos operacionais gravados pelo pipeline.'''

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationalEvent:
    production_id: str
    clip_id: str
    stage: str
    method: str
    result: str
    error: str
    started_at: str
    timestamp: str
    command: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            'schema_version': 1,
            'producao_id': self.production_id,
            'id_clipe': self.clip_id,
            'etapa': self.stage,
            'metodo': self.method,
            'comando': list(self.command),
            'resultado': self.result,
            'erro': self.error,
            'inicio_em': self.started_at,
            'timestamp': self.timestamp,
        }
