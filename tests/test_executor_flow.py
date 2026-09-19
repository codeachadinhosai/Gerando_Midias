import argparse
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import executar_flow as flow


class ExecutorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.clip = copy.deepcopy(flow.load_clips(flow.ROOT / 'preparados/flow/WAFFLE_VIDEO_01/6e4ffaf8f4d87925')[0])
        self.clip['folder'] = self.folder
        binary = self.folder / '.venv/Scripts/gflow.exe'
        binary.parent.mkdir(parents=True)
        binary.touch()
        self.args = argparse.Namespace(acao='imagem', arquivo=None, planilha=self.folder/'test.xlsx', gflow_raiz=self.folder, projeto='test', modelo_video='veo-fast', timeout=1)
        self.row = {'aprovacao': 'aprovada'}
        for name, value in [('Workbook', None), ('row_for', self.row), ('sync', None)]:
            p = patch.object(flow, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def generated(self, cmd, **kwargs):
        Path(cmd[cmd.index('-o')+1]).write_bytes(b'test media')
        return argparse.Namespace(returncode=0)

    def image(self):
        with patch.object(flow.subprocess, 'run', side_effect=self.generated) as run:
            flow.execute(self.clip, self.args)
            self.assertEqual(run.call_count, 1)

    def test_resume_does_not_generate_twice(self):
        self.image()
        with patch.object(flow.subprocess, 'run') as run:
            flow.execute(self.clip, self.args)
            run.assert_not_called()

    def test_video_blocked_without_bound_approval(self):
        self.image()
        self.args.acao = 'video'
        with patch.object(flow.subprocess, 'run') as run, self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)
        run.assert_not_called()

    def test_approved_video_uses_exact_frame(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        self.args.acao = 'video'
        with patch.object(flow.subprocess, 'run', side_effect=self.generated) as run:
            flow.execute(self.clip, self.args)
        cmd = run.call_args.args[0]
        frame = flow.state_for(self.clip)['imagem']['arquivo']
        self.assertEqual(cmd[cmd.index('--initial-frame')+1], frame)

    def test_revoked_approval_blocks(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        self.row['aprovacao'] = 'rejeitada'
        self.args.acao = 'video'
        with self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)

    def test_changed_frame_blocks(self):
        self.image()
        record = flow.state_for(self.clip)['imagem']
        Path(record['arquivo']).write_bytes(b'changed')
        self.args.acao = 'aprovar'
        with self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)

    def test_register_user_image_copies_and_revokes_bound_approval(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        supplied = self.folder / 'supplied.jpeg'
        supplied.write_bytes(b'user supplied image')
        self.args.acao = 'registrar-imagem'
        self.args.arquivo = supplied
        result = flow.execute(self.clip, self.args)
        state = flow.state_for(self.clip)
        self.assertEqual(result, 'imagem fornecida registrada; revisar e vincular nova aprovacao')
        self.assertEqual(state['imagem']['modelo'], 'fornecida_pelo_usuario')
        self.assertNotIn('aprovacao', state)
        self.assertNotEqual(Path(state['imagem']['arquivo']), supplied)
        self.assertEqual(Path(state['imagem']['arquivo']).read_bytes(), supplied.read_bytes())

    def test_failed_submission_is_not_retried(self):
        with patch.object(flow.subprocess, 'run', return_value=argparse.Namespace(returncode=1)), self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)
        with patch.object(flow.subprocess, 'run') as run, self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)
        run.assert_not_called()

    def test_excel_failure_preserves_generated_asset(self):
        with patch.object(flow, 'sync', side_effect=OSError('Excel aberto')), patch.object(flow.subprocess, 'run', side_effect=self.generated), self.assertRaises(OSError):
            flow.execute(self.clip, self.args)
        self.assertTrue(flow.media(flow.state_for(self.clip)['imagem']).exists())

    def test_reference_order_and_prompt_preserved(self):
        cmd = flow.command(self.clip, 'imagem', 'gflow', 'project', 'nano2', self.folder/'image.png')
        refs = [cmd[i+1] for i, v in enumerate(cmd) if v == '--ref']
        self.assertEqual(refs, [str(p) for p in self.clip['refs']])
        self.assertIn(self.clip['prompts']['imagem'], cmd)

    def test_input_change_rejected_after_generation(self):
        self.image()
        self.clip['fingerprint'] = 'changed'
        with self.assertRaises(flow.Invalid):
            flow.state_for(self.clip)

    def test_generated_media_is_exported_once(self):
        source = self.folder / 'imagem.jpg'
        source.write_bytes(b'generated image')
        record = {'arquivo': str(source), 'sha256': flow.digest(source), 'modelo': 'nano2'}
        root = self.folder / 'delivery-root'
        with patch.object(flow, 'ROOT', root):
            first = flow.export_delivery(self.clip, 'imagem', record)
            second = flow.export_delivery(self.clip, 'imagem', record)
        self.assertEqual(first, second)
        expected = '000001_{}_imagem.jpg'.format(self.clip['plan']['id_clipe'])
        self.assertEqual(first.name, expected)
        self.assertEqual(len(flow.read_json(root / 'entregas_flow/indice_entregas.json')), 1)

    def test_r2v_reference_limit(self):
        self.clip['plan']['pipeline']['metodo_video'] = 'r2v'
        with self.assertRaises(flow.Invalid):
            flow.command(self.clip, 'video', 'gflow', 'project', 'veo-fast', self.folder/'video.mp4')


if __name__ == '__main__':
    unittest.main()


