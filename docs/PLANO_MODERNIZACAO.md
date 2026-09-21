# Plano de modernização do Pipeline Flow

Status: Fase 6 em andamento — acessibilidade, responsividade e experiência visual concluídas
Última atualização: 2026-09-20
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
GFLOW_VIDEO_MODEL=omni-flash
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

- `README.md`: instalação e primeiro uso, incluindo clonagem, entrada na pasta,
  criação de ambiente virtual compatível com Python 3.11 ou superior e
  instalação das dependências;
- `docs/ARQUITETURA.md`: componentes e dependências;
- `docs/FLUXO_OPERACIONAL.md`: jornada completa;
- `docs/CONFIGURACAO.md`: variáveis do ambiente;
- `docs/PLANILHA.md`: responsabilidade das colunas;
- `docs/IA_E_CLASSIFICACAO.md`: ZIP, contrato, hashes e respostas;
- `docs/SOLUCAO_DE_PROBLEMAS.md`: erros e recuperação;
- `docs/adr/`: decisões arquiteturais relevantes.

O primeiro uso deve permitir que uma pessoa parta de um clone limpo sem
depender de conhecimento transmitido fora do repositório. A documentação deve:

- explicar como copiar `exemplos/controle_pipeline_flow.modelo.xlsx` para
  `entradas/controle_pipeline_flow.xlsx` sem versionar a planilha operacional;
- distinguir comandos PowerShell de valores que devem ser escritos no `.env`;
- documentar onde obter o `gflow`, a localização esperada de `gflow.exe` e como
  preencher `GFLOW_ROOT` e `GFLOW_PROJECT_ID`;
- deixar explícito que vídeo usa somente `omni-flash` e pode consumir créditos;
- orientar a classificação manual pela IA, a importação da resposta, a revisão
  humana e a primeira execução segura pelo painel;
- incluir um diagnóstico inicial que confira Python, dependências, `.env`,
  planilha, diretórios graváveis e presença do `gflow.exe`, sem executar geração;
- informar plataformas e versões de Python suportadas;
- explicar quais dados, mídias e segredos nunca devem ser enviados ao Git.

Antes da distribuição para terceiros, também devem ser definidos e publicados:

- uma licença explícita, escolhida pela titular do projeto;
- descrição e tópicos do repositório no GitHub;
- política de suporte, atualização de dependências e compatibilidade;
- notas de versão e instruções de atualização para a `v1.0.0`.

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
- clone limpo instala o projeto com o comando documentado;
- comandos de ajuda e diagnóstico funcionam sem dados privados;
- smoke test do painel usa somente requisições de leitura;
- CI não exige segredos nem chama o Flow real;
- exemplos sanitizados são suficientes para validar o primeiro uso sem
  produções históricas.

Pipeline Git:

```text
instalar → lint → testes → validar contratos → smoke test web
```

A matriz de CI deve executar em Windows, nas versões mínima e corrente de
Python suportadas, e incluir instalação do pacote, Ruff, suíte completa,
compilação dos módulos, validação dos exemplos e smoke test somente leitura. A
estratégia de pinagem ou arquivo de restrições deve ser definida antes da
`v1.0.0` para tornar as instalações reproduzíveis sem congelar dependências de
forma incompatível com a manutenção do projeto.

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

Status: concluída. Estados e logs foram normalizados; hashes, aprovação, locks,
retomada e idempotência foram reforçados; e as migrações históricas possuem
simulação, backup, aplicação atômica e testes de integração sem chamadas reais
ao Flow.

### Fase 4 — Interface somente leitura

Construir painel, produções, clipes, imagens, entregas e logs.

Critério: abrir o painel não altera nenhum estado.

Status: concluída. O backend FastAPI local, as consultas de produções, clipes,
mídias, entregas e logs, as travas de somente leitura, o painel HTML responsivo
e a validação visual e de acessibilidade estão concluídos.

### Fase 5 — Operação pela interface

Permitir preparar pacotes, importar respostas, registrar imagens, aprovar,
rejeitar, gerar carrosséis, liberar vídeos e acompanhar execução.

Critério: concluir o fluxo sem editar a planilha manualmente, mantendo travas.

Status: concluída. Preparação de pacotes, download do ZIP consolidado,
importação de respostas existentes ou enviadas e registro de imagens na revisão
ativa estão disponíveis na interface. Aprovação e rejeição vinculadas ao hash e
à revisão também estão concluídas. A galeria e a geração versionada de
carrosséis locais estão disponíveis sem depender da aprovação de vídeo.
A liberação unitária de vídeo, a execução em segundo plano e o acompanhamento
também estão implementados. A auditoria de segurança, caminhos, comandos,
concorrência e trava de créditos foi concluída com regressões específicas.

