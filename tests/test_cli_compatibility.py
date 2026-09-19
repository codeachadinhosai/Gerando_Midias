import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / 'scripts' / 'rodar_pipeline.py'


class CliProcessCompatibilityTest(unittest.TestCase):
    def run_command(self, arguments, extra_environment=None):
        environment = os.environ.copy()
        environment['PYTHONUTF8'] = '1'
        if extra_environment:
            environment.update(extra_environment)
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30,
            check=False,
        )

    def test_new_and_legacy_help_expose_the_same_options(self):
        new = self.run_command(['-m', 'pipeline_flow', '--help'])
        legacy = self.run_command([str(LEGACY), '--help'])

        self.assertEqual(new.returncode, 0, new.stderr)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertIn('usage: python -m pipeline_flow', new.stdout)
        self.assertIn('usage: rodar_pipeline.py', legacy.stdout)
        options = re.compile(r'--[a-z][a-z-]*')
        self.assertEqual(set(options.findall(new.stdout)), set(options.findall(legacy.stdout)))

    def test_new_and_legacy_cli_reject_invalid_config_without_traceback(self):
        invalid = {'GFLOW_TIMEOUT_SECONDS': 'invalido'}
        new = self.run_command(['-m', 'pipeline_flow', '--help'], invalid)
        legacy = self.run_command([str(LEGACY), '--help'], invalid)

        for result in (new, legacy):
            self.assertEqual(result.returncode, 2)
            self.assertIn('configuracao invalida', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_new_and_legacy_cli_reject_unknown_arguments(self):
        new = self.run_command(['-m', 'pipeline_flow', '--opcao-inexistente'])
        legacy = self.run_command([str(LEGACY), '--opcao-inexistente'])

        self.assertEqual(new.returncode, 2)
        self.assertEqual(legacy.returncode, 2)
        self.assertNotIn('Traceback', new.stderr)
        self.assertNotIn('Traceback', legacy.stderr)


if __name__ == '__main__':
    unittest.main()
