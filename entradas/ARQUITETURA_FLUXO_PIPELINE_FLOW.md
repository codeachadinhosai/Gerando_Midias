# ARQUITETURA E FLUXO OPERACIONAL --- PIPELINE FLOW

## 1. Objetivo deste documento

Este documento define **como o projeto deve funcionar de ponta a ponta**
antes das alterações no código.

Ele será a referência para a próxima etapa de desenvolvimento: comparar
o projeto atual com esta arquitetura e alterar `fila.py`, `runner.py`, o
script de execução e os demais componentes para que todos obedeçam ao
mesmo contrato.

Os dois arquivos centrais de configuração e controle são:

``` text
controle_pipeline_flow.xlsx
CLASSIFICADOR_UNIVERSAL.txt
```

A ideia central é separar claramente as responsabilidades:

``` text
VOCÊ
    ↓
controle_pipeline_flow.xlsx
    ↓
LEITURA / VALIDAÇÃO / ENRIQUECIMENTO
    ↓
CLASSIFICADOR_UNIVERSAL.txt
    ↓
PLANO DA PRODUÇÃO + PLANOS DOS CLIPES
    ↓
EXECUTOR
    ↓
IMAGEM / FRAME
    ↓
APROVAÇÃO HUMANA
    ↓
VÍDEO
    ↓
MONTAGEM / RESULTADO
```

O **Classificador Universal pensa e planeja**.

O **Python executa**.

O **Flow gera os ativos**.

A **planilha controla o processo**.

A **pessoa aprova os frames antes da geração dos vídeos quando
necessário**.

------------------------------------------------------------------------

# 2. Estrutura conceitual do sistema

O sistema terá seis camadas principais.

## Camada 1 --- Entradas

Contém:

-   imagens de produto;
-   imagens de inspiração;
-   imagens de ambiente;
-   imagens de detalhe;
-   vídeos existentes;
-   frames existentes;
-   referências globais da Júlia;
-   links de produto;
-   instruções humanas;
-   planilha de controle.

## Camada 2 --- Manifesto

O arquivo:

``` text
controle_pipeline_flow.xlsx
```

é a fonte operacional da produção.

Ele informa:

-   quais entradas devem ser processadas;
-   qual produto pertence a cada linha;
-   quais clipes pertencem à mesma produção;
-   a ordem dos clipes;
-   o papel desejado;
-   relações entre referências;
-   materiais existentes;
-   instruções humanas;
-   aprovação;
-   estado atual do pipeline.

## Camada 3 --- Enriquecimento

Responsável por transformar as entradas brutas em dados utilizáveis pelo
classificador.

Exemplos:

-   verificar se arquivos existem;
-   resolver `usar_com`;
-   localizar `material_existente`;
-   agrupar por `produto_id`;
-   agrupar por `producao_id`;
-   ordenar os clipes;
-   obter dados factuais do `link_produto`;
-   localizar referências globais da Júlia.

Essa camada **não decide o fluxo criativo**.

## Camada 4 --- Classificação e planejamento

O contrato está em:

``` text
CLASSIFICADOR_UNIVERSAL.txt
```

O classificador recebe o manifesto enriquecido e decide:

-   estrutura narrativa da produção;
-   função de cada clipe;
-   gerar, adaptar ou reutilizar;
-   fluxo cadastrado;
-   referências necessárias;
-   necessidade de Júlia;
-   necessidade de mão/rosto/corpo;
-   cena;
-   ação;
-   continuidade;
-   fala;
-   timeline;
-   necessidade de imagem;
-   necessidade de aprovação;
-   método de vídeo;
-   prompts finais.

## Camada 5 --- Execução

O Python lê os planos produzidos pelo classificador.

Ele não deve reinterpretar criativamente a produção.

Sua responsabilidade é:

-   montar comandos;
-   chamar o Flow/gflow;
-   localizar arquivos;
-   salvar resultados;
-   atualizar estados;
-   interromper quando precisa de aprovação;
-   continuar após aprovação;
-   registrar erros.

## Camada 6 --- Saída

Contém:

-   planos;
-   imagens geradas;
-   vídeos gerados;
-   vídeos reutilizados;
-   logs;
-   estado atualizado na planilha;
-   eventualmente a produção final montada.

------------------------------------------------------------------------

# 3. Estrutura recomendada de diretórios

A implementação pode adaptar os nomes físicos existentes, mas
conceitualmente o projeto deve possuir:

``` text
projeto/
│
├── controle_pipeline_flow.xlsx
├── CLASSIFICADOR_UNIVERSAL.txt
│
├── entrada/
│   └── imagens/
│
├── ativos/
│   └── julia/
│       ├── aberturas/
│       ├── ctas/
│       ├── lifestyle/
│       ├── frames/
│       └── outros/
│
├── referencias_globais/
│   └── julia/
│       ├── rosto.jpg
│       ├── rosto_1.jpg
│       ├── Corpo.png
│       └── mao.jpg
│
├── output/
│   ├── planos/
│   ├── flow/
│   │   ├── imagens/
│   │   └── videos/
│   ├── producoes/
│   └── logs/
│
└── scripts/
```