### Fase 6 — Acabamento e distribuição

Acessibilidade, responsividade, documentação, comando único, CI e release
`v1.0.0`.

Entregáveis restantes:

- reescrever o início do README como roteiro executável de primeiro uso;
- documentar a criação da planilha operacional a partir do modelo sanitizado;
- documentar obtenção, instalação e validação do `gflow.exe`;
- criar diagnóstico seguro de configuração, sem geração nem consumo de créditos;
- consolidar configuração, planilha, classificação por IA e atualização em
  documentos próprios, mantendo o README curto;
- escolher e adicionar a licença do projeto;
- completar descrição, tópicos e instruções de suporte do repositório;
- configurar GitHub Actions para instalação limpa, Ruff, testes, contratos e
  smoke test web somente leitura;
- definir a estratégia de dependências reproduzíveis e a matriz de Python;
- executar teste de aceitação com uma pessoa partindo de um clone limpo;
- preparar notas de versão, auditoria final, tag e release `v1.0.0`.

Critério: uma pessoa com acesso autorizado ao Flow consegue clonar, instalar,
configurar, validar e executar o primeiro fluxo seguindo apenas a documentação;
a CI reproduz as verificações sem segredos, dados reais ou chamadas pagas; e a
licença e as condições de suporte estão explícitas.

Status: em andamento. O refinamento de acessibilidade, responsividade e
experiência visual foi concluído sem alterar os fluxos operacionais. Restam a
consolidação do primeiro uso, o diagnóstico de configuração, a licença, a
configuração de CI, o teste de aceitação em clone limpo e a auditoria de release.

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

Consolidar o roteiro de primeiro uso da Fase 6: clonagem, ambiente virtual,
instalação, criação da planilha operacional, preenchimento do `.env`, instalação
do `gflow`, classificação pela IA e primeira execução segura. O diagnóstico de
configuração, a escolha da licença, a CI, o teste de aceitação e o release
continuam atividades separadas, cada uma com gate próprio.

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

### 2026-09-21 - Auditoria de primeiro uso e distribuição

O projeto público foi avaliado a partir da perspectiva de uma pessoa sem acesso
ao histórico local. A instalação documentada foi reproduzida em clone limpo: o
pacote e as dependências foram instalados, a wheel foi construída e a CLI
principal exibiu ajuda fora da pasta do repositório.

Foram incorporadas à Fase 6 as lacunas encontradas: roteiro de clonagem e
instalação para Python 3.11+, criação da planilha a partir do modelo, distinção
entre comandos e valores do `.env`, obtenção e validação do `gflow.exe`,
diagnóstico seguro, licença, metadados do GitHub, política de suporte, CI em
Windows, dependências reproduzíveis, teste de aceitação e release `v1.0.0`.

Decisão: o projeto está tecnicamente instalável, mas a Fase 6 somente poderá ser
concluída quando uma pessoa autorizada conseguir executar o primeiro fluxo a
partir de um clone limpo usando apenas a documentação. A escolha da licença
permanece decisão da titular e não deve ser presumida pelo agente.

Próxima ação: consolidar o roteiro de primeiro uso sob gate `low`, sem alterar
comportamento; qualquer diagnóstico novo em código exige novo gate `medium`.

### 2026-09-21 - Auditoria Git e portabilidade dos testes

Atividade concluida sem versionar configuracoes locais, producoes ou midias
reais.

- screenshots temporarios do painel passaram a ser ignorados;
- UUID de projeto, caminhos da maquina e exemplos de producao real foram
  removidos dos arquivos candidatos;
- testes do executor e dos contratos passaram a criar revisoes, pacotes,
  anexos e respostas sinteticos em diretorios temporarios;
- uma copia contendo somente arquivos visiveis ao Git simulou um clone limpo;
- verificacao: 152 testes passaram no ambiente isolado, a compilacao Python
  passou e `git diff --check` nao encontrou erros;
- `ruff` nao estava instalado no ambiente e permaneceu como verificacao
  pendente.

### 2026-09-20 - Omni Flash obrigatório para vídeo

Decisão arquitetural concluída sem versionar produções ou mídias reais.

- `omni-flash` passou a ser o único modelo de vídeo aceito pelo domínio,
  pelas CLIs e pelas operações do painel;
- configurações explícitas com outro modelo agora falham antes de criar uma
  tentativa ou chamar o Flow;
- `.env.example`, arquitetura, fluxo operacional e guia de preenchimento
  foram alinhados à regra;
- uma tentativa com erro de configuração foi reconciliada somente após
  confirmar log não retentável e ausência de arquivo de saída, preservando
  seu histórico;
