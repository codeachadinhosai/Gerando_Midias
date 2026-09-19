# Plano de modernização do Pipeline Flow

Status: Fase 2 concluída e versionada localmente; Fase 3 pendente
Última atualização: 2026-09-19  
Documento de referência para continuidade entre contas e sessões do Codex.

## 1. Objetivo

Transformar o pipeline atual em um projeto Git organizado, documentado,
configurável por `.env` e operável por uma interface web local, preservando
todo o comportamento já validado.

Resultados esperados:

- comandos simples e configuração centralizada;
- código separado por responsabilidade;
- documentação suficiente para manutenção por outra pessoa ou agente;
- testes sem consumo de créditos do Flow;
- interface clara para acompanhar, revisar e executar o pipeline;
- migração incremental, sem apagar histórico nem interromper o fluxo atual.

## 2. Estado atual importante

- O repositório Git local está inicializado na branch `main`, com a primeira
  linha de base versionada localmente e sem remoto ou tag.
- O comando principal é `scripts/rodar_pipeline.py`.
- Imagens e vídeos gerados são copiados para `entregas_flow` e indexados.
- Imagens fornecidas podem migrar para uma nova revisão quando o arquivo existe
  e ainda não há vídeo concluído.
- Campos vazios `cta_destino` e `cta_palavra` podem ser preenchidos pela IA.
- O ZIP consolidado para classificação fica em
  `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip`.
- Respostas da IA ficam separadas em `preparados/respostas_ia/`.
- Carrosséis são renderizados localmente em
  `entregas_flow/carrossel/<producao_id>/`.

## 3. Princípios

1. Preservar antes de reorganizar.
2. Uma mudança estrutural por vez.
3. Compatibilidade temporária com os scripts atuais.
4. Configuração fora do código.
5. Operações caras exigem confirmação explícita.
6. Toda execução deve ser retomável e idempotente.
7. Arquivos de usuário nunca devem ser apagados implicitamente.
8. Documentação e testes fazem parte da entrega.

## 4. Estrutura-alvo

```text
pipeline-flow/
├── .env.example
├── .gitignore
├── AGENTS.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml
├── docs/
├── src/pipeline_flow/
│   ├── config.py
│   ├── domain/
│   ├── services/
│   ├── adapters/
│   ├── cli.py
│   └── web/
├── scripts/
├── tests/
├── entradas/
├── preparados/
├── entregas_flow/
└── logs/
```

Responsabilidades:

- `domain`: modelos de estado e validações sem acesso a arquivos;
- `services`: preparação, classificação, execução, entrega e carrossel;
- `adapters`: Excel, sistema de arquivos e cliente do gflow;
- `cli.py`: comandos públicos;
- `web`: backend local, templates e ativos da interface;
- `scripts`: wrappers temporários compatíveis com os comandos existentes.

## 5. Git

O repositório foi inicializado na pasta deste projeto após inventário,
sanitização de exemplos e auditoria do primeiro índice. A linha de base local
contém somente código, contratos, documentação, testes e exemplos sanitizados.
Não há remoto configurado.

O `.gitignore` deve excluir no mínimo:

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
logs/
*.log
preparados/flow/
preparados/pacotes/
preparados/pacotes_ia/
preparados/respostas_ia/
preparados/ultima_execucao_automatica.json
entregas_flow/
entradas/backups/
*.mp4
*.mov
*.webm
```

Versionar contratos, guias, código, testes e uma planilha-modelo sem dados
reais. Não versionar segredos, mídia de produção, respostas operacionais ou
dados pessoais.

Convenção de commits:

- `feat:` funcionalidade;
- `fix:` correção;
- `docs:` documentação;
- `test:` testes;
- `refactor:` mudança interna sem alterar comportamento.

Criar a primeira tag estável como `v0.1.0` somente depois que a Fase 1 cumprir
o critério de configuração centralizada; a tag ainda não foi criada.

## 6. Configuração por ambiente

Criar `.env.example`:

```dotenv
GFLOW_PROJECT_ID=
GFLOW_ROOT=D:/caminho/para/gflow-videos
PIPELINE_SPREADSHEET=entradas/controle_pipeline_flow.xlsx
PIPELINE_OUTPUT_DIR=preparados
PIPELINE_DELIVERY_DIR=entregas_flow
GFLOW_VIDEO_MODEL=veo-fast
GFLOW_TIMEOUT_SECONDS=1800
WEB_HOST=127.0.0.1
WEB_PORT=8765
```

Precedência:

1. argumento explícito da CLI;
2. variável do ambiente do processo;
3. variável carregada do `.env`;
4. padrão seguro;
5. erro claro se uma configuração obrigatória estiver ausente.

O comando cotidiano deve se tornar:

```powershell
python -m pipeline_flow
```

O argumento `--projeto` deve continuar disponível como sobrescrita opcional.

## 7. Interface web local

Uma página HTML estática não consegue, com segurança, ler a planilha, registrar
arquivos, iniciar etapas e acompanhar processos. A solução recomendada é:

- FastAPI no backend local;
- Jinja e HTML semântico;
- JavaScript simples;
- CSS próprio e responsivo;
- servidor restrito a `127.0.0.1`;
- acesso padrão em `http://127.0.0.1:8765`.