Não é obrigatório migrar tudo imediatamente para essa estrutura. Ela
define a separação lógica desejada.

------------------------------------------------------------------------

# 4. Etapa 0 --- Preparação dos insumos

Antes de executar o pipeline, devem existir os arquivos necessários.

## Obrigatório

``` text
controle_pipeline_flow.xlsx
CLASSIFICADOR_UNIVERSAL.txt
```

## Conforme a produção

Podem existir:

``` text
imagens de produto
imagens de inspiração
imagens de ambiente
vídeos existentes
frames existentes
```

## Referências globais da Júlia

Quando os fluxos utilizarem Júlia, o sistema poderá recorrer a:

``` text
rosto.jpg
rosto_1.jpg
Corpo.png
mao.jpg
```

Essas referências não precisam ser repetidas em cada linha do Excel.

------------------------------------------------------------------------

# 5. Etapa 1 --- Leitura da planilha

O sistema abre:

``` text
controle_pipeline_flow.xlsx
```

e lê a aba operacional.

A primeira regra é:

``` text
classifica = sim
```

Somente essas linhas entram na rodada.

Linhas com:

``` text
classifica = não
```

permanecem catalogadas, mas são ignoradas.

O sistema não deve excluir essas linhas.

------------------------------------------------------------------------

# 6. Etapa 2 --- Validação do manifesto

Antes de chamar IA ou Flow, validar os dados.

## Verificações mínimas

Para cada linha ativa:

-   `arquivo` existe?
-   `produto_id` está definido quando necessário?
-   `producao_id` está definido?
-   `ordem` é válida?
-   existe duplicidade problemática de ordem?
-   arquivos indicados em `usar_com` existem?
-   `material_existente` existe quando informado?
-   `uso_material` possui valor válido?
-   `papel_na_producao` possui valor válido?

Erros de estrutura devem ser registrados antes da classificação.

Exemplo:

``` text
status = pendente
erro = arquivo indicado em usar_com não encontrado
```

Não chamar geração para uma entrada estruturalmente inválida.

------------------------------------------------------------------------

# 7. Etapa 3 --- Agrupamento das produções

As linhas são agrupadas por:

``` text
producao_id
```

Exemplo:

``` text
CX001_VIDEO_01
```

Dentro da produção, ordenar por:

``` text
ordem
```

Resultado:

``` text
CX001_VIDEO_01

1 abertura
2 principal
3 principal
4 principal
5 cta
```

O Classificador Universal deve receber a produção **como conjunto**, e
não cinco chamadas independentes sem contexto.

------------------------------------------------------------------------

# 8. Produto x produção

É importante manter essa distinção.

## `produto_id`

Responde:

``` text
qual é o produto?
```

Exemplo:

``` text
CX001
```

## `producao_id`

Responde:

``` text
a qual vídeo esta entrada pertence?
```

Exemplo:

``` text
CX001_VIDEO_01
```

O mesmo produto pode gerar:

``` text
CX001_VIDEO_01
CX001_VIDEO_02
CX001_VIDEO_03
```

Cada produção pode ter narrativa e materiais diferentes.

------------------------------------------------------------------------

# 9. Etapa 4 --- Resolução das referências

Para cada linha, o sistema cria um inventário real de referências.

## Arquivo principal

Vem de:

``` text
arquivo
```

## Referências complementares

Vêm de:

``` text
usar_com
```

Exemplo:

``` text
arquivo = produto_frente.jpg
usar_com = produto_lado.jpg; produto_detalhe.jpg
```

Essas três imagens pertencem ao contexto do **mesmo clipe**.

`usar_com` nunca deve definir a sequência da produção.

------------------------------------------------------------------------

# 10. Etapa 5 --- Resolução de materiais existentes

Verificar:

``` text
material_existente
uso_material
```

O objetivo é evitar geração desnecessária.

## `reutilizar`

O material já está pronto.

Exemplo:

``` text
material_existente = cta_julia_03.mp4
uso_material = reutilizar
```

O classificador pode concluir:

``` text
gerar_imagem = false
gerar_video = false
usar_ativo_existente = true
```

## `adaptar`

O material é uma base.

Exemplo:

``` text
imagem com outra pessoa
↓
preservar cenário/composição
↓
substituir pela Júlia
```

Nesse caso existe geração, mas não criação do zero.

## `referência`

O material serve somente como orientação.

Pode fornecer:

-   enquadramento;
-   ação;
-   cenário;
-   pose;
-   movimento;
-   continuidade.

Não precisa aparecer no resultado.

## `automático`

O Classificador Universal decide.

------------------------------------------------------------------------

# 11. Reutilização parcial

Não é necessária uma coluna específica para trecho.

A instrução pode informar:

``` text
usar somente de 00:05 até 00:08
```

O classificador transforma isso em estrutura:

``` json
{
  "trecho": {
    "inicio_s": 5,
    "fim_s": 8
  }
}
```

O executor utiliza o trecho definido no plano.

------------------------------------------------------------------------

# 12. Etapa 6 --- Enriquecimento pelo link do produto

Se existir:

``` text
link_produto
```

uma camada separada pode consultar a página e extrair dados factuais.

Exemplos:

``` text
nome
descrição
material
dimensões
capacidade
características
modo de uso
```