- verificação: 152 testes passaram; gerações reais permanecem fora do
  versionamento e exigem aprovação humana vinculada ao frame.

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

### 2026-09-19 — Normalização de estados e logs da Fase 3

Atividade concluída tecnicamente sem executar o pipeline operacional, chamar o
Flow, migrar arquivos históricos ou alterar hashes, aprovação, locks e regras
de retomada.

- criado um vocabulário de estados por campo para `status`,
  `imagem_status`, `video_status` e `carrossel_status`;
- adotado `snake_case` ASCII como representação canônica das novas gravações;
- mantida leitura compatível com valores históricos que usam espaços ou
  acentos, sem regravação automática;
- estados desconhecidos passam a produzir erro claro com o nome do campo;
- criado o evento operacional versionado e o histórico append-only
  `<pasta_do_clipe>/logs/eventos.jsonl`;
- integrados ao histórico executor e carrossel, registrando produção, clipe,
  etapa, método, resultado, erro e horários;
- IDs de projeto e conteúdos longos do comando são redigidos no log
  estruturado; o `gflow.log` bruto continua preservado;
- atualizados arquitetura e guia de preenchimento com o contrato canônico;
- usado um grafo estrutural temporário do pacote para localizar os pontos
  centrais de persistência; nenhum artefato do grafo foi criado no repositório.
- adicionado `/graphify-out/` ao `.gitignore` após a auditoria detectar que
  conversões temporárias poderiam expor cópias de planilhas operacionais ao
  índice Git;
- commit local da normalização de estados e logs criado sem tag ou publicação
  remota.

Verificações: 58 testes e 3 subtestes aprovados, incluindo compatibilidade de
grafias legadas, rejeição de estados inválidos, redação de comando e logs de
sucesso e falha no executor e no carrossel. `git diff --check` não encontrou
erros. Nenhuma chamada ao Flow foi feita.

Auditoria final: os 13 arquivos previstos foram conferidos, o índice não contém
estado operacional, mídia, segredo ou artefato do Graphify, e as CLIs nova e
histórica mantêm as mesmas opções. O Ruff não foi executado porque permanece
indisponível no ambiente atual.

Próxima ação: iniciar, sob novo gate `high`, o reforço dos hashes e do vínculo
de aprovação à revisão correta, sem reutilizar automaticamente este gate.

### 2026-09-20 — Hashes e vínculo de aprovação da Fase 3

Atividade concluída tecnicamente sem chamar o Flow, gerar mídia, apagar ativos
históricos ou migrar em massa estados operacionais.

- a resposta importada passou a ser conferida contra o SHA-256 que nomeia sua
  pasta de revisão;
- `plano_producao.json` e cada `plano_clipe.json` passaram a ser
  comparados com o conteúdo validado de `resposta_ia.json` antes da execução;
- novos registros de imagem e vídeo em `execucao.json` passaram a usar
  esquema versionado, SHA-256 do arquivo, SHA-256 da revisão importada e
  fingerprint operacional;
- o vínculo técnico de aprovação passou a registrar produção, clipe, pacote,
  revisão, fingerprint, caminho canônico e SHA-256 exato do frame;
- vídeo passa a ser bloqueado se qualquer parte do vínculo divergir da revisão
  ou do arquivo atual;
- ativar uma revisão diferente limpa a aprovação na planilha, enquanto
  reimportar a mesma revisão preserva a decisão já registrada;
- gerar ou registrar outra imagem revoga a aprovação anterior; sincronizações
  comuns e vídeos históricos concluídos não reescrevem a célula;
- aprovações históricas sem identificação de revisão falham de modo seguro e
  exigem nova revisão humana, sem apagar a mídia anterior;
- arquitetura e guia operacional foram atualizados com o novo contrato.

Verificações: 69 testes aprovados sem cache, incluindo adulteração de resposta,
mudança de revisão, aprovação legada, troca de frame e preservação idempotente;
compilação de `src/`, `scripts/` e `tests/`; e
`git diff --check` sem erros. O Ruff não foi executado porque continua
indisponível no ambiente atual. Nenhuma chamada ao Flow foi feita.

Arquivos alterados: executor, orquestrador, importador, carrossel, três módulos
de teste, arquitetura, guia operacional e este plano. As alterações permanecem
sem commit nesta atividade.

Próxima ação: iniciar, sob novo gate `high`, o reforço de locks, retomada
e idempotência. Migrações históricas e testes de recuperação permanecem em
bloco posterior.

### 2026-09-20 — Locks, retomada e idempotência da Fase 3

Atividade concluída tecnicamente sem chamar o Flow, gerar mídia, apagar ativos
históricos ou executar migração de estado.