### Telas

#### Painel

Mostrar produções ativas, clipes, imagens pendentes, aprovações, vídeos
liberados, erros, última execução e próxima ação recomendada.

#### Produção

Apresentar a sequência:

```text
Preparação → Classificação IA → Imagem → Revisão → Carrossel → Vídeo → Entrega
```

Cada clipe deve mostrar imagem, produto, papel, estado, aprovação, carrossel,
vídeo e erro.

#### Revisão

- imagem em tamanho adequado;
- resumo do plano;
- aprovar ou rejeitar;
- justificativa;
- usar outra imagem;
- histórico de versões.

#### Pacotes de IA

- baixar o ZIP mais recente;
- localizar ou enviar respostas JSON;
- validar antes da importação;
- mostrar correspondência de hash;
- listar respostas ausentes.

#### Carrossel

- pré-visualização;
- título, destaque e CTA;
- contadores de caracteres;
- regeneração local;
- galeria por produção.

#### Entregas

- galeria de imagens, vídeos e cards;
- filtros por produção;
- índice de entregas;
- distinção entre original e cópia;
- ação para abrir a pasta.

#### Configuração

- projeto Flow;
- planilha;
- modelo;
- timeout;
- diagnóstico do ambiente.

### UX e acessibilidade

- cores semânticas, nunca apenas decorativas;
- verde concluído, âmbar pendente, vermelho erro e azul em execução;
- navegação por teclado e foco visível;
- contraste adequado;
- layout responsivo;
- respeito a redução de movimento;
- confirmação explícita antes de consumir créditos;
- logs recolhíveis;
- sempre responder: o que está pronto, o que bloqueia e qual é o próximo passo.

## 8. Segurança operacional

- nunca executar texto arbitrário recebido pela interface;
- evitar `shell=True`;
- validar que caminhos permanecem dentro das raízes permitidas;
- manter locks por clipe;
- impedir duas execuções simultâneas da mesma etapa;
- preservar SHA-256 e histórico;
- fazer backup antes de alterar a planilha;
- exigir aprovação humana antes de vídeo;
- manter `.env` fora do Git;
- registrar auditoria das ações da interface.

## 9. Documentação final

- `README.md`: instalação e primeiro uso;
- `docs/ARQUITETURA.md`: componentes e dependências;
- `docs/FLUXO_OPERACIONAL.md`: jornada completa;
- `docs/CONFIGURACAO.md`: variáveis do ambiente;
- `docs/PLANILHA.md`: responsabilidade das colunas;
- `docs/IA_E_CLASSIFICACAO.md`: ZIP, contrato, hashes e respostas;
- `docs/SOLUCAO_DE_PROBLEMAS.md`: erros e recuperação;
- `docs/adr/`: decisões arquiteturais relevantes.

## 10. Testes e integração contínua

Ferramentas sugeridas: pytest, Ruff, testes unitários, integração com planilha
temporária, validação de contratos, smoke test web e GitHub Actions.

Casos obrigatórios:

- retomada não duplica geração;
- aprovação fica vinculada ao hash;
- vídeo sem aprovação é bloqueado;
- imagem fornecida migra entre revisões;
- vídeo concluído impede troca destrutiva;
- entregas são idempotentes;
- carrossel respeita limites;
- testes nunca chamam o Flow real.

Pipeline Git:

```text
instalar → lint → testes → validar contratos → smoke test web
```

## 11. Fases

### Fase 1 — Fundação

Inicializar Git; criar `.gitignore`, `.env.example` e README; centralizar a
configuração e manter os comandos atuais funcionando.

Critério: o pipeline roda sem informar o projeto a cada comando.

Status: concluída. Git, política de ignore, atributos de arquivos, documentação
inicial, exemplos sanitizados, linha de base local, configuração centralizada
por `.env` e testes de compatibilidade estão concluídos. O comando principal
aceita o projeto configurado sem exigir `--projeto`, que permanece disponível
como sobrescrita.

### Fase 2 — Organização interna

Criar `src/pipeline_flow`, separar domínio, serviços e adaptadores, converter
scripts em wrappers e eliminar imports por manipulação de `sys.path`.

Critério: testes passam e a CLI antiga continua compatível.

Status: concluída. O pacote `src/pipeline_flow` contém a fachada pública,
domínio, serviços, adaptadores, orquestrador e implementações operacionais. Os
caminhos em `scripts/` são wrappers compatíveis, não há manipulação de
`sys.path` e a nova CLI `python -m pipeline_flow` foi validada em conjunto
com os comandos antigos.

### Fase 3 — Confiabilidade

Normalizar estados e logs; reforçar retomada, hashes, locks e migrações; criar
testes de integração.

Critério: interrupções podem ser retomadas sem duplicar ativos.

### Fase 4 — Interface somente leitura

Construir painel, produções, clipes, imagens, entregas e logs.

Critério: abrir o painel não altera nenhum estado.

### Fase 5 — Operação pela interface

Permitir preparar pacotes, importar respostas, registrar imagens, aprovar,
rejeitar, gerar carrosséis, liberar vídeos e acompanhar execução.

Critério: concluir o fluxo sem editar a planilha manualmente, mantendo travas.

