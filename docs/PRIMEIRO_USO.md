# Primeiro uso

Este guia leva uma pessoa de um clone limpo até uma revisão importada e aberta
no painel. Ele para antes de qualquer geração paga.

## 1. Pré-requisitos

- Windows com PowerShell;
- Git;
- Python 3.11 ou superior;
- acesso autorizado ao Flow.

O projeto instala `gflow-cli==0.74.0` e cria o executável:

```text
.venv/Scripts/gflow.exe
```

`GFLOW_ROOT` é necessário apenas para manter compatibilidade com uma
instalação externa existente.

## 2. Clonar e instalar

Abra o PowerShell:

```powershell
git clone https://github.com/codeachadinhosai/Gerando_Midias.git
Set-Location Gerando_Midias
powershell -ExecutionPolicy Bypass -File .\scripts\instalar.ps1
.\.venv\Scripts\Activate.ps1
```

O instalador valida Python 3.11 ou superior, cria a `.venv`, instala o projeto
com as ferramentas de desenvolvimento e instala o Chromium usado pelo
`gflow-cli`. Use `-SemDev` para omitir testes e lint ou `-SemChromium`
somente quando o navegador compatível já estiver instalado pelo Playwright.

## 3. Criar os arquivos locais

```powershell
Get-Item .env
Get-Item entradas\controle_pipeline_flow.xlsx
Get-Item identidade\identidade.txt
```

O instalador copia esses modelos somente quando ainda não existem. Eles são
ignorados pelo Git. O arquivo de identidade é fictício: substitua-o somente por
dados que você tenha autorização para usar.
Não versione o `.env`, a planilha operacional, identidades, respostas da IA,
produções, logs ou mídias.

## 4. Configurar o ambiente

Abra `.env` em um editor. Não cole as linhas `NOME=VALOR` diretamente no
PowerShell.

Para preparar e revisar sem gerar mídia, os caminhos padrão podem ser mantidos.
Para usar o Flow, configure:

```dotenv
GFLOW_PROJECT_ID=seu-projeto
GFLOW_VIDEO_MODEL=omni-flash
```

Deixe `GFLOW_ROOT` vazio para usar o executável instalado no projeto. O único
modelo de vídeo aceito pelo pipeline é `omni-flash`. Consulte
[Configuração](CONFIGURACAO.md) para todas as variáveis e sua precedência.

## 5. Fazer verificações sem geração

```powershell
gflow auth login --browser chrome
gflow auth status
python scripts\diagnosticar_configuracao.py
python -m pipeline_flow --help
python scripts\preparar_insumos.py --help
python scripts\gerar_imagens.py --help
python scripts\servir_painel.py --help
```

O login abre uma janela do navegador e salva a sessão somente no perfil local
do `gflow`, fora do Git. Ele não gera mídia. Se já houver uma sessão válida,
use apenas `gflow auth status`.

O diagnóstico não gera mídia, não cria arquivos e não executa o `gflow`. Ele
mostra separadamente se o pipeline local está pronto e se a geração no Flow
está disponível. Corrija qualquer `ERRO`; avisos sobre projeto ou
`gflow.exe` podem permanecer enquanto você trabalhar somente nas etapas
locais. Os comandos com `--help` também não executam o pipeline.

## 6. Preencher a primeira produção

Abra `entradas/controle_pipeline_flow.xlsx` e use a aba `Controle`:

1. preencha a partir da linha 4;
2. use uma linha por clipe;
3. defina `producao_id`, `produto_id`, `ordem` e `papel_na_producao`;
4. informe em `arquivo` uma imagem real colocada em `entradas/`;
5. descreva em `instrucao` o que preservar e o que alterar;
6. em `fala_audio`, deixe vazio para a IA criar a fala da Julia, escreva a fala
   exata desejada ou use `sem_audio` para pedir vídeo sem fala;
7. marque `classifica=sim` somente nas linhas desta rodada;
8. salve e feche o Excel.

A aba `Exemplo_Producao` contém dados fictícios para consulta e não é
processada como produção. Para detalhes de todas as colunas, consulte o
[guia da planilha](PLANILHA.md).

## 7. Preparar o pacote

```powershell
python scripts\preparar_insumos.py preparar
```

Esse comando não chama o Flow nem consome créditos. Confira:

- `preparados/relatorio_preparacao.json`;
- `preparados/pacotes/<producao_id>/<revisao>/`;
- `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip`.