- criado um lock por clipe com esquema versionado, token aleatório, PID,
  host, operação, horário e contexto da revisão;
- uma execução concorrente com processo local ativo é bloqueada; locks locais
  órfãos são arquivados em `logs/locks/` antes da retomada, enquanto locks de
  outro host, inválidos ou malformados falham de modo seguro e são preservados;
- a verificação de processo no Windows usa consulta somente leitura, sem enviar
  sinais ao processo proprietário;
- executor e carrossel compartilham a mesma exclusão mútua por clipe, e a
  liberação só remove o lock quando o token ainda pertence à execução atual;
- cada tentativa recebe chave de idempotência determinística vinculada à
  produção, clipe, etapa, modelo, revisão, fingerprint, pacote e, no vídeo, ao
  frame aprovado;
- o estado da tentativa distingue `preparada` de `submetida`: tentativas que
  não chegaram ao envio podem ser refeitas, mas envios incertos sem saída local
  são bloqueados para impedir cobrança e mídia duplicadas;
- uma tentativa submetida que já possua exatamente uma saída local válida é
  promovida para o registro de mídia sem novo envio ao Flow;
- caminhos de tentativa e saída são validados dentro da pasta do clipe, e uma
  tentativa de vídeo não pode aceitar imagem como resultado;
- arquitetura e guia operacional foram atualizados com as regras de
  concorrência, recuperação e intervenção manual.

Verificações: 82 testes aprovados sem cache, incluindo concorrência, lock
órfão, lock estrangeiro ou malformado, troca de token, retomada sem reenvio,
envio incerto, adulteração da chave de idempotência e separação estrita entre
saídas de imagem e vídeo; compilação de `src/`, `scripts/` e `tests/`; e
`git diff --check` sem erros. Os avisos exibidos limitam-se à futura
normalização CRLF/LF pelo Git. O Ruff não foi executado porque continua
indisponível no ambiente atual. Nenhuma chamada ao Flow foi feita.

Arquivos alterados nesta atividade: controle de execução, executor, carrossel,
dois módulos de teste, arquitetura, guia operacional e este plano. As
alterações permanecem sem commit.

Próxima ação: iniciar, sob novo gate `high`, as migrações e os testes de
integração de recuperação da Fase 3.

### 2026-09-20 — Migrações e recuperação da Fase 3

Atividade concluída tecnicamente sem chamar o Flow, gerar mídia, aplicar a
migração aos estados reais, apagar arquivos históricos ou publicar alterações.

- criado um migrador explícito de `execucao.json`, com simulação como padrão e
  aplicação somente mediante `--aplicar`;
- a aplicação usa o lock compartilhado do clipe, preserva backup imutável pelo
  hash do estado original e grava o estado novo de forma atômica;
- estados, mídias, aprovações e tentativas têm suas versões validadas antes de
  qualquer escrita, e formatos desconhecidos falham de modo seguro;
- aprovações legadas sem vínculo comprovável são arquivadas no histórico e
  exigem nova revisão humana; o sistema pode limpar a célula `aprovacao`, mas
  nunca conceder aprovação;
- revisões com clipes pendentes podem ser auditadas sem liberar esses clipes
  para execução, e estados sob `antigos/` permanecem fora da migração;
- adicionado teste de integração com planilha XLSX real para recuperar uma
  tentativa submetida com saída local, promovendo-a sem nova chamada ao Flow;
- arquitetura e guia operacional foram atualizados com simulação, aplicação,
  backups, reaprovação e procedimento de recuperação.

Verificações finais: 91 testes e 3 subtestes aprovados sem cache; compilação de
`src/`, `scripts/` e `tests`; CLI executada em modo simulação sobre os dados
locais, com 45 estados migráveis, nenhum erro e 1 estado histórico preservado;
e `git diff --check` sem erros. Os avisos exibidos limitam-se à futura
normalização CRLF/LF pelo Git. O Ruff não foi executado porque continua
indisponível no ambiente atual. Nenhuma chamada ao Flow foi feita.

Arquivos alterados nesta atividade: migrador e wrapper compatível, CLI,
adaptador XLSX, carregamento de revisões, testes de migração e recuperação,
arquitetura, guia operacional e este plano. As alterações da Fase 3 permanecem
sem commit.

O critério da Fase 3 foi cumprido: interrupções com resultado local válido são
retomadas sem duplicar ativos, enquanto resultados incertos permanecem
bloqueados. Próxima ação: iniciar, sob novo gate `medium`, o backend local e as
consultas somente leitura da Fase 4.

### 2026-09-20 — Backend e consultas somente leitura da Fase 4