### Fase 6 — Acabamento

Acessibilidade, responsividade, documentação, comando único, CI e release
`v1.0.0`.

## 12. Modelo recomendado

Para Codex, usar GPT-5.6 Sol. O nome oficial do esforço é `low`, não
`light`.

```toml
model = "gpt-5.6"
model_reasoning_effort = "medium"
plan_mode_reasoning_effort = "high"
model_verbosity = "medium"
```

Usar `low` para documentação e mudanças mecânicas; `medium` para arquitetura,
refatoração e interface; `high` apenas para bugs complexos e auditorias.

## 13. Próxima ação

Iniciar a Fase 3 com gate próprio para normalizar estados e logs. Essa atividade
deve preservar hashes, aprovações, locks e retomada e não deve migrar dados
históricos sem um gate específico. A configuração ou publicação em remoto
permanece uma atividade separada.

Já concluído nesta fase:

- inventário de arquivos, tamanhos, mídias e possíveis dados sensíveis;
- `.gitignore`, `.env.example`, README, `pyproject.toml` e
  `.gitattributes`;
- identidade fictícia e planilha-modelo sanitizada e determinística;
- estabilização da suíte local em 46 testes;
- revisão do primeiro índice e exclusão de todo estado operacional;
- inicialização do Git na branch `main` e primeira linha de base local.
- carregamento centralizado de `.env` com compatibilidade para os comandos
  legados e sobrescritas explícitas da CLI.
- testes de compatibilidade para padrões, `.env`, ambiente, alias legado e
  sobrescritas das CLIs, sem chamadas ao Flow.

Ao terminar uma fase, registrar data, arquivos alterados, decisões, testes,
pendências e próxima ação.

## 14. Registro de progresso

### 2026-09-19 — Inventário anterior à Fase 1

Atividade concluída sem alterar, mover ou apagar arquivos operacionais. A Fase 1
ainda não foi iniciada.

- inventariados 1.496 arquivos em 365 diretórios, totalizando 801,83 MiB;
- identificadas 528 mídias e 495 arquivos de dados operacionais;
- maiores áreas: `preparados/` com 647,94 MiB, `entregas_flow/` com
  62,04 MiB, `referencia_gflow_original/` com 49,13 MiB e `entradas/` com
  17,95 MiB;
- confirmada a existência de `.env` com seis variáveis preenchidas; os valores
  não foram exibidos e o arquivo deve permanecer fora do Git;
- confirmado que não existe `.gitignore` na raiz;
- a varredura dos textos candidatos não encontrou e-mails, telefones, chaves
  privadas, tokens literais nem caminhos de usuário;
- imagens de identidade, planilha operacional, backups, pacotes, respostas,
  logs, entregas, ZIPs e mídias de produção foram classificados como não
  versionáveis.

Conteúdo proposto para o primeiro commit:

- criar `.gitignore`, `.env.example`, `README.md` e `pyproject.toml`;
- incluir `AGENTS.md`, `AUTOMACAO_FLOW.md`,
  `CONTRATO_INSUMOS.md`,
  `GUIA_INSUMOS_FLOW.md`, `LEIA-ME.md` e
  `docs/PLANO_MODERNIZACAO.md`;
- incluir `scripts/*.py`, `tests/*.py` e `fluxos/**/*.txt`;
- incluir `entradas/01_COMO_USAR_EM_OUTRA_IA.md`,
  `entradas/02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md`,
  `entradas/ARQUITETURA_FLUXO_PIPELINE_FLOW.md`,
  `entradas/GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md`,
  `entradas/LEIA-ME.txt` e
  `entradas/CLASSIFICADOR_UNIVERSAL.txt`;
- criar uma planilha-modelo sanitizada e um `identidade.example.txt` antes de
  versionar exemplos desses insumos.

Exclusões obrigatórias do primeiro commit:

- `.env`, `preparados/`, `entregas_flow/`, `entradas/backups/` e
  `referencia_gflow_original/`;
- `entradas/controle_pipeline_flow.xlsx` e todas as mídias atuais de
  `entradas/`;
- arquivos de identidade reais, imagens soltas da raiz, ZIPs, logs, caches,
  arquivos compilados e produções reais.
- `proposta_pov/` e os modelos avulsos da raiz permanecem fora até revisão
  de uso, duplicidade e conteúdo.
- a cópia legada `CLASSIFICADOR_UNIVERSAL.txt` da raiz permanece fora; a fonte
  canônica versionável é `entradas/CLASSIFICADOR_UNIVERSAL.txt`, usada pelo
  preparador e declarada pelo contrato.

Verificações realizadas: contagem por extensão e diretório, inspeção dos
maiores arquivos, nomes de variáveis do `.env` sem valores, busca por nomes e
conteúdos potencialmente sensíveis e confirmação de que o projeto ainda não é
um repositório Git.

Pendência e próxima ação: criar e revisar o `.gitignore`, o `.env.example` e os
arquivos iniciais da Fase 1 antes de executar `git init`.

### 2026-09-19 — Fundação versionável da Fase 1

Atividade concluída sem inicializar o repositório e sem alterar os scripts
operacionais.

Arquivos criados:

