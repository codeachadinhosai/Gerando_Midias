import json
import os
from pathlib import Path
import socket
import tempfile
import unittest

from openpyxl import Workbook as OpenpyxlWorkbook

from pipeline_flow.services.execution_control import (
    LOCK_SCHEMA_VERSION,
    LockError,
    acquire_lock,
    process_is_alive,
    release_lock,
)
from pipeline_flow.services.preparar_insumos import (
    HEADERS,
    Invalid,
    Workbook,
)


class ExecutionLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.lock = self.folder / '.execucao.lock'

    def test_live_owner_blocks_second_process(self):
        handle = acquire_lock(self.lock, 'imagem')
        self.addCleanup(
            lambda: self.lock.exists() and release_lock(handle)
        )

        with self.assertRaisesRegex(LockError, 'processo ativo'):
            acquire_lock(self.lock, 'video')

    def test_process_probe_is_read_only_and_distinguishes_missing_pid(self):
        self.assertTrue(process_is_alive(os.getpid()))
        self.assertFalse(process_is_alive(2147483647))

    def test_dead_owner_is_archived_before_new_lock(self):
        stale = {
            'schema_version': LOCK_SCHEMA_VERSION,
            'token': 'stale-token',
            'pid': 999999,
            'hostname': socket.gethostname(),
            'operacao': 'imagem',
            'inicio_em': '2026-09-20T10:00:00Z',
        }
        self.lock.write_text(json.dumps(stale), encoding='utf-8')

        handle = acquire_lock(
            self.lock,
            'video',
            is_alive=lambda pid: False,
        )
        self.addCleanup(
            lambda: self.lock.exists() and release_lock(handle)
        )

        self.assertIsNotNone(handle.recovered_from)
        self.assertTrue(handle.recovered_from.is_file())
        archived = json.loads(
            handle.recovered_from.read_text(encoding='utf-8')
        )
        self.assertEqual(archived['token'], 'stale-token')
        current = json.loads(self.lock.read_text(encoding='utf-8'))
        self.assertEqual(current['token'], handle.token)
        self.assertEqual(current['pid'], os.getpid())

    def test_dead_owner_is_preserved_when_external_effect_is_uncertain(self):
        stale = {
            'schema_version': LOCK_SCHEMA_VERSION,
            'token': 'stale-token',
            'pid': 999999,
            'hostname': socket.gethostname(),
            'operacao': 'video-pago',
            'inicio_em': '2026-09-20T10:00:00Z',
        }
        self.lock.write_text(json.dumps(stale), encoding='utf-8')

        with self.assertRaisesRegex(LockError, 'orfao preservado'):
            acquire_lock(
                self.lock,
                'video-pago',
                is_alive=lambda pid: False,
                recover_stale=False,
            )

        current = json.loads(self.lock.read_text(encoding='utf-8'))
        self.assertEqual(current['token'], 'stale-token')

    def test_foreign_host_lock_fails_closed(self):
        foreign = {
            'schema_version': LOCK_SCHEMA_VERSION,
            'token': 'foreign-token',
            'pid': 42,
            'hostname': 'outro-host',
            'operacao': 'video',
            'inicio_em': '2026-09-20T10:00:00Z',
        }
        self.lock.write_text(json.dumps(foreign), encoding='utf-8')

        with self.assertRaisesRegex(LockError, 'outro host'):
            acquire_lock(
                self.lock,
                'imagem',
                is_alive=lambda pid: False,
            )

        self.assertTrue(self.lock.is_file())

    def test_malformed_lock_is_preserved(self):
        self.lock.write_text('not-json', encoding='utf-8')

        with self.assertRaisesRegex(LockError, 'Lock invalido'):
            acquire_lock(self.lock, 'imagem')

        self.assertEqual(
            self.lock.read_text(encoding='utf-8'),
            'not-json',
        )

    def test_release_does_not_remove_replaced_lock(self):
        handle = acquire_lock(self.lock, 'imagem')
        replacement = json.loads(self.lock.read_text(encoding='utf-8'))
        replacement['token'] = 'replacement-token'
        self.lock.write_text(json.dumps(replacement), encoding='utf-8')

        with self.assertRaisesRegex(LockError, 'substituido'):
            release_lock(handle)

        self.assertTrue(self.lock.is_file())
        current = json.loads(self.lock.read_text(encoding='utf-8'))
        self.assertEqual(current['token'], 'replacement-token')

    def test_workbook_save_respects_cross_process_lock(self):
        sheet_path = self.folder / 'controle.xlsx'
        book = OpenpyxlWorkbook()
        sheet = book.active
        sheet.title = 'Controle'
        sheet.append(HEADERS)
        sheet.append([''] * len(HEADERS))
        sheet.append([''] * len(HEADERS))
        sheet.append([''] * len(HEADERS))
        book.save(sheet_path)
        workbook = Workbook(sheet_path)
        lock_path = (
            self.folder / 'backups' / '.controle.xlsx.lock'
        )
        handle = acquire_lock(lock_path, 'salvar-planilha')
        try:
            with self.assertRaisesRegex(Invalid, 'processo ativo'):
                workbook.save()
        finally:
            release_lock(handle)

        self.assertTrue(sheet_path.is_file())


if __name__ == '__main__':
    unittest.main()