Atividade concluída sem expor o servidor à rede, alterar estados operacionais,
executar o pipeline ou chamar o Flow.

- criado `pipeline_flow.web` com uma aplicação FastAPI e um modelo de leitura
  recomposto a cada requisição;
- adicionadas consultas para painel, produções, revisões, clipes, mídias,
  entregas e eventos operacionais;
- todas as rotas funcionais usam `GET`; tentativas de escrita recebem `405`;
- o servidor aceita apenas `localhost` e endereços de loopback, rejeitando
  `0.0.0.0` e endereços da rede local;
- caminhos de entrega são validados contra a raiz configurada, caminhos
  externos são reduzidos ao nome e comandos persistidos não são expostos;
- valores históricos inválidos da planilha são exibidos como diagnósticos sem
  ocultar as linhas restantes nem regravar o arquivo;
- criado `scripts/servir_painel.py` como comando compatível e declaradas as
  dependências FastAPI e Uvicorn;
- ampliado o ignore para artefatos Graphify em subpastas e `*.egg-info/`.

Verificações: 98 testes e 3 subtestes aprovados sem cache; compilação de `src/`,
`scripts/` e `tests`; ajuda da nova CLI com código 0; consulta sobre os dados
locais retornando 5 produções ativas, 25 clipes, 28 entregas e 1 diagnóstico
histórico; e comparação de 48 hashes antes e depois da consulta, todos
inalterados. `git diff --check` não encontrou erros. O único aviso da suíte é
uma depreciação interna do `TestClient` do FastAPI/Starlette. O Ruff permanece
indisponível. Nenhuma chamada ao Flow foi feita.

Arquivos alterados nesta atividade: configuração de dependências e ignores,
leitor XLSX, pacote web, wrapper da CLI, testes, arquitetura e este plano. As
alterações permanecem sem commit.

Próxima ação: iniciar, sob novo gate `medium`, o painel HTML de produções,
clipes, imagens, entregas e logs da Fase 4.

### 2026-09-20 — Painel visual e conclusão da Fase 4

Atividade concluída sem alterar estados operacionais, executar o pipeline,
aprovar imagens ou chamar o Flow.

- construído painel HTML local com visão geral, indicadores, próximas ações,
  diagnósticos, produções, clipes, prévias de mídia, entregas e eventos;
- adicionados filtros por texto, produção e próxima ação, estados vazios,
  mensagens de falha e atualização manual dos dados;
- aplicado layout responsivo, navegação por teclado, foco visível, região viva,
  redução de movimento, cores semânticas e impressão simplificada;
- revisada a semântica da navegação com `aria-current`, garantida a visibilidade
  da seção ativa em navegação horizontal e contextualizados os textos
  alternativos das mídias;
- preservadas as rotas exclusivamente de leitura, a restrição a loopback e as
  validações de caminhos e extensões de mídia.

Verificações: 101 testes e 3 subtestes aprovados sem cache; compilação de
`src/`, `scripts/` e `tests`; smoke test real em Chrome nas larguras 1440, 768,
390 e 320 px, sem overflow da página, respostas HTTP com erro ou perda de
visibilidade da seção ativa; contraste principal entre 4,55:1 e 9,99:1; e
`git diff --check` sem erros. Permanece apenas o aviso conhecido de depreciação
interna do `TestClient`; o Ruff continua indisponível no ambiente.

O critério da Fase 4 foi cumprido: abrir e navegar pelo painel não altera
estado. As alterações das Fases 3 e 4 permanecem sem commit. Próxima ação:
iniciar, sob novo gate `medium`, a preparação de pacotes, importação de
respostas e registro de imagens pela interface na Fase 5.

### 2026-09-20 — Pacotes, respostas e imagens pela interface na Fase 5

Atividade concluída sem chamar o Flow, aprovar imagens, gerar mídia ou liberar
vídeo. As mutações exercitadas pelos testes usaram somente diretórios temporários.

- criada a fachada `pipeline_flow.web.operations`, reutilizando os serviços
  existentes de preparação, importação e registro de imagem;
- a preparação atualiza revisões, relatório e ZIP consolidado, que pode ser
  baixado pela interface sem aceitar caminho fornecido pelo navegador;
- respostas existentes podem ser selecionadas e novos JSON podem ser enviados,
  validados, importados com atualização da planilha e preservados em
  `preparados/respostas_ia/`;
- o registro de imagem aceita PNG, JPEG e WebP de até 50 MiB, valida extensão e
  conteúdo, limita a operação à revisão ativa e reutiliza lock, histórico, cópia
  para a revisão, revogação de aprovação anterior e sincronização da planilha;
