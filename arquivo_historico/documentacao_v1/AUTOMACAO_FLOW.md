# Automação conectada ao gflow existente

O novo `scripts/executar_flow.py` lê os planos já importados e chama o gflow instalado em `../gflow-videos/.venv/Scripts/gflow.exe`. Mantém a sessão em `../gflow-videos/data/flow_gflow`. Não modifica o código antigo nem a cópia de referência.

Execute na pasta prompts. Aponte explicitamente para a revisão desejada; o executor não escolhe a mais recente por data.

```powershell
$producao = 'preparados/flow/WAFFLE_VIDEO_01/b9180beada4abde7'
python scripts/executar_flow.py listar --producao $producao
```

`listar` verifica arquivos e hashes sem gerar, abrir navegador ou alterar a planilha. O exemplo é uma revisão existente, não uma recomendação para substituir outra revisão mais recente.

Antes de gerar, importe a resposta correspondente com `preparar_insumos.py importar --atualizar-excel`, conforme GUIA_INSUMOS_FLOW.md. A coluna plano_arquivo deve apontar para a revisão selecionada. Feche o Excel para permitir gravação. Faça login usando o script de login do projeto gflow existente se a sessão ainda não estiver pronta.

```powershell
python scripts/executar_flow.py imagem --producao $producao --projeto 'ID_DO_PROJETO_FLOW'
```

As imagens usam `nano2`, aspecto 9:16 e referências na ordem exportada. Cada chamada cria uma pasta gerados exclusiva dentro do clipe, com mídia e gflow.log. O arquivo execucao.json registra etapa, comando, modelo, horário e hashes. O Excel recebe o caminho da imagem e aguardando_aprovacao.

Abra e revise cada imagem. Marque aprovacao=aprovada na linha correspondente do Excel, salve e feche. Vincule a decisão ao arquivo exato, um clipe de cada vez:

```powershell
python scripts/executar_flow.py aprovar --producao $producao --clipe WAFFLE_VIDEO_01_01
```

Repita para os demais clipes revisados. O comando não altera o campo humano aprovacao. A decisão é vinculada ao caminho e SHA-256 da imagem; uma imagem diferente ou aprovação revogada bloqueia o vídeo.

```powershell
python scripts/executar_flow.py video --producao $producao --projeto 'ID_DO_PROJETO_FLOW' --modelo-video veo-fast
```

Vídeos usam i2v/r2v conforme plano, 9:16 e oito segundos. O modelo é explícito; padrão veo-fast. O executor respeita limites de referências do r2v. Adicione --clipe para processar somente um clipe. Use --gflow-raiz para outro ambiente e --planilha para outra planilha.

## Retomada e falhas

Repetir a mesma etapa verifica a mídia registrada e sincroniza o Excel sem gerar novamente. Se o Excel estiver aberto, a mídia e o registro ficam preservados; feche-o e repita.

Falha, timeout ou interrupção após iniciar uma chamada deixam tentativa registrada. A execução não reenvia automaticamente: confira o Flow e o log, pois o provedor pode ter consumido créditos e concluído a geração. A recuperação de uma tentativa incerta é manual. Não apague esse registro sem conferir o resultado. Um encerramento forçado também pode deixar .execucao.lock; remova-o somente após confirmar que o processo terminou.

Ativos finais completos podem ser reutilizados se ativo_existente_ref_id estiver nas referências exportadas. Recortes de trechos e montagem final ainda não são implementados. A ferramenta não faz classificação por IA, avaliação visual automática, nem validação técnica por ffprobe. O resultado gerado precisa de revisão visual. Não há tentativas automáticas pagas.

O ambiente existente deve estar instalado e autenticado. A disponibilidade real dos modelos e controles depende da conta Flow. A implementação foi validada localmente com chamadas simuladas e leitura dos planos; geração real não foi executada nessa entrega.

## Testes

```powershell
python -m unittest discover -s tests -v
```
