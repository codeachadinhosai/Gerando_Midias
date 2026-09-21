import argparse
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook as OpenpyxlWorkbook
from pipeline_flow.services import executar_flow as flow
from pipeline_flow.services.preparar_insumos import HEADERS, Workbook


def build_imported_revision(root):
    staging = root / 'fixture-revisions' / 'staging'
    clip_id = 'PROD_TESTE_01_01'
    clip_folder = staging / clip_id
    reference = clip_folder / 'referencias' / '01_produto.png'
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b'synthetic reference')

    plan = {
        'versao': '2.0',
        'producao_id': 'PROD_TESTE_01',
        'produto_id': 'produto_teste',
        'id_clipe': clip_id,
        'ordem': 1,
        'status': 'pronto',
        'papel_na_producao': 'principal',
        'origem_clipe': {
            'modo': 'adaptar',
            'trecho': None,
        },
        'pipeline': {
            'gerar_imagem': True,
            'metodo_imagem': 'i2i',
            'tipo_imagem': 'frame_inicial',
            'aprovacao_necessaria': True,
            'gerar_video': True,
            'metodo_video': 'i2v',
            'duracao_video_s': 8,
            'aspecto': '9:16',
            'usar_ativo_existente': False,
        },
    }
    summary = {
        'versao': '2.0',
        'producao_id': 'PROD_TESTE_01',
        'status': 'planejada',
        'clipes': [{
            'id_clipe': clip_id,
            'ordem': 1,
            'status_planejado': 'pronto',
        }],
    }
    flow_data = {
        'pacote_sha256': 'b' * 64,
        'referencias': [{
            'ref_id': 'ref_produto',
            'arquivo': 'referencias/01_produto.png',
            'ordem': 1,
            'sha256': flow.digest(reference),
        }],
    }
    response = {
        'pacote_sha256': 'b' * 64,
        'plano_producao': summary,
        'clipes': [{
            'plano': plan,
            'prompt_imagem': 'Prompt synthetic de imagem.',
            'prompt_video': 'Prompt synthetic de video.',
        }],
    }

    flow.write_json(staging / 'plano_producao.json', summary)
    flow.write_json(staging / 'resposta_ia.json', response)
    flow.write_json(clip_folder / 'plano_clipe.json', plan)
    flow.write_json(clip_folder / 'insumos_flow.json', flow_data)
    (clip_folder / 'prompt_imagem.txt').write_text(
        response['clipes'][0]['prompt_imagem'],
        encoding='utf-8',
    )
    (clip_folder / 'prompt_video.txt').write_text(
        response['clipes'][0]['prompt_video'],
        encoding='utf-8',
    )

    revision = staging.parent / flow.signature(response)[:16]
    staging.rename(revision)
    return revision


class ExecutorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.production = build_imported_revision(self.folder)
        self.clip = copy.deepcopy(flow.load_clips(self.production)[0])
        self.clip['folder'] = self.folder
        binary = self.folder / '.venv/Scripts/gflow.exe'
        binary.parent.mkdir(parents=True)
        binary.touch()
        self.args = argparse.Namespace(acao='imagem', arquivo=None, planilha=self.folder/'test.xlsx', gflow_raiz=self.folder, projeto='test', modelo_video='omni-flash', timeout=1)
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

    def operation_events(self):
        path = self.folder / 'logs' / 'eventos.jsonl'
        return [
            json.loads(line)
            for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]

    def test_success_writes_structured_operational_log(self):
        self.image()
        event = self.operation_events()[-1]
        self.assertEqual(event['producao_id'], self.clip['plan']['producao_id'])
        self.assertEqual(event['id_clipe'], self.clip['plan']['id_clipe'])
        self.assertEqual(event['etapa'], 'imagem')
        self.assertEqual(event['metodo'], 'i2i')
        self.assertEqual(event['erro'], '')
        self.assertIn('<redigido>', event['comando'])
        self.assertNotIn('test', event['comando'])

    def test_resume_does_not_generate_twice(self):
        self.image()
        with patch.object(flow.subprocess, 'run') as run:
            flow.execute(self.clip, self.args)
            run.assert_not_called()

    def test_success_persists_deterministic_idempotency_key(self):
        self.image()
        state = flow.state_for(self.clip)
        key = state['imagem']['idempotency_key']

        self.assertRegex(key, r'^[0-9a-f]{64}$')
        self.assertEqual(state['historico'][-1]['idempotency_key'], key)
        self.assertEqual(state['historico'][-1]['resultado'], 'concluida')

    def test_attempt_history_persists_only_command_hash(self):
        self.image()
        state_text = (self.folder / 'execucao.json').read_text(
            encoding='utf-8'
        )
        history = flow.state_for(self.clip)['historico'][-1]

        self.assertRegex(history['comando_sha256'], r'^[0-9a-f]{64}$')
        self.assertNotIn('comando', history)
        self.assertNotIn(self.args.projeto, state_text)
        self.assertNotIn(self.clip['prompts']['imagem'], state_text)

    def test_completed_attempt_is_recovered_without_resubmission(self):
        run_dir = self.folder / 'gerados' / 'interrupted'
        run_dir.mkdir(parents=True)
        output = run_dir / 'imagem.png'
        output.write_bytes(b'completed before process interruption')
        key = flow.operation_idempotency_key(
            self.clip,
            'imagem',
            'nano2',
        )
        state = flow.state_for(self.clip)
        state['tentativa'] = {
            'schema_version': 2,
            'etapa': 'imagem',
            'inicio': '2026-09-20T10:00:00Z',
            'comando': ['gflow', 'image'],
            'diretorio': str(run_dir),
            'saida': str(output),
            'modelo': 'nano2',
            'idempotency_key': key,
            'revisao_sha256': self.clip['revision_sha256'],
            'fingerprint_sha256': self.clip['fingerprint'],
        }
        flow.atomic(self.folder / 'execucao.json', state)

        with patch.object(flow.subprocess, 'run') as run:
            result = flow.execute(self.clip, self.args)

        run.assert_not_called()
        self.assertEqual(
            result,
            'tentativa recuperada sem nova chamada ao Flow',
        )
        recovered = flow.state_for(self.clip)
        self.assertNotIn('tentativa', recovered)
        self.assertTrue(recovered['imagem']['recuperada'])
        self.assertEqual(recovered['imagem']['idempotency_key'], key)
        self.assertEqual(
            recovered['historico'][-1]['resultado'],
            'recuperada_sem_reenvio',
        )

    def test_uncertain_attempt_stays_blocked_without_resubmission(self):
        run_dir = self.folder / 'gerados' / 'uncertain'
        run_dir.mkdir(parents=True)
        key = flow.operation_idempotency_key(
            self.clip,
            'imagem',
            'nano2',
        )
        state = flow.state_for(self.clip)
        state['tentativa'] = {
            'schema_version': 2,
            'etapa': 'imagem',
            'inicio': '2026-09-20T10:00:00Z',
            'comando': ['gflow', 'image'],
            'diretorio': str(run_dir),
            'saida': str(run_dir / 'imagem.png'),
            'modelo': 'nano2',
            'idempotency_key': key,
            'revisao_sha256': self.clip['revision_sha256'],
            'fingerprint_sha256': self.clip['fingerprint'],
        }
        flow.atomic(self.folder / 'execucao.json', state)

        with (
            patch.object(flow.subprocess, 'run') as run,
            self.assertRaisesRegex(flow.Invalid, key),
        ):
            flow.execute(self.clip, self.args)

        run.assert_not_called()
        self.assertIn('tentativa', flow.state_for(self.clip))

    def test_tampered_idempotency_key_is_rejected(self):
        run_dir = self.folder / 'gerados' / 'tampered-key'
        run_dir.mkdir(parents=True)
        state = flow.state_for(self.clip)
        state['tentativa'] = {
            'schema_version': 2,
            'etapa': 'imagem',
            'status': 'submetida',
            'inicio': '2026-09-20T10:00:00Z',
            'comando': ['gflow', 'image'],
            'diretorio': str(run_dir),
            'saida': str(run_dir / 'imagem.png'),
            'modelo': 'nano2',
            'idempotency_key': 'f' * 64,
            'revisao_sha256': self.clip['revision_sha256'],
            'fingerprint_sha256': self.clip['fingerprint'],
        }
        flow.atomic(self.folder / 'execucao.json', state)

        with (
            patch.object(flow.subprocess, 'run') as run,
            self.assertRaisesRegex(flow.Invalid, 'Chave idempotente'),
        ):
            flow.execute(self.clip, self.args)

        run.assert_not_called()

    def test_prepared_attempt_is_safely_retried_before_submission(self):
        run_dir = self.folder / 'gerados' / 'prepared'
        run_dir.mkdir(parents=True)
        key = flow.operation_idempotency_key(
            self.clip,
            'imagem',
            'nano2',
        )
        state = flow.state_for(self.clip)
        state['tentativa'] = {
            'schema_version': 2,
            'etapa': 'imagem',
            'status': 'preparada',
            'inicio': '2026-09-20T10:00:00Z',
            'comando': ['gflow', 'image'],
            'diretorio': str(run_dir),
            'saida': str(run_dir / 'imagem.png'),
            'modelo': 'nano2',
            'idempotency_key': key,
            'revisao_sha256': self.clip['revision_sha256'],
            'fingerprint_sha256': self.clip['fingerprint'],
        }
        flow.atomic(self.folder / 'execucao.json', state)

        with patch.object(
            flow.subprocess,
            'run',
            side_effect=self.generated,
        ) as run:
            flow.execute(self.clip, self.args)

        self.assertEqual(run.call_count, 1)
        resumed = flow.state_for(self.clip)
        self.assertEqual(
            resumed['historico'][-2]['resultado'],
            'descartada_antes_do_envio',
        )
        self.assertEqual(
            resumed['imagem']['idempotency_key'],
            key,
        )

    def test_video_attempt_does_not_accept_image_as_output(self):
        run_dir = self.folder / 'gerados' / 'wrong-output'
        run_dir.mkdir(parents=True)
        (run_dir / 'imagem.png').write_bytes(b'image is not a video')
        attempt = {
            'etapa': 'video',
            'diretorio': str(run_dir),
            'saida': str(run_dir / 'video.mp4'),
        }

        self.assertEqual(
            flow.attempt_output_candidates(self.clip, attempt),
            [],
        )

    def test_active_clip_lock_blocks_execution_and_is_preserved(self):
        handle = flow.acquire_clip_lock(self.clip, 'imagem')
        try:
            with self.assertRaisesRegex(flow.Invalid, 'processo ativo'):
                flow.execute(self.clip, self.args)
            self.assertTrue(handle.path.is_file())
        finally:
            flow.release_lock(handle)

    def test_video_blocked_without_bound_approval(self):
        self.image()
        self.args.acao = 'video'
        with patch.object(flow.subprocess, 'run') as run, self.assertRaises(flow.Invalid):
            flow.execute(self.clip, self.args)
        run.assert_not_called()

    def test_video_rejects_non_omni_model(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        self.args.acao = 'video'
        self.args.modelo_video = 'veo-fast'

        with (
            patch.object(flow.subprocess, 'run') as run,
            self.assertRaisesRegex(flow.Invalid, 'somente.*omni-flash'),
        ):
            flow.execute(self.clip, self.args)

        run.assert_not_called()
        self.assertNotIn('tentativa', flow.state_for(self.clip))

    def test_video_gate_cannot_be_disabled_by_plan_flag(self):
        self.image()
        self.clip['plan']['pipeline']['aprovacao_necessaria'] = False
        self.args.acao = 'video'

        with (
            patch.object(flow.subprocess, 'run') as run,
            self.assertRaisesRegex(flow.Invalid, 'Aprovacao ausente'),
        ):
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
        self.assertIs(run.call_args.kwargs['shell'], False)

    def test_global_credit_lock_blocks_paid_video_without_submission(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        self.args.acao = 'video'
        self.args.credit_lock_path = self.folder / 'video-credit.lock'
        handle = flow.acquire_lock(
            self.args.credit_lock_path,
            'video-pago',
        )
        try:
            with (
                patch.object(flow.subprocess, 'run') as run,
                self.assertRaisesRegex(flow.Invalid, 'Outra geracao paga'),
            ):
                flow.execute(self.clip, self.args)
        finally:
            flow.release_lock(handle)

        run.assert_not_called()
        self.assertNotIn('tentativa', flow.state_for(self.clip))
        self.assertFalse((self.folder / '.execucao.lock').exists())

    def test_video_revalidates_expected_frame_hash_before_submission(self):
        self.image()
        self.args.acao = 'aprovar'
        flow.execute(self.clip, self.args)
        self.args.acao = 'video'
        self.args.expected_image_sha256 = 'f' * 64

        with (
            patch.object(flow.subprocess, 'run') as run,
            self.assertRaisesRegex(flow.Invalid, 'imagem mudou'),
        ):
            flow.execute(self.clip, self.args)

        run.assert_not_called()
        self.assertNotIn('tentativa', flow.state_for(self.clip))

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
        event = self.operation_events()[-1]
        self.assertEqual(event['resultado'], 'erro')
        self.assertIn('gflow retornou 1', event['erro'])
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

    def test_delivery_index_cannot_redirect_copy_outside_delivery_root(self):
        source = self.folder / 'imagem.jpg'
        source.write_bytes(b'generated image')
        record = flow.media_record(
            self.clip, source, modelo='nano2'
        )
        delivery = self.folder / 'delivery-root'
        delivery.mkdir()
        outside = self.folder / 'outside.jpg'
        outside.write_bytes(b'preserve me')
        flow.atomic(delivery / 'indice_entregas.json', [{
            'sequencia': 1,
            'origem': str(source.resolve()),
            'entrega': str(outside.resolve()),
        }])

        with self.assertRaisesRegex(flow.Invalid, 'fora da pasta'):
            flow.export_delivery(
                self.clip, 'imagem', record, delivery
            )

        self.assertEqual(outside.read_bytes(), b'preserve me')
        self.assertFalse((delivery / '.indice_entregas.lock').exists())

    def test_media_record_outside_revision_is_rejected_when_bound_to_clip(self):
        outside = self.folder.parent / 'outside-media.jpg'
        outside.write_bytes(b'external media')
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        record = flow.media_record(
            self.clip, outside, modelo='nano2'
        )

        with self.assertRaisesRegex(flow.Invalid, 'fora da pasta da revisao'):
            flow.media(record, self.clip)

    def test_omni_flash_r2v_reference_limit(self):
        self.clip['plan']['pipeline']['metodo_video'] = 'r2v'
        self.clip['refs'] = [
            self.folder / f'referencia-{index}.png'
            for index in range(8)
        ]
        with self.assertRaises(flow.Invalid):
            flow.command(
                self.clip,
                'video',
                'gflow',
                'project',
                'omni-flash',
                self.folder / 'video.mp4',
            )

    def test_tampered_imported_response_is_rejected(self):
        source = self.production
        destination = self.folder / source.name
        shutil.copytree(source, destination)
        response_path = destination / 'resposta_ia.json'
        response = flow.read_json(response_path)
        response['teste_integridade'] = True
        flow.write_json(response_path, response)

        with self.assertRaisesRegex(flow.Invalid, 'Resposta importada alterada'):
            flow.load_clips(destination)

    def test_migration_loader_can_skip_pending_clips_explicitly(self):
        source = self.production
        staging = self.folder / 'staging-revision'
        shutil.copytree(source, staging)
        response_path = staging / 'resposta_ia.json'
        response = flow.read_json(response_path)
        pending = response['clipes'][0]['plano']
        pending['status'] = 'pendente'
        pending['motivo'] = 'Fixture de migracao'
        clip_id = pending['id_clipe']
        flow.write_json(
            staging / clip_id / 'plano_clipe.json',
            pending,
        )
        flow.write_json(response_path, response)
        revision = self.folder / flow.signature(response)[:16]
        staging.rename(revision)

        with self.assertRaisesRegex(flow.Invalid, 'Plano pendente'):
            flow.load_clips(revision)

        clips = flow.load_clips(revision, skip_pending=True)
        self.assertNotIn(
            clip_id,
            {clip['plan']['id_clipe'] for clip in clips},
        )


class IntegrityBindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.frame = self.folder / 'frame.png'
        self.frame.write_bytes(b'frame reviewed by a human')
        self.clip = {
            'folder': self.folder,
            'fingerprint': 'a' * 64,
            'revision_sha256': 'c' * 64,
            'flow': {'pacote_sha256': 'b' * 64},
            'plan': {
                'producao_id': 'PROD_01',
                'id_clipe': 'PROD_01_01',
            },
        }

    def test_approval_records_frame_clip_package_and_revision_hashes(self):
        approval = flow.approval_record(
            self.clip,
            self.frame,
            '2026-09-20T10:00:00Z',
        )

        self.assertTrue(flow.approval_is_bound(self.clip, approval, self.frame))
        self.assertEqual(approval['schema_version'], flow.APPROVAL_SCHEMA_VERSION)
        self.assertEqual(approval['producao_id'], 'PROD_01')
        self.assertEqual(approval['id_clipe'], 'PROD_01_01')
        self.assertEqual(approval['revisao_sha256'], self.clip['revision_sha256'])
        self.assertEqual(approval['fingerprint_sha256'], self.clip['fingerprint'])
        self.assertEqual(approval['pacote_sha256'], 'b' * 64)
        self.assertEqual(approval['imagem_sha256'], flow.digest(self.frame))
        self.assertEqual(approval['imagem_arquivo'], str(self.frame.resolve()))

    def test_approval_from_another_revision_is_not_bound(self):
        approval = flow.approval_record(self.clip, self.frame, 'now')
        changed = copy.deepcopy(self.clip)
        changed['fingerprint'] = 'c' * 64

        self.assertFalse(flow.approval_is_bound(changed, approval, self.frame))

    def test_legacy_approval_without_revision_fails_closed(self):
        legacy = {
            'sha256': flow.digest(self.frame),
            'arquivo': str(self.frame),
            'em': 'before-schema-2',
        }

        self.assertFalse(flow.approval_is_bound(self.clip, legacy, self.frame))

    def test_media_record_from_another_revision_is_rejected(self):
        record = flow.media_record(self.clip, self.frame, modelo='nano2')
        changed = copy.deepcopy(self.clip)
        changed['fingerprint'] = 'c' * 64

        with self.assertRaisesRegex(flow.Invalid, 'outra revisao'):
            flow.media(record, changed)

    def test_sync_revokes_unbound_spreadsheet_approval(self):
        state = {
            'fingerprint': self.clip['fingerprint'],
            'imagem': flow.media_record(
                self.clip,
                self.frame,
                modelo='fornecida_pelo_usuario',
            ),
        }

        with (
            patch.object(flow, 'Workbook') as workbook_type,
            patch.object(flow, 'row_for', return_value={'_linha': 2}),
        ):
            flow.sync(
                self.folder / 'controle.xlsx',
                self.clip,
                state,
                revoke_unbound_approval=True,
            )

        workbook = workbook_type.return_value
        updated = {
            call.args[1]: call.args[2]
            for call in workbook.set.call_args_list
        }
        self.assertEqual(updated['aprovacao'], '')

    def test_sync_preserves_current_bound_approval(self):
        image = flow.media_record(
            self.clip,
            self.frame,
            modelo='fornecida_pelo_usuario',
        )
        state = {
            'fingerprint': self.clip['fingerprint'],
            'imagem': image,
            'aprovacao': flow.approval_record(self.clip, self.frame, 'now'),
        }

        with (
            patch.object(flow, 'Workbook') as workbook_type,
            patch.object(flow, 'row_for', return_value={'_linha': 2}),
        ):
            flow.sync(
                self.folder / 'controle.xlsx',
                self.clip,
                state,
                revoke_unbound_approval=True,
            )

        updated_fields = {
            call.args[1]
            for call in workbook_type.return_value.set.call_args_list
        }
        self.assertNotIn('aprovacao', updated_fields)

    def test_sync_without_image_change_does_not_rewrite_approval(self):
        state = {
            'fingerprint': self.clip['fingerprint'],
            'imagem': flow.media_record(
                self.clip,
                self.frame,
                modelo='fornecida_pelo_usuario',
            ),
        }

        with (
            patch.object(flow, 'Workbook') as workbook_type,
            patch.object(flow, 'row_for', return_value={'_linha': 2}),
        ):
            flow.sync(self.folder / 'controle.xlsx', self.clip, state)

        updated_fields = {
            call.args[1]
            for call in workbook_type.return_value.set.call_args_list
        }
        self.assertNotIn('aprovacao', updated_fields)


class HumanImageReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'PROD_01_01'
        self.folder.mkdir()
        (self.folder / 'plano_clipe.json').write_text('{}', encoding='utf-8')
        self.frame = self.folder / 'frame.png'
        self.frame.write_bytes(b'review frame')
        self.clip = {
            'folder': self.folder,
            'fingerprint': 'a' * 64,
            'revision_sha256': 'c' * 64,
            'flow': {'pacote_sha256': 'b' * 64},
            'plan': {
                'producao_id': 'PROD_01',
                'id_clipe': 'PROD_01_01',
                'ordem': 1,
                'pipeline': {'gerar_video': True},
            },
        }
        self.sheet = Path(self.tmp.name) / 'controle.xlsx'
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
            'plano_arquivo': str(self.folder / 'plano_clipe.json'),
            'status': 'aguardando_aprovacao',
            'imagem_status': 'gerada',
        }
        sheet.append([values.get(name, '') for name in HEADERS])
        book.save(self.sheet)
        flow.atomic(self.folder / 'execucao.json', {
            'schema_version': flow.EXECUTION_SCHEMA_VERSION,
            'fingerprint': self.clip['fingerprint'],
            'imagem': flow.media_record(
                self.clip,
                self.frame,
                modelo='nano2',
            ),
            'historico': [],
        })

    def row(self):
        return Workbook(self.sheet).records()[0]

    def test_approval_updates_sheet_and_binds_exact_frame(self):
        result = flow.record_human_image_review(
            self.clip,
            self.sheet,
            'aprovada',
            flow.digest(self.frame),
        )

        state = flow.state_for(self.clip)
        self.assertEqual(result['decisao'], 'aprovada')
        self.assertEqual(self.row()['aprovacao'], 'aprovada')
        self.assertEqual(self.row()['status'], 'pronto_para_video')
        self.assertTrue(
            flow.approval_is_bound(self.clip, state['aprovacao'], self.frame)
        )
        self.assertEqual(state['historico'][-1]['resultado'], 'aprovada')
        self.assertFalse((self.folder / '.execucao.lock').exists())

    def test_rejection_revokes_binding_and_persists_reason(self):
        flow.record_human_image_review(
            self.clip,
            self.sheet,
            'aprovada',
            flow.digest(self.frame),
        )
        result = flow.record_human_image_review(
            self.clip,
            self.sheet,
            'rejeitada',
            flow.digest(self.frame),
            'Produto deformado no canto direito.',
        )

        state = flow.state_for(self.clip)
        row = self.row()
        self.assertEqual(result['decisao'], 'rejeitada')
        self.assertNotIn('aprovacao', state)
        self.assertEqual(row['aprovacao'], 'rejeitada')
        self.assertEqual(row['status'], 'aguardando_aprovacao')
        self.assertEqual(row['erro'], 'Produto deformado no canto direito.')
        self.assertEqual(
            state['historico'][-1]['justificativa'],
            'Produto deformado no canto direito.',
        )

    def test_changed_image_hash_fails_without_writes(self):
        original_state = (self.folder / 'execucao.json').read_bytes()
        original_sheet = self.sheet.read_bytes()

        with self.assertRaises(flow.ImageReviewConflict):
            flow.record_human_image_review(
                self.clip,
                self.sheet,
                'aprovada',
                'd' * 64,
            )

        self.assertEqual((self.folder / 'execucao.json').read_bytes(), original_state)
        self.assertEqual(self.sheet.read_bytes(), original_sheet)
        self.assertFalse((self.folder / '.execucao.lock').exists())

    def test_approval_state_failure_keeps_video_blocked(self):
        with (
            patch.object(flow, 'atomic', side_effect=OSError('state unavailable')),
            self.assertRaisesRegex(OSError, 'state unavailable'),
        ):
            flow.record_human_image_review(
                self.clip,
                self.sheet,
                'aprovada',
                flow.digest(self.frame),
            )

        self.assertEqual(self.row()['aprovacao'], 'aprovada')
        self.assertNotIn('aprovacao', flow.state_for(self.clip))

    def test_rejection_sheet_failure_revokes_binding_first(self):
        flow.record_human_image_review(
            self.clip,
            self.sheet,
            'aprovada',
            flow.digest(self.frame),
        )

        with (
            patch.object(flow.Workbook, 'save', side_effect=OSError('sheet unavailable')),
            self.assertRaisesRegex(OSError, 'sheet unavailable'),
        ):
            flow.record_human_image_review(
                self.clip,
                self.sheet,
                'rejeitada',
                flow.digest(self.frame),
                'Frame inconsistente.',
            )

        self.assertNotIn('aprovacao', flow.state_for(self.clip))


if __name__ == '__main__':
    unittest.main()


