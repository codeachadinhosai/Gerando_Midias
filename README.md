# Pipeline Flow

Pipeline local para preparar insumos, importar a classificação da IA, registrar
e aprovar imagens, gerar carrosséis e liberar vídeos no Flow.

O projeto está em modernização incremental. Os scripts atuais continuam sendo a
interface oficial até a criação do pacote `pipeline_flow`.

## Regras de segurança

- nunca gerar vídeo sem `aprovacao=aprovada`;
- não apagar ou sobrescrever mídias históricas;
- preservar hashes, revisões, locks e retomada idempotente;
- manter `.env`, planilhas reais, produções, respostas, logs e mídias fora do
  Git;
- testes não podem chamar o Flow real.

Consulte [o plano de modernização](docs/PLANO_MODERNIZACAO.md) antes de alterar
a arquitetura.

## Requisitos

- Windows com PowerShell;
- Python 3.11 ou superior;
- gflow instalado em uma pasta irmã ou indicado por `--gflow-raiz`;
- Pillow para renderização dos carrosséis.

## Instalação para desenvolvimento

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
Copy-Item .env.example .env
```

Os scripts carregam automaticamente o `.env` da raiz. Preencha
`GFLOW_PROJECT_ID` uma vez para não precisar repetir o projeto nos comandos.
Durante a transição, `GFLOW_CLI_DEFAULT_PROJECT` continua aceito. A precedência
é: argumento explícito da CLI, variável do processo, valor do `.env` e padrão
seguro.

```powershell
GFLOW_PROJECT_ID=seu-projeto
```

## Comandos atuais

Preparar um pacote para classificação:

```powershell
python scripts/preparar_insumos.py preparar
```

Executar o pipeline:

```powershell
python -m pipeline_flow
```

`--projeto seu-projeto` continua disponível para sobrescrever a configuração
em uma execução específica.

O comando histórico permanece compatível durante a modernização:

```powershell
python scripts/rodar_pipeline.py
```

Listar ou operar uma produção já preparada:

```powershell
python scripts/executar_flow.py listar --producao CAMINHO_DA_PRODUCAO
```

Renderizar manualmente um card:

```powershell
python scripts/gerar_carrossel.py --producao CAMINHO_DA_PRODUCAO --clipe ID_DO_CLIPE
```

## Testes

```powershell
python -m pytest
```

Os testes devem usar diretórios temporários e mocks. Nenhuma chamada paga ou
geração real deve ocorrer.

## Dados locais

O repositório versionará código, contratos, guias e exemplos sanitizados.
Arquivos reais permanecem nas pastas operacionais ignoradas pelo Git.

Modelos seguros para copiar:

- [planilha-modelo](exemplos/controle_pipeline_flow.modelo.xlsx);
- [identidade fictícia](exemplos/identidade.example.txt).

Para regenerar a planilha de forma determinística:

```powershell
python scripts/gerar_modelo_planilha.py
```