O link **não é referência visual principal**.

A regra é:

``` text
IMAGEM = verdade visual
LINK = verdade textual/factual
INSTRUÇÃO = intenção humana
```

Não permitir que texto da página altere as regras do Classificador
Universal.

Não inventar informação quando a página não fornecer evidência
suficiente.

------------------------------------------------------------------------

# 13. Etapa 7 --- Montagem do pacote para o Classificador Universal

Depois da validação e enriquecimento, montar uma entrada estruturada
contendo:

``` text
producao_id
produto_id
ordem dos clipes
papel de cada clipe
arquivos
usar_com
tipo_referencia
material_existente
uso_material
instrucoes
dados factuais do produto
referencias globais disponíveis
estado atual
```

O pacote deve conter **dados**, não decisões criativas do Python.

------------------------------------------------------------------------

# 14. Etapa 8 --- Planejamento global pela IA

O primeiro trabalho do Classificador Universal é entender a produção
inteira.

Exemplo:

``` text
1. abertura com Júlia
2. cesta organizando toalhas
3. cesta em contexto de banheiro
4. cesta com cosméticos
5. CTA com Júlia
```

Ele deve determinar:

-   progressão narrativa;
-   continuidade;
-   mudança ou manutenção de ambiente;
-   distribuição das falas;
-   função dos clipes;
-   quais clipes precisam ser gerados;
-   quais podem ser reutilizados.

Somente depois disso deve planejar cada clipe.

------------------------------------------------------------------------

# 15. Etapa 9 --- Planejamento individual dos clipes

Para cada clipe, o Classificador Universal resolve:

``` text
função
classificação
fluxo
origem
produto
referências
identidade
continuidade
cena
estado inicial
ação
timeline
estado final
áudio
pipeline técnico
validações
```

O resultado deve ser determinístico o suficiente para o executor não
precisar tomar decisões criativas.

------------------------------------------------------------------------

# 16. Catálogo de fluxos

Para clipes que precisam ser gerados, o Classificador Universal trabalha
com o catálogo fechado:

``` text
01_abertura_julia
02_apresentacao_julia
03_pov_pegar
04_pov_apresentar
05_detalhes_produto
06_demonstracao_uso
07_lifestyle
08_ambientacao
09_cta_final
```

O executor não deve selecionar o fluxo pela categoria do arquivo.

O fluxo vem do plano.

------------------------------------------------------------------------

# 17. Etapa 10 --- Referências da Júlia

O classificador decide quais referências globais são necessárias.

## Exemplo --- abertura

Pode exigir:

``` text
rosto.jpg
rosto_1.jpg
Corpo.png
mao.jpg
```

dependendo do enquadramento.

## Exemplo --- POV somente com mão

Pode exigir apenas:

``` text
mao.jpg
```

Não deve exigir rosto apenas porque o clipe pertence à identidade da
Júlia.

## Exemplo --- produto sem pessoa

Pode não exigir nenhuma referência da Júlia.

Isso elimina a regra antiga de exigir rosto indiscriminadamente em toda
geração de imagem.

------------------------------------------------------------------------

# 18. Etapa 11 --- Decisão do pipeline técnico

Cada plano deve responder explicitamente:

``` text
precisa gerar imagem?
precisa aprovação?
precisa gerar vídeo?
qual método?
```

Exemplos:

## Abertura adaptando imagem

``` text
imagem: i2i
aprovação: sim
vídeo: i2v
```

## POV

``` text
imagem POV: i2i
aprovação: sim
vídeo: i2v
```

## Vídeo existente

``` text
imagem: não
aprovação: não
vídeo: não
ativo existente: sim
```

## Frame existente pronto

``` text
imagem: não
aprovação: conforme estado
vídeo: i2v
```

------------------------------------------------------------------------

# 19. Métodos técnicos

O plano pode usar:

``` text
nenhum
i2i
i2v
r2v
storyboard_i2i
extrair_frame
reutilizar_ativo
```

A escolha pertence ao Classificador Universal.

O runner apenas traduz a escolha em comando gflow compatível.

------------------------------------------------------------------------

# 20. Etapa 12 --- Geração do plano

Para cada produção:

``` text
output/planos/<producao_id>/plano_producao.json
```

Para cada clipe:

``` text
output/planos/<producao_id>/<id_clipe>/plano_clipe.json
```

Quando necessário:

``` text
prompt_imagem.txt
prompt_video.txt
```

Exemplo:

``` text
output/
└── planos/
    └── CX001_VIDEO_01/
        ├── plano_producao.json
        ├── CX001_VIDEO_01_01/
        │   ├── plano_clipe.json
        │   ├── prompt_imagem.txt
        │   └── prompt_video.txt
        ├── CX001_VIDEO_01_02/
        │   ├── plano_clipe.json
        │   ├── prompt_imagem.txt
        │   └── prompt_video.txt
        └── ...
```

------------------------------------------------------------------------

# 21. Etapa 13 --- Atualização da planilha após classificação

Após classificação:

``` text
status = classificado
classificacao = categoria definida
fluxo = fluxo definido
plano_arquivo = caminho do plano
```

Se precisa de imagem:

``` text
imagem_status = pendente
```

Se não precisa:

``` text
imagem_status = nao_necessaria
```

A planilha se torna o painel visível do estado real.

Os campos operacionais `status`, `imagem_status`, `video_status` e
`carrossel_status` usam valores canônicos em `snake_case` ASCII. A leitura
continua aceitando grafias históricas com espaços ou acentos, mas toda nova
gravação usa a forma canônica. Essa compatibilidade de leitura não reescreve
planilhas nem pacotes históricos automaticamente.

------------------------------------------------------------------------

# 22. Etapa 14 --- Geração de imagem/frame

O executor lê:

``` text
plano_clipe.json
prompt_imagem.txt
```

e utiliza as referências definidas no plano.

Não deve tentar inferir referências novamente.

Exemplo de referências:

``` text
produto
rosto
rosto_1
corpo
mao
cena
```

A ordem de referências deve ser explícita quando o modelo depender dela.

O resultado vai para algo como:

``` text
output/flow/imagens/<id_clipe>.png
```

------------------------------------------------------------------------

# 23. Etapa 15 --- Gate humano de imagem

Após a geração:

``` text
imagem_status = gerada
status = aguardando_aprovacao
```

A pessoa verifica o frame.

## Se aprovado

``` text
aprovacao = aprovada
status = pronto_para_video
```

## Se rejeitado

``` text
aprovacao = rejeitada
```

O vídeo não é gerado.

O fluxo deverá permitir corrigir/regenerar a imagem.

## Vínculo técnico da aprovação

O valor humano `aprovacao=aprovada` é necessário, mas não é suficiente para
liberar vídeo. O executor grava em `execucao.json` um vínculo versionado que
contém:

- produção e clipe;
- SHA-256 da resposta importada e do pacote de origem;
- fingerprint dos planos, insumos e prompts exportados;
- caminho canônico e SHA-256 do frame revisado;
- data da aprovação.

Antes de liberar vídeo, todos esses valores precisam corresponder à revisão
ativa e ao arquivo atual. A resposta importada também é validada contra o hash
usado no nome da pasta, e os planos individuais precisam corresponder ao
conteúdo de `resposta_ia.json`.

Ativar outra revisão ou registrar/gerar outra imagem revoga a aprovação
anterior na planilha. Registros históricos de aprovação que não identificam a
revisão deixam de autorizar vídeo e exigem uma nova revisão humana; nenhuma
mídia histórica é apagada ou sobrescrita.

Esse gate deve ser **genérico**.

O conceito anterior de:

``` text
--gate-rosto
```

deve evoluir para algo como:

``` text
--gate-imagem
```

porque o que está sendo aprovado pode ser:

-   rosto;
-   Júlia inteira;
-   produto;
-   POV;
-   mão;
-   cenário;
-   composição;
-   frame de storyboard.

------------------------------------------------------------------------

# 24. Etapa 16 --- Geração do vídeo

Quando:

``` text
gerar_video = true
```

e, se aplicável:

``` text
aprovacao = aprovada
```

o executor lê:

``` text
prompt_video.txt
plano_clipe.json
```

e chama o método indicado:

``` text
i2v
r2v
outro método suportado
```

O vídeo deve respeitar:

``` text
9:16
8 segundos
timeline definida
fala definida
referências definidas
```

O runner não deve acrescentar uma narrativa própria baseada em
categorias antigas.

------------------------------------------------------------------------

# 25. Etapa 17 --- Reutilização de vídeo

Quando o plano indicar:

``` text
usar_ativo_existente = true
gerar_video = false
```

não chamar Flow.

Registrar:

``` text
video_status = reutilizado
video_arquivo = caminho do ativo
```

Se houver trecho:

``` text
5s → 8s
```

a etapa de composição utiliza somente esse intervalo.

------------------------------------------------------------------------

# 26. Etapa 18 --- Atualização após vídeo

Durante geração:

``` text
status = gerando_video
video_status = gerando
```

Após sucesso:

``` text
video_status = gerado
video_arquivo = caminho
status = concluido
```

Em erro:

``` text
video_status = erro
status = erro
erro = descrição real
```

------------------------------------------------------------------------

# 27. Etapa 19 --- Produção final

Quando todos os clipes válidos de uma `producao_id` estiverem concluídos
ou reutilizados, existe material suficiente para montar a produção.

A ordem é definida exclusivamente por:

``` text
ordem
```

Exemplo:

``` text
01_abertura.mp4
02_toalhas.mp4
03_banheiro.mp4
04_cosmeticos.mp4
05_cta_reutilizado.mp4
```

A montagem não deve reordenar criativamente os clipes.

------------------------------------------------------------------------

# 28. Fluxo completo de estados

Fluxo normal com geração de imagem:

``` text
novo
↓
classificando
↓
classificado
↓
aguardando_imagem
↓
imagem gerada
↓
aguardando_aprovacao
↓
aprovada
↓
pronto_para_video
↓
gerando_video
↓
concluido
```

Fluxo com vídeo existente:

``` text
novo
↓
classificando
↓
classificado
↓
material validado
↓
video_status = reutilizado
↓
concluido
```

Fluxo com problema:

``` text
novo
↓
classificando
↓
pendente ou erro
```

------------------------------------------------------------------------

# 29. Responsabilidade de cada componente

## `controle_pipeline_flow.xlsx`

Responsável por:

``` text
manifesto
relações
sequência
intenção
estado
aprovação
```

Não deve conter prompts gigantes.

## `CLASSIFICADOR_UNIVERSAL.txt`

Responsável por:

``` text
regras de decisão
catálogo
planejamento
continuidade
reutilização
identidade
fala
timeline
pipeline técnico
```

## JSON de plano

Responsável por:

``` text
decisão técnica resolvida
```

É a ponte entre IA e Python.

## `prompt_imagem.txt`

Responsável por:

``` text
instrução final para geração do frame
```

## `prompt_video.txt`

Responsável por:

``` text
instrução final para geração do vídeo
```

## Python

Responsável por:

``` text
ler
validar
chamar serviços
executar planos
salvar arquivos
atualizar estados
registrar erros
```

Não é o cérebro criativo.

## Flow / gflow

Responsável por:

``` text
gerar imagem
gerar vídeo
```

Não deve decidir a produção.

## Usuário

Responsável por:

``` text
manifesto
intenção
materiais
aprovação
```

------------------------------------------------------------------------

# 30. Mudança arquitetural principal no projeto atual

O projeto atual possui decisões importantes baseadas em:

``` text
categoria
nome de pasta
tipo de fila
regras internas do runner
```

A arquitetura desejada muda para:

``` text
PLANO JSON
↓
EXECUTOR
```

Ou seja:

``` text
ANTES

categoria
↓
Python decide pipeline
↓
Flow
```

deve evoluir para:

``` text
DEPOIS

planilha
↓
Classificador Universal
↓
plano_clipe.json
↓
Python executa exatamente o plano
↓
Flow
```

------------------------------------------------------------------------

# 31. Alterações previstas em `fila.py`

A implementação deverá ser revisada para representar conceitos como:

``` text
producao_id
produto_id
ordem
papel_na_producao
material_existente
uso_material
plano_arquivo
imagem_status
aprovacao
video_status
```

O `ItemFila` atual deverá deixar de ser apenas uma representação
orientada por categoria e passar a carregar/obedecer o plano do clipe.

A leitura de ficha de produto poderá continuar útil, mas deve alimentar
a camada de **enriquecimento**, não decidir fluxo.

------------------------------------------------------------------------

# 32. Alterações previstas em `runner.py`

O runner atual possui lógica que escolhe comportamentos por categoria.

Essa responsabilidade deve ser reduzida.

O runner deve receber algo equivalente a:

``` json
{
  "gerar_imagem": true,
  "metodo_imagem": "i2i",
  "gerar_video": true,
  "metodo_video": "i2v"
}
```

e executar.

As funções existentes de:

``` text
i2i
i2v
r2v
```

podem ser reaproveitadas.

A principal mudança é **quem decide utilizá-las**.

------------------------------------------------------------------------

# 33. Referência de mão no executor

A etapa i2i atual precisa evoluir para aceitar explicitamente:

``` text
produto
rosto
rosto_1
corpo
mao
```

Não assumir sempre:

``` text
produto + rostos + corpo
```

Exemplo POV:

``` text
produto + mao
```

Exemplo abertura:

``` text
cena + rosto + rosto_1 + corpo
```

Exemplo lifestyle:

``` text
produto + rosto + rosto_1 + corpo + mao
```

A ordem deve vir do plano.

------------------------------------------------------------------------

# 34. Alteração do gate

Substituir o conceito específico:

``` text
gate-rosto
```

por:

``` text
gate-imagem
```

A regra passa a ser:

> qualquer frame novo que servirá como base para vídeo pode exigir
> aprovação.

O gate deve funcionar independentemente da categoria.

------------------------------------------------------------------------

# 35. Enriquecimento de produto

Criar ou isolar uma etapa que faça:

``` text
link_produto
↓
extração
↓
normalização
↓
dados_produto
↓
Classificador Universal
```

A saída pode ser um objeto semelhante a:

``` json
{
  "nome": "",
  "descricao": "",
  "atributos": [],
  "fonte": "",
  "incertezas": []
}
```

O classificador usa esses dados como evidência factual.

------------------------------------------------------------------------

# 36. Novo módulo de leitura da planilha

Será necessário um componente responsável por:

``` text
ler Excel
validar colunas
normalizar valores
filtrar classifica=sim
agrupar producao_id
ordenar ordem
resolver caminhos
atualizar status
```

Esse módulo deve ser independente da lógica de geração.

------------------------------------------------------------------------

# 37. Novo módulo de planejamento

Será necessário integrar a IA usando:

``` text
CLASSIFICADOR_UNIVERSAL.txt
+
manifesto estruturado
+
referências
+
dados do produto
```

e validar que a resposta respeita os schemas definidos.

Planos inválidos não devem chegar ao runner.

------------------------------------------------------------------------

# 38. Validação dos planos

Antes de executar, verificar:

``` text
JSON válido
fluxo conhecido
método conhecido
arquivos existem
referências existem
duração suportada
aspecto suportado
prompts existem quando necessários
gate coerente
```