- `.gitignore`, cobrindo segredos, caches, logs, estados operacionais,
  planilhas reais, mídias, identidades e arquivos pesados;
- `.env.example`, separando as variáveis legadas já reconhecidas das
  variáveis-alvo que ainda serão centralizadas;
- `README.md`, com regras de segurança, instalação, comandos atuais e estado
  da modernização;
- `pyproject.toml`, com Python 3.11+, Pillow e ferramentas de desenvolvimento.

Decisões:

- o carregamento automático de `.env` não foi anunciado como pronto;
- `git init` continua bloqueado até criar exemplos sanitizados, revisar a
  lista versionável e confirmar o índice;
- nenhuma dependência foi instalada e nenhuma chamada ao Flow foi executada.

Verificações:

- `pyproject.toml` carregado com sucesso por `tomllib`;
- 11 caminhos operacionais testados foram ignorados e 6 caminhos versionáveis
  permaneceram disponíveis, usando um repositório temporário removido ao final;
- suíte: 30 testes passaram e 2 falharam em
  `tests/test_prompts_pipeline.py`;
- causa confirmada: o pacote histórico usado como fixture não contém
  `gerar_carrossel`, `cta_destino` e `cta_palavra`, hoje incluídos em
  `HUMAN`; a correção dos testes ficou fora desta atividade.

Pendências: criar a planilha-modelo e a identidade de exemplo sanitizadas,
estabilizar os dois testes do fixture histórico e somente depois revisar o
primeiro índice Git.

### 2026-09-19 — Exemplos sanitizados

Atividade concluída sem copiar dados, mídias ou metadados da planilha
operacional.

Arquivos criados:

- `exemplos/identidade.example.txt`, com personagem explicitamente fictícia e
  orientações para não registrar dados pessoais desnecessários;
- `exemplos/controle_pipeline_flow.modelo.xlsx`, gerado do zero com as abas
  `Controle`, `Guia`, `Referencias_Identidade` e `Exemplo_Producao`;
- `scripts/gerar_modelo_planilha.py`, gerador reproduzível do XLSX.

Arquivos atualizados:

- `pyproject.toml`, com `openpyxl` somente nas dependências de
  desenvolvimento;
- `README.md`, com links para os exemplos e o comando de regeneração.

Propriedades do modelo:

- 31 cabeçalhos idênticos ao contrato atual;
- nenhuma linha operacional na aba `Controle`;
- três linhas fictícias na aba de exemplo, todas com `classifica=não`;
- listas suspensas para os principais campos humanos;
- nenhuma fórmula, referência real ou conteúdo da planilha operacional;
- geração determinística, com SHA-256
  `E570AA69F541FA698BDD0AF218BEA636F0415E70D0DF66D2FDD45B9E8B3C29BF`.

Verificações: leitura pelo `openpyxl` e pela classe `Workbook` do pipeline,
regeneração com hash estável, compilação do gerador, busca por nomes e e-mails
reais e 2 testes de namespace aprovados. O Ruff não estava instalado e não foi
executado.

Próxima ação: estabilizar os dois testes que dependem do fixture histórico,
revisar todos os caminhos candidatos ao primeiro commit e somente depois
preparar a inicialização do Git.

### 2026-09-19 — Revisão final dos candidatos ao primeiro commit

Atividade concluída sem inicializar o repositório e sem alterar arquivos
operacionais.

- a suíte completa foi executada sem cache e sem chamadas ao Flow: 33 testes
  passaram;
- os dois testes históricos antes pendentes já estavam estabilizados no estado
  atual do projeto;
- a simulação do primeiro índice revelou relatórios, mensagens de classificação,
  dados de importação e um script operacional ainda visíveis em `preparados/`;
- o `.gitignore` passou a excluir `preparados/` integralmente, conforme a regra
  de não versionar estado operacional;
- os dois arquivos chamados `CLASSIFICADOR_UNIVERSAL.txt` possuem conteúdo e
  hashes diferentes; o código usa `entradas/CLASSIFICADOR_UNIVERSAL.txt` como
  fonte canônica, enquanto a cópia legada da raiz passou a ser ignorada;
- a lista proposta para o primeiro commit foi corrigida para conter somente o
  classificador canônico.

Verificações: suíte local completa; nova simulação do índice com repositório Git
temporário externo à pasta do projeto; 63 arquivos candidatos, totalizando
391.406 bytes; nenhum caminho operacional ou proibido elegível; busca por
padrões comuns de segredo sem ocorrências nos arquivos versionáveis.

Próxima ação: em atividade separada com gate `high`, inicializar o Git,
conferir o índice real e preparar a linha de base sem criar commit, tag ou
publicação remota.

### 2026-09-19 — Inicialização do Git e linha de base staged

Atividade concluída sem criar commit, tag ou remoto.

- o repositório Git foi inicializado na branch `main`;
- foi criada `.gitattributes` para manter textos versionados em LF e impedir
  conversão de planilhas, imagens, vídeos e ZIPs;
- 64 arquivos permitidos foram adicionados ao índice;
- nenhum arquivo ignorado ou caminho operacional foi encontrado no índice;
- não há remotos, tags nem commits;
- a varredura do conteúdo staged não encontrou padrões comuns de segredos;
- o modelo XLSX manteve o SHA-256 determinístico
  `E570AA69F541FA698BDD0AF218BEA636F0415E70D0DF66D2FDD45B9E8B3C29BF`;
