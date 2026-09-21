import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline_flow.domain import (
    CarouselStatus,
    ImageStatus,
    PipelineStatus,
    StateError,
    normalize_state,
    normalize_states,
)
from pipeline_flow.domain.events import OperationalEvent
from pipeline_flow.services import gerar_carrossel as carousel
from pipeline_flow.services.operational_log import (
    append_event,
    sanitize_command,
    sanitize_error,
)


class OperationalStatesTest(unittest.TestCase):
    def test_legacy_spelling_is_read_as_canonical_state(self):
        record = normalize_states({
            'status': 'aguardando aprovação',
            'imagem_status': 'não necessária',
            'video_status': '',
            'carrossel_status': 'não solicitado',
        })
        self.assertEqual(record['status'], PipelineStatus.WAITING_APPROVAL)
        self.assertEqual(record['imagem_status'], ImageStatus.NOT_REQUIRED)
        self.assertEqual(record['video_status'], '')
        self.assertEqual(record['carrossel_status'], CarouselStatus.NOT_REQUESTED)

    def test_unknown_state_is_rejected_with_field_name(self):
        with self.assertRaisesRegex(StateError, 'video_status'):
            normalize_state('video_status', 'talvez')


class OperationalLogTest(unittest.TestCase):
    def test_error_redacts_project_and_prompt_from_timeout_text(self):
        command = [
            'gflow.exe',
            'video',
            'i2v',
            '--initial-frame',
            'frame.png',
            'prompt privado curto',
            '--aspect',
            '9:16',
            '--project',
            'project-secret',
        ]
        error = sanitize_error(
            'Command prompt privado curto project-secret timed out',
            command,
        )

        self.assertNotIn('prompt privado curto', error)
        self.assertNotIn('project-secret', error)
        self.assertEqual(error.count('<redigido>'), 2)

    def test_jsonl_event_has_required_fields_and_redacts_command(self):
        command = sanitize_command([
            'gflow.exe',
            'image',
            'i2i',
            'prompt\nprivado',
            '--project',
            'project-secret',
        ])
        event = OperationalEvent(
            production_id='PROD_01',
            clip_id='PROD_01_01',
            stage='imagem',
            method='i2i',
            result='gerado',
            error='',
            started_at='2026-09-19T10:00:00Z',
            timestamp='2026-09-19T10:00:01Z',
            command=command,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = append_event(Path(tmp) / 'logs' / 'eventos.jsonl', event)
            payload = json.loads(path.read_text(encoding='utf-8').strip())

        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['producao_id'], 'PROD_01')
        self.assertEqual(payload['id_clipe'], 'PROD_01_01')
        self.assertEqual(payload['etapa'], 'imagem')
        self.assertEqual(payload['metodo'], 'i2i')
        self.assertEqual(payload['resultado'], 'gerado')
        self.assertEqual(payload['erro'], '')
        self.assertIn('<conteudo_omitido>', payload['comando'])
        self.assertIn('<redigido>', payload['comando'])
        self.assertNotIn('project-secret', payload['comando'])

    def test_carousel_success_and_failure_are_both_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            clip = {
                'folder': folder,
                'fingerprint': 'a' * 64,
                'revision_sha256': 'b' * 64,
                'flow': {'pacote_sha256': 'c' * 64},
                'plan': {'producao_id': 'PROD_01', 'id_clipe': 'PROD_01_01'},
            }
            destination = folder / 'card.png'
            with patch.object(carousel, '_generate', return_value=destination):
                self.assertEqual(carousel.generate(clip, 'controle.xlsx'), destination)
            with patch.object(carousel, '_generate', side_effect=ValueError('falha local')):
                with self.assertRaisesRegex(ValueError, 'falha local'):
                    carousel.generate(clip, 'controle.xlsx')

            events = [
                json.loads(line)
                for line in (folder / 'logs' / 'eventos.jsonl')
                .read_text(encoding='utf-8')
                .splitlines()
            ]
            self.assertFalse((folder / '.execucao.lock').exists())

        self.assertEqual([event['resultado'] for event in events], ['gerado', 'erro'])
        self.assertEqual(events[1]['erro'], 'falha local')


if __name__ == '__main__':
    unittest.main()
