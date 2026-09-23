# Configuração

O pipeline lê a configuração a partir da raiz do projeto. Os valores seguem
esta precedência:

```text
argumento da CLI > variável do processo > arquivo .env > padrão seguro
```

O arquivo `.env` usa linhas `NOME=VALOR`. Essas linhas são conteúdo de
arquivo e não comandos PowerShell. Ele aceita valores entre aspas, mas não faz
interpolação de variáveis nem executa comandos.

## Configuração mínima

Copie o modelo:

```powershell
Copy-Item .env.example .env
```

Para operações que chamam o Flow:

```dotenv
GFLOW_PROJECT_ID=seu-projeto
GFLOW_VIDEO_MODEL=omni-flash
```

O instalador do projeto inclui `gflow-cli==0.74.0`. Sem `GFLOW_ROOT`, o
pipeline procura o executável em:

```text
<RAIZ_DO_PROJETO>/.venv/Scripts/gflow.exe
```

## Variáveis do pipeline

| Variável | Padrão | Uso |
|---|---|---|
| `GFLOW_PROJECT_ID` | vazio | Projeto usado nas chamadas de geração. Obrigatório para gerar mídia. |
| `GFLOW_ROOT` | raiz deste projeto | Sobrescreve a raiz do executável somente para uma instalação externa existente. |
| `GFLOW_VIDEO_MODEL` | `omni-flash` | Modelo de vídeo. O pipeline aceita somente `omni-flash`. |
| `GFLOW_TIMEOUT_SECONDS` | `1800` | Limite positivo, em segundos, para chamadas externas. |
| `PIPELINE_SPREADSHEET` | `entradas/controle_pipeline_flow.xlsx` | Planilha operacional. Caminho relativo parte da raiz do projeto. |
| `PIPELINE_OUTPUT_DIR` | `preparados` | Pacotes, respostas importadas, revisões e estados. |
| `PIPELINE_DELIVERY_DIR` | `entregas_flow` | Carrosséis e entregas finais. |
| `WEB_HOST` | `127.0.0.1` | Host do painel. Deve ser localhost ou loopback. |
| `WEB_PORT` | `8765` | Porta positiva do painel local. |

`GFLOW_CLI_DEFAULT_PROJECT` continua aceito como alias legado de
`GFLOW_PROJECT_ID`. Prefira o nome novo.

`GFLOW_CLI_HOME` continua aceito para inferir a raiz do `gflow` quando
`GFLOW_ROOT` não está preenchido. O formato esperado é
`<GFLOW_ROOT>/data/flow_gflow`. Em instalações novas, deixe ambos vazios.

No `.env` deste repositório, o pipeline interpreta diretamente apenas os
aliases `GFLOW_CLI_DEFAULT_PROJECT` e `GFLOW_CLI_HOME`. As demais variáveis
`GFLOW_CLI_*` do modelo são referências para o ambiente externo e não devem
ser consideradas automaticamente repassadas ao processo `gflow`. Configure-as
somente conforme a documentação da instalação fornecida pelo responsável.

O perfil, a sessão e os metadados locais do `gflow` ficam em `data/`, que é
ignorada pelo Git. Nunca versione essa pasta.

## Dependências e versões

`pyproject.toml` é a fonte das dependências instaláveis. O `gflow-cli` fica
fixado em `0.74.0` porque sua linha de comando é um contrato direto do
pipeline; atualizações exigem testes antes de alterar a versão. As demais
dependências usam faixas compatíveis e são verificadas pela suíte.

A matriz suportada é Windows com Python 3.11, versão mínima, e Python 3.13,
versão corrente. Antes da release `v1.0.0`, a instalação limpa deve ser
validada nas duas versões pela CI.

## Caminhos

Caminhos relativos em `.env` são resolvidos a partir da raiz do repositório.
Em Windows, prefira barras `/`:

```dotenv
GFLOW_ROOT=D:/ferramentas/gflow-videos
PIPELINE_SPREADSHEET=entradas/controle_pipeline_flow.xlsx
```

Não aponte `PIPELINE_OUTPUT_DIR` ou `PIPELINE_DELIVERY_DIR` para dentro de
pastas versionadas. Estados, respostas, logs e mídias devem permanecer fora do
Git.

## Sobrescritas pontuais

Os argumentos servem para uma execução específica:

```powershell
python -m pipeline_flow --projeto SEU_PROJETO --gflow-raiz D:\ferramentas\gflow-videos
```

Usar um argumento não altera o `.env`.

## Verificação segura

```powershell
python scripts\diagnosticar_configuracao.py
python scripts\diagnosticar_configuracao.py --json
python -m pipeline_flow --help
python scripts\servir_painel.py --help
```

O diagnóstico confere:

- Python 3.11 ou superior e plataforma;
- dependências de execução e `openpyxl`;
- existência e validade sintática do `.env`;
- carregamento da configuração sem executar o pipeline;
- existência e estrutura da aba `Controle` na planilha;
- permissão de escrita aparente nos diretórios configurados, sem criar arquivos;
- presença de `GFLOW_PROJECT_ID`, `gflow.exe` e modelo `omni-flash`.

A saída separa `Pipeline local` de `Geração no Flow`. A ausência do projeto
ou do executável externo aparece como aviso e não bloqueia preparação,
classificação, importação, revisão ou carrosséis locais. Erros que impedem o
trabalho local encerram o comando com código 2; avisos encerram com código 0.

`--json` produz uma saída estruturada para suporte e automação. O conteúdo do
`.env` e o identificador do projeto não são exibidos. Nenhuma dessas
verificações gera mídia, cria diretórios ou executa o `gflow`.

## Erros comuns

- `gflow.exe nao encontrado`: execute `scripts\instalar.ps1`; se estiver
  usando uma instalação externa, corrija `GFLOW_ROOT`;
- projeto ausente: preencha `GFLOW_PROJECT_ID` ou use `--projeto`;
- modelo inválido: mantenha `GFLOW_VIDEO_MODEL=omni-flash`;
- timeout inválido: use um inteiro positivo em `GFLOW_TIMEOUT_SECONDS`;
- planilha ausente: copie o modelo para
  `entradas/controle_pipeline_flow.xlsx`;
- painel recusado: mantenha `WEB_HOST=127.0.0.1` ou outro endereço loopback.

Para falhas operacionais depois da importação, consulte
[Solução de problemas](SOLUCAO_DE_PROBLEMAS.md).
