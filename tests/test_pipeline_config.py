import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline_flow import adapters
from pipeline_flow import cli as rodar_pipeline
from pipeline_flow import config as pipeline_config
from pipeline_flow.services import executar_flow, gerar_carrossel, preparar_insumos


class PipelineConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def write_env(self, content):
        path = self.root / '.env'
        path.write_text(content, encoding='utf-8')
        return path

    def test_safe_defaults(self):
        config = pipeline_config.load_config(self.root, environ={})
        self.assertEqual(config.spreadsheet, self.root / 'entradas/controle_pipeline_flow.xlsx')
        self.assertEqual(config.output_dir, self.root / 'preparados')
        self.assertEqual(config.delivery_dir, self.root / 'entregas_flow')
        self.assertEqual(config.video_model, 'omni-flash')
        self.assertEqual(config.timeout_seconds, 1800)
        self.assertEqual(config.web_host, '127.0.0.1')
        self.assertEqual(config.web_port, 8765)
        self.assertEqual(config.project_id, '')
        self.assertEqual(config.gflow_root, self.root)

    def test_dotenv_loads_paths_and_project(self):
        self.write_env(
            'GFLOW_PROJECT_ID=dotenv-project\n'
            'PIPELINE_SPREADSHEET=local/control.xlsx\n'
            'PIPELINE_OUTPUT_DIR=work\n'
            'PIPELINE_DELIVERY_DIR=delivery\n'
            'GFLOW_VIDEO_MODEL=omni-flash\n'
            'GFLOW_TIMEOUT_SECONDS=42\n'
        )
        config = pipeline_config.load_config(self.root, environ={})
        self.assertEqual(config.project_id, 'dotenv-project')
        self.assertEqual(config.spreadsheet, self.root / 'local/control.xlsx')
        self.assertEqual(config.output_dir, self.root / 'work')
        self.assertEqual(config.delivery_dir, self.root / 'delivery')
        self.assertEqual(config.video_model, 'omni-flash')
        self.assertEqual(config.timeout_seconds, 42)

    def test_process_environment_overrides_dotenv(self):
        self.write_env('GFLOW_PROJECT_ID=dotenv\nGFLOW_TIMEOUT_SECONDS=20\n')
        config = pipeline_config.load_config(
            self.root,
            environ={'GFLOW_PROJECT_ID': 'process', 'GFLOW_TIMEOUT_SECONDS': '30'},
        )
        self.assertEqual(config.project_id, 'process')
        self.assertEqual(config.timeout_seconds, 30)

    def test_modern_project_name_precedes_legacy_alias(self):
        config = pipeline_config.load_config(
            self.root,
            environ={
                'GFLOW_PROJECT_ID': 'modern',
                'GFLOW_CLI_DEFAULT_PROJECT': 'legacy',
            },
        )
        self.assertEqual(config.project_id, 'modern')
        fallback = pipeline_config.load_config(
            self.root, environ={'GFLOW_CLI_DEFAULT_PROJECT': 'legacy'}
        )
        self.assertEqual(fallback.project_id, 'legacy')

    def test_legacy_cli_home_resolves_gflow_root(self):
        gflow_root = self.root / 'gflow-videos'
        config = pipeline_config.load_config(
            self.root,
            environ={'GFLOW_CLI_HOME': str(gflow_root / 'data/flow_gflow')},
        )
        self.assertEqual(config.gflow_root, gflow_root)

    def test_explicit_gflow_root_keeps_external_installation_compatible(self):
        gflow_root = self.root / 'external-gflow'
        config = pipeline_config.load_config(
            self.root,
            environ={'GFLOW_ROOT': str(gflow_root)},
        )
        self.assertEqual(config.gflow_root, gflow_root)

    def test_invalid_values_raise_clear_errors(self):
        cases = (
            ({'GFLOW_TIMEOUT_SECONDS': 'zero'}, 'GFLOW_TIMEOUT_SECONDS'),
            ({'WEB_PORT': '0'}, 'WEB_PORT'),
            ({'GFLOW_VIDEO_MODEL': 'unknown'}, 'GFLOW_VIDEO_MODEL'),
            ({'GFLOW_VIDEO_MODEL': 'veo-fast'}, 'GFLOW_VIDEO_MODEL'),
        )
        for environ, expected in cases:
            with self.subTest(environ=environ), self.assertRaisesRegex(
                pipeline_config.ConfigError, expected
            ):
                pipeline_config.load_config(self.root, environ=environ)

    def test_dotenv_parser_accepts_export_and_quotes_but_rejects_code(self):
        valid = self.write_env('export GFLOW_PROJECT_ID=\'quoted project\'\n')
        self.assertEqual(
            adapters.read_dotenv(valid)['GFLOW_PROJECT_ID'], 'quoted project'
        )
        invalid = self.write_env('not a variable\n')
        with self.assertRaisesRegex(pipeline_config.ConfigError, 'NOME=VALOR'):
            adapters.read_dotenv(invalid)


def fake_config(root):
    root = Path(root).resolve()
    return pipeline_config.PipelineConfig(
        root=root,
        spreadsheet=root / 'configured.xlsx',
        output_dir=root / 'configured-output',
        delivery_dir=root / 'configured-delivery',
        gflow_root=root / 'configured-gflow',
        project_id='configured-project',
        video_model='omni-flash',
        timeout_seconds=321,
        web_host='127.0.0.1',
        web_port=8765,
    )


class CliCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.config = fake_config(self.root)

    def test_pipeline_runs_with_configured_project_without_cli_argument(self):
        captured = {}

        def run(args):
            captured['args'] = args
            return {'erros': []}

        with (
            patch.object(rodar_pipeline, 'load_config', return_value=self.config),
            patch.object(rodar_pipeline, 'run', side_effect=run),
            patch.object(rodar_pipeline, 'human_next_action', return_value='ok'),
            patch.object(sys, 'argv', ['rodar_pipeline.py']),
            redirect_stdout(io.StringIO()),
        ):
            result = rodar_pipeline.main()

        self.assertEqual(result, 0)
        self.assertEqual(captured['args'].projeto, 'configured-project')
        self.assertEqual(captured['args'].planilha, self.config.spreadsheet)
        self.assertEqual(captured['args'].output_dir, self.config.output_dir)
        self.assertEqual(captured['args'].delivery_dir, self.config.delivery_dir)

    def test_explicit_pipeline_arguments_override_config(self):
        captured = {}

        def run(args):
            captured['args'] = args
            return {'erros': []}

        argv = [
            'rodar_pipeline.py',
            '--projeto', 'cli-project',
            '--planilha', str(self.root / 'cli.xlsx'),
            '--saida', str(self.root / 'cli-output'),
            '--entregas', str(self.root / 'cli-delivery'),
            '--gflow-raiz', str(self.root / 'cli-gflow'),
            '--modelo-video', 'omni-flash',
            '--timeout', '99',
        ]
        with (
            patch.object(rodar_pipeline, 'load_config', return_value=self.config),
            patch.object(rodar_pipeline, 'run', side_effect=run),
            patch.object(rodar_pipeline, 'human_next_action', return_value='ok'),
            patch.object(sys, 'argv', argv),
            redirect_stdout(io.StringIO()),
        ):
            result = rodar_pipeline.main()

        args = captured['args']
        self.assertEqual(result, 0)
        self.assertEqual(args.projeto, 'cli-project')
        self.assertEqual(args.planilha, self.root / 'cli.xlsx')
        self.assertEqual(args.output_dir, self.root / 'cli-output')
        self.assertEqual(args.respostas, self.root / 'cli-output/respostas_ia')
        self.assertEqual(args.delivery_dir, self.root / 'cli-delivery')
        self.assertEqual(args.gflow_raiz, self.root / 'cli-gflow')
        self.assertEqual(args.modelo_video, 'omni-flash')
        self.assertEqual(args.timeout, 99)

    def test_executor_keeps_project_override(self):
        captured = {}
        clip = {'plan': {'id_clipe': 'clip-1', 'pipeline': {}}}

        def execute(loaded_clip, args):
            captured['args'] = args
            return 'ok'

        argv = [
            'executar_flow.py', 'imagem',
            '--producao', str(self.root / 'production'),
            '--projeto', 'cli-project',
        ]
        with (
            patch.object(executar_flow, 'load_config', return_value=self.config),
            patch.object(executar_flow, 'load_clips', return_value=[clip]),
            patch.object(executar_flow, 'execute', side_effect=execute),
            patch.object(sys, 'argv', argv),
            redirect_stdout(io.StringIO()),
        ):
            result = executar_flow.main()

        self.assertEqual(result, 0)
        self.assertEqual(captured['args'].projeto, 'cli-project')
        self.assertEqual(captured['args'].delivery_dir, self.config.delivery_dir)

    def test_carousel_uses_configured_paths(self):
        captured = {}
        clip = {'plan': {'carrossel': {'ativo': True}}}

        def generate(loaded_clip, sheet, delivery):
            captured.update(sheet=sheet, delivery=delivery)
            return self.root / 'card.png'

        argv = ['gerar_carrossel.py', '--producao', str(self.root / 'production')]
        with (
            patch.object(gerar_carrossel, 'load_config', return_value=self.config),
            patch.object(gerar_carrossel.flow, 'load_clips', return_value=[clip]),
            patch.object(gerar_carrossel, 'generate', side_effect=generate),
            patch.object(sys, 'argv', argv),
            redirect_stdout(io.StringIO()),
        ):
            result = gerar_carrossel.main()

        self.assertEqual(result, 0)
        self.assertEqual(captured['sheet'], self.config.spreadsheet)
        self.assertEqual(captured['delivery'], self.config.delivery_dir)

    def test_preparer_uses_configured_paths(self):
        captured = {}

        def prepare(root, sheet, sources, output_dir=None):
            captured.update(root=root, sheet=sheet, output=output_dir)
            return {'pacotes': [], 'pendencias': []}

        argv = ['preparar_insumos.py', '--raiz', str(self.root), 'preparar']
        with (
            patch.object(preparar_insumos, 'load_config', return_value=self.config),
            patch.object(preparar_insumos, 'prepare', side_effect=prepare),
            patch.object(sys, 'argv', argv),
            redirect_stdout(io.StringIO()),
        ):
            result = preparar_insumos.main()

        self.assertEqual(result, 0)
        self.assertEqual(captured['root'], self.root)
        self.assertEqual(captured['sheet'], self.config.spreadsheet)
        self.assertEqual(captured['output'], self.config.output_dir)

    def test_invalid_configuration_returns_clean_error(self):
        error = pipeline_config.ConfigError('timeout invalido')
        stderr = io.StringIO()
        with (
            patch.object(rodar_pipeline, 'load_config', side_effect=error),
            patch.object(sys, 'argv', ['rodar_pipeline.py']),
            redirect_stderr(stderr),
        ):
            result = rodar_pipeline.main()

        self.assertEqual(result, 2)
        self.assertIn('configuracao invalida', stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
