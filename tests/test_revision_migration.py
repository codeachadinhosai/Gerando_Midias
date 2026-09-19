import tempfile
import unittest
from pathlib import Path

from pipeline_flow.services.preparar_insumos import Invalid, validate_revision_migration


class RevisionMigrationTest(unittest.TestCase):
    def test_generated_image_can_migrate_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "frame.jpg"
            image.write_bytes(b"frame")
            validate_revision_migration({
                "imagem_status": "gerada",
                "imagem_arquivo": str(image),
                "video_status": "",
            })

    def test_completed_video_stays_blocked(self):
        with self.assertRaises(Invalid):
            validate_revision_migration({
                "imagem_status": "gerada",
                "imagem_arquivo": "frame.jpg",
                "video_status": "gerado",
            })

    def test_missing_generated_image_stays_blocked(self):
        with self.assertRaises(Invalid):
            validate_revision_migration({
                "imagem_status": "gerada",
                "imagem_arquivo": "missing.jpg",
                "video_status": "",
            })


if __name__ == "__main__":
    unittest.main()
