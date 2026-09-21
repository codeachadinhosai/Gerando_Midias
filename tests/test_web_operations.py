import io
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from pipeline_flow.config import load_config
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.web.app import create_app
from pipeline_flow.web.operations import (
    OperationConflict,
    OperationError,
    PipelineOperations,
)


class WebOperationsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'preparados'
        self.responses = self.output / 'respostas_ia'
        self.delivery = self.root / 'entregas_flow'
        self.output.mkdir()
        self.responses.mkdir()
        self.delivery.mkdir()
        base = load_config(self.root, environ={})
        self.config = replace(
            base,
            output_dir=self.output,
            delivery_dir=self.delivery,
            spreadsheet=self.root / 'controle.xlsx',
        )
        self.client = TestClient(create_app(self.config))

    @staticmethod
    def image_bytes():
        buffer = io.BytesIO()
        Image.new('RGB', (12, 20), 'white').save(buffer, format='PNG')
        return buffer.getvalue()

    def test_catalog_lists_only_valid_packages_and_responses(self):
        package = self.output / 'pacotes' / 'PROD_01' / ('a' * 16)
        package.mkdir(parents=True)
        (package / 'manifesto.json').write_text(json.dumps({
            'producao_id': 'PROD_01',
            'pacote_sha256': 'a' * 64,
            'clipes': [{'id_clipe': 'PROD_01_01'}],
        }), encoding='utf-8')
        (self.responses / 'resposta.json').write_text(json.dumps({
            'pacote_sha256': 'a' * 64,
            'plano_producao': {'producao_id': 'PROD_01'},
        }), encoding='utf-8')
        latest = self.output / 'pacotes_ia' / 'ULTIMO_PACOTE_IA.zip'
        latest.parent.mkdir()
        latest.write_bytes(b'zip content')

        response = self.client.get('/api/operations')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pacotes'][0]['id'], 'PROD_01/' + 'a' * 16)
        self.assertEqual(response.json()['respostas'][0]['id'], 'resposta.json')
        self.assertTrue(response.json()['pacote_ia']['disponivel'])
        download = self.client.get('/api/operations/package-latest')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b'zip content')

    def test_mutations_require_explicit_confirmation_header(self):
        endpoints = (
            ('/api/operations/prepare', None),
            (
                '/api/operations/import?package_id=PROD_01%2F'
                + 'a' * 16
                + '&response_id=resposta.json',
                None,
            ),
            (
                '/api/operations/import-upload?package_id=PROD_01%2F'
                + 'a' * 16
                + '&filename=resposta.json',
                b'{}',
            ),
            (
                '/api/operations/review-image',
                json.dumps({
                    'production_id': 'PROD_01',
                    'revision': 'b' * 16,
                    'clip_id': 'PROD_01_01',
                    'decision': 'aprovada',
                    'image_sha256': 'c' * 64,
                }).encode(),
            ),
            (
                '/api/operations/generate-carousel',
                json.dumps({
                    'production_id': 'PROD_01',
                    'revision': 'b' * 16,
                    'clip_id': 'PROD_01_01',
                    'image_sha256': 'c' * 64,
                    'regenerate': False,
                }).encode(),
            ),
            (
                '/api/operations/generate-video',
                json.dumps({
                    'production_id': 'PROD_01',
                    'revision': 'b' * 16,
                    'clip_id': 'PROD_01_01',
                    'image_sha256': 'c' * 64,
                    'credit_confirmation': 'GERAR VIDEO',
                }).encode(),
            ),
        )
        for endpoint, content in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, content=content)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Confirmação explícita', response.json()['detail'])

    def test_health_distinguishes_queries_from_confirmed_operations(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['consultas_somente_leitura'])
        self.assertTrue(response.json()['operacoes_confirmadas'])

    def test_external_browser_origins_are_blocked(self):
        external = self.client.get(
            '/api/health',
            headers={'Origin': 'https://example.invalid'},
        )
        cross_site = self.client.get(
            '/api/health',
            headers={'Sec-Fetch-Site': 'cross-site'},
        )
        local = self.client.get(
            '/api/health',
            headers={'Origin': 'http://127.0.0.1:8765'},
        )

        self.assertEqual(external.status_code, 403)
        self.assertEqual(cross_site.status_code, 403)
        self.assertEqual(local.status_code, 200)

    def test_json_body_limit_is_enforced_before_operation(self):
        with patch.object(PipelineOperations, 'review_image') as mocked:
            response = self.client.post(
                '/api/operations/review-image',
                content=b'{' + (b' ' * (8 * 1024)) + b'}',
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 413)
        mocked.assert_not_called()

    def test_prepare_route_calls_local_service_after_confirmation(self):
        expected = {'preparacao': {'pacotes': []}, 'pacote_ia': None}
        with patch.object(
            PipelineOperations, 'prepare_packages', return_value=expected
        ) as mocked:
            response = self.client.post(
                '/api/operations/prepare',
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with()

    def test_register_image_route_forwards_validated_upload(self):
        expected = {'resultado': 'imagem registrada'}
        query = (
            '/api/operations/register-image?production_id=PROD_01'
            '&revision=' + 'b' * 16
            + '&clip_id=PROD_01_01&filename=frame.png'
        )
        content = self.image_bytes()
        with patch.object(
            PipelineOperations, 'register_image', return_value=expected
        ) as mocked:
            response = self.client.post(
                query,
                content=content,
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with(
            'PROD_01', 'b' * 16, 'PROD_01_01', 'frame.png', content
        )

    def test_review_route_forwards_decision_and_expected_hash(self):
        expected = {'resultado': 'imagem aprovada e vinculada ao frame'}
        payload = {
            'production_id': 'PROD_01',
            'revision': 'b' * 16,
            'clip_id': 'PROD_01_01',
            'decision': 'aprovada',
            'image_sha256': 'c' * 64,
            'reason': '',
        }
        with patch.object(
            PipelineOperations, 'review_image', return_value=expected
        ) as mocked:
            response = self.client.post(
                '/api/operations/review-image',
                json=payload,
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with(
            'PROD_01',
            'b' * 16,
            'PROD_01_01',
            'aprovada',
            'c' * 64,
            '',
        )

    def test_review_route_reports_stale_image_as_conflict(self):
        with patch.object(
            PipelineOperations,
            'review_image',
            side_effect=OperationConflict('A imagem mudou.'),
        ):
            response = self.client.post(
                '/api/operations/review-image',
                json={
                    'production_id': 'PROD_01',
                    'revision': 'b' * 16,
                    'clip_id': 'PROD_01_01',
                    'decision': 'rejeitada',
                    'image_sha256': 'c' * 64,
                    'reason': 'Anatomia incorreta.',
                },
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 409)
        self.assertIn('imagem mudou', response.json()['detail'])

    def test_carousel_route_forwards_local_generation_request(self):
        expected = {'resultado': 'carrossel gerado localmente'}
        payload = {
            'production_id': 'PROD_01',
            'revision': 'b' * 16,
            'clip_id': 'PROD_01_01',
            'image_sha256': 'c' * 64,
            'regenerate': True,
        }
        with patch.object(
            PipelineOperations, 'generate_carousel', return_value=expected
        ) as mocked:
            response = self.client.post(
                '/api/operations/generate-carousel',
                json=payload,
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with(
            'PROD_01',
            'b' * 16,
            'PROD_01_01',
            'c' * 64,
            True,
        )

    def test_video_route_forwards_only_fixed_release_fields(self):
        expected = {
            'id': 'job-1',
            'status': 'queued',
        }
        payload = {
            'production_id': 'PROD_01',
            'revision': 'b' * 16,
            'clip_id': 'PROD_01_01',
            'image_sha256': 'c' * 64,
            'credit_confirmation': 'GERAR VIDEO',
            'command': ['nao', 'executar'],
        }
        with patch.object(
            PipelineOperations,
            'start_video',
            return_value=expected,
        ) as mocked:
            response = self.client.post(
                '/api/operations/generate-video',
                json=payload,
                headers={'X-Pipeline-Confirmation': 'confirmar'},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with(
            'PROD_01',
            'b' * 16,
            'PROD_01_01',
            'c' * 64,
            'GERAR VIDEO',
        )

    def test_execution_catalog_route_never_exposes_command(self):
        expected = {
            'execucoes': [{'id': 'job-1', 'status': 'running'}],
            'executor': {'disponivel': True},
        }
        with patch.object(
            PipelineOperations,
            'execution_catalog',
            return_value=expected,
        ):
            response = self.client.get('/api/operations/executions')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertNotIn('comando', response.text.lower())

    def test_image_validation_checks_content_and_extension(self):
        suffix, width, height = PipelineOperations._validate_image(
            'frame.png', self.image_bytes()
        )
        self.assertEqual((suffix, width, height), ('.png', 12, 20))
        with self.assertRaises(OperationError):
            PipelineOperations._validate_image('frame.png', b'not an image')
        with self.assertRaises(OperationError):
            PipelineOperations._validate_image('frame.jpg', self.image_bytes())

    def test_uploaded_response_is_persisted_after_valid_import(self):
        revision = 'c' * 16
        package = self.output / 'pacotes' / 'PROD_01' / revision
        package.mkdir(parents=True)
        (package / 'manifesto.json').write_text(
            json.dumps({'producao_id': 'PROD_01'}),
            encoding='utf-8',
        )
        content = json.dumps({
            'pacote_sha256': 'd' * 64,
            'plano_producao': {'producao_id': 'PROD_01'},
        }).encode()
        operations = PipelineOperations(self.config)
        with patch(
            'pipeline_flow.web.operations.import_response',
            return_value={'clipes': 1, 'excel_atualizado': True},
        ) as mocked:
            result = operations.import_uploaded(
                f'PROD_01/{revision}', 'resposta.json', content
            )

        saved = Path(result['resposta_salva'])
        self.assertEqual(saved.read_bytes(), content)
        self.assertTrue(saved.is_relative_to(self.responses))
        self.assertTrue(mocked.call_args.kwargs['update_excel'])

    def test_register_image_removes_temporary_upload(self):
        operations = PipelineOperations(self.config)
        clip = {'plan': {'id_clipe': 'PROD_01_01'}}
        captured = {}

        def execute(_clip, args):
            captured['path'] = Path(args.arquivo)
            self.assertEqual(captured['path'].read_bytes(), self.image_bytes())
            return 'imagem fornecida registrada'

        with (
            patch.object(operations, '_active_clip', return_value=clip),
            patch('pipeline_flow.web.operations.flow.execute', side_effect=execute),
        ):
            result = operations.register_image(
                'PROD_01', 'e' * 16, 'PROD_01_01',
                'frame.png', self.image_bytes(),
            )

        self.assertFalse(captured['path'].exists())
        self.assertEqual(result['largura'], 12)
        self.assertEqual(result['altura'], 20)

    def test_generate_carousel_uses_active_clip_and_delivery_root(self):
        operations = PipelineOperations(self.config)
        clip = {'plan': {'id_clipe': 'PROD_01_01'}}
        destination = self.delivery / 'carrossel' / 'PROD_01' / 'card.png'
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b'card')

        with (
            patch.object(operations, '_active_clip', return_value=clip),
            patch(
                'pipeline_flow.web.operations.carousel.generate',
                return_value=destination,
            ) as generate,
        ):
            result = operations.generate_carousel(
                'PROD_01',
                'e' * 16,
                'PROD_01_01',
                'f' * 64,
                True,
            )

        generate.assert_called_once_with(
            clip,
            self.config.spreadsheet,
            self.config.delivery_dir,
            expected_image_sha256='f' * 64,
            force=True,
        )
        self.assertEqual(result['arquivo'], 'carrossel/PROD_01/card.png')

    def test_video_release_requires_exact_credit_phrase(self):
        operations = PipelineOperations(self.config)

        with self.assertRaisesRegex(OperationError, 'GERAR VIDEO'):
            operations.start_video(
                'PROD_01',
                'e' * 16,
                'PROD_01_01',
                'f' * 64,
                'gerar video',
            )

    def test_execution_catalog_reports_persistent_credit_lock(self):
        operations = PipelineOperations(self.config)
        operations.credit_lock_path.parent.mkdir(parents=True)
        operations.credit_lock_path.write_text('{}', encoding='utf-8')

        catalog = operations.execution_catalog()

        self.assertTrue(catalog['executor']['trava_credito_ativa'])
        self.assertNotIn('project_id', catalog['executor'])

    def test_image_dimensions_have_an_explicit_pixel_limit(self):
        class OversizedImage:
            size = (10_000, 5_000)
            format = 'PNG'

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def verify(self):
                return None

        with (
            patch.object(Image, 'open', return_value=OversizedImage()),
            self.assertRaisesRegex(OperationError, 'limite seguro de pixels'),
        ):
            PipelineOperations._validate_image(
                'frame.png', b'valid-looking-content'
            )

    def test_execution_errors_redact_timeout_command_and_project_id(self):
        configured = replace(self.config, project_id='project-secret')
        operations = PipelineOperations(configured)
        timeout = subprocess.TimeoutExpired(
            ['gflow', '--project', 'project-secret'],
            configured.timeout_seconds,
        )

        timeout_message = operations._safe_execution_error(timeout)
        generic_message = operations._safe_execution_error(
            OperationError('Falha no projeto project-secret.'),
        )

        self.assertIn('tempo limite', timeout_message)
        self.assertNotIn('gflow', timeout_message)
        self.assertNotIn('project-secret', timeout_message)
        self.assertIn('<redigido>', generic_message)
        self.assertNotIn('project-secret', generic_message)

    def test_video_job_uses_only_server_configuration_and_tracks_success(self):
        operations = PipelineOperations(self.config)
        clip = {'plan': {'id_clipe': 'PROD_01_01'}}
        captured = {}

        class ImmediateThread:
            def __init__(self, target, args, **_kwargs):
                self.target = target
                self.args = args

            def start(self):
                self.target(*self.args)

        def execute(_clip, args):
            captured['args'] = args
            return 'gerado; revisar resultado visualmente'

        with (
            patch.object(operations, '_active_clip', return_value=clip),
            patch.object(operations, '_video_preflight'),
            patch(
                'pipeline_flow.web.operations.threading.Thread',
                side_effect=ImmediateThread,
            ),
            patch(
                'pipeline_flow.web.operations.flow.execute',
                side_effect=execute,
            ),
        ):
            result = operations.start_video(
                'PROD_01',
                'e' * 16,
                'PROD_01_01',
                'f' * 64,
                'GERAR VIDEO',
            )

        args = captured['args']
        self.assertEqual(args.acao, 'video')
        self.assertEqual(args.gflow_raiz, self.config.gflow_root)
        self.assertEqual(args.projeto, self.config.project_id)
        self.assertEqual(args.modelo_video, self.config.video_model)
        self.assertEqual(args.expected_image_sha256, 'f' * 64)
        self.assertEqual(result['status'], 'succeeded')
        catalog = operations.execution_catalog()
        self.assertEqual(catalog['execucoes'][0]['status'], 'succeeded')
        self.assertNotIn('comando', catalog['execucoes'][0])

    def test_only_one_paid_video_job_can_be_active(self):
        operations = PipelineOperations(self.config)
        clip = {'plan': {'id_clipe': 'PROD_01_01'}}

        with (
            patch.object(operations, '_active_clip', return_value=clip),
            patch.object(operations, '_video_preflight'),
            patch('pipeline_flow.web.operations.threading.Thread') as thread,
        ):
            first = operations.start_video(
                'PROD_01', 'e' * 16, 'PROD_01_01', 'f' * 64, 'GERAR VIDEO'
            )
            with self.assertRaisesRegex(OperationConflict, 'em andamento'):
                operations.start_video(
                    'PROD_02', 'd' * 16, 'PROD_02_01', 'c' * 64, 'GERAR VIDEO'
                )

        self.assertEqual(first['status'], 'queued')
        thread.return_value.start.assert_called_once_with()

    def test_video_preflight_rejects_stale_gallery_hash(self):
        operations = PipelineOperations(self.config)
        frame = self.root / 'frame.png'
        frame.write_bytes(b'current frame')
        clip = {
            'folder': self.root,
            'plan': {
                'pipeline': {
                    'gerar_video': True,
                    'aprovacao_necessaria': True,
                },
            },
        }

        with (
            patch('pipeline_flow.web.operations.Workbook'),
            patch.object(flow, 'state_for', return_value={'imagem': {'arquivo': 'frame'}}),
            patch.object(flow, 'row_for', return_value={'aprovacao': 'aprovada'}),
            patch.object(flow, 'media', return_value=frame),
            self.assertRaisesRegex(OperationConflict, 'imagem mudou'),
        ):
            operations._video_preflight(clip, 'a' * 64)

    def test_video_preflight_requires_bound_approval(self):
        operations = PipelineOperations(self.config)
        frame = self.root / 'frame.png'
        frame.write_bytes(b'current frame')
        clip = {
            'folder': self.root,
            'plan': {
                'pipeline': {
                    'gerar_video': True,
                    'aprovacao_necessaria': True,
                },
            },
        }

        with (
            patch('pipeline_flow.web.operations.Workbook'),
            patch.object(flow, 'state_for', return_value={'imagem': {'arquivo': 'frame'}}),
            patch.object(flow, 'row_for', return_value={'aprovacao': 'aprovada'}),
            patch.object(flow, 'media', return_value=frame),
            patch.object(flow, 'approval_is_bound', return_value=False),
            self.assertRaisesRegex(OperationError, 'aprovada e vinculada'),
        ):
            operations._video_preflight(clip, flow.digest(frame))


if __name__ == '__main__':
    unittest.main()