Corrija qualquer pendência antes de classificar. Não renomeie revisões nem
misture arquivos de pacotes diferentes.

## 8. Classificar e importar

Siga o guia [IA e classificação](IA_E_CLASSIFICACAO.md). Ele descreve o pacote,
as responsabilidades da IA, o contrato atual e a importação. Os roteiros
históricos para
[um novo chat](../arquivo_historico/guias_legados/02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md) e
[outra IA](../arquivo_historico/guias_legados/01_COMO_USAR_EM_OUTRA_IA.md) permanecem disponíveis para
consulta detalhada.

A classificação deve produzir JSON puro, preservar `pacote_sha256` e não gerar
imagem, vídeo ou aprovação. Salve a resposta em
`preparados/respostas_ia/`.

Depois importe usando os caminhos reais informados na preparação:

```powershell
$Pacote = (Resolve-Path 'preparados/pacotes/PRODUCAO/REVISAO').Path
$Resposta = (Resolve-Path 'preparados/respostas_ia/ARQUIVO.json').Path
python scripts\preparar_insumos.py importar --pacote $Pacote --resposta $Resposta --atualizar-excel
```

A importação valida o contrato, preserva a revisão e atualiza a planilha com
backup. Ela não chama o Flow.

## 9. Abrir o painel

```powershell
python scripts\servir_painel.py
```

Abra `http://127.0.0.1:8765`. Navegar e consultar o painel não altera estado.
Operações de escrita pedem confirmação. A geração de vídeo exige imagem
aprovada e vinculada, confirmação final e a frase exata `GERAR VIDEO`.

Na aba **Assistente**, escolha uma situação, a produção e o clipe. Para usar
uma imagem pronta, informe também o nome do arquivo em `entradas/`. O painel
monta o comando PowerShell com a revisão real, explica a ordem dos passos e
avisa quando pode haver consumo de créditos. O botão **Copiar comando** copia
somente o texto: o assistente não executa o comando, não altera a planilha e
não chama o Flow.

Use **Continuar todo o pipeline** para o trabalho cotidiano. As demais opções
servem para consultar ou repetir uma etapa específica sem precisar digitar
manualmente produção, revisão e clipe.

Para encerrar o servidor, pressione `Ctrl+C` no terminal.

## 10. Chegar ao limite seguro

Antes de qualquer chamada externa, simule as imagens pendentes:

```powershell
python scripts\gerar_imagens.py
```

Sem `--executar`, o comando apenas lista o que faria. Até este ponto, nenhuma
chamada paga precisa ter sido feita.

O resultado é um resumo de todas as produções ativas, com quantidades
`pendentes`, `geradas`, `ja_concluidas`, `ignoradas` e `erros`. Você
não precisa informar produção ou clipe para obter essa visão geral.

Antes de continuar, copie o caminho exibido como `destino` ao importar a
resposta e informe o ID do clipe. Guarde esses dois textos em variáveis para
não precisar repetir caminhos longos:

```powershell
$Producao = 'preparados\flow\PRODUCAO\REVISAO'
$Clipe = 'PRODUCAO_01'
python scripts/executar_flow.py listar --producao $Producao --clipe $Clipe
```

Substitua somente os valores entre aspas. Não digite literalmente
`PRODUCAO`, `REVISAO` ou `PRODUCAO_01`. As variáveis são apenas apelidos
temporários válidos naquele terminal.

O filtro `--clipe` é opcional. Para listar todos os clipes de uma revisão,
use apenas:

```powershell
python scripts/executar_flow.py listar --producao $Producao
```

Use `--clipe $Clipe` quando quiser limitar uma aprovação ou geração a um
único item.

Confira o caminho da produção, o ID, `prompt_imagem.txt`, as referências na
ordem de `insumos_flow.json`, o projeto do Flow e a estimativa de custo antes
de executar uma geração.

## 11. Gerar a imagem

Faça primeiro a simulação limitada à revisão e ao clipe:

```powershell
python scripts/gerar_imagens.py --producao $Producao --clipe $Clipe
```

Para confirmar a chamada ao Flow:

```powershell
python scripts/gerar_imagens.py --producao $Producao --clipe $Clipe --executar
```

O segundo comando pode consumir créditos. Em caso de sucesso, o pipeline:

