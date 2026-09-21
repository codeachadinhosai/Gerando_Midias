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
GFLOW_ROOT=D:/caminho/para/gflow-videos
GFLOW_VIDEO_MODEL=omni-flash
```

O `gflow` é externo a este repositório. Obtenha a instalação com a pessoa
responsável pelo ambiente. O pipeline procura o executável em:

```text
<GFLOW_ROOT>/.venv/Scripts/gflow.exe
```

## Variáveis do pipeline

| Variável | Padrão | Uso |
|---|---|---|
| `GFLOW_PROJECT_ID` | vazio | Projeto usado nas chamadas de geração. Obrigatório para gerar mídia. |
| `GFLOW_ROOT` | pasta `gflow-videos` irmã do projeto | Raiz externa que contém `.venv/Scripts/gflow.exe`. |
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
`<GFLOW_ROOT>/data/flow_gflow`. Prefira configurar `GFLOW_ROOT` diretamente.

No `.env` deste repositório, o pipeline interpreta diretamente apenas os
aliases `GFLOW_CLI_DEFAULT_PROJECT` e `GFLOW_CLI_HOME`. As demais variáveis
`GFLOW_CLI_*` do modelo são referências para o ambiente externo e não devem
ser consideradas automaticamente repassadas ao processo `gflow`. Configure-as
somente conforme a documentação da instalação fornecida pelo responsável.

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
python -m pipeline_flow --help
python scripts\servir_painel.py --help
Test-Path entradas\controle_pipeline_flow.xlsx
Test-Path D:\caminho\para\gflow-videos\.venv\Scripts\gflow.exe
```

Essas verificações não geram mídia. Ainda não existe um comando único de
diagnóstico; sua implementação permanece uma atividade separada da Fase 6.

## Erros comuns

- `gflow.exe nao encontrado`: corrija `GFLOW_ROOT` e confirme o caminho
  exato do executável;
- projeto ausente: preencha `GFLOW_PROJECT_ID` ou use `--projeto`;
- modelo inválido: mantenha `GFLOW_VIDEO_MODEL=omni-flash`;
- timeout inválido: use um inteiro positivo em `GFLOW_TIMEOUT_SECONDS`;
- planilha ausente: copie o modelo para
  `entradas/controle_pipeline_flow.xlsx`;
- painel recusado: mantenha `WEB_HOST=127.0.0.1` ou outro endereço loopback.

Para falhas operacionais depois da importação, consulte
[Solução de problemas](SOLUCAO_DE_PROBLEMAS.md).
