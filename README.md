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
- Git;
- Python 3.11 ou superior;
- acesso ao Flow e ao identificador do projeto usado nas gerações;
- `gflow` externo, necessário apenas para gerar imagens ou vídeos.

O `gflow` não é distribuído neste repositório. Obtenha-o com a pessoa
responsável pelo ambiente e confirme que existe:

```text
<GFLOW_ROOT>\.venv\Scripts\gflow.exe
```

Preparação de pacotes, classificação, importação, revisão e carrosséis locais
podem ser organizados antes de configurar o executável externo.

## Primeiro uso

No PowerShell:

```powershell
git clone https://github.com/codeachadinhosai/Gerando_Midias.git
Set-Location Gerando_Midias
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
Copy-Item exemplos\controle_pipeline_flow.modelo.xlsx entradas\controle_pipeline_flow.xlsx
```

Edite o arquivo `.env`; as linhas `NOME=VALOR` são conteúdo do arquivo, não
comandos PowerShell. Para gerar mídia, preencha pelo menos:

```dotenv
GFLOW_PROJECT_ID=seu-projeto
GFLOW_ROOT=D:/caminho/para/gflow-videos
```

Antes de usar dados reais, leia o [guia de primeiro uso](docs/PRIMEIRO_USO.md)
e a [referência de configuração](docs/CONFIGURACAO.md). O guia cobre a planilha,
a classificação pela IA, a importação, o painel e o limite seguro antes de
qualquer operação paga.

## Comandos atuais

Diagnosticar a instalação sem gerar mídia:

```powershell
python scripts/diagnosticar_configuracao.py
```

O diagnóstico verifica Python, dependências, `.env`, planilha, diretórios e
disponibilidade do Flow. Ele não exibe o ID do projeto, não cria arquivos e não
executa o `gflow`.

Preparar um pacote para classificação:

```powershell
python scripts/preparar_insumos.py preparar
```

Executar o pipeline:

```powershell
python -m pipeline_flow
```

Esse comando percorre etapas pendentes e pode chamar o `gflow` quando já
existem planos importados e autorizações válidas. No primeiro uso, prepare e
importe os dados antes; faça a revisão pelo painel e confirme separadamente
qualquer geração.

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

## Licença

Este projeto é distribuído sob a [Licença MIT](LICENSE).

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

Documentação complementar:

- [primeiro uso](docs/PRIMEIRO_USO.md);
- [configuração](docs/CONFIGURACAO.md);
- [planilha operacional](docs/PLANILHA.md);
- [IA e classificação](docs/IA_E_CLASSIFICACAO.md);
- [fluxo operacional](docs/FLUXO_OPERACIONAL.md);
- [solução de problemas](docs/SOLUCAO_DE_PROBLEMAS.md);
- [referência histórica detalhada da planilha](entradas/GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md).