- todas as escritas exigem confirmação no formulário, diálogo final e cabeçalho
  `X-Pipeline-Confirmation: confirmar`;
- criada a seção responsiva `Operações`, com seleções dependentes, feedback
  acessível e indicação explícita de que aprovação e Flow estão fora do bloco.

Verificações: 109 testes e 6 subtestes aprovados sem cache; validação de sintaxe
do JavaScript; compilação de `src/`, `scripts/` e `tests`; smoke test em Chrome
nas larguras 1440, 768, 390 e 320 px, sem overflow, respostas HTTP com erro ou
falhas de console; acesso direto à seção mantendo `scrollY=0`; ZIP disponível
para download; e requisição de escrita sem confirmação recusada com HTTP 400.
`git diff --check` não encontrou erros. Permanece o aviso conhecido de
depreciação do `TestClient`; o Ruff continua indisponível no ambiente.

Arquivos alterados nesta atividade: fachada e rotas web, HTML, CSS, JavaScript,
dois módulos de teste, README, arquitetura e este plano. As alterações das Fases
3, 4 e deste bloco da Fase 5 permanecem sem commit.

Próxima ação concluída no registro abaixo.

### 2026-09-20 — Aprovação e rejeição pela interface na Fase 5

Atividade concluída sem chamar o Flow, gerar mídia ou iniciar vídeo. Aprovar na
interface registra a decisão humana e seu vínculo técnico, mas a execução de
vídeo permanece fora deste bloco.

- criado caminho explícito `Workbook.set_human_approval`, restrito aos valores
  `aprovada` e `rejeitada`, sem retirar a proibição de aprovação do método de
  escrita sistêmica;
- criada transação sob lock por clipe que reabre estado e planilha, bloqueia
  clipes com vídeo, valida a imagem atual e compara o SHA-256 esperado pela tela;
- a aprovação grava primeiro a planilha e depois o vínculo técnico; a rejeição
  remove primeiro o vínculo, exige justificativa e só depois atualiza a planilha,
  mantendo falhas parciais fechadas para vídeo;
- decisões registram revisão, SHA-256, horário e justificativa no histórico do
  estado e geram evento operacional estruturado;
- criada a rota `POST /api/operations/review-image`, com confirmação obrigatória,
  JSON limitado a 8 KiB e resposta `409` quando a imagem ficou obsoleta;
- criada a seção responsiva `Revisão`, com prévia ampla, produto, papel, revisão,
  hash, decisão atual, última justificativa, confirmação explícita e ações
  distintas de aprovação e rejeição;
- o modelo de leitura passou a expor a decisão humana, o resumo seguro da última
  revisão e os indicadores do plano necessários para selecionar somente frames
  que controlam vídeo.

Verificações: 119 testes e 6 subtestes aprovados;
compilação de `src/`, `scripts/` e `tests`; validação de sintaxe do JavaScript; e smoke test
em Chrome nas larguras 1440, 768, 390 e 320 px, com 21 cards reais, `scrollY=0`,
sem overflow horizontal, falhas de JavaScript ou respostas HTTP com erro. Os
testes cobrem hash obsoleto, rejeição com justificativa e as duas ordens de
falha parcial. Permanece somente o aviso conhecido de depreciação do
`TestClient`.

Próxima ação concluída no registro abaixo.

### 2026-09-20 — Carrossel e operações locais pela interface na Fase 5

Atividade concluída sem chamar o Flow, consumir créditos, gerar vídeo ou alterar
dados operacionais reais. As gerações exercitadas pelos testes usaram somente
diretórios temporários; o smoke test fez apenas consultas locais.

- criada a seção responsiva `Carrossel`, agrupada por produção, com prévia 9:16,
  conteúdo do plano, destino e palavra de CTA, contadores de caracteres e estado
  da versão já gerada;
- a autorização exige simultaneamente `gerar_carrossel=sim` na planilha e
  `carrossel.ativo=true` no plano, mas é independente de `aprovacao` e nunca
  autoriza nem inicia vídeo;
- criada a rota `POST /api/operations/generate-carousel`, com confirmação
  obrigatória, corpo JSON limitado a 8 KiB e resposta `409` para revisão ou hash
  obsoleto;
- o serviço reabre o clipe sob o lock operacional, revalida o SHA-256 esperado
  e verifica que a saída é um PNG não vazio de 1080 x 1920;
- gerar novamente cria um arquivo com identificador único e preserva todas as
  versões anteriores; a saída continua restrita a `PIPELINE_DELIVERY_DIR`;
- a próxima ação do painel prioriza o carrossel local autorizado sem confundir
  essa permissão com a revisão humana necessária para vídeo.

