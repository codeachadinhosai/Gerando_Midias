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
6. marque `classifica=sim` somente nas linhas desta rodada;
7. salve e feche o Excel.

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

Para encerrar o servidor, pressione `Ctrl+C` no terminal.

## 10. Limite seguro do primeiro uso

Antes de qualquer chamada externa, simule as imagens pendentes:

```powershell
python scripts\gerar_imagens.py
```

Sem `--executar`, o comando apenas lista o que faria. Não use `--executar`
até confirmar projeto, referências, prompt, custo e disponibilidade do
`gflow.exe`.

O comando `python -m pipeline_flow` é o orquestrador cotidiano, mas pode
executar gerações pendentes quando já existem planos e aprovações válidas.
Use-o somente depois de entender o
[fluxo operacional](FLUXO_OPERACIONAL.md) e as
[regras de recuperação](SOLUCAO_DE_PROBLEMAS.md).

## Resultado esperado

Ao terminar este guia, você deve ter:

- ambiente Python instalado;
- `.env` e planilha operacional somente locais;
- pacote preparado sem pendências;
- resposta da IA validada e importada;
- revisão visível no painel;
- nenhuma chamada paga feita durante as verificações.
