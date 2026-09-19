## Execução automática

Use `python scripts/rodar_pipeline.py --projeto ID_DO_PROJETO_FLOW` para preparar, importar respostas compatíveis e executar todas as imagens e vídeos pendentes. Após revisar uma imagem nova, marque `aprovacao=aprovada` no Excel e rode o mesmo comando novamente. O relatório fica em `preparados/ultima_execucao_automatica.json`.

# Preparar insumos para imagens e vÃ­deos no Flow

A primeira etapa funciona localmente com Python 3.11+ e biblioteca padrÃ£o. NÃ£o precisa instalar pacotes, autenticar no Flow nem fornecer chave de API.

## 1. Planilha e referÃªncias
Edite entradas/controle_pipeline_flow.xlsx, aba Controle. CabeÃ§alho na linha 1; linhas 2 e 3 explicativas; registros desde a linha 4.
Uma linha ativa Ã© um clipe. Use producao_id e ordem para sequÃªncia, usar_com para referÃªncias do mesmo clipe.
Os IDs aceitam letras ASCII, nÃºmeros, hÃ­fen e sublinhado.
Por padrÃ£o as imagens sÃ£o buscadas em entradas/ e referencia_gflow_original/Fila Flow/. Se houver dois arquivos com o mesmo nome, informe um caminho relativo Ã  raiz de busca em vez de depender de uma escolha automÃ¡tica.
Para outras pastas, use --fontes. NÃ£o hÃ¡ leitura de .env ou sessÃµes do navegador.

## 2. Preparar pacote
Na pasta prompts:
```powershell
python scripts/preparar_insumos.py preparar
```
Resultado: preparados/pacotes/<producao_id>/<revisao>/.
ContÃ©m manifesto, classificador v2, contrato, identidade e anexos reais.
preparados/relatorio_preparacao.json lista pacotes e pendÃªncias. Uma linha invÃ¡lida bloqueia a produÃ§Ã£o correspondente, mas outras produÃ§Ãµes podem ser preparadas.
Reexecutar com as mesmas entradas reutiliza a revisÃ£o.

## 3. Classificar com uma IA
Entregue o conteÃºdo do pacote Ã  IA: instruÃ§Ãµes + manifesto + anexos reais. Pode ser esta conversa ou outra IA multimodal.
PeÃ§a resposta_ia.json conforme CONTRATO_INSUMOS.md, com os dois prompts completos quando houver geraÃ§Ã£o de imagem e vÃ­deo.
A preparaÃ§Ã£o nÃ£o inventa um plano nem chama uma IA sozinha. ImportaÃ§Ã£o manual Ã© a interface escolhida para permitir qualquer provedor.
Linhas que usam vÃ­deos requerem uma IA capaz de analisÃ¡-los. ExtraÃ§Ã£o de frames fica para uma prÃ³xima etapa.

## 4. Importar e exportar os insumos
```powershell
python scripts/preparar_insumos.py importar --pacote "preparados/pacotes/PRODUCAO/REVISAO" --resposta "caminho/resposta_ia.json" --atualizar-excel
```
A resposta Ã© validada antes da exportaÃ§Ã£o. A revisÃ£o deve corresponder ao pacote; campos humanos da planilha nÃ£o podem ter mudado.
Resultado: preparados/flow/<producao_id>/<revisao_da_resposta>/<id_clipe>/.
- prompt_imagem.txt: texto pronto para colar no Flow.
- prompt_video.txt: prompt do classificador para o vÃ­deo, quando aplicÃ¡vel.
- insumos_video.json: mÃ©todo, duraÃ§Ã£o e requisito de aprovaÃ§Ã£o; nÃ£o representa liberaÃ§Ã£o para gerar.
- referencias/: somente anexos selecionados, numerados.
- insumos_flow.json: ordem dos anexos, hashes, aspecto e modelo solicitado.
- plano_clipe.json: decisÃµes completas.
- COMO_USAR.txt: instruÃ§Ãµes da etapa manual.
O plano de produÃ§Ã£o fica na pasta superior. Casos pendentes recebem PENDENCIA.txt e nÃ£o tÃªm prompt pronto.

## 5. Gerar no Flow
Cole prompt_imagem.txt, anexe os arquivos de referencias/ na ordem indicada e selecione Nano Banana 2 e 9:16.
Esta entrega nÃ£o abre o navegador, nÃ£o gera imagem e nÃ£o consome crÃ©ditos.
A disponibilidade e os identificadores dos modelos devem ser conferidos no ambiente real.
Para usar uma imagem criada ou editada fora do executor, execute `python scripts/executar_flow.py registrar-imagem --producao PASTA --clipe ID --arquivo IMAGEM`. O comando copia a imagem para uma pasta versionada, calcula seu hash, atualiza o estado e revoga o vÃ­nculo tÃ©cnico de aprovaÃ§Ã£o anterior. Revise e registre `aprovacao=aprovada` ou `rejeitada`. Somente apÃ³s a nova aprovaÃ§Ã£o, use `prompt_video.txt` com a imagem aprovada (i2v) ou as referÃªncias indicadas no plano (r2v), em 9:16 e oito segundos. Se houver divergÃªncia visual, corrija a imagem ou revise o plano e os prompts.
ApÃ³s gerar e conferir o vÃ­deo, salve-o e registre video_arquivo, video_status=gerado e status=concluido. A geraÃ§Ã£o e o registro dessas etapas continuam manuais. NÃ£o reutilize o prompt de um pacote antigo como se tivesse sido validado pelo contrato novo.

## Estado e preservaÃ§Ã£o
A importaÃ§Ã£o com --atualizar-excel marca apenas classificado/imagem pendente, sem fingir geraÃ§Ã£o ou aprovaÃ§Ã£o.
Campos humanos, inclusive aprovacao, nÃ£o sÃ£o alterados.
Excel aberto pode impedir a atualizaÃ§Ã£o: os insumos permanecem salvos e ultima_importacao.json registra o erro; feche o Excel e repita.
Cada alteraÃ§Ã£o de XLSX tem backup em entradas/backups/. AlteraÃ§Ãµes simultÃ¢neas detectadas impedem a gravaÃ§Ã£o.
Imagens/vÃ­deos jÃ¡ em andamento ou concluÃ­dos nÃ£o tÃªm estados sobrescritos pela importaÃ§Ã£o.
NÃ£o renumerar clipes de uma produÃ§Ã£o jÃ¡ usada; criar nova producao_id para uma nova sequÃªncia.
Prompts e respostas de revisÃµes anteriores sÃ£o preservados. NÃ£o editar anexos dentro dos pacotes.

## Reparar as listas da planilha
```powershell
python scripts/preparar_insumos.py corrigir-planilha
```
Remove somente as validaÃ§Ãµes equivocadas O4:O500 e R4:R500. Preserva os valores e demais partes do XLSX, com backup.
O arquivo correto chama-se controle_pipeline_flow.xlsx, sem sufixo v3.

## Testes
```powershell
python -m unittest discover -s tests -v
```
A cÃ³pia referencia_gflow_original/ permanece intacta. Nada deve ser copiado de volta ao projeto de produÃ§Ã£o para testar esta primeira etapa.

## VersÃµes
Novos pacotes: 2.2-insumos. Pacotes 2.1 permanecem legÃ­veis e podem nÃ£o conter prompt_video.txt. Preparar novamente cria uma revisÃ£o com os contratos atuais; respostas e imagens anteriores permanecem preservadas. NÃ£o reimporte sobre clipes com mÃ­dia jÃ¡ gerada para atualizar seu estado.