- preserva tentativas anteriores;
- grava a imagem em uma pasta versionada `gerados/<tentativa>/`;
- exporta uma cópia para `entregas_flow/`;
- atualiza `imagem_status`, `imagem_arquivo` e `atualizado_em` na planilha.

Não aprove a imagem sem abri-la e conferir produto, anatomia, identidade,
composição, texto visual e fidelidade ao prompt.

## 12. Aprovar ou rejeitar a imagem

Abra `imagem_arquivo`, registrado na aba `Controle`.

Se a imagem estiver correta:

1. escreva `aprovada` na coluna `aprovacao`;
2. salve e feche o Excel;
3. registre o vínculo técnico:

```powershell
python scripts/executar_flow.py aprovar --producao $Producao --clipe $Clipe
```

Esse comando não gera mídia nem consome créditos. Ele vincula a aprovação ao
arquivo, hash, pacote e revisão atuais. Alterar a imagem ou importar uma nova
revisão invalida esse vínculo.

Se a imagem estiver incorreta, escreva `rejeitada`, salve a planilha e não
execute o comando de vídeo.

## 13. Gerar o carrossel opcional

O carrossel só é criado quando a linha foi classificada com
`gerar_carrossel=sim` e o plano importado contém `carrossel.ativo=true`.
Ele é local, não chama o Flow e não exige `aprovacao=aprovada`.

```powershell
python scripts/gerar_carrossel.py --producao $Producao --clipe $Clipe
```

O arquivo é salvo em:

```text
entregas_flow/carrossel/<producao_id>/
```

Cada regeneração cria um arquivo versionado e preserva o anterior.

## 14. Liberar e gerar o vídeo

Antes da geração, confirme:

- plano com `gerar_video=true`;
- imagem atual registrada;
- `aprovacao=aprovada` na planilha;
- comando `aprovar` concluído para o frame atual;
- `GFLOW_PROJECT_ID` configurado;
- `gflow.exe` disponível;
- modelo `omni-flash`.

Consulte novamente o estado sem gerar:

```powershell
python scripts/executar_flow.py listar --producao $Producao --clipe $Clipe
```

Somente depois execute:

```powershell
python scripts/executar_flow.py video --producao $Producao --clipe $Clipe --modelo-video omni-flash
```

Esse comando chama o Flow e pode consumir créditos. Em caso de sucesso, o
pipeline preserva a tentativa em `gerados/<tentativa>/video.mp4`, exporta a
entrega para `entregas_flow/` e atualiza `video_status` e
`video_arquivo`.

## 15. Retomar e localizar resultados

Os caminhos atuais ficam registrados na aba `Controle`:

- `imagem_arquivo`: frame gerado ou registrado;
- `carrossel_arquivo`: card local;
- `video_arquivo`: vídeo final;
- `erro`: última falha operacional;
- `atualizado_em`: horário da última mudança.

Consulte também `entregas_flow/indice_entregas.json`. Se um comando falhar,
não apague revisões, tentativas, hashes ou locks. Corrija a causa e consulte as
[regras de recuperação](SOLUCAO_DE_PROBLEMAS.md).

O comando `python -m pipeline_flow` é o orquestrador cotidiano, mas pode
executar gerações pendentes quando já existem planos e aprovações válidas.
Use-o somente depois de entender o
[fluxo operacional](FLUXO_OPERACIONAL.md) e as
[regras de recuperação](SOLUCAO_DE_PROBLEMAS.md).

O orquestrador imprime um resumo e a seção `PRÓXIMA AÇÃO`, além de gravar:

```text
preparados/ultima_execucao_automatica.json
```

Ele não é um comando somente de consulta: pode preparar, importar, gerar
imagens, criar carrosséis e gerar todos os vídeos já aprovados. Para apenas
consultar, prefira `gerar_imagens.py` sem `--executar`,
`executar_flow.py listar` ou o painel local.

## Resultado esperado

Ao chegar ao final da seção 10, você deve ter:

- ambiente Python instalado;
- `.env` e planilha operacional somente locais;
- pacote preparado sem pendências;
- resposta da IA validada e importada;
- revisão visível no painel;
- nenhuma chamada paga feita durante as verificações.

Ao concluir também as etapas opcionais de execução, você deve ter:

- imagem gerada e revisada;
- aprovação humana vinculada tecnicamente ao frame atual;
- carrossel local, quando solicitado;
- vídeo de oito segundos gerado exclusivamente com `omni-flash`;
- entregas e estados registrados sem sobrescrever tentativas anteriores.