- a suíte local passou novamente com 33 testes;
- o Ruff está declarado nas dependências de desenvolvimento, mas não está
  instalado no ambiente Python atual e não pôde ser executado;
- `git diff --cached --check` registrou avisos não destrutivos de linha em
  branco no fim de arquivos legados e dois hard breaks Markdown já existentes;
  nenhum erro de conteúdo ou segurança foi identificado.

Próxima ação: sob novo gate `high`, fazer a conferência final do índice e
criar o primeiro commit local. A tag `v0.1.0` permanece adiada até a Fase 1
cumprir seu critério de configuração centralizada; nenhuma publicação remota
está autorizada.

### 2026-09-19 — Primeiro commit local da modernização

Atividade concluída sem criar tag ou configurar/publicar remoto.

- autoria Git confirmada como configurada, sem registrar seus valores neste
  documento;
- índice final mantido com 64 arquivos: código, testes, contratos, documentação,
  fluxos e exemplos sanitizados;
- nenhum caminho ignorado, dado operacional ou padrão comum de segredo foi
  encontrado no índice;
- commit local criado na branch `main` com a mensagem
  `feat: establish audited project baseline`;
- a suíte permaneceu com 33 testes aprovados;
- Ruff não foi executado porque ainda não está instalado no ambiente atual;
- a tag `v0.1.0` e qualquer remoto continuam deliberadamente ausentes.

Próxima ação: centralizar a configuração por `.env` preservando
`--projeto` e os comandos legados, seguida de testes de compatibilidade sem
chamadas ao Flow.

### 2026-09-19 — Configuração centralizada por ambiente

Atividade concluída preservando os comandos atuais e sem executar geração no
Flow.

- criado `scripts/pipeline_config.py`, com leitura conservadora do `.env`,
  variáveis do processo, padrões seguros, validação de modelo, timeout e porta;
- integrados planilha, diretórios de preparados e entregas, raiz do gflow,
  projeto, modelo e timeout aos quatro comandos operacionais;
- mantido `GFLOW_CLI_DEFAULT_PROJECT` como compatibilidade e adotado
  `GFLOW_PROJECT_ID` como nome preferencial;
- preservados `--projeto` e os demais argumentos como sobrescritas por
  execução;
- erros de configuração passaram a produzir mensagem controlada e código de
  saída 2, sem traceback;
- atualizados `.env.example` e README para refletir o comportamento atual.

Verificações: 33 testes existentes aprovados, compilação de `scripts/` e
`tests/`, comandos de ajuda validados anteriormente, três verificações de
configuração inválida com código de saída 2 e `git diff --check` sem erros.
Nenhuma chamada ao Flow foi feita.

Pendência e próxima ação: criar testes específicos de compatibilidade para a
precedência CLI, ambiente, `.env` e padrões, inclusive o alias legado do
projeto. A Fase 1 e a tag `v0.1.0` permanecem abertas até essa comprovação.

### 2026-09-19 — Testes de compatibilidade e conclusão da Fase 1

Atividade concluída sem acessar a planilha operacional, chamar o Flow, gerar
mídia ou alterar estados persistidos.

- criado `tests/test_pipeline_config.py` com 13 casos novos;
- comprovados padrões seguros, caminhos relativos à raiz, carregamento do
  `.env`, precedência do ambiente e validação de modelo, timeout e porta;
- comprovada a preferência de `GFLOW_PROJECT_ID` e a compatibilidade de
  `GFLOW_CLI_DEFAULT_PROJECT` e `GFLOW_CLI_HOME`;
- comprovado que o comando principal recebe o projeto configurado sem
  `--projeto` e que argumentos explícitos continuam sobrescrevendo a
  configuração;
- exercitados com mocks o executor, o preparador e o carrossel, sem executar
  geração ou escrever em diretórios operacionais;
- comprovado que configuração inválida retorna código 2 e mensagem controlada,
  sem traceback.

Verificações: 13 testes novos e 46 testes totais aprovados, compilação de
`scripts/` e `tests/` concluída e `git diff --check` sem erros. Ruff
continua declarado, mas não está instalado no ambiente atual.

O critério da Fase 1 foi cumprido: o projeto configurado é usado pelo comando
principal sem precisar informar `--projeto` a cada execução. A tag `v0.1.0`
ainda não foi criada.

Pendência e próxima ação: auditar o diff e o índice, criar o commit local da
Fase 1 e a tag `v0.1.0`, sem configurar nem publicar remoto.

### 2026-09-19 — Auditoria e release local `v0.1.0`

Atividade concluída sem configurar remoto, publicar código ou executar o Flow.

- auditados os nove arquivos da configuração centralizada, documentação e
  testes;
- índice preparado por lista explícita, sem `.env`, planilha operacional,
  mídias, preparados, entregas ou outros arquivos ignorados;
- busca no índice não encontrou padrões comuns de segredos ou chaves privadas;
- corrigida durante a auditoria a herança do diretório de respostas quando
  `--saida` é informado sem `--respostas`;
