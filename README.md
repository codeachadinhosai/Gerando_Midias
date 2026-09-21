# Pipeline Flow

Pipeline local para preparar insumos, importar a classificação da IA, registrar
e aprovar imagens, gerar carrosséis e liberar vídeos no Flow.

O projeto está em modernização incremental. O pacote `pipeline_flow`, os
scripts compatíveis e o painel web local compartilham os mesmos serviços.

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

Abrir o painel local:

```powershell
python scripts/servir_painel.py
```

O endereço padrão é `http://127.0.0.1:8765`. As consultas não alteram arquivos.
Na seção **Operações**, preparação de pacotes, importação de respostas e
registro de imagens exigem confirmação explícita. A seção **Revisão** permite
aprovar ou rejeitar o frame ativo; a decisão é revalidada contra revisão e
SHA-256, e a rejeição exige justificativa. Aprovar não inicia nem libera
automaticamente a execução do vídeo pelo painel.
A seção **Carrossel** reúne os cards autorizados por produção, mostra o conteúdo
do plano e permite gerar ou gerar novamente o PNG local. A autorização
`gerar_carrossel=sim` é independente da aprovação de vídeo; cada regeneração
cria outro arquivo, preserva a versão anterior e não chama o Flow nem consome
créditos.
A seção **Vídeos** mostra o estado de cada clipe e libera somente uma geração
paga por vez entre os processos oficiais do projeto. A ação exige imagem
aprovada e vinculada,
SHA-256 atual, `gflow.exe`, projeto configurado, checkbox, a frase
`GERAR VIDEO` e confirmação final. A execução ocorre em segundo plano e pode
consumir créditos; tentativas incertas permanecem bloqueadas para impedir
reenvio automático. Se `preparados/.locks/video-credit.lock` permanecer após
uma interrupção, confira `execucao.json`, `gflow.log` e o Flow antes de remover
a trava manualmente.

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
