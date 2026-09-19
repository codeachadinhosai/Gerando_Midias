import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.preparar_insumos import (
    HEADERS,
    Invalid,
    ROOT,
    import_response,
    read_json,
    validate_response,
    write_json,
)

PACKAGE = ROOT/'preparados/pacotes/CX001_VIDEO_01/32191b2f87bbd692'

class PromptsTest(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(PACKAGE/'manifesto.json')
        self.response = read_json(ROOT/'preparados/respostas_ia/CX001_VIDEO_01.json')
        self.manifest['versao'] = '2.2-insumos'
        self.entry = self.response['clipes'][0]
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos. ' + self.entry['plano']['audio']['fala_exata']
        self.entry['plano']['arquivos_saida']['prompt_video'] = 'prompt_video.txt'

    def validate(self):
        return validate_response(self.response, self.manifest, PACKAGE)

    def current_workbook_rows(self):
        return [
            {
                **{name: clip["entrada"].get(name, "") for name in HEADERS},
                "_linha": clip["linha"],
            }
            for clip in self.manifest["clipes"]
        ]

    def test_identity_block_option_requires_boolean(self):
        self.entry['incluir_bloco_identidade'] = 'false'
        with self.assertRaises(Invalid): self.validate()

    def test_simple_prompt_export_keeps_identity_file(self):
        self.entry['incluir_bloco_identidade'] = False
        rows = self.current_workbook_rows()
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.preparar_insumos.Workbook') as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp)/'resposta.json'
            write_json(response_file, self.response)
            result = import_response(tmp, PACKAGE, response_file)
            folder = Path(result['destino'])/self.entry['plano']['id_clipe']
            prompt = (folder/'prompt_imagem.txt').read_text(encoding='utf-8')
            self.assertTrue(prompt.startswith(self.entry['prompt_imagem'].strip()))
            self.assertIn('ORDEM EXATA DOS ANEXOS:', prompt)
            if self.entry['plano']['identidade_julia']['necessaria']:
                self.assertEqual((folder/'identidade.txt').read_bytes(), (PACKAGE/'identidade.txt').read_bytes())

    def test_import_rejects_change_in_new_human_field(self):
        rows = self.current_workbook_rows()
        rows[0]["gerar_carrossel"] = "sim"
        with tempfile.TemporaryDirectory() as tmp, patch("scripts.preparar_insumos.Workbook") as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp) / "resposta.json"
            write_json(response_file, self.response)
            with self.assertRaisesRegex(Invalid, "Campos humanos mudaram"):
                import_response(tmp, PACKAGE, response_file)

    def editing_contract(self):
        self.manifest['versao'] = '2.3-insumos'
        for e in self.response['clipes']:
            p = e['plano']
            if p['pipeline']['gerar_imagem']:
                p['origem_clipe']['modo'] = 'adaptar'
                e['incluir_bloco_identidade'] = False
                p['edicao_imagem'] = {'base_ref_id': p['referencias'][0]['ref_id'], 'preservar': ['Cenário e objetos'], 'alterar': ['Expandir bordas para 9:16']}
                e['prompt_imagem'] = 'Edite a Referência 1 como imagem-base. Não recrie a cena do zero. ' + e['prompt_imagem']

    def test_editing_contract_accepts_explicit_base(self):
        self.editing_contract()
        self.validate()

    def test_editing_contract_rejects_missing_base(self):
        self.editing_contract()
        del self.entry['plano']['edicao_imagem']
        with self.assertRaises(Invalid): self.validate()

    def test_editing_contract_rejects_unknown_base(self):
        self.editing_contract()
        self.entry['plano']['edicao_imagem']['base_ref_id'] = 'missing'
        with self.assertRaises(Invalid): self.validate()

    def test_editing_contract_rejects_generation_prompt(self):
        self.editing_contract()
        self.entry['prompt_imagem'] = 'Crie uma fotografia 9:16.'
        with self.assertRaises(Invalid): self.validate()

    def test_editing_contract_rejects_empty_changes(self):
        self.editing_contract()
        self.entry['plano']['edicao_imagem']['alterar'] = []
        with self.assertRaises(Invalid): self.validate()

    def test_two_prompts(self):
        self.assertEqual(len(self.validate()), 1)

    def test_missing_video_rejected(self):
        del self.entry['prompt_video']
        with self.assertRaises(Invalid): self.validate()

    def test_wrong_speech_rejected(self):
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos. Fala diferente.'
        with self.assertRaises(Invalid): self.validate()

    def test_new_frame_requires_approval(self):
        self.entry['plano']['pipeline']['aprovacao_necessaria'] = False
        with self.assertRaises(Invalid): self.validate()

    def test_legacy_without_video(self):
        self.manifest['versao'] = '2.1-insumos'
        del self.entry['prompt_video']
        self.entry['plano']['arquivos_saida']['prompt_video'] = None
        self.assertEqual(len(self.validate()), 1)

    def test_no_video_no_prompt(self):
        self.entry['plano']['pipeline']['gerar_video'] = False
        with self.assertRaises(Invalid): self.validate()
        self.entry['prompt_video'] = None
        self.entry['plano']['arquivos_saida']['prompt_video'] = None
        self.assertEqual(len(self.validate()), 1)

    def test_pending_rejects_prompts(self):
        self.entry['plano']['status'] = 'pendente'
        self.entry['plano']['motivo'] = 'Referência insuficiente'
        self.entry['prompt_imagem'] = None
        with self.assertRaises(Invalid): self.validate()

    def test_export_and_repeat_preserve_media(self):
        # Snapshot isolates the test from the user's current approval and workbook.
        rows = self.current_workbook_rows()
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.preparar_insumos.Workbook') as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp)/'resposta.json'
            write_json(response_file, self.response)
            result = import_response(tmp, PACKAGE, response_file)
            folder = Path(result['destino'])/self.entry['plano']['id_clipe']
            self.assertEqual((folder/'prompt_video.txt').read_text(encoding='utf-8').strip(), self.entry['prompt_video'])
            self.assertTrue((folder/'prompt_imagem.txt').is_file())
            metadata = read_json(folder/'insumos_video.json')
            self.assertTrue(metadata['aprovacao_necessaria'])
            self.assertFalse(metadata['video_gerado'])
            media = folder/'imagem_gerada.jpeg'
            media.write_bytes(b'preservar')
            self.assertEqual(import_response(tmp, PACKAGE, response_file)['destino'], result['destino'])
            self.assertEqual(media.read_bytes(), b'preservar')
            wb.return_value.save.assert_not_called()

if __name__ == '__main__':
    unittest.main()
