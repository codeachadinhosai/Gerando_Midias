# Primeiro uso

Este guia leva uma pessoa de um clone limpo até uma revisão importada e aberta
no painel. Ele para antes de qualquer geração paga.

## 1. Pré-requisitos

- Windows com PowerShell;
- Git;
- Python 3.11 ou superior;
- acesso autorizado ao Flow;
- `gflow` fornecido pela pessoa responsável pelo ambiente, caso seja necessário
  gerar imagens ou vídeos.

O `gflow` é uma dependência externa e não está incluído no repositório. A raiz
informada em `GFLOW_ROOT` deve conter:

```text
<GFLOW_ROOT>/.venv/Scripts/gflow.exe
```

Sem esse executável ainda é possível instalar o projeto, preparar pacotes,
classificar e importar respostas, revisar dados e trabalhar com carrosséis a
partir de uma imagem já registrada. Não tente gerar imagem ou vídeo.

## 2. Clonar e instalar

Abra o PowerShell:

```powershell
git clone https://github.com/codeachadinhosai/Gerando_Midias.git
Set-Location Gerando_Midias
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

O resultado de `py --version` deve ser Python 3.11 ou superior. A instalação
`.[dev]` é a recomendada nesta fase porque inclui as ferramentas de planilha,
testes e lint usadas pelo projeto.

## 3. Criar os arquivos locais

```powershell
Copy-Item .env.example .env
Copy-Item exemplos\controle_pipeline_flow.modelo.xlsx entradas\controle_pipeline_flow.xlsx
New-Item -ItemType Directory -Force identidade | Out-Null
Copy-Item exemplos\identidade.example.txt identidade\identidade.txt
```

Esses arquivos são ignorados pelo Git. O arquivo de identidade copiado é
fictício: substitua-o somente por dados que você tenha autorização para usar.
Não versione o `.env`, a planilha operacional, identidades, respostas da IA,
produções, logs ou mídias.

## 4. Configurar o ambiente

Abra `.env` em um editor. Não cole as linhas `NOME=VALOR` diretamente no
PowerShell.

Para preparar e revisar sem gerar mídia, os caminhos padrão podem ser mantidos.
Para usar o Flow, configure:

```dotenv
GFLOW_PROJECT_ID=seu-projeto
GFLOW_ROOT=D:/caminho/para/gflow-videos
GFLOW_VIDEO_MODEL=omni-flash
```

Use barras `/` ou caminhos absolutos válidos. O único modelo de vídeo aceito
pelo pipeline é `omni-flash`. Consulte
[Configuração](CONFIGURACAO.md) para todas as variáveis e sua precedência.

## 5. Fazer verificações sem geração

```powershell
python -m pipeline_flow --help
python scripts\preparar_insumos.py --help
python scripts\gerar_imagens.py --help
python scripts\servir_painel.py --help
Test-Path entradas\controle_pipeline_flow.xlsx
$GflowRoot = (Get-Content .env | Select-String '^GFLOW_ROOT=').Line.Split('=', 2)[1]
Test-Path (Join-Path $GflowRoot '.venv\Scripts\gflow.exe')
```

Os comandos com `--help` não executam o pipeline. O último teste é apenas uma
conferência de caminho; se `GFLOW_ROOT` ainda estiver com o valor de exemplo,
o resultado esperado é `False`.

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
[guia da planilha](../entradas/GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md).

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

Para classificar neste projeto, siga
[Como processar em um novo chat](../entradas/02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md).
Para outra IA, siga
[Como usar em outra IA](../entradas/01_COMO_USAR_EM_OUTRA_IA.md).

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
