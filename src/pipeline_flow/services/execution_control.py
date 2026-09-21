'''Controle persistente de exclusao mutua para operacoes por clipe.'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
from typing import Callable, Mapping
import uuid


LOCK_SCHEMA_VERSION = 1


class LockError(ValueError):
    '''Lock ativo, invalido ou alterado por outro processo.'''


@dataclass(frozen=True)
class LockHandle:
    path: Path
    token: str
    recovered_from: Path | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _windows_process_is_alive(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5
    error_invalid_parameter = 87
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(
        process_query_limited_information,
        False,
        pid,
    )
    if not handle:
        error = ctypes.get_last_error()
        if error == error_invalid_parameter:
            return False
        if error == error_access_denied:
            return True
        return True
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(
            handle,
            ctypes.byref(exit_code),
        ):
            return True
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == 'nt':
        return _windows_process_is_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Falha fechada: sem prova de que morreu, o lock continua ativo.
        return True
    return True


def _read_lock(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise LockError(
            f'Lock invalido em {path}; inspecione-o antes de qualquer remocao.'
        ) from exc
    if not isinstance(payload, dict):
        raise LockError(
            f'Lock invalido em {path}; inspecione-o antes de qualquer remocao.'
        )
    return payload


def _owner_is_alive(
    payload: Mapping[str, object],
    *,
    hostname: str,
    is_alive: Callable[[int], bool],
) -> bool:
    if payload.get('schema_version') != LOCK_SCHEMA_VERSION:
        raise LockError('Versao desconhecida do lock; remocao automatica bloqueada.')
    owner_host = payload.get('hostname')
    owner_pid = payload.get('pid')
    if owner_host != hostname:
        raise LockError(
            'Lock pertence a outro host; confirme o processo antes de remove-lo.'
        )
    if not isinstance(owner_pid, int) or owner_pid <= 0:
        raise LockError('Lock sem PID valido; remocao automatica bloqueada.')
    return is_alive(owner_pid)


def _create_lock(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(
            descriptor,
            'w',
            encoding='utf-8',
            newline='\n',
        ) as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(',', ':'))
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _archive_stale_lock(path: Path, payload: Mapping[str, object]) -> Path:
    archive_dir = path.parent / 'logs' / 'locks'
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / f'{path.stem}.orfao.{uuid.uuid4().hex}.json'
    os.replace(path, archive)
    return archive


def acquire_lock(
    path: Path,
    operation: str,
    *,
    context: Mapping[str, object] | None = None,
    is_alive: Callable[[int], bool] = process_is_alive,
    recover_stale: bool = True,
) -> LockHandle:
    path = Path(path)
    hostname = socket.gethostname()
    token = uuid.uuid4().hex
    payload = {
        **dict(context or {}),
        'schema_version': LOCK_SCHEMA_VERSION,
        'token': token,
        'pid': os.getpid(),
        'hostname': hostname,
        'operacao': str(operation),
        'inicio_em': utc_now(),
    }
    recovered_from = None

    for _ in range(4):
        try:
            _create_lock(path, payload)
            return LockHandle(path=path, token=token, recovered_from=recovered_from)
        except FileExistsError:
            try:
                existing = _read_lock(path)
            except FileNotFoundError:
                continue
            if _owner_is_alive(
                existing,
                hostname=hostname,
                is_alive=is_alive,
            ):
                raise LockError(
                    'Execucao bloqueada por processo ativo: '
                    f'pid={existing.get("pid")}, '
                    f'operacao={existing.get("operacao")}.'
                )
            if not recover_stale:
                raise LockError(
                    'Lock orfao preservado para revisao manual; '
                    'a operacao anterior pode ter produzido efeito externo.'
                )
            try:
                recovered_from = _archive_stale_lock(path, existing)
            except FileNotFoundError:
                continue

    raise LockError('Nao foi possivel adquirir o lock apos concorrencia.')


def release_lock(handle: LockHandle) -> None:
    try:
        payload = _read_lock(handle.path)
    except FileNotFoundError as exc:
        raise LockError(
            'Lock desapareceu durante a execucao; estado concorrente suspeito.'
        ) from exc
    if payload.get('token') != handle.token:
        raise LockError(
            'Lock foi substituido por outro processo; o lock atual foi preservado.'
        )
    handle.path.unlink()