Exemplo:

``` text
gerar_imagem=true
```

exige:

``` text
prompt_imagem
método de imagem
referências necessárias
```

------------------------------------------------------------------------

# 39. Idempotência

O pipeline deve poder ser executado novamente sem destruir trabalho
concluído.

Exemplos:

Se:

``` text
video_status = gerado
```

não gerar novamente por padrão.

Se:

``` text
video_status = reutilizado
```

não gerar substituto.

Se:

``` text
imagem_status = gerada
aprovacao = pendente
```

não gerar vídeo.

Se:

``` text
aprovacao = rejeitada
```

não avançar até existir nova imagem/decisão.

------------------------------------------------------------------------

# 40. Logs

Cada execução deve registrar pelo menos:

``` text
producao_id
id_clipe
etapa
comando/método
resultado
erro
timestamp
```

Evitar que a única evidência de erro fique no terminal.

A planilha recebe a mensagem resumida.

O log pode conter detalhes técnicos.

O executor e o renderizador de carrossel mantêm um histórico append-only em:

``` text
<pasta_do_clipe>/logs/eventos.jsonl
```

Cada linha é um objeto JSON independente com `schema_version`,
`producao_id`, `id_clipe`, `etapa`, `metodo`, `comando`, `resultado`,
`erro`, `inicio_em` e `timestamp`. IDs de projeto e conteúdos longos do
comando são redigidos no log estruturado. Projeto e prompt também são
redigidos de mensagens de erro. Tentativas novas não guardam a linha de
comando em `execucao.json`: registram somente `comando_sha256`, modelo,
chave idempotente, diretório e saída. O `gflow.log` bruto continua sendo
preservado localmente no diretório ignorado da tentativa.

## Controle de concorrência e retomada

Executor e carrossel compartilham um lock exclusivo por clipe em
`.execucao.lock`. O arquivo possui esquema versionado, token aleatório, PID,
hostname, operação, horário e hashes da revisão. Um segundo processo não remove
nem substitui um lock cujo proprietário continua ativo.

Quando o proprietário local não existe mais, o lock órfão é movido para
`logs/locks/` antes da criação de outro lock. Locks malformados, de versão
desconhecida ou pertencentes a outro host falham de modo seguro e precisam ser
inspecionados. A verificação do processo no Windows usa consulta somente leitura
ao sistema operacional.

Nova geração de vídeo também adquire a trava global
`preparados/.locks/video-credit.lock`, compartilhada pela CLI e pelo painel.
Ela limita a uma única operação paga entre processos. Se o processo morrer,
essa trava não é recuperada automaticamente: como o efeito externo pode ser
incerto, é obrigatório conferir `execucao.json`, `gflow.log` e o Flow antes da
remoção manual. O índice de entregas e o salvamento da planilha usam locks
próprios para evitar colisão entre clipes e processos.

Cada chamada externa recebe uma `idempotency_key` determinística baseada em
produção, clipe, etapa, modelo, revisão, pacote, fingerprint e frame inicial
quando aplicável. A tentativa persistida distingue:

- `preparada`: ainda não houve submissão; uma interrupção pode descartar essa
  preparação e tentar novamente com a mesma chave;
- `submetida` com saída local válida: o arquivo é promovido para o estado
  concluído sem nova chamada ao Flow;
- `submetida` sem saída local: o executor bloqueia novo envio e exige
  conferência do `execucao.json`, do `gflow.log` e do Flow.

Imagens e vídeos recuperados preservam a tentativa no histórico, com resultado
`recuperada_sem_reenvio`. Saídas de imagem nunca são aceitas como resultado de
vídeo, e todos os caminhos de tentativa precisam permanecer dentro da pasta do
clipe.

## Migração versionada de estados

O comando `scripts/migrar_estados.py` moderniza `execucao.json` legados sem
gerar mídia. Sem `--aplicar`, ele executa somente uma simulação e informa
quais registros seriam alterados. A aplicação precisa ser solicitada
explicitamente:

``` powershell
python scripts/migrar_estados.py
python scripts/migrar_estados.py --producao PRODUCAO --clipe CLIPE
python scripts/migrar_estados.py --aplicar
```

Cada aplicação adquire o mesmo `.execucao.lock` usado pelo executor, verifica o
fingerprint da revisão e os hashes das mídias, cria um backup imutável em
`logs/migrations/` e só então substitui o estado de forma atômica. Repetir a
migração de um estado já atualizado não cria outro backup nem outro evento.

Registros legados de imagem e vídeo recebem a versão e os hashes da revisão
somente quando o arquivo original ainda existe e coincide com seu SHA-256.
Aprovações legadas não são promovidas automaticamente: são preservadas em
`aprovacoes_historicas`, removidas do vínculo ativo e, quando a revisão ainda
está ativa na planilha, a célula de aprovação é limpa. O sistema pode revogar
essa célula, mas nunca preenchê-la como aprovada.

Tentativas antigas ou incertas não são reenviadas pela migração. Elas continuam
sujeitas às regras conservadoras de retomada. Estados dentro de diretórios
`antigos/` também não são reescritos automaticamente e aparecem no relatório
como histórico preservado.

## Backend local com operações confirmadas

