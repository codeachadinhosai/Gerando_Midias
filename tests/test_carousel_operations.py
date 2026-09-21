import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook as OpenpyxlWorkbook
from PIL import Image

from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services import gerar_carrossel as carousel
from pipeline_flow.services.preparar_insumos import HEADERS, Workbook


class CarouselOperationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'PROD_01_01'
        self.folder.mkdir()
        self.frame = self.folder / 'frame.png'
        Image.new('RGB', (90, 160), 'white').save(self.frame, 'PNG')
        self.plan = {
            'producao_id': 'PROD_01',
            'id_clipe': 'PROD_01_01',
            'ordem': 1,
            'papel_na_producao': 'cta',
            'pipeline': {'gerar_video': True},
            'carrossel': {
                'ativo': True,
                'formato': '9:16',
                'texto': 'Um título útil',
                'subtexto': 'Destaque curto',
                'cta': 'Salve para consultar depois',
                'cta_destino': 'salvar',
                'cta_palavra': 'CASA',
            },
        }
        (self.folder / 'plano_clipe.json').write_text(
            json.dumps(self.plan),
            encoding='utf-8',
        )
        self.clip = {
            'folder': self.folder,
            'fingerprint': 'a' * 64,
            'revision_sha256': 'c' * 64,
            'flow': {'pacote_sha256': 'b' * 64, 'referencias': []},
            'plan': self.plan,
        }
        self.sheet = self.root / 'controle.xlsx'
        book = OpenpyxlWorkbook()
        sheet = book.active
        sheet.title = 'Controle'
        sheet.append(HEADERS)
        sheet.append([''] * len(HEADERS))
        sheet.append([''] * len(HEADERS))
        values = {
            'classifica': 'sim',
            'producao_id': 'PROD_01',
            'ordem': '1',
            'papel_na_producao': 'cta',
            'plano_arquivo': str(self.folder / 'plano_clipe.json'),
            'imagem_status': 'gerada',
            'aprovacao': 'rejeitada',
            'gerar_carrossel': 'sim',
            'carrossel_status': 'pendente',
        }
        sheet.append([values.get(name, '') for name in HEADERS])
        book.save(self.sheet)
        flow.atomic(self.folder / 'execucao.json', {
            'schema_version': flow.EXECUTION_SCHEMA_VERSION,
            'fingerprint': self.clip['fingerprint'],
            'imagem': flow.media_record(
                self.clip,
                self.frame,
                modelo='fornecida_pelo_usuario',
            ),
        })
        self.delivery = self.root / 'entregas'

    @staticmethod
    def fake_render(_source, destination, _carousel, papel='principal'):
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (carousel.WIDTH, carousel.HEIGHT), 'white').save(
            destination,
            'PNG',
        )

    def row(self):
        return Workbook(self.sheet).records()[0]

    def test_generation_is_local_and_independent_from_video_approval(self):
        with patch.object(carousel, 'render', side_effect=self.fake_render):
            destination = carousel.generate(
                self.clip,
                self.sheet,
                self.delivery,
                expected_image_sha256=flow.digest(self.frame),
            )

        state = flow.state_for(self.clip)
        row = self.row()
        self.assertTrue(destination.is_file())
        self.assertEqual(state['carrossel']['arquivo'], str(destination))
        self.assertEqual(state['carrossel']['origem_sha256'], flow.digest(self.frame))
        self.assertEqual(row['carrossel_status'], 'gerado')
        self.assertEqual(row['aprovacao'], 'rejeitada')
        event = json.loads(
            (self.folder / 'logs' / 'eventos.jsonl')
            .read_text(encoding='utf-8')
            .splitlines()[-1]
        )
        self.assertEqual(event['etapa'], 'carrossel')
        self.assertEqual(event['metodo'], 'renderizacao_local')

    def test_regeneration_creates_new_file_and_preserves_previous(self):
        with patch.object(carousel, 'render', side_effect=self.fake_render) as render:
            first = carousel.generate(
                self.clip,
                self.sheet,
                self.delivery,
                expected_image_sha256=flow.digest(self.frame),
            )
            second = carousel.generate(
                self.clip,
                self.sheet,
                self.delivery,
                expected_image_sha256=flow.digest(self.frame),
                force=True,
            )

        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        self.assertEqual(render.call_count, 2)
        self.assertEqual(flow.state_for(self.clip)['carrossel']['arquivo'], str(second))

    def test_stale_image_hash_blocks_before_rendering_or_state_change(self):
        original = (self.folder / 'execucao.json').read_bytes()
        with (
            patch.object(carousel, 'render') as render,
            self.assertRaises(carousel.CarouselConflict),
        ):
            carousel.generate(
                self.clip,
                self.sheet,
                self.delivery,
                expected_image_sha256='d' * 64,
            )

        render.assert_not_called()
        self.assertEqual((self.folder / 'execucao.json').read_bytes(), original)
        self.assertFalse((self.delivery / 'carrossel').exists())
        self.assertFalse((self.folder / '.execucao.lock').exists())

    def test_destination_cannot_escape_delivery_directory(self):
        original = (self.folder / 'execucao.json').read_bytes()
        self.clip['plan']['producao_id'] = '../../fora'

        with (
            patch.object(
                carousel.flow,
                'row_for',
                return_value={
                    'gerar_carrossel': 'sim',
                    'ordem': '1',
                    'papel_na_producao': 'cta',
                },
            ),
            patch.object(carousel, 'render') as render,
            self.assertRaisesRegex(
                carousel.Invalid,
                'fora da pasta de entregas',
            ),
        ):
            carousel.generate(
                self.clip,
                self.sheet,
                self.delivery,
                expected_image_sha256=flow.digest(self.frame),
            )

        render.assert_not_called()
        self.assertEqual((self.folder / 'execucao.json').read_bytes(), original)
        self.assertFalse((self.root / 'fora').exists())
        self.assertFalse((self.folder / '.execucao.lock').exists())


if __name__ == '__main__':
    unittest.main()
