import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline_flow.services import diagnosticar_configuracao as diagnostics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL = PROJECT_ROOT / "exemplos" / "controle_pipeline_flow.modelo.xlsx"


class ConfigurationDiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        spreadsheet = self.root / "entradas" / "controle_pipeline_flow.xlsx"
        spreadsheet.parent.mkdir()
        shutil.copy2(MODEL, spreadsheet)

    def diagnose(self, **kwargs):
        options = {
            "module_available": lambda _name: True,
            "python_version": (3, 11, 0),
            "os_name": "nt",
            "access": lambda _path, _mode: True,
        }
        options.update(kwargs)
        return diagnostics.diagnose(self.root, **options)

    def create_complete_env(self):
        gflow = self.root / "gflow"
        binary = gflow / ".venv" / "Scripts" / "gflow.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"")
        (self.root / ".env").write_text(
            "GFLOW_PROJECT_ID=private-project-id\n"
            f"GFLOW_ROOT={gflow.as_posix()}\n"
            "GFLOW_VIDEO_MODEL=omni-flash\n",
            encoding="utf-8",
        )
        return binary

    def test_complete_environment_is_ready_without_writing_files(self):
        self.create_complete_env()
        before = {path.relative_to(self.root) for path in self.root.rglob("*")}

        report = self.diagnose(environ={})

        after = {path.relative_to(self.root) for path in self.root.rglob("*")}
        self.assertEqual(report["status"], "pronto")
        self.assertTrue(report["somente_leitura"])
        self.assertTrue(report["pipeline_local_pronto"])
        self.assertTrue(report["geracao_flow_pronta"])
        self.assertEqual(before, after)
        self.assertNotIn("private-project-id", json.dumps(report))

    def test_missing_flow_requirements_are_warnings_for_local_work(self):
        report = self.diagnose(
            environ={"GFLOW_ROOT": str(self.root / "gflow-ausente")}
        )

        statuses = {
            item["id"]: item["status"]
            for item in report["verificacoes"]
        }
        self.assertEqual(report["status"], "atencao")
        self.assertTrue(report["pipeline_local_pronto"])
        self.assertFalse(report["geracao_flow_pronta"])
        self.assertEqual(statuses["env"], "aviso")
        self.assertEqual(statuses["projeto_flow"], "aviso")
        self.assertEqual(statuses["gflow"], "aviso")

    def test_invalid_dotenv_returns_local_error(self):
        (self.root / ".env").write_text("isto nao e uma atribuicao\n", encoding="utf-8")

        report = self.diagnose(environ={})

        self.assertEqual(report["status"], "erro")
        self.assertFalse(report["pipeline_local_pronto"])
        check = next(
            item for item in report["verificacoes"]
            if item["id"] == "configuracao"
        )
        self.assertEqual(check["status"], "erro")
        self.assertIn("NOME=VALOR", check["mensagem"])

    def test_missing_required_dependency_blocks_local_readiness(self):
        report = self.diagnose(
            environ={},
            module_available=lambda name: name != "fastapi",
        )

        self.assertFalse(report["pipeline_local_pronto"])
        check = next(
            item for item in report["verificacoes"]
            if item["id"] == "dependencia_fastapi"
        )
        self.assertEqual(check["status"], "erro")

    def test_main_uses_nonzero_exit_only_for_local_errors(self):
        ready = {
            "status": "atencao",
            "somente_leitura": True,
            "pipeline_local_pronto": True,
            "geracao_flow_pronta": False,
            "configuracao": {},
            "verificacoes": [],
        }
        blocked = {**ready, "status": "erro", "pipeline_local_pronto": False}

        with (
            patch.object(diagnostics, "diagnose", return_value=ready),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(diagnostics.main(["--json"]), 0)
            self.assertTrue(json.loads(output.getvalue())["somente_leitura"])

        with (
            patch.object(diagnostics, "diagnose", return_value=blocked),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(diagnostics.main([]), 2)


if __name__ == "__main__":
    unittest.main()