O módulo `pipeline_flow.web` oferece uma API FastAPI local que recompõe a visão
do pipeline diretamente da planilha, das revisões importadas, dos estados de
execução, do índice de entregas e dos logs estruturados. A consulta não mantém
cache persistente e não grava nos arquivos de origem.

A área `Operações` reutiliza os serviços existentes para preparar pacotes,
importar respostas e registrar uma imagem pronta. Essas mutações são locais,
exigem confirmação explícita no formulário e no cabeçalho HTTP e não chamam o
Flow, aprovam imagens ou liberam vídeos.

A área `Revisão` registra a decisão humana `aprovada` ou `rejeitada`. O backend
reabre o clipe da revisão ativa sob o mesmo lock operacional, valida o SHA-256
enviado pela tela contra a imagem atual e recusa decisões obsoletas com HTTP
`409`. Aprovações gravam primeiro a planilha e depois o vínculo técnico;
rejeições removem primeiro o vínculo técnico e exigem justificativa. Assim, uma
falha parcial permanece fechada para vídeo. Nenhuma decisão inicia geração.

O servidor é iniciado por:

``` powershell
python scripts/servir_painel.py
```

`WEB_HOST` precisa ser `localhost` ou um endereço de loopback, e `WEB_PORT`
define a porta. Endereços como `0.0.0.0` e IPs da rede local são rejeitados.

Rotas disponíveis nesta etapa:

- `GET /api/health`: diagnóstico do backend;
- `GET /api/dashboard`: totais, próximas ações e eventos recentes;
- `GET /api/productions`: produções e revisões conhecidas;
- `GET /api/productions/{producao_id}`: detalhe de uma produção;
- `GET /api/clips`: clipes, estados, mídias e vínculo de aprovação;
- `GET /api/deliveries`: índice de entregas e validade dos caminhos;
- `GET /api/logs`: eventos operacionais, com limite entre 1 e 500.
- `GET /api/operations`: pacotes, respostas e ZIP consolidado disponíveis;
- `GET /api/operations/executions`: diagnóstico seguro do executor e tarefas
  iniciadas pelo processo atual do painel, sem expor comandos;
- `GET /api/operations/package-latest`: download do ZIP mais recente;
- `POST /api/operations/prepare`: prepara revisões e o ZIP consolidado;
- `POST /api/operations/import`: importa resposta já salva;
- `POST /api/operations/import-upload`: valida, importa e preserva um JSON enviado;
- `POST /api/operations/register-image`: registra imagem na revisão ativa;
- `POST /api/operations/review-image`: registra aprovação ou rejeição humana
  vinculada à revisão e ao SHA-256 esperado.
- `POST /api/operations/generate-carousel`: gera ou regenera um card local
  autorizado, vinculado à revisão e ao SHA-256 esperado da imagem.
- `POST /api/operations/generate-video`: após confirmação reforçada, inicia em
  segundo plano uma geração unitária de vídeo e responde com HTTP `202`.

O backend não expõe o comando persistido em tentativas interrompidas. Caminhos
fora das raízes configuradas são reduzidos ao nome do arquivo, e entregas fora
de `PIPELINE_DELIVERY_DIR` são marcadas como inseguras. Estados históricos
desconhecidos aparecem como diagnósticos associados à linha, sem esconder as
demais linhas e sem reescrever a planilha.

As rotas de escrita exigem `X-Pipeline-Confirmation: confirmar`, validam
identificadores sem aceitar caminhos arbitrários e limitam uploads a 50 MiB
durante o streaming. Requisições de navegador com origem externa ou contexto
`cross-site` são bloqueadas. Imagens também têm limite explícito de pixels.
Respostas devem ser JSON válido; imagens são verificadas pelo conteúdo e pela
extensão. O registro usa o lock por clipe, revoga aprovação anterior e rejeita
revisões inativas ou clipes com vídeo já concluído.
O corpo JSON de revisão é limitado a 8 KiB; rejeições exigem justificativa de
até 500 caracteres. A aprovação só libera o gate técnico quando planilha e
`execucao.json` concordam sobre o frame, o hash, o pacote e a revisão.
O corpo JSON de carrossel também é limitado a 8 KiB. A operação exige
`gerar_carrossel=sim` e `carrossel.ativo=true`, revalida o SHA-256 da imagem
dentro do lock do clipe e valida que a saída é um PNG 1080 x 1920 não vazio.
Essa autorização é independente de `aprovacao` e nunca libera vídeo. Ao gerar
novamente, o renderizador cria um nome versionado e mantém todos os arquivos
anteriores.

A liberação de vídeo usa somente a ação fixa `video` e as configurações do
servidor (`GFLOW_ROOT`, `GFLOW_PROJECT_ID`, modelo e timeout). O navegador não
fornece binário, argumentos, diretório, projeto, modelo nem texto de comando.
Além de `X-Pipeline-Confirmation: confirmar`, o corpo JSON limitado a 8 KiB
precisa conter a frase exata `GERAR VIDEO`. A interface também exige checkbox e
diálogo final informando que pode haver consumo de créditos.

