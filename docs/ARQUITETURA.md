# Arquitetura do Pipeline Flow

Este documento descreve a arquitetura implementada do pipeline local. A regra
principal continua sendo: a IA planeja, o Python executa, a planilha controla e
a pessoa aprova frames antes de qualquer geracao de video.

## Componentes

### Planilha operacional

`entradas/controle_pipeline_flow.xlsx` e a fonte de verdade operacional. Ela
define quais linhas entram na rodada (`classifica=sim`), agrupa clipes por
`producao_id`, ordena por `ordem`, registra caminhos dos planos e acompanha
estados de imagem, carrossel, video e erro.

Campos humanos registram fatos, relacoes e intencao. Campos de sistema registram
resultado, estado e caminhos. A coluna `aprovacao` e uma decisao humana, mas a
liberacao tecnica de video tambem exige vinculo em `execucao.json`.

### Classificador Universal

`entradas/CLASSIFICADOR_UNIVERSAL.txt` e o cerebro criativo. Ele recebe o pacote
preparado, examina os anexos reais, respeita `CONTRATO_INSUMOS.md` e devolve um
`resposta_ia.json` com `pacote_sha256`, `plano_producao` e uma entrada por clipe
com `plano`, `prompt_imagem` e `prompt_video`.

O Python nao escolhe fluxo, cena, acao, fala, referencias criativas ou metodo
tecnico por conta propria. Essas decisoes pertencem ao plano importado.

`entradas/MENSAGEM_CLASSIFICACAO.txt` contem somente a instrucao operacional
que o orquestrador inclui nos pacotes consolidados. Ela fica separada dos guias
historicos para que a execucao nao dependa de documentacao arquivada.

### Pacote Python

O pacote principal fica em `src/pipeline_flow`.

- `domain`: estados canonicos, eventos operacionais e modelos sem acesso a
  arquivos.
- `services`: preparacao, importacao, diagnostico seguro, execucao Flow,
  carrossel, migracao, logs e controle de execucao.
- `web`: backend FastAPI local, consultas, operacoes confirmadas, templates e
  ativos da interface.
- `config.py`: fachada publica de configuracao.
- `cli.py`: comando principal `python -m pipeline_flow`.

Os scripts em `scripts/` sao wrappers compativeis com o fluxo anterior. Eles
chamam os servicos do pacote para evitar divergencia entre CLI e painel.

O diagnostico de configuracao e exposto por
`scripts/diagnosticar_configuracao.py`. Ele somente le ambiente, caminhos e a
estrutura da planilha; nao cria arquivos, nao inicia subprocessos e nao chama o
Flow. O relatorio separa a prontidao local da disponibilidade para geracao
externa.

### Backend local

O painel e servido por FastAPI em loopback:

```powershell
python scripts/servir_painel.py
```

O host precisa ser `localhost` ou endereco de loopback. Enderecos como
`0.0.0.0` ou IPs da rede local sao rejeitados.

Consultas `GET` remontam a visao do pipeline a partir da planilha, dos planos,
do indice de entregas e dos logs. Operacoes `POST` exigem confirmacao explicita
com `X-Pipeline-Confirmation: confirmar`.

## Configuracao

A configuracao e carregada por `pipeline_flow.services.load_config` na ordem:

1. variaveis do processo;
2. `.env` na raiz do projeto;
3. padroes seguros;
4. argumentos explicitos da CLI sobrescrevem o resultado quando existirem.

Variaveis reconhecidas:

- `GFLOW_PROJECT_ID`: projeto Flow usado para gerar video.
- `GFLOW_CLI_DEFAULT_PROJECT`: alias legado aceito durante a transicao.
- `GFLOW_ROOT`: raiz da instalacao do `gflow-videos`.
- `PIPELINE_SPREADSHEET`: caminho da planilha operacional.
- `PIPELINE_OUTPUT_DIR`: raiz de `preparados`.
- `PIPELINE_DELIVERY_DIR`: raiz de `entregas_flow`.
- `GFLOW_VIDEO_MODEL`: deve ser `omni-flash`; outros modelos são rejeitados.
- `GFLOW_TIMEOUT_SECONDS`: timeout positivo em segundos.
- `WEB_HOST`: host local do painel.
- `WEB_PORT`: porta local do painel.

`.env` nunca deve ser versionado. `.env.example` documenta os nomes esperados
sem segredos.

## Estados canonicos

Estados persistidos nos campos `status`, `imagem_status`, `video_status` e
`carrossel_status` sao gravados em `snake_case` ASCII. Grafias historicas com
acentos ou espacos continuam aceitas na leitura, mas novas escritas usam a forma
canonica.

- `status`: `novo`, `classificando`, `classificado`, `aguardando_imagem`,
  `imagem_gerada`, `aguardando_aprovacao`, `aprovada`, `pronto_para_video`,
  `gerando_video`, `material_validado`, `concluido`, `pendente`, `erro`.
- `imagem_status`: `pendente`, `gerando`, `gerada`, `nao_necessaria`, `erro`.
- `video_status`: `pendente`, `gerando`, `gerado`, `reutilizado`,
  `nao_necessario`, `erro`.
- `carrossel_status`: `pendente`, `gerando`, `gerado`, `nao_solicitado`,
  `erro`.

Valores desconhecidos falham com mensagem clara em vez de serem normalizados
silenciosamente.

## Persistencia e saidas

As pastas operacionais principais sao:

- `preparados/pacotes`: pacotes por producao e revisao.
- `preparados/pacotes_ia`: ZIP consolidado para classificacao.
- `preparados/respostas_ia`: respostas JSON preservadas.
- `preparados/flow`: planos, prompts, referencias e estados por revisao.
- `entregas_flow`: copias finais e carrosseis locais.
- `logs`: backups, migracoes, locks arquivados e registros tecnicos.

Midias historicas, respostas reais, logs, caches, planilhas reais e arquivos
pesados permanecem fora do Git.

## Seguranca operacional

- Nunca gerar video sem `aprovacao=aprovada` e vinculo tecnico valido.
- Nunca apagar ou sobrescrever midias historicas.
- Nao executar texto arbitrario vindo da interface.
- Evitar `shell=True`.
- Validar caminhos dentro das raizes autorizadas.
- Usar locks por clipe e trava global de credito para video.
- Fazer backup antes de migrar estados.
- Redigir projeto, prompts longos e linha de comando em APIs e logs seguros.
- Testes usam mocks e diretorios temporarios; nunca chamam o Flow real.

## Dependencias

Dependencias de execucao declaradas em `pyproject.toml`:

- `fastapi`;
- `Pillow`;
- `uvicorn`.

Dependencias de desenvolvimento:

- `openpyxl`;
- `pytest`;
- `ruff`.

O projeto requer Python 3.11 ou superior.