Verificações: 127 testes e 6 subtestes aprovados; compilação de `src/`,
`scripts/` e `tests`; validação de sintaxe do JavaScript; e smoke test em Chrome
nas larguras 1440, 768, 390 e 320 px, com 21 cards reais, `scrollY=0`, sem
overflow horizontal, falhas de JavaScript ou respostas HTTP com erro. A revisão
visual confirmou três colunas no desktop e uma coluna no celular. Os testes
cobrem autorização independente, plano inativo, hash obsoleto, lock liberado em
falha, validação do PNG, bloqueio de saída fora da pasta de entregas e
regeneração que mantém a versão anterior.

O skill `data-experience-designer` orientou a hierarquia, a leitura operacional,
os estados explícitos e a revisão responsiva da galeria. Permanece somente o
aviso conhecido de depreciação interna do `TestClient`. As alterações das Fases
3, 4 e 5 continuam sem commit.

Próxima ação concluída no registro abaixo.

### 2026-09-20 — Liberação e acompanhamento de vídeo pela interface na Fase 5

Atividade concluída sem chamar o Flow, consumir créditos, gerar mídia ou alterar
estado operacional real. Todos os caminhos de execução foram exercitados com
mocks e diretórios temporários; o smoke test enviou somente requisições GET.

- criada a seção responsiva `Vídeos`, com diagnóstico do executor, prévias,
  método, duração, modelo, vínculo de aprovação e estados bloqueado, pronto, na
  fila, em execução, interrompido, falhou e concluído;
- a rota `POST /api/operations/generate-video` aceita somente produção, revisão,
  clipe, SHA-256 esperado e a frase exata `GERAR VIDEO`; binário, projeto,
  modelo, timeout, diretórios e argumentos vêm exclusivamente da configuração;
- a interface acrescenta checkbox e diálogo final sobre consumo de créditos;
  o backend mantém o cabeçalho de confirmação e responde com HTTP `202`;
- o preflight recusa revisão inativa, plano sem vídeo, vídeo concluído, tentativa
  pendente, lock, imagem ausente ou obsoleta, aprovação desvinculada, projeto
  ausente e `gflow.exe` indisponível;
- o executor revalida o SHA-256 esperado dentro do lock, imediatamente antes de
  preparar a tentativa e executar o comando fixo com `shell=False`;
- toda nova geração exige `aprovacao=aprovada` e vínculo técnico, mesmo se o
  campo `aprovacao_necessaria` de um plano futuro vier incorreto;
- o processo atual do painel permite somente uma geração paga simultânea e usa
  uma tarefa em segundo plano; estados persistentes, idempotência e retomada
  conservadora continuam em `execucao.json`, locks e eventos;
- criada a consulta `GET /api/operations/executions`; ela nunca devolve o
  comando, redige o ID do projeto, resume timeouts e limita mensagens de erro;
- o frontend faz polling apenas enquanto uma tarefa está ativa ou seu término
  ainda não apareceu na leitura persistente.

Verificações: 138 testes e 6 subtestes aprovados; compilação de `src/`,
`scripts/` e `tests`; validação de sintaxe do JavaScript; busca por problemas de
codificação nos arquivos alterados; e `git diff --check` sem erros. O smoke test
em Chrome nas larguras 1440, 768, 390 e 320 px mostrou 25 clipes planejados, 3
vídeos concluídos, `scrollY=0`, sem overflow horizontal, falhas de JavaScript,
respostas HTTP com erro ou requisições POST. Como não há aprovação técnica
vinculada e o `gflow.exe` configurado está ausente, nenhum botão pago foi
exibido, que é o comportamento fechado esperado.

O skill `data-experience-designer` orientou a hierarquia dos bloqueios, a
separação entre diagnóstico e ação paga, os estados semânticos e a revisão
responsiva. Permanece somente o aviso conhecido de depreciação interna do
`TestClient`. As alterações das Fases 3, 4 e 5 continuam sem commit.

Próxima ação: sob novo gate `high`, auditar segurança, caminhos, comandos,
concorrência e trava de créditos da Fase 5.

### 2026-09-20 — Auditoria de segurança e trava de créditos da Fase 5

Auditoria concluída sem chamar o Flow, consumir créditos, gerar mídia ou alterar
estado operacional real. As verificações usaram mocks, arquivos sintéticos e
diretórios temporários.

Achados corrigidos:

- a trava de vídeo pago passou a ser global e persistente entre os processos
  oficiais do projeto; um lock órfão é preservado para revisão manual porque o
  efeito externo pode ser incerto;
- a aprovação, o SHA-256 e o vínculo da revisão são revalidados novamente no
  executor imediatamente antes de adquirir a trava e preparar a submissão;