Antes de criar a tarefa, o backend confirma revisão ativa, plano com
`gerar_video=true`, ausência de vídeo ou tentativa pendente, executável e
projeto configurados, imagem atual, `aprovacao=aprovada` e vínculo técnico em
qualquer nova geração, mesmo se o plano trouxer um indicador divergente. O
executor revalida novamente o SHA-256 e a aprovação dentro do lock do clipe,
imediatamente antes de preparar a tentativa. A trava global persistente aceita
no máximo uma geração paga por vez entre processos oficiais do projeto.

O acompanhamento em memória informa fila, execução, sucesso ou falha e é
consultado por polling somente enquanto necessário. `execucao.json`, o lock e
`logs/eventos.jsonl` continuam sendo a fonte persistente: reiniciar o servidor
pode limpar a lista em memória, mas não autoriza reenvio de uma tentativa
incerta. Mensagens de timeout são resumidas, o ID do projeto é redigido e a API
jamais retorna a linha de comando. Mídias registradas precisam permanecer na
pasta da revisão, e entradas do índice não podem redirecionar cópias para fora
de `PIPELINE_DELIVERY_DIR`.

------------------------------------------------------------------------

# 41. Critérios para considerar a arquitetura implementada

A migração estará funcional quando for possível:

1.  adicionar imagens à entrada;
2.  preencher somente as colunas humanas da planilha;
3.  executar classificação;
4.  receber planos coerentes para uma produção completa;
5.  gerar somente as imagens necessárias;
6.  visualizar os frames;
7.  aprovar/rejeitar;
8.  gerar vídeos somente dos frames aprovados;
9.  reutilizar CTA/vídeos existentes sem regenerar;
10. usar `mao.jpg` em POV sem exigir rosto;
11. manter sequência por `producao_id` + `ordem`;
12. atualizar automaticamente o Excel;
13. retomar uma execução interrompida;
14. produzir todos os clipes finais na ordem correta.

------------------------------------------------------------------------

# 42. Ordem recomendada das alterações no código

A implementação deve ser feita em etapas para evitar quebrar o projeto
inteiro de uma vez.

## Fase A --- Modelo de dados

Implementar:

``` text
leitura do Excel
novos campos
producao_id
ordem
material_existente
estados
```

Sem alterar geração ainda.

## Fase B --- Planner

Implementar:

``` text
entrada estruturada
CLASSIFICADOR_UNIVERSAL.txt
plano_producao.json
plano_clipe.json
validação de schema
```

## Fase C --- Executor orientado por plano

Adaptar:

``` text
runner.py
fila.py
```

para executar:

``` text
metodo_imagem
metodo_video
referencias
prompts
```

do JSON.

## Fase D --- Referências da Júlia

Adicionar suporte explícito a:

``` text
rosto
rosto_1
corpo
mao
```

sem dependências desnecessárias.

## Fase E --- Gate de imagem

Migrar:

``` text
--gate-rosto
```

para:

``` text
--gate-imagem
```

e integrar com `aprovacao`.

## Fase F --- Reutilização

Implementar:

``` text
reutilizar
adaptar
referência
trechos
```

## Fase G --- Atualização automática do Excel

Cada etapa passa a refletir o estado real.

## Fase H --- Composição final

Montar os vídeos concluídos/reutilizados em ordem.

------------------------------------------------------------------------

# 43. Regra para as próximas alterações do projeto

Antes de modificar uma função existente, perguntar:

``` text
essa decisão pertence ao planner ou ao executor?
```

Se for uma decisão sobre:

``` text
qual fluxo
qual cena
qual ação
qual referência
qual fala
qual pipeline
```

ela pertence ao **Classificador Universal**.

Se for uma decisão sobre:

``` text
como chamar o comando
onde salvar
como validar arquivo
como atualizar status
como tratar retorno
```

ela pertence ao **Python/executor**.

Essa separação deve orientar toda a refatoração.

------------------------------------------------------------------------

# 44. Resultado esperado

Ao final, a operação diária deverá ser aproximadamente:

``` text
1. colocar os arquivos nas pastas corretas

2. preencher:
   controle_pipeline_flow.xlsx

3. executar classificação

4. revisar o planejamento quando houver pendência

5. gerar frames

6. aprovar/rejeitar frames

7. gerar vídeos aprovados

8. reutilizar automaticamente ativos já prontos

9. montar a produção na ordem definida

10. consultar o Excel para saber exatamente o estado de tudo
```

O objetivo não é tornar a planilha responsável por todas as decisões.

O objetivo é que ela seja a **interface operacional**, enquanto:

``` text
CLASSIFICADOR_UNIVERSAL.txt = cérebro/contrato
plano JSON = decisão resolvida
Python = executor
Flow = gerador
usuário = controle e aprovação
```

------------------------------------------------------------------------

# 45. Documento-base da refatoração

Este arquivo deve ser tratado como o **documento de arquitetura
funcional** do pipeline.

A próxima etapa de desenvolvimento deve comparar cada componente atual
do projeto com este documento e produzir uma lista objetiva de:

``` text
MANTER
ALTERAR
REMOVER
CRIAR
```

por arquivo/módulo.

Depois dessa análise, as mudanças podem ser implementadas
progressivamente sem perder as funcionalidades existentes que continuam
úteis.