- identidade Git local do repositório corrigida sem registrar seus valores
  neste documento;
- commit local criado com a mensagem
  `feat: centralize pipeline configuration`;
- tag anotada `v0.1.0` criada sobre o commit da Fase 1.

Verificações finais: 46 testes aprovados, compilação de `scripts/` e
`tests/`, `git diff --cached --check` sem erros e conferência de que não há
remoto configurado. Ruff não foi executado porque não está instalado.

Próxima ação: iniciar a Fase 2 com gate `medium`, criando
`src/pipeline_flow` e separando domínio, serviços e adaptadores. Qualquer
configuração ou publicação no GitHub exige atividade e autorização próprias.

### 2026-09-19 — Pacote e camadas iniciais da Fase 2

Atividade concluída sem alterar os scripts operacionais, executar o Flow ou
modificar estados persistidos.

- criado o pacote `src/pipeline_flow` com versão e fachada pública de
  configuração;
- criada a camada `domain` com modelo imutável e validações puras;
- criada a camada `adapters` para ambiente do processo, leitura conservadora
  de `.env` e resolução de caminhos;
- criada a camada `services` para aplicar precedência e compor a configuração;
- configurado o `pyproject.toml` para descobrir pacotes em `src/` e permitir
  os imports durante os testes;
- criado `tests/test_package_architecture.py` com quatro testes de fronteira,
  validação e equivalência com a implementação legada.

Decisão de transição: `scripts/pipeline_config.py` permanece temporariamente
como implementação usada pelas CLIs atuais. A duplicação evita quebrar a
execução direta antes da conversão explícita dos scripts em wrappers; ela deve
ser removida na próxima atividade.

Verificações: descoberta dos quatro pacotes esperados, compilação de `src/`,
`scripts/` e `tests/`, 50 testes aprovados, ajuda das CLIs principais
preservada e `git diff --check` sem erros. Ruff continua indisponível no
ambiente. Nenhuma chamada ao Flow foi feita.

Próxima ação: converter os scripts em wrappers, apontar a configuração para a
fachada `pipeline_flow.config` e remover a duplicação e eventuais manipulações
de `sys.path`, preservando todos os comandos atuais.

### 2026-09-19 — Implementações no pacote e wrappers legados

Atividade concluída sem executar o Flow, gerar mídia ou alterar estados
operacionais.

- movidos preparador, executor, carrossel e gerador do modelo para
  `pipeline_flow.services`;
- movido o orquestrador principal para `pipeline_flow.cli`;
- substituídos os seis módulos em `scripts/` por wrappers que preservam os
  caminhos e comandos existentes;
- removida a implementação duplicada de configuração; a fonte canônica passou
  a ser `pipeline_flow.config`;
- atualizados os imports internos e os testes para usar módulos canônicos;
- removida a única manipulação explícita de `sys.path`;
- ajustado o cálculo de `ROOT` para a profundidade do layout `src/`;
- instalado o próprio projeto em modo editável no ambiente do usuário, sem
  dependências e sem isolamento de build.

Verificações: 50 testes aprovados, compilação de `src/`, `scripts/` e
`tests/`, ausência de imports internos legados, `git diff --check` sem erros
e execução com código 0 da ajuda dos cinco comandos legados e do wrapper de
configuração. A instalação editável aponta para este workspace. Nenhuma chamada
ao Flow foi feita.

Próxima ação: criar `pipeline_flow.__main__` e testes de subprocesso para
comparar a nova CLI com os comandos antigos, concluindo o critério da Fase 2.

### 2026-09-19 — Nova CLI e conclusão técnica da Fase 2

Atividade concluída sem executar o pipeline operacional ou chamar o Flow.

- criado `pipeline_flow.__main__` para o comando
  `python -m pipeline_flow`;
- ajustado o orquestrador para aceitar um nome de programa explícito sem
  alterar o wrapper legado;
- criado `tests/test_cli_compatibility.py` com três testes de subprocesso;
- comparadas as opções apresentadas pelas CLIs nova e antiga;
- comprovados códigos de saída e mensagens controladas para configuração
  inválida e argumento desconhecido;
- atualizado o README para tornar a nova CLI o comando principal e manter
  documentado o comando histórico.

Verificações: 53 testes aprovados, compilação de `src/`, `scripts/` e
`tests/`, duas ajudas com código 0, conjunto idêntico de opções, ausência de
`sys.path` e `git diff --check` sem erros. Nenhuma chamada ao Flow foi feita.

O critério da Fase 2 foi cumprido: os testes passam, a CLI antiga continua
compatível e a nova CLI está disponível.

Pendência e próxima ação: auditar o diff e o índice da Fase 2 e criar um commit
local antes de iniciar a normalização de estados e logs da Fase 3.

### 2026-09-19 — Auditoria e commit local da Fase 2

Atividade concluída sem criar tag, configurar remoto, executar o pipeline
operacional ou chamar o Flow.

- auditados os 27 arquivos da reorganização interna e da compatibilidade das
  CLIs;
- removidas linhas em branco excedentes detectadas pela conferência final;
- confirmado que o índice não contém `.env`, mídias, preparados, entregas ou
  outros estados operacionais;
