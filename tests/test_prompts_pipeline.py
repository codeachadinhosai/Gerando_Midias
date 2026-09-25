import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline_flow.services.preparar_insumos import (
    HEADERS,
    Invalid,
    digest,
    import_response,
    read_json,
    validate_response,
    write_json,
)


def build_synthetic_package(root):
    package = root / 'pacote'
    attachments = package / 'anexos'
    attachments.mkdir(parents=True)

    base = attachments / 'ref_base.png'
    face = attachments / 'ref_face.png'
    classifier = package / 'CLASSIFICADOR_UNIVERSAL.txt'
    contract = package / 'CONTRATO_INSUMOS.md'
    identity = package / 'identidade.txt'
    base.write_bytes(b'synthetic base image')
    face.write_bytes(b'synthetic identity image')
    classifier.write_text('Synthetic classifier contract.\n', encoding='utf-8')
    contract.write_text('Synthetic input contract.\n', encoding='utf-8')
    identity.write_text('Synthetic identity reference.\n', encoding='utf-8')

    clip_id = 'PROD_TESTE_01_01'
    package_hash = 'a' * 64
    base_id = 'ref_base'
    face_id = 'ref_face'
    entry = {
        name: ''
        for name in HEADERS
    }
    entry.update({
        'classifica': 'sim',
        'arquivo': 'produto.png',
        'produto_id': 'produto_teste',
        'producao_id': 'PROD_TESTE_01',
        'ordem': '1',
        'papel_na_producao': 'principal',
        'tipo_referencia': 'base_edicao',
        'uso_material': 'nenhum',
        'gerar_carrossel': 'nao',
    })
    manifest = {
        'versao': '2.2-insumos',
        'producao_id': 'PROD_TESTE_01',
        'pacote_sha256': package_hash,
        'planilha': str(root / 'controle.xlsx'),
        'clipes': [{
            'linha': 4,
            'id_clipe': clip_id,
            'ordem': 1,
            'entrada': entry,
            'referencias': {
                'produto.png': base_id,
            },
        }],
        'referencias_globais': {
            'rosto.png': face_id,
        },
        'inventario': {
            base_id: {
                'id': base_id,
                'arquivo': 'anexos/ref_base.png',
                'nome_original': 'produto.png',
                'origem': 'synthetic',
                'sha256': digest(base),
            },
            face_id: {
                'id': face_id,
                'arquivo': 'anexos/ref_face.png',
                'nome_original': 'rosto.png',
                'origem': 'synthetic',
                'sha256': digest(face),
            },
        },
        'contratos': {
            'classificador': digest(classifier),
            'contrato': digest(contract),
        },
        'identidade_sha256': digest(identity),
    }
    plan = {
        'versao': '2.0',
        'producao_id': 'PROD_TESTE_01',
        'produto_id': 'produto_teste',
        'id_clipe': clip_id,
        'ordem': 1,
        'status': 'pronto',
        'papel_na_producao': 'principal',
        'classificacao': {
            'categoria': 'DetalhesProduto',
            'fluxo': '05_detalhes_produto',
        },
        'origem_clipe': {
            'modo': 'gerar',
            'trecho': None,
        },
        'referencias': [
            {
                'ref_id': base_id,
                'arquivo': 'anexos/ref_base.png',
                'tipo': 'base_edicao',
                'uso': 'Preservar produto e enquadramento.',
            },
            {
                'ref_id': face_id,
                'arquivo': 'anexos/ref_face.png',
                'tipo': 'identidade_rosto',
                'uso': 'Preservar identidade visual.',
            },
        ],
        'identidade_julia': {
            'necessaria': True,
            'rosto': True,
            'rosto_1': False,
            'corpo': False,
            'mao': False,
        },
        'estado_inicial': 'Produto estavel sobre a bancada.',
        'estado_final': 'Produto permanece estavel sobre a bancada.',
        'cena': {
            'ambiente': 'Cozinha clara.',
            'origem_ambiente': 'referencia',
            'apoio': 'Bancada clara.',
            'luz': 'Luz natural suave.',
            'camera': 'Camera vertical estavel.',
            'enquadramento': 'Produto inteiro em 9:16.',
            'roupa': 'Roupa lisa.',
            'maos': 'Maos naturais quando visiveis.',
        },
        'acao': {
            'descricao': 'Apresentar o produto sem deformar.',
        },
        'cronograma': [
            {'inicio_s': 0, 'fim_s': 1.2, 'acao': 'Estabelecer quadro.'},
            {'inicio_s': 1.2, 'fim_s': 3, 'acao': 'Iniciar movimento.'},
            {'inicio_s': 3, 'fim_s': 6.5, 'acao': 'Concluir movimento.'},
            {'inicio_s': 6.5, 'fim_s': 8, 'acao': 'Estabilizar quadro.'},
        ],
        'audio': {
            'ativo': True,
            'fala_exata': 'Este produto merece um olhar mais atento.',
            'inicio_s': 0,
            'fim_maximo_s': 6.5,
        },
        'pipeline': {
            'gerar_imagem': True,
            'metodo_imagem': 'i2i',
            'aprovacao_necessaria': True,
            'gerar_video': True,
            'metodo_video': 'i2v',
            'duracao_video_s': 8,
            'aspecto': '9:16',
            'usar_ativo_existente': False,
        },
        'arquivos_saida': {
            'prompt_imagem': 'prompt_imagem.txt',
            'prompt_video': 'prompt_video.txt',
        },
    }
    response = {
        'pacote_sha256': package_hash,
        'plano_producao': {
            'versao': '2.0',
            'producao_id': 'PROD_TESTE_01',
            'total_clipes': 1,
            'clipes': [{
                'id_clipe': clip_id,
                'ordem': 1,
                'papel': 'principal',
                'fluxo': '05_detalhes_produto',
            }],
        },
        'clipes': [{
            'incluir_bloco_identidade': True,
            'plano': plan,
            'prompt_imagem': 'Composicao de produto em formato 9:16.',
            'prompt_video': 'Video 9:16, 8 segundos.',
        }],
    }
    write_json(package / 'manifesto.json', manifest)
    write_json(root / 'resposta.json', response)
    return package, root / 'resposta.json'

