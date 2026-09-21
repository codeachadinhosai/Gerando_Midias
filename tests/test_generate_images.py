import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from pipeline_flow.services import gerar_imagens


class GenerateImagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.args = Namespace(
            planilha=self.root / 'control.xlsx',
            output_dir=self.root / 'output',
            delivery_dir=self.root / 'delivery',
            gflow_raiz=self.root / 'gflow',
            projeto='project-id',
            timeout=30,
            producao=self.root / 'production',
            clipe=None,
            executar=False,
        )

    @staticmethod
    def clip(generate=True, completed=False):
        return {
            'plan': {
                'id_clipe': 'CLIP_01',
                'pipeline': {'gerar_imagem': generate},
            },
            'state': {'imagem': {'arquivo': 'image.png'}}
            if completed else {},
        }

    def test_simulation_does_not_call_flow(self):
        clip = self.clip()
        with (
            patch.object(gerar_imagens.flow, 'load_clips', return_value=[clip]),
            patch.object(gerar_imagens.flow, 'state_for', return_value={}),
            patch.object(gerar_imagens.flow, 'execute') as execute,
        ):
            report = gerar_imagens.run(self.args)

        self.assertEqual(report['pendentes'], 1)
        self.assertEqual(report['geradas'], 0)
        execute.assert_not_called()

    def test_execution_uses_image_stage_and_skips_completed(self):
        self.args.executar = True
        pending = self.clip()
        completed = self.clip(completed=True)
        completed['plan']['id_clipe'] = 'CLIP_02'

        def state_for(clip):
            return clip['state']

        with (
            patch.object(
                gerar_imagens.flow,
                'load_clips',
                return_value=[pending, completed],
            ),
            patch.object(
                gerar_imagens.flow,
                'state_for',
                side_effect=state_for,
            ),
            patch.object(
                gerar_imagens.flow,
                'execute',
                return_value='gerado; revisar resultado visualmente',
            ) as execute,
        ):
            report = gerar_imagens.run(self.args)

        self.assertEqual(report['geradas'], 1)
        self.assertEqual(report['ja_concluidas'], 1)
        self.assertEqual(execute.call_args.args[1].acao, 'imagem')


if __name__ == '__main__':
    unittest.main()
