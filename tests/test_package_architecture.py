import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import pipeline_flow
import scripts.pipeline_config as legacy_config
from pipeline_flow import adapters, domain, services


class PackageArchitectureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_public_facade_exposes_stable_configuration_api(self):
        self.assertIs(pipeline_flow.ConfigError, domain.ConfigError)
        self.assertIs(pipeline_flow.PipelineConfig, domain.PipelineConfig)
        self.assertIs(pipeline_flow.load_config, services.load_config)
        self.assertEqual(pipeline_flow.__version__, '0.1.0')
        self.assertIs(legacy_config.load_config, pipeline_flow.load_config)

    def test_layered_service_matches_legacy_configuration(self):
        dotenv = self.root / '.env'
        dotenv.write_text(
            'GFLOW_PROJECT_ID=project-from-env\n'
            'PIPELINE_OUTPUT_DIR=custom-output\n'
            'PIPELINE_DELIVERY_DIR=custom-delivery\n'
            'GFLOW_VIDEO_MODEL=omni-flash\n'
            'GFLOW_TIMEOUT_SECONDS=45\n',
            encoding='utf-8',
        )
        process = {'WEB_PORT': '9000'}

        current = legacy_config.load_config(self.root, environ=process)
        layered = pipeline_flow.load_config(self.root, environ=process)

        self.assertEqual(asdict(layered), asdict(current))
        self.assertEqual(layered.responses_dir, current.responses_dir)

    def test_domain_validation_has_no_environment_dependency(self):
        self.assertEqual(domain.positive_int('12', 1, 'VALUE'), 12)
        self.assertEqual(domain.video_model(''), 'omni-flash')
        with self.assertRaisesRegex(domain.ConfigError, 'VALUE'):
            domain.positive_int('zero', 1, 'VALUE')

    def test_dotenv_adapter_is_conservative(self):
        path = self.root / '.env'
        path.write_text('export GFLOW_PROJECT_ID=\'local project\'\n', encoding='utf-8')
        self.assertEqual(
            adapters.read_dotenv(path),
            {'GFLOW_PROJECT_ID': 'local project'},
        )
        path.write_text('comando sem atribuicao\n', encoding='utf-8')
        with self.assertRaises(domain.ConfigError):
            adapters.read_dotenv(path)


if __name__ == '__main__':
    unittest.main()