class PromptsTest(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.package, response_file = build_synthetic_package(
            Path(self.fixture.name)
        )
        self.manifest = read_json(self.package / 'manifesto.json')
        self.response = read_json(response_file)
        self.manifest['versao'] = '2.2-insumos'
        self.entry = self.response['clipes'][0]
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos. ' + self.entry['plano']['audio']['fala_exata']
        self.entry['plano']['arquivos_saida']['prompt_video'] = 'prompt_video.txt'

    def validate(self):
        return validate_response(self.response, self.manifest, self.package)

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
        with tempfile.TemporaryDirectory() as tmp, patch('pipeline_flow.services.preparar_insumos.Workbook') as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp)/'resposta.json'
            write_json(response_file, self.response)
            result = import_response(tmp, self.package, response_file)
            folder = Path(result['destino'])/self.entry['plano']['id_clipe']
            prompt = (folder/'prompt_imagem.txt').read_text(encoding='utf-8')
            self.assertTrue(prompt.startswith(self.entry['prompt_imagem'].strip()))
            self.assertIn('ORDEM EXATA DOS ANEXOS:', prompt)
            if self.entry['plano']['identidade_julia']['necessaria']:
                self.assertEqual((folder/'identidade.txt').read_bytes(), (self.package/'identidade.txt').read_bytes())

    def test_import_rejects_change_in_new_human_field(self):
        rows = self.current_workbook_rows()
        rows[0]["gerar_carrossel"] = "sim"
        with tempfile.TemporaryDirectory() as tmp, patch("pipeline_flow.services.preparar_insumos.Workbook") as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp) / "resposta.json"
            write_json(response_file, self.response)
            with self.assertRaisesRegex(Invalid, "Campos humanos mudaram"):
                import_response(tmp, self.package, response_file)

    def editing_contract(self):
        self.manifest['versao'] = '2.3-insumos'
        for e in self.response['clipes']:
            p = e['plano']
            if p['pipeline']['gerar_imagem']:
                p['origem_clipe']['modo'] = 'adaptar'
                e['incluir_bloco_identidade'] = False
                p['edicao_imagem'] = {'base_ref_id': p['referencias'][0]['ref_id'], 'preservar': ['Cenário e objetos'], 'alterar': ['Expandir bordas para 9:16']}
                e['prompt_imagem'] = 'Edite a Referência 1 como imagem-base. Não recrie a cena do zero. ' + e['prompt_imagem']

    def audio_contract(self):
        self.editing_contract()
        self.manifest['versao'] = '2.4-insumos'

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

    def test_audio_contract_requires_julia_speech_by_default(self):
        self.audio_contract()
        self.entry['plano']['audio']['ativo'] = False
        self.entry['plano']['audio']['fala_exata'] = ''
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos, sem fala.'
        with self.assertRaisesRegex(Invalid, 'exige fala da Julia'):
            self.validate()

    def test_audio_contract_accepts_explicit_silence(self):
        self.audio_contract()
        self.manifest['clipes'][0]['entrada']['fala_audio'] = 'sem_audio'
        self.entry['plano']['audio']['ativo'] = False
        self.entry['plano']['audio']['fala_exata'] = ''
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos, sem fala.'
        self.validate()

    def test_audio_contract_preserves_human_speech_exactly(self):
        self.audio_contract()
        speech = 'A Julia apresenta este produto com naturalidade.'
        self.manifest['clipes'][0]['entrada']['fala_audio'] = speech
        with self.assertRaisesRegex(Invalid, 'preservada exatamente'):
            self.validate()
        self.entry['plano']['audio']['fala_exata'] = speech
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos. ' + speech
        self.validate()

    def test_legacy_editing_contract_allows_silent_principal_clip(self):
        self.editing_contract()
        self.entry['plano']['audio']['ativo'] = False
        self.entry['plano']['audio']['fala_exata'] = ''
        self.entry['prompt_video'] = 'Vídeo 9:16, 8 segundos, sem fala.'
        self.validate()

    def test_audio_contract_detects_changed_human_speech(self):
        self.audio_contract()
        write_json(self.package / 'manifesto.json', self.manifest)
        rows = self.current_workbook_rows()
        rows[0]['fala_audio'] = 'sem_audio'
        with tempfile.TemporaryDirectory() as tmp, patch(
            'pipeline_flow.services.preparar_insumos.Workbook'
        ) as workbook_type:
            workbook_type.return_value.records.return_value = rows
            response_file = Path(tmp) / 'resposta.json'
            write_json(response_file, self.response)
            with self.assertRaisesRegex(Invalid, 'Campos humanos mudaram'):
                import_response(tmp, self.package, response_file)

    def test_audio_contract_does_not_overwrite_human_speech(self):
        self.audio_contract()
        write_json(self.package / 'manifesto.json', self.manifest)
        rows = self.current_workbook_rows()
        with tempfile.TemporaryDirectory() as tmp, patch(
            'pipeline_flow.services.preparar_insumos.Workbook'
        ) as workbook_type:
            workbook = workbook_type.return_value
            workbook.records.return_value = rows
            response_file = Path(tmp) / 'resposta.json'
            write_json(response_file, self.response)
            import_response(
                tmp,
                self.package,
                response_file,
                update_excel=True,
            )
            updated_fields = {
                call.args[1]
                for call in workbook.set.call_args_list
            }
            self.assertNotIn('fala_audio', updated_fields)

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
        with tempfile.TemporaryDirectory() as tmp, patch('pipeline_flow.services.preparar_insumos.Workbook') as wb:
            wb.return_value.records.return_value = rows
            response_file = Path(tmp)/'resposta.json'
            write_json(response_file, self.response)
            result = import_response(tmp, self.package, response_file)
            folder = Path(result['destino'])/self.entry['plano']['id_clipe']
            self.assertEqual((folder/'prompt_video.txt').read_text(encoding='utf-8').strip(), self.entry['prompt_video'])
            self.assertTrue((folder/'prompt_imagem.txt').is_file())
            metadata = read_json(folder/'insumos_video.json')
            self.assertTrue(metadata['aprovacao_necessaria'])
            self.assertFalse(metadata['video_gerado'])
            media = folder/'imagem_gerada.jpeg'
            media.write_bytes(b'preservar')
            self.assertEqual(import_response(tmp, self.package, response_file)['destino'], result['destino'])
            self.assertEqual(media.read_bytes(), b'preservar')
            wb.return_value.save.assert_not_called()

    def test_import_revokes_approval_only_when_revision_changes(self):
        rows = self.current_workbook_rows()
        with tempfile.TemporaryDirectory() as tmp, patch(
            'pipeline_flow.services.preparar_insumos.Workbook'
        ) as workbook_type:
            workbook = workbook_type.return_value
            workbook.records.return_value = rows
            response_file = Path(tmp) / 'resposta.json'
            write_json(response_file, self.response)

            result = import_response(
                tmp,
                self.package,
                response_file,
                update_excel=True,
            )
            approval_updates = [
                call.args[2]
                for call in workbook.set.call_args_list
                if call.args[1] == 'aprovacao'
            ]
            self.assertEqual(approval_updates, [''])

            clip_id = self.entry['plano']['id_clipe']
            rows[0]['plano_arquivo'] = str(
                Path(result['destino']) / clip_id / 'plano_clipe.json'
            )
            workbook.set.reset_mock()

            import_response(
                tmp,
                self.package,
                response_file,
                update_excel=True,
            )
            updated_fields = {
                call.args[1]
                for call in workbook.set.call_args_list
            }
            self.assertNotIn('aprovacao', updated_fields)

if __name__ == '__main__':
    unittest.main()