- tentativas novas guardam `comando_sha256`, mas não persistem linha de comando,
  prompt nem ID de projeto; erros estruturados também redigem prompt e projeto;
- mídia de estado precisa permanecer dentro da pasta da revisão, e o índice de
  entregas não pode redirecionar cópias para fora da raiz autorizada;
- índice de entregas e salvamento do XLSX receberam locks entre processos,
  mantendo as verificações otimistas de hash e os backups existentes;
- uploads e JSON são limitados durante o streaming; requisições de navegador
  externas ou `cross-site` são bloqueadas; imagens têm limite seguro de pixels;
- a API continua sem aceitar comandos, binários, argumentos, projeto, modelo ou
  diretórios fornecidos pelo navegador e mantém `shell=False`.

Verificações: 149 testes e 6 subtestes aprovados; compilação de `src/`,
`scripts/` e `tests`; `git diff --check`; buscas estáticas por execução insegura,
persistência indevida de comando, leitura integral de corpos HTTP e vazamento na
API. `bandit` e `ruff` não estavam instalados, portanto nenhum pacote foi
baixado apenas para a auditoria. O único aviso da suíte continua sendo a
depreciação interna do `TestClient`.

A consulta ao grafo local ajudou a localizar a relação entre executor, aprovação,
planilha, entregas e locks; os achados foram confirmados diretamente no código.
As alterações das Fases 3, 4 e 5 continuam sem commit.

Próxima ação: iniciar a Fase 6 com novo gate, começando pelo refinamento de
acessibilidade, responsividade e experiência visual.

### 2026-09-20 — Acessibilidade e responsividade da Fase 6

Atividade concluída sem chamar o Flow, consumir créditos, gerar mídia, enviar
requisições de escrita ou alterar estado operacional.

- a navegação passou a seguir o padrão semântico de abas, com
  `tablist`, `tab`, `tabpanel`, seleção explícita, foco roving e suporte a
  setas, `Home` e `End`;
- a troca de seção deixou de mover o foco automaticamente para o título e o
  carregamento inicial deixou de provocar deslocamento da página;
- o painel agora informa carregamento, atualização e falha em todas as áreas,
  usa `aria-busy` durante consultas e mantém o estado da conexão visível em
  telas pequenas;
- alvos de toque, navegação horizontal, quebra de conteúdo, cartões, eventos e
  cabeçalho foram refinados até 320 px;
- foram acrescentados comportamentos específicos para contraste aumentado,
  cores forçadas e redução de movimento, sem depender apenas de cor para
  comunicar estado.

Verificações: 149 testes e 6 subtestes aprovados; compilação de `src/`,
`scripts/` e `tests`; validação de sintaxe do JavaScript; e
`git diff --check`. O smoke test real em Chrome percorreu as oito seções nas
larguras 1440, 768, 390 e 320 px, com um único painel visível, `scrollY=0`,
sem overflow horizontal, falhas de JavaScript, respostas HTTP com erro ou
requisições POST. A navegação por setas e `Home` também foi exercitada.

O skill `data-experience-designer` orientou hierarquia, estados, semântica,
contraste e revisão responsiva. A consulta do Graphify mostrou que o grafo
existente ainda não representa os ativos web atuais; por isso, o código e o
navegador foram usados como fontes de verdade. Permanece somente o aviso
conhecido de depreciação interna do `TestClient`. As alterações das Fases 3,
4, 5 e 6 continuam sem commit.

Próxima ação: consolidar a documentação final e a solução de problemas da
Fase 6 sob novo gate `low`.

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
| 6 | Consolidar roteiro de primeiro uso, planilha-modelo, `.env`, pré-requisito do `gflow` e suporte | GPT-5.6 Sol low | a documentação exigir novo comando, validação executável ou mudança de contrato |
| 6 | Consolidar documentação final e solução de problemas | GPT-5.6 Sol low | a documentação exigir mudança de código ou contrato |
| 6 | Definir licença, metadados do repositório e política de distribuição | GPT-5.6 Sol low | houver publicação externa, mudança de acesso ou decisão jurídica não fornecida pela titular |
| 6 | Criar diagnóstico seguro de configuração e testes de primeiro uso | GPT-5.6 Sol medium | o diagnóstico passar a alterar arquivos, executar o Flow ou tratar segredos |
| 6 | Configurar CI e validar instalação, lint, testes, contratos e smoke web | GPT-5.6 Sol medium | a CI precisar de segredos, publicação ou mudança de permissões |
| 6 | Executar aceitação a partir de clone limpo com uma pessoa usuária | GPT-5.6 Sol medium | o teste passar a usar produção real, consumir créditos ou exigir mudança de comportamento |
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
