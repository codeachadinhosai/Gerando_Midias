'''Persistência append-only de eventos operacionais estruturados.'''

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from pipeline_flow.domain.events import OperationalEvent


def sanitize_command(command: Iterable[object] | None) -> tuple[str, ...]:
    '''Remove projeto e conteúdo longo sem perder a forma auditável do comando.'''
    if command is None:
        return ()
    sanitized: list[str] = []
    redact_next = False
    for item in command:
        value = str(item)
        if redact_next:
            sanitized.append('<redigido>')
            redact_next = False
            continue
        sanitized.append('<conteudo_omitido>' if '\n' in value or len(value) > 160 else value)
        if value == '--project':
            redact_next = True
    return tuple(sanitized)


def sanitize_error(
    error: object,
    command: Iterable[object] | None = None,
) -> str:
    text = str(error or '')
    items = [str(item) for item in command or ()]
    sensitive = []
    if '--project' in items:
        index = items.index('--project') + 1
        if index < len(items):
            sensitive.append(items[index])
    if '--aspect' in items:
        index = items.index('--aspect') - 1
        if index >= 0:
            sensitive.append(items[index])
    for value in sensitive:
        if value:
            text = text.replace(value, '<redigido>')
    return text[:2000]


def append_event(path: Path, event: OperationalEvent) -> Path:
    '''Acrescenta uma linha JSON completa e força sua persistência em disco.'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.as_dict(), ensure_ascii=False, separators=(',', ':'))
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(line + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return path


def record_clip_event(
    clip: dict,
    *,
    stage: str,
    method: str,
    result: str,
    error: str,
    started_at: str,
    timestamp: str,
    command: Iterable[object] | None = None,
) -> Path:
    event = OperationalEvent(
        production_id=str(clip['plan']['producao_id']),
        clip_id=str(clip['plan']['id_clipe']),
        stage=stage,
        method=method,
        result=result,
        error=sanitize_error(error, command),
        started_at=started_at,
        timestamp=timestamp,
        command=sanitize_command(command),
    )
    return append_event(clip['folder'] / 'logs' / 'eventos.jsonl', event)