- a busca no índice não encontrou padrões comuns de chaves privadas ou tokens;
- preservadas a nova CLI `python -m pipeline_flow` e a CLI histórica
  `python scripts/rodar_pipeline.py` com o mesmo conjunto de opções;
- commit local da Fase 2 criado sem nova tag e sem publicação remota.

Verificações finais: 53 testes e 3 subtestes aprovados, duas ajudas com código
0, ausência de manipulação de `sys.path` no código e `git diff --cached --check`
sem erros. Nenhuma chamada ao Flow foi feita. O Ruff continua indisponível no
ambiente atual.

Próxima ação: iniciar a Fase 3, sob gate `high`, pela normalização de estados e
logs. Hashes e aprovação, locks e retomada, e migrações e testes de recuperação
permanecem blocos posteriores com gates próprios.

Nenhuma fase deve ser marcada como concluída sem testes e sem atualização deste
registro.

## 15. Gate de modelo por atividade

Antes de executar cada atividade material, o agente deve anunciar a próxima
ação, recomendar a configuração e aguardar confirmação de Gabi. O agente não
deve alterar a configuração por conta própria.

Mensagem obrigatória:

> Gabi, agora vamos fazer **[atividade]**. Configure para **GPT-5.6 Sol,
> esforço [nível]**. Motivo: [uma frase]. Quando estiver configurado, me avise
> para eu continuar.

### Esforço low

Usar quando todas as condições forem verdadeiras:

- documentação ou inventário;
- alteração mecânica e localizada;
- até 3 arquivos;
- sem mudança de estado, persistência, segurança ou contrato;
- testes simples e conhecidos.

Exemplos: corrigir README, ajustar texto, listar arquivos, criar índice de
documentação e atualizar exemplos.

### Esforço medium

Usar se ocorrer qualquer uma destas condições:

- implementação de funcionalidade;
- refatoração entre módulos;
- criação da configuração por `.env`;
- criação de testes;
- construção da interface HTML;
- alteração entre 4 e 10 arquivos;
- mudança reversível em estado ou persistência;
- integração entre CLI, Excel, arquivos e interface.

É o padrão para as Fases 1, 2, 4, 5 e 6.

### Esforço high

Usar se ocorrer qualquer uma destas condições:

- migração estrutural de estados ou ativos;
- alteração de hashes, locks, aprovação ou retomada;
- segurança, permissões ou execução de comandos;
- refatoração transversal acima de 10 arquivos;
- diagnóstico de corrupção ou perda potencial de dados;
- decisão arquitetural difícil de reverter;
- preparação de release após mudanças amplas.

É o padrão para a Fase 3 e para a auditoria final da Fase 5.

### Esforços acima de high

`xhigh` ou `max` não fazem parte do fluxo normal. Só recomendar quando houver
uma auditoria excepcionalmente complexa e explicar por que `high` não basta.

### Regras de troca

- Se a sessão já estiver no nível recomendado ou acima, não pedir troca.
- Não pedir downgrade durante uma atividade em andamento.
- Ao mudar de atividade, reavaliar o nível.
- Se o nível atual não puder ser confirmado, apresentar a recomendação mesmo
  assim e pedir confirmação de Gabi.
- `low`, `medium` e `high` são os nomes oficiais usados neste projeto.

### Configuração por fase

| Fase | Atividade principal | Configuração inicial |
|---|---|---|
| 1 | Git, ignore, env e README | GPT-5.6 Sol medium |
| 2 | reorganização interna | GPT-5.6 Sol medium |
| 3 | estados, hashes, locks e retomada | GPT-5.6 Sol high |
| 4 | painel HTML somente leitura | GPT-5.6 Sol medium |
| 5 | operações pela interface | GPT-5.6 Sol medium |
| 5 — auditoria | segurança e créditos | GPT-5.6 Sol high |
| 6 | acabamento, CI e documentação | GPT-5.6 Sol medium |

### Limites do gate

Um gate autoriza somente a atividade anunciada e o conjunto contínuo de
alterações necessário para concluí-la. Ele não autoriza automaticamente a fase
inteira nem a atividade seguinte.

- `low`: no máximo 3 arquivos, somente documentação, inventário ou alteração
  mecânica localizada, sem mudar estado, persistência, segurança, contratos ou
  comportamento do pipeline;
- `medium`: implementação ou refatoração reversível de até 10 arquivos, desde
  que não altere hashes, locks, aprovação, retomada, permissões ou execução de
  comandos;
- `high`: sem limite numérico pré-fixado, mas com escopo explicitamente
  delimitado; obrigatório para segurança, comandos, créditos, estados, hashes,
  locks, aprovação, retomada, migrações, risco de perda de dados ou mudanças
  transversais acima de 10 arquivos.

Se uma atividade ultrapassar qualquer limite do nível anunciado, o agente deve
parar antes da ampliação, reclassificar a atividade, emitir um novo gate e
aguardar nova confirmação. Uma confirmação não pode ser reaproveitada depois de
mudança material de objetivo. Leituras e verificações sem alteração podem ser
feitas antes do gate.

### Roteiro de gates da modernização

Esta tabela deve ser consultada antes de cada atividade material. A coluna
“Configuração” informa o mínimo recomendado; se a sessão já estiver nesse nível
ou acima, basta confirmar a configuração atual, sem pedir redução.

| Fase | Atividade delimitada | Configuração | Novo gate obrigatório quando... |
|---|---|---|---|
| Preparação | Ler contratos, inventariar arquivos, tamanhos, mídias e possíveis dados sensíveis | GPT-5.6 Sol low | o inventário passar a alterar, mover ou excluir arquivos |
| 1 | Definir o primeiro commit e criar ou ajustar `.gitignore`, `.env.example` e documentação inicial | GPT-5.6 Sol medium | surgir mudança de comportamento ou mais de 10 arquivos |
| 1 | Inicializar Git, conferir o índice e criar a linha de base sem dados operacionais | GPT-5.6 Sol high | antes de qualquer commit, tag, publicação remota ou correção de vazamento |
| 1 | Centralizar configuração por `.env` e preservar argumentos e comandos atuais | GPT-5.6 Sol medium | a alteração alcançar credenciais, permissões ou execução arbitrária |
| 1 | Criar testes de compatibilidade da configuração e dos comandos existentes | GPT-5.6 Sol medium | os testes exigirem migração de estado ou chamada real ao Flow |
| 2 | Criar o pacote `src/pipeline_flow` e separar domínio, serviços e adaptadores | GPT-5.6 Sol medium | a refatoração ultrapassar 10 arquivos ou alterar contratos persistidos |
| 2 | Converter scripts em wrappers e remover manipulações de `sys.path` | GPT-5.6 Sol medium | wrappers passarem a executar comandos externos de forma diferente |
| 2 | Validar compatibilidade da CLI antiga e da nova CLI | GPT-5.6 Sol medium | for necessário migrar dados ou alterar estados existentes |
| 3 | Normalizar estados e logs | GPT-5.6 Sol high | o objetivo mudar entre estados, logs e recuperação; cada bloco deve ter gate próprio |
| 3 | Reforçar hashes e vínculo de aprovação à revisão correta | GPT-5.6 Sol high | houver mudança adicional em formato persistido ou migração histórica |
| 3 | Reforçar locks, retomada e idempotência | GPT-5.6 Sol high | a solução passar a alterar concorrência, filas ou estratégia de recuperação |
| 3 | Criar migrações e testes de integração de recuperação | GPT-5.6 Sol high | aparecer risco não previsto de corrupção ou perda de dados |
| 4 | Construir backend local e consultas somente leitura | GPT-5.6 Sol medium | qualquer endpoint passar a alterar estado ou iniciar processos |
| 4 | Construir painel, produções, clipes, imagens, entregas e logs | GPT-5.6 Sol medium | a atividade ultrapassar 10 arquivos ou incluir operação do pipeline |
| 4 | Fazer smoke test, revisão responsiva e acessibilidade do modo leitura | GPT-5.6 Sol medium | o teste revelar falha de segurança, estado ou contrato |
| 5 | Implementar preparação de pacotes, importação de respostas e registro de imagens | GPT-5.6 Sol medium | a operação envolver execução externa, permissões ou migração persistida |
| 5 | Implementar aprovação, rejeição e vínculo da decisão ao hash | GPT-5.6 Sol high | o modelo de aprovação ou revisão precisar mudar novamente |
| 5 | Implementar carrossel e operações locais sem consumo de créditos | GPT-5.6 Sol medium | a atividade passar a liberar vídeo ou chamar serviço pago |
| 5 | Implementar liberação de vídeo, execução de comandos e acompanhamento | GPT-5.6 Sol high | surgir novo comando, nova permissão ou nova forma de consumir créditos |
| 5 — auditoria | Auditar segurança, caminhos, comandos, concorrência e trava de créditos | GPT-5.6 Sol high | o escopo da auditoria mudar ou uma correção estrutural virar nova atividade |
| 6 | Refinar acessibilidade, responsividade e experiência visual | GPT-5.6 Sol medium | o trabalho deixar de ser acabamento e alterar fluxos operacionais |
| 6 | Consolidar documentação final e solução de problemas | GPT-5.6 Sol low | a documentação exigir mudança de código ou contrato |
| 6 | Configurar CI e validar instalação, lint, testes, contratos e smoke web | GPT-5.6 Sol medium | a CI precisar de segredos, publicação ou mudança de permissões |
| 6 | Fazer auditoria final, preparar release, tag e `v1.0.0` | GPT-5.6 Sol high | antes de publicar em remoto ou distribuir artefatos fora do projeto |

### Aplicação obrigatória da mensagem

Para cada linha iniciada no roteiro, substituir `[atividade]`, `[nível]` e o
motivo na mensagem obrigatória desta seção. Exemplo:

> Gabi, agora vamos fazer **o inventário de arquivos, tamanhos, mídias e dados
> sensíveis antes do primeiro commit**. Configure para **GPT-5.6 Sol, esforço
> low**. Motivo: é uma inspeção documental sem alteração de estado. Quando
> estiver configurado, me avise para eu continuar.

A confirmação vale somente para essa atividade delimitada. Ao concluí-la, o
agente deve registrar o resultado no progresso do plano e emitir o gate da
próxima atividade material, se houver.
