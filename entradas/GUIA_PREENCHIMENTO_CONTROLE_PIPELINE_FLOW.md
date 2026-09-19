# Guia de Preenchimento --- Controle Pipeline Flow

Este arquivo explica como preencher a planilha
**`controle_pipeline_flow.xlsx`** e qual Ã© a funÃ§Ã£o de cada coluna no
fluxo de classificaÃ§Ã£o, geraÃ§Ã£o de imagens, aprovaÃ§Ã£o e geraÃ§Ã£o de
vÃ­deos.

## OperaÃ§Ã£o completa: do Excel ao vÃ­deo

Execute no PowerShell dentro de `prompts`. Salve e feche o Excel antes dos comandos que o atualizam.

### Comando único recomendado

Depois de salvar e fechar o Excel, execute:

```powershell
python scripts/rodar_pipeline.py --projeto ID_DO_PROJETO_FLOW
```
Exemplo:
```powershell
python scripts/rodar_pipeline.py --projeto afdedea7-dcc2-484c-98ab-6a93016cdec3
```
O executor lê a planilha e retoma todas as produções ativas. Ele prepara pacotes novos, importa automaticamente uma `resposta_ia.json` cujo `pacote_sha256` corresponda ao pacote, gera todas as imagens pendentes, vincula aprovações já registradas no Excel e gera todos os vídeos liberados. Etapas concluídas não são reenviadas.

Quando uma imagem acaba de ser gerada ou registrada, o comando para aquele clipe em `aguardando revisao e aprovacao humana da imagem`. Abra `imagem_arquivo`, revise, marque `aprovacao=aprovada`, salve e feche o Excel. Execute o mesmo comando novamente; ele vincula a aprovação ao hash da imagem e gera os vídeos pendentes.

Se você informou uma imagem própria em `imagem_arquivo`, o executor a copia e registra automaticamente quando o clipe ainda não possui imagem no `execucao.json`. Não substitui vídeo já concluído.

Ao importar uma nova revisão, uma linha com `imagem_status=gerada` pode ser migrada quando `imagem_arquivo` aponta para uma imagem existente e ainda não há vídeo concluído. O novo plano é ativado, e na execução seguinte essa imagem é copiada para a pasta versionada da nova revisão por `registrar-imagem`; nenhuma nova imagem é solicitada ao Flow. Etapas marcadas como `gerando` e vídeos gerados ou reutilizados continuam bloqueando a troca de revisão.

Ao importar uma nova revisão, uma linha com `imagem_status=gerada` pode ser migrada quando `imagem_arquivo` aponta para uma imagem existente e ainda não há vídeo concluído. O novo plano é ativado, e na execução seguinte essa imagem é copiada para a pasta versionada da nova revisão por `registrar-imagem`; nenhuma nova imagem é solicitada ao Flow. Etapas marcadas como `gerando` e vídeos gerados ou reutilizados continuam bloqueando a troca de revisão.

A classificação visual continua sendo feita pela IA. Quando houver pacote novo sem uma resposta correspondente em `preparados/respostas_ia/`, o relatório indicará `pacote novo sem resposta_ia correspondente` e preservará essa produção sem gerar mídia. O resultado completo de cada execução fica em `preparados/ultima_execucao_automatica.json`.

Para somente retomar planos já importados, sem preparar nem procurar novas respostas:

```powershell
python scripts/rodar_pipeline.py --sem-preparar --projeto ID_DO_PROJETO_FLOW
```
### 1. Preparar

Coloque os arquivos em `entradas/` e preencha `entradas/controle_pipeline_flow.xlsx`. Cada linha com `classifica=sim` Ã© um clipe. Preencha os campos humanos descritos neste guia. No contrato 2.3, `arquivo` Ã© a imagem-base; em `instrucao`, diga o que preservar, alterar e nÃ£o copiar, inclusive a expansÃ£o para 9:16.

```powershell
cd D:\04_APPs\Achadinhos_criativos\01_gflow-videos\prompts
python scripts/preparar_insumos.py preparar
```

Confira `preparados/relatorio_preparacao.json`. O pacote fica em `preparados/pacotes/PRODUCAO/REVISAO/`. PeÃ§a ao assistente para examinar os anexos, executar o Classificador Universal e salvar o JSON em `preparados/respostas_ia/`. Em outra IA, envie o classificador, contrato, manifesto, identidade e todos os anexos da mesma revisÃ£o. O `pacote_sha256` deve coincidir.

## Mensagem pronta para colar no novo chat

```text
Processe as linhas com classifica=sim de entradas/controle_pipeline_flow.xlsx atÃ© exportar os planos e os prompts completos de imagem e vÃ­deo, atualizando a planilha.

Leia entradas/CLASSIFICADOR_UNIVERSAL.txt, CONTRATO_INSUMOS.md e identidade/identidade.txt. Execute python scripts/preparar_insumos.py preparar e use as revisÃµes retornadas em preparados/relatorio_preparacao.json; nÃ£o escolha uma revisÃ£o por uma aba aberta no editor.

Atue como o classificador: leia os manifestos e examine visualmente os anexos reais de cada pacote. Respeite as instruÃ§Ãµes da planilha, a identidade de JÃºlia e os papÃ©is das referÃªncias. Penteado, roupa, pose e expressÃ£o seguem a cena. NÃ£o invente dados de produto nem alegue consultar links que nÃ£o leu.

Se existir resposta_ia.json correspondente ao hash do pacote, revise-a antes de importar. Confira produto, cenÃ¡rio, continuidade, roupa, penteado, ordem dos anexos, duraÃ§Ã£o das falas e coerÃªncia entre planos e prompts. FaÃ§a a classificaÃ§Ã£o aqui; nÃ£o me peÃ§a para levar o pacote a outra IA. Se nÃ£o puder examinar uma referÃªncia necessÃ¡ria, informe a pendÃªncia.

Salve cada resposta em preparados/respostas_ia/ com nome que inclua produÃ§Ã£o e revisÃ£o, preservando respostas anteriores. Para a redaÃ§Ã£o simples de personagem exigida pelo classificador atual, use incluir_bloco_identidade=false em cada objeto de clipe, ao lado de plano, prompt_imagem e prompt_video. A identidade continua sendo consultada e copiada como arquivo de apoio; mantenha as referÃªncias faciais/corporais necessÃ¡rias e as orientaÃ§Ãµes visuais no prompt final.

Valide e importe com python scripts/preparar_insumos.py importar --pacote CAMINHO_REAL_DO_PACOTE --resposta CAMINHO_REAL_DA_RESPOSTA --atualizar-excel. Use os caminhos reais entre aspas.

Confira os arquivos exportados e se a planilha foi atualizada. NÃ£o altere aprovaÃ§Ã£o humana nem force atualizaÃ§Ã£o de linhas com mÃ­dia em andamento ou jÃ¡ gerada. Se houver bloqueio, preserve os ativos e explique exatamente o que falta.

Entregue links diretos para os novos prompts de imagem, as pastas de referÃªncias e o resultado da importaÃ§Ã£o. Preserve as revisÃµes anteriores. NÃ£o gere imagens ou vÃ­deos, nÃ£o publique nada e nÃ£o registre aprovaÃ§Ã£o nesta etapa.
```

### 2. Importar

Importar significa validar o `resposta_ia.json`, exportar os planos e
prompts para `preparados/flow/` e registrar os caminhos na planilha.
Essa etapa nÃ£o gera imagens nem vÃ­deos e nÃ£o consome crÃ©ditos.

VocÃª precisa informar dois caminhos diferentes:

1. **Pacote:** a pasta exata retornada em
   `preparados/relatorio_preparacao.json` pelo comando `preparar`.
2. **Resposta:** o arquivo JSON criado pelo classificador para aquele
   pacote, dentro de `preparados/respostas_ia/`.

NÃ£o substitua `PRODUCAO` e `REVISAO` por palavras aproximadas. Copie os
caminhos reais. `Resolve-Path` converte o caminho relativo em caminho
absoluto e tambÃ©m avisa imediatamente se ele nÃ£o existir.

```powershell
$Pacote = (Resolve-Path 'preparados/pacotes/PRODUCAO/REVISAO_DO_PACOTE').Path
$Resposta = (Resolve-Path 'preparados/respostas_ia/PRODUCAO_REVISAO_DO_PACOTE.json').Path
python scripts/preparar_insumos.py importar --pacote $Pacote --resposta $Resposta --atualizar-excel
```

Exemplo real da produÃ§Ã£o de waffle:

```powershell
$Pacote = (Resolve-Path 'preparados/pacotes/WAFFLE_VIDEO_01/5d0909cb05bc7fbd').Path
$Resposta = (Resolve-Path 'preparados/respostas_ia/WAFFLE_VIDEO_01_5d0909cb05bc7fbd.json').Path
python scripts/preparar_insumos.py importar --pacote $Pacote --resposta $Resposta --atualizar-excel
```

O resultado esperado tem esta forma:

```json
{
  "destino": "CAMINHO_COMPLETO/preparados/flow/PRODUCAO/REVISAO_DA_RESPOSTA",
  "clipes": 3,
  "excel_atualizado": true,
  "erro_excel": null
}
```

`excel_atualizado=true` confirma que os campos de sistema foram gravados
na planilha, inclusive `plano_arquivo` e `fala_audio`. `erro_excel=null`
confirma que nÃ£o houve bloqueio ao salvar.

O valor de `destino` Ã© a pasta exportada que serÃ¡ usada nos prÃ³ximos
comandos. A Ãºltima parte desse caminho Ã© calculada a partir da resposta
validada e pode ser diferente da revisÃ£o do pacote. Copie o `destino`
retornado, sem tentar adivinhar seu nome:

```powershell
$Producao = 'CAMINHO_EXATO_COPIADO_DO_CAMPO_destino'
python scripts/executar_flow.py listar --producao $Producao
```

No exemplo atual, a importaÃ§Ã£o retornou:

```powershell
$Producao = (Resolve-Path 'preparados/flow/WAFFLE_VIDEO_01/6e4ffaf8f4d87925').Path
python scripts/executar_flow.py listar --producao $Producao
```

`listar` apenas confere se planos, prompts e referÃªncias estÃ£o completos;
ele nÃ£o abre o Flow e nÃ£o consome crÃ©ditos. Se `excel_atualizado=false`
porque o Excel estava aberto, feche a planilha e repita o comando de
`importar`. Se jÃ¡ houver mÃ­dia, preserve-a e use a revisÃ£o apontada por
`plano_arquivo` na planilha.

### 3. Entrar no Flow

```powershell
..\gflow-videos\.venv\Scripts\python.exe ..\gflow-videos\scripts\gerar_video_flow.py --login
..\gflow-videos\.venv\Scripts\python.exe ..\gflow-videos\scripts\gerar_video_flow.py --checar
$ProjetoFlow = 'ID_DO_PROJETO'
```

Copie o ID da URL `https://flow.google.com/project/ID_DO_PROJETO`.
O diagnÃ³stico esperado contÃ©m `ok: true`.

### 4. Gerar uma imagem

Este comando pode consumir crÃ©ditos:

```powershell
python scripts/executar_flow.py imagem --producao $Producao --clipe ID_DO_CLIPE --projeto $ProjetoFlow
```

Usa `nano2`, 9:16 e as referÃªncias do plano. Salva imagem e log em `gerados/`, registra `execucao.json` e atualiza o Excel. Se a mÃ­dia foi gerada mas o Excel estava aberto, feche-o e repita: nÃ£o haverÃ¡ nova geraÃ§Ã£o.

#### Usar uma imagem entregue por vocÃª

Se vocÃª criou, editou ou escolheu outra imagem fora do executor, registre-a
antes da aprovaÃ§Ã£o. O comando copia o arquivo para uma pasta versionada do
clipe, calcula seu hash e atualiza `execucao.json` e o Excel:

```powershell
$Imagem = (Resolve-Path 'CAMINHO/DA/SUA/IMAGEM.jpeg').Path
python scripts/executar_flow.py registrar-imagem --producao $Producao --clipe ID_DO_CLIPE --arquivo $Imagem
```

Formatos aceitos: PNG, JPG, JPEG e WebP. A imagem original nÃ£o Ã© movida nem
alterada. O executor preserva as geraÃ§Ãµes anteriores e cria uma nova pasta
`gerados/manual_...` com a cÃ³pia registrada.

Registrar outra imagem revoga o vÃ­nculo tÃ©cnico da aprovaÃ§Ã£o anterior.
Revise a nova imagem, mantenha ou registre `aprovacao=aprovada` no Excel
e execute novamente o comando `aprovar`. Se o clipe jÃ¡ possui vÃ­deo
registrado, o comando bloqueia a troca; nesse caso, preserve o vÃ­deo e
prepare uma nova revisÃ£o.

### 5. Aprovar

Abra `imagem_arquivo` e confira produto, JÃºlia, mÃ£os, anatomia, cenÃ¡rio, roupa, penteado, objetos, enquadramento e ausÃªncia de invenÃ§Ãµes. No Excel, marque `aprovacao=aprovada` ou `rejeitada`, salve e feche. Se aprovou:

```powershell
python scripts/executar_flow.py aprovar --producao $Producao --clipe ID_DO_CLIPE
```

O comando nÃ£o decide por vocÃª; vincula a aprovaÃ§Ã£o ao caminho e SHA-256. Imagem alterada ou aprovaÃ§Ã£o revogada bloqueia o vÃ­deo. Se rejeitou, nÃ£o execute `aprovar` nem `video`.

### 6. Gerar o vÃ­deo

Este comando pode consumir crÃ©ditos:

```powershell
python scripts/executar_flow.py video --producao $Producao --clipe ID_DO_CLIPE --projeto $ProjetoFlow --modelo-video veo-fast
```

TambÃ©m aceita `veo-lite`, `veo-quality`, `omni-flash` e `veo-lite-lp`. O contrato atual usa 9:16 e oito segundos. Ao concluir, revise o MP4 e confira no Excel `video_status=gerado`, `video_arquivo` e `status=concluido`. Repita as etapas 4â€“6 para cada clipe.

```powershell
python scripts/executar_flow.py listar --producao $Producao
```

O executor gera vÃ­deos individuais; ainda nÃ£o os concatena. Monte-os em um editor seguindo `ordem`.

### Retomada e diagnÃ³stico

- Repetir etapa concluÃ­da sincroniza o Excel sem gerar novamente.
- Em falha ou timeout, confira `execucao.json`, `gflow.log` e o Flow; a chamada pode ter consumido crÃ©ditos.
- O executor nÃ£o reenvia tentativa incerta automaticamente.
- Remova `.execucao.lock` somente apÃ³s confirmar que nÃ£o hÃ¡ processo.
- NÃ£o altere planos, prompts ou referÃªncias e nÃ£o misture revisÃµes.
- Recortes e montagem final ainda nÃ£o sÃ£o automatizados.

```powershell
python scripts/preparar_insumos.py corrigir-planilha
python -m unittest discover -s tests -v
python scripts/executar_flow.py --help
```

------------------------------------------------------------------------

## 1. Regra geral

A planilha funciona como o **painel de controle do pipeline**.

Existem dois grupos de campos:

-   **VOCÃŠ**: campos preenchidos ou alterados manualmente por vocÃª.
-   **SISTEMA**: campos preenchidos e atualizados automaticamente pelo
    classificador/gerador.

A coluna **`aprovacao`** Ã© uma decisÃ£o humana, embora futuramente o
sistema possa oferecer uma interface ou comando para registrar essa
decisÃ£o na planilha.

O fluxo geral esperado Ã©:

``` text
Imagens / materiais de entrada
        â†“
Planilha
        â†“
Classificador Universal
        â†“
Plano do clipe / produÃ§Ã£o
        â†“
GeraÃ§Ã£o da imagem ou frame, quando necessÃ¡ria
        â†“
AprovaÃ§Ã£o humana
        â†“
GeraÃ§Ã£o do vÃ­deo
        â†“
AtualizaÃ§Ã£o da planilha
```

------------------------------------------------------------------------

## 2. Colunas preenchidas por vocÃª

### `classifica`

**Preenchido por:** VOCÃŠ\
**Uso:** controla se a linha deve entrar no processamento.

Valores:

-   `sim` --- a entrada pode ser considerada pelo Classificador
    Universal.
-   `nÃ£o` --- a entrada permanece catalogada, mas deve ser ignorada
    naquela rodada.

`nÃ£o` nÃ£o significa excluir nem concluir o item.

------------------------------------------------------------------------

### `arquivo`

**Preenchido por:** VOCÃŠ\
**Uso:** identifica o arquivo principal daquela linha.

Exemplos:

``` text
Produto_08.webp
InicioJulia_02.jpg
cesta_frente.png
```

O nome deve corresponder ao arquivo existente na pasta de entrada.

O arquivo pode ser uma foto de produto, uma cena de inspiraÃ§Ã£o, um frame
ou outro insumo visual.

------------------------------------------------------------------------

### `produto_id`

**Preenchido por:** VOCÃŠ\
**Uso:** identifica qual produto estÃ¡ relacionado Ã  entrada.

Exemplo:

``` text
CX001
```

VÃ¡rias imagens podem possuir o mesmo `produto_id`.

Exemplo:

``` text
Produto_08.webp â†’ CX001
Produto_09.webp â†’ CX001
Produto_10.webp â†’ CX001
```

O `produto_id` identifica o **produto**, e nÃ£o o vÃ­deo final.

O mesmo produto pode ser usado em vÃ¡rias produÃ§Ãµes diferentes.

------------------------------------------------------------------------

### `producao_id`

**Preenchido por:** VOCÃŠ\
**Uso:** agrupa os clipes que pertencem ao mesmo vÃ­deo/produÃ§Ã£o final.

Exemplo:

``` text
CX001_VIDEO_01
```

Se cinco linhas tiverem o mesmo `producao_id`, o sistema entende que
elas fazem parte da mesma produÃ§Ã£o.

Exemplo:

``` text
ordem 1 â†’ abertura
ordem 2 â†’ principal
ordem 3 â†’ principal
ordem 4 â†’ principal
ordem 5 â†’ CTA
```

Um mesmo `produto_id` pode possuir vÃ¡rias produÃ§Ãµes:

``` text
produto_id = CX001

CX001_VIDEO_01
CX001_VIDEO_02
CX001_VIDEO_03
```

------------------------------------------------------------------------

### `ordem`

**Preenchido por:** VOCÃŠ\
**Uso:** determina a posiÃ§Ã£o daquele clipe dentro da produÃ§Ã£o.

Exemplo:

``` text
1
2
3
4
5
```

O sistema deve considerar a sequÃªncia completa da produÃ§Ã£o ao planejar
os clipes, principalmente para manter continuidade narrativa.

------------------------------------------------------------------------

### `papel_na_producao`

**Preenchido por:** VOCÃŠ\
**Uso:** informa a funÃ§Ã£o desejada daquele clipe na produÃ§Ã£o.

Valores previstos:

-   `automÃ¡tico`
-   `abertura`
-   `principal`
-   `cta`

#### `automÃ¡tico`

O Classificador Universal determina a funÃ§Ã£o mais adequada.

#### `abertura`

Indica que o clipe participa da abertura da produÃ§Ã£o. Quando aplicÃ¡vel
Ã s regras do Classificador Universal, Ã© onde pode ocorrer a abertura
iniciada por **"Bora..."**.

#### `principal`

ConteÃºdo principal da produÃ§Ã£o: demonstraÃ§Ã£o, lifestyle, POV, detalhes,
ambientaÃ§Ã£o, apresentaÃ§Ã£o etc.

O Classificador Universal ainda decide qual fluxo especÃ­fico serÃ¡ usado.

#### `cta`

Indica um clipe de encerramento/CTA.

Pode ser gerado do zero, adaptado de uma imagem ou reaproveitado de um
material existente.

------------------------------------------------------------------------

### `link_produto`

**Preenchido por:** VOCÃŠ\
**Uso:** fonte opcional de **informaÃ§Ãµes factuais sobre o produto**.

O link nÃ£o determina:

-   fluxo;
-   estilo;
-   enquadramento;
-   storyboard;
-   aparÃªncia visual do produto;
-   ordem dos clipes.

Ele serve apenas para obter informaÃ§Ãµes como, quando disponÃ­veis:

-   nome;
-   descriÃ§Ã£o;
-   material;
-   capacidade;
-   dimensÃµes;
-   caracterÃ­sticas;
-   modo de uso;
-   informaÃ§Ãµes tÃ©cnicas.

A imagem continua sendo a principal evidÃªncia visual.

Se o campo estiver vazio, o sistema trabalha com os demais insumos
disponÃ­veis.

------------------------------------------------------------------------

### `usar_com`

**Preenchido por:** VOCÃŠ\
**Uso:** associa outras imagens ao **mesmo clipe**.

Esta coluna nÃ£o deve ser usada para montar a sequÃªncia da produÃ§Ã£o. Para
isso existem `producao_id` e `ordem`.

Exemplo:

``` text
arquivo = produto_frente.jpg
usar_com = produto_lado.jpg
```

Isso significa:

> Para planejar/gerar este clipe, considere tambÃ©m `produto_lado.jpg`.

Outro exemplo:

``` text
arquivo = cena_inspiracao.jpg
usar_com = produto_real.jpg
```

Pode significar que a cena fornece composiÃ§Ã£o/ambiente enquanto outra
imagem fornece a aparÃªncia correta do produto.

Para mÃºltiplos arquivos, separar por ponto e vÃ­rgula:

``` text
produto_lado.jpg; produto_detalhe.jpg
```

------------------------------------------------------------------------

### `tipo_referencia`

**Preenchido por:** VOCÃŠ\
**Uso:** informa o papel que a imagem exerce como insumo.

Valores previstos:

-   `base_edicao`
-   `produto`
-   `inspiraÃ§Ã£o`
-   `detalhe`
-   `ambiente`
-   `outro`

#### `base_edicao`

A imagem jÃ¡ existente Ã© a base que deve ser editada. Ela deve permanecer
como ReferÃªncia 1, e a IA deve preservar tudo que nÃ£o for indicado
explicitamente para alteraÃ§Ã£o. Use este valor quando vocÃª nÃ£o quer que a
cena seja recriada a partir da imagem, mas modificada diretamente.

#### `produto`

A imagem representa o produto que deve ser preservado/considerado.

#### `inspiraÃ§Ã£o`

A imagem serve como inspiraÃ§Ã£o de cena, composiÃ§Ã£o, pose, ambiente ou
linguagem visual. Uma pessoa incidental nessa imagem nÃ£o deve ser
tratada automaticamente como identidade da JÃºlia.

#### `detalhe`

A imagem enfatiza algum detalhe especÃ­fico do produto.

#### `ambiente`

A imagem Ã© principalmente uma referÃªncia de local/cenÃ¡rio.

#### `outro`

Use quando a referÃªncia nÃ£o se encaixar nas opÃ§Ãµes anteriores.

O campo pode ficar vazio quando vocÃª quiser deixar a anÃ¡lise do papel da
imagem para a IA.

------------------------------------------------------------------------

### `material_existente`

**Preenchido por:** VOCÃŠ\
**Uso:** indica uma imagem ou vÃ­deo jÃ¡ pronto que pode ser aproveitado
naquele clipe.

Exemplos:

``` text
cta_julia_03.mp4
abertura_cozinha.mp4
frame_banheiro.jpg
```

Esse campo permite reutilizar a biblioteca de ativos existentes em vez
de gerar tudo novamente.

------------------------------------------------------------------------

### `uso_material`

**Preenchido por:** VOCÃŠ\
**Uso:** informa como o `material_existente` deve ser tratado.

Valores:

-   `automÃ¡tico`
-   `reutilizar`
-   `adaptar`
-   `referÃªncia`

#### `automÃ¡tico`

O Classificador Universal analisa o material e decide o tratamento
adequado.

#### `reutilizar`

O ativo jÃ¡ estÃ¡ pronto e deve ser aproveitado diretamente, quando
compatÃ­vel com o plano.

Exemplo:

``` text
material_existente = cta_julia_03.mp4
uso_material = reutilizar
```

Nesse caso, o sistema pode concluir que nÃ£o precisa gerar nova imagem
nem novo vÃ­deo para aquele clipe.

#### `adaptar`

O ativo existente serve como base, mas precisa de alteraÃ§Ã£o.

Exemplos:

-   substituir a pessoa pela JÃºlia;
-   trocar o produto;
-   gerar um novo frame a partir da composiÃ§Ã£o;
-   adaptar uma cena para o produto atual.

#### `referÃªncia`

O material serve somente como evidÃªncia de:

-   aÃ§Ã£o;
-   movimento;
-   enquadramento;
-   composiÃ§Ã£o;
-   cenÃ¡rio;
-   continuidade.

Ele nÃ£o precisa aparecer diretamente no resultado final.

------------------------------------------------------------------------

### `instrucao`

**Preenchido por:** VOCÃŠ\
**Uso:** campo livre para intenÃ§Ã£o, restriÃ§Ã£o ou orientaÃ§Ã£o adicional.

Exemplos:

``` text
destacar a estampa
```

``` text
JÃºlia deve aparecer usando o produto
```

``` text
usar somente de 00:05 atÃ© 00:08 do vÃ­deo existente
```

``` text
preservar a composiÃ§Ã£o da imagem, mas substituir a pessoa pela JÃºlia
```

``` text
este clipe deve continuar a aÃ§Ã£o do anterior
```

Evite repetir nesta coluna informaÃ§Ãµes que jÃ¡ possuem coluna prÃ³pria.

------------------------------------------------------------------------

## 3. Colunas atualizadas pelo sistema

### `status`

**Preenchido por:** SISTEMA\
**Uso:** mostra o estado geral atual daquela linha.

Estados previstos:

-   `novo`
-   `classificando`
-   `classificado`
-   `aguardando_imagem`
-   `aguardando_aprovacao`
-   `pronto_para_video`
-   `gerando_video`
-   `concluido`
-   `pendente`
-   `erro`

Exemplo de evoluÃ§Ã£o:

``` text
novo
â†“
classificando
â†“
classificado
â†“
aguardando_imagem
â†“
aguardando_aprovacao
â†“
pronto_para_video
â†“
gerando_video
â†“
concluido
```

Nem todos os clipes precisam passar por todos os estados. Um CTA
reutilizado, por exemplo, pode pular geraÃ§Ã£o de imagem e vÃ­deo.

------------------------------------------------------------------------

### `classificacao`

**Preenchido por:** SISTEMA\
**Uso:** registra a classificaÃ§Ã£o criativa/funcional determinada pelo
Classificador Universal.

Exemplos:

``` text
POVPegar
Lifestyle
DetalhesProduto
ApresentacaoJulia
Ambientacao
AberturaJulia
CTA
```

VocÃª nÃ£o precisa escolher isso antecipadamente.

------------------------------------------------------------------------

### `fluxo`

**Preenchido por:** SISTEMA\
**Uso:** registra o fluxo tÃ©cnico/catalogado escolhido pelo
Classificador Universal.

Exemplos conceituais:

``` text
01_abertura_julia
03_pov_pegar
05_detalhes_produto
07_lifestyle
09_cta_final
```

`classificacao` descreve o tipo de clipe; `fluxo` identifica o fluxo
registrado que serÃ¡ executado.

------------------------------------------------------------------------

### `plano_arquivo`

**Preenchido por:** SISTEMA\
**Uso:** caminho para o arquivo tÃ©cnico produzido pelo classificador.

Exemplo:

``` text
output/planos/CX001_VIDEO_01_02.json
```

Esse JSON pode armazenar informaÃ§Ãµes extensas que nÃ£o devem ocupar
cÃ©lulas do Excel:

-   referÃªncias;
-   contexto;
-   decisÃ£o do classificador;
-   timeline;
-   fala;
-   prompt de imagem;
-   prompt de vÃ­deo;
-   mÃ©todo de geraÃ§Ã£o;
-   uso de material existente;
-   continuidade;
-   requisitos de identidade da JÃºlia.

O Excel permanece como painel operacional e o JSON guarda o plano
tÃ©cnico completo.

------------------------------------------------------------------------

### `imagem_status`

**Preenchido por:** SISTEMA\
**Uso:** informa o estado da imagem/frame que antecede a geraÃ§Ã£o do
vÃ­deo.

Valores:

-   `pendente`
-   `gerando`
-   `gerada`
-   `erro`
-   `nÃ£o necessÃ¡ria`

Exemplo:

``` text
imagem_status = gerada
status = aguardando_aprovacao
```

------------------------------------------------------------------------

### `imagem_arquivo`

**Preenchido por:** SISTEMA\
**Uso:** registra onde estÃ¡ a imagem/frame gerado.

Exemplo:

``` text
output/flow/imagens/CX001_VIDEO_01_02.png
```

Ã‰ essa imagem que deve ser inspecionada antes da aprovaÃ§Ã£o.

------------------------------------------------------------------------

### `aprovacao`

**Preenchido por:** VOCÃŠ\
**Uso:** gate humano antes da geraÃ§Ã£o do vÃ­deo.

Valores:

-   `pendente`
-   `aprovada`
-   `rejeitada`
-   `nÃ£o necessÃ¡ria`

#### `pendente`

Ainda nÃ£o houve decisÃ£o.

#### `aprovada`

A imagem pode ser usada para gerar o vÃ­deo.

#### `rejeitada`

A imagem nÃ£o deve seguir para o vÃ­deo e precisa ser corrigida/regenerada
conforme o fluxo definido.

#### `nÃ£o necessÃ¡ria`

Usado quando nÃ£o existe frame a aprovar, por exemplo em determinados
reaproveitamentos de material pronto.

O gerador de vÃ­deo nÃ£o deve avanÃ§ar sobre um clipe que exige aprovaÃ§Ã£o
enquanto `aprovacao` nÃ£o estiver como `aprovada`.

------------------------------------------------------------------------

### `video_status`

**Preenchido por:** SISTEMA\
**Uso:** acompanha a etapa de vÃ­deo.

Valores previstos:

-   `aguardando`
-   `gerando`
-   `gerado`
-   `reutilizado`
-   `erro`
-   `nÃ£o necessÃ¡rio`

`reutilizado` Ã© especialmente Ãºtil quando `material_existente` jÃ¡ Ã© um
vÃ­deo final que serÃ¡ usado na produÃ§Ã£o.

------------------------------------------------------------------------

### `video_arquivo`

**Preenchido por:** SISTEMA\
**Uso:** registra o caminho do vÃ­deo daquele clipe.

Pode apontar para um vÃ­deo recÃ©m-gerado ou para um ativo existente
reutilizado.

Exemplos:

``` text
output/flow/videos/CX001_VIDEO_01_02.mp4
```

ou, quando reutilizado:

``` text
ativos/julia/ctas/cta_julia_03.mp4
```

------------------------------------------------------------------------

### `erro`

**Preenchido por:** SISTEMA\
**Uso:** registra falhas ou pendÃªncias que impedem o avanÃ§o.

Exemplos:

``` text
arquivo informado em usar_com nÃ£o encontrado
```

``` text
nÃ£o foi possÃ­vel obter informaÃ§Ãµes do link do produto
```

``` text
referÃªncia necessÃ¡ria para identidade da JÃºlia nÃ£o encontrada
```

``` text
falha na geraÃ§Ã£o do frame
```

O objetivo Ã© permitir entender pelo prÃ³prio Excel por que uma linha nÃ£o
avanÃ§ou.

------------------------------------------------------------------------

### `atualizado_em`

**Preenchido por:** SISTEMA\
**Uso:** registra data e hora da Ãºltima atualizaÃ§Ã£o daquela linha.

Exemplo:

``` text
2026-09-17 14:32:10
```

Ajuda na auditoria e na retomada do pipeline.

------------------------------------------------------------------------

### `fala_audio`

**Preenchido por:** SISTEMA\
**Uso:** registra a fala exata que deve ser pronunciada no vÃ­deo daquele clipe.

O valor vem de `plano.audio.fala_exata` apÃ³s a resposta ser validada e
importada. A cÃ©lula fica vazia quando o clipe nÃ£o possui Ã¡udio ativo.

Esse campo Ã© informativo e facilita a revisÃ£o das falas diretamente no
Excel. AlterÃ¡-lo manualmente nÃ£o substitui a revisÃ£o do plano e do prompt
de vÃ­deo.

------------------------------------------------------------------------

## 4. ReferÃªncias globais da JÃºlia

As referÃªncias da JÃºlia nÃ£o precisam ser repetidas linha a linha na
planilha.

Elas devem existir como recursos globais do sistema:

``` text
referencias_globais/
â””â”€â”€ julia/
    â”œâ”€â”€ rosto.jpg
    â”œâ”€â”€ rosto_1.jpg
    â”œâ”€â”€ Corpo.png
    â””â”€â”€ mao.jpg
```

FunÃ§Ãµes:

-   `rosto.jpg` --- identidade facial principal;
-   `rosto_1.jpg` --- referÃªncia facial complementar da mesma JÃºlia;
-   `Corpo.png` --- proporÃ§Ãµes corporais e silhueta;
-   `mao.jpg` --- aparÃªncia da mÃ£o, tom de pele e unhas, especialmente
    importante para POV.

O Classificador Universal deve determinar quais dessas referÃªncias sÃ£o
necessÃ¡rias para cada clipe.

Um POV apenas com mÃ£o pode precisar de `mao.jpg` sem precisar das
referÃªncias faciais.

Uma cena lifestyle com JÃºlia visÃ­vel pode exigir rosto, corpo e mÃ£o.

------------------------------------------------------------------------

## 5. Exemplo de uma produÃ§Ã£o completa

Suponha uma produÃ§Ã£o de uma caixa organizadora composta por cinco clipes
de 8 segundos.

  arquivo                 produto_id   producao_id        ordem papel_na_producao
  ----------------------- ------------ ---------------- ------- -------------------
  InicioJulia_02.jpg      CX001        CX001_VIDEO_01         1 abertura
  Produto_08.webp         CX001        CX001_VIDEO_01         2 principal
  Produto_09.webp         CX001        CX001_VIDEO_01         3 principal
  Produto_10.webp         CX001        CX001_VIDEO_01         4 principal
  InicioJuliaCTA_05.jpg   CX001        CX001_VIDEO_01         5 cta

O Classificador Universal deve primeiro compreender a **produÃ§Ã£o como um
conjunto** e depois planejar cada clipe.

Conceitualmente:

``` text
CLIP 1
Abertura com JÃºlia
"Bora..."
        â†“
CLIP 2
Primeiro caso de uso
        â†“
CLIP 3
Segundo caso de uso
        â†“
CLIP 4
Terceiro caso de uso
        â†“
CLIP 5
CTA
```

Os clipes principais podem ser planejados como continuidade narrativa em
vez de vÃ­deos independentes.

------------------------------------------------------------------------

## 6. Exemplo com CTA existente

Se jÃ¡ existir um CTA adequado:

``` text
arquivo              = InicioJuliaCTA_05.jpg
produto_id           = CX001
producao_id          = CX001_VIDEO_01
ordem                = 5
papel_na_producao    = cta
material_existente   = cta_julia_03.mp4
uso_material         = reutilizar
instrucao            =
```

O Classificador Universal deve avaliar o ativo dentro do plano da
produÃ§Ã£o.

Se estiver adequado:

``` text
gerar imagem = nÃ£o
gerar vÃ­deo = nÃ£o
usar ativo existente = sim
video_status = reutilizado
```

Se quiser apenas parte do CTA:

``` text
material_existente = cta_julia_03.mp4
uso_material = reutilizar
instrucao = usar somente de 00:05 atÃ© 00:08
```

O plano tÃ©cnico deve registrar o trecho escolhido.

------------------------------------------------------------------------

## 7. DiferenÃ§a entre os campos que mais podem causar dÃºvida

### `produto_id` x `producao_id`

`produto_id` responde:

> Qual Ã© o produto?

`producao_id` responde:

> A qual vÃ­deo/produÃ§Ã£o esta linha pertence?

------------------------------------------------------------------------

### `producao_id` x `usar_com`

`producao_id` reÃºne **clipes diferentes da mesma produÃ§Ã£o**.

`usar_com` reÃºne **referÃªncias adicionais para o mesmo clipe**.

------------------------------------------------------------------------

### `tipo_referencia` x `papel_na_producao`

`tipo_referencia` descreve **o que a imagem representa como insumo**.

Exemplo:

``` text
base_edicao
inspiraÃ§Ã£o
produto
detalhe
ambiente
```

`papel_na_producao` descreve **a funÃ§Ã£o daquele clipe no vÃ­deo final**.

Exemplo:

``` text
abertura
principal
cta
```

------------------------------------------------------------------------

### `material_existente` x `usar_com`

`usar_com` aponta para outras referÃªncias que ajudam a construir o
clipe.

`material_existente` indica um ativo jÃ¡ produzido que pode ser
reutilizado, adaptado ou usado como referÃªncia.

------------------------------------------------------------------------

### `classifica` x `status`

`classifica` Ã© uma decisÃ£o sua:

> Quero que esta entrada participe do processamento?

`status` Ã© registrado pelo sistema:

> Em qual etapa esta entrada estÃ¡ agora?

------------------------------------------------------------------------

## 8. PrincÃ­pio de funcionamento

A planilha deve registrar **fatos, relaÃ§Ãµes, intenÃ§Ã£o humana e estado
operacional**.

Ela nÃ£o deve exigir que vocÃª decida antecipadamente detalhes que
pertencem ao Classificador Universal, como:

-   POVPegar ou POVApresentar;
-   Lifestyle ou DetalhesProduto;
-   i2i, i2v ou r2v;
-   necessidade de storyboard;
-   referÃªncias da JÃºlia necessÃ¡rias;
-   prompt final de imagem;
-   prompt final de vÃ­deo.

Essas decisÃµes devem ser resolvidas pelo Classificador Universal e
registradas no `plano_arquivo`.

Em resumo:

``` text
VOCÃŠ
â†’ informa o que existe, o que pertence a quÃª e o que deseja.

CLASSIFICADOR UNIVERSAL
â†’ decide como transformar esses insumos em clipes.

SISTEMA / FLOW
â†’ executa o plano.

VOCÃŠ
â†’ aprova a imagem quando necessÃ¡rio.

SISTEMA
â†’ gera ou reutiliza o vÃ­deo e atualiza a planilha.
```


## AtualizaÃ§Ã£o: ediÃ§Ã£o obrigatÃ³ria em 2.3-insumos
Informe em arquivo a cena-base e em usar_com as referÃªncias para substituiÃ§Ã£o. Em instrucao, liste alteraÃ§Ãµes e preservaÃ§Ãµes. Use material_existente com uso_material=adaptar para editar um ativo pronto, ou reutilizar para usÃ¡-lo sem mudanÃ§as.


CONTRATO LOCAL 2.3-insumos â€” EDIÃ‡ÃƒO OBRIGATÃ“RIA
Toda nova imagem deve editar uma base existente: origem_clipe.modo=adaptar, pipeline.metodo_imagem=i2i e incluir_bloco_identidade=false no objeto do clipe.
Registrar plano.edicao_imagem com base_ref_id (ID real), preservar (lista nÃ£o vazia de elementos concretos) e alterar (lista nÃ£o vazia de ediÃ§Ãµes autorizadas).
A base deve ser a ReferÃªncia 1; nÃ£o usar referÃªncias de identidade como base de cena. Priorizar material_existente quando solicitado para adaptaÃ§Ã£o; caso contrÃ¡rio, arquivo principal, se adequado. Outra base exige justificativa e coerÃªncia com a intenÃ§Ã£o humana.
ComeÃ§ar prompt_imagem literalmente com: Edite a ReferÃªncia 1 como imagem-base. NÃ£o recrie a cena do zero.
Preservar tudo que nÃ£o estiver listado para alteraÃ§Ã£o. NÃ£o remover objetos, alimentos ou bebidas, nem substituir cenÃ¡rio, roupa ou penteado por escolhas genÃ©ricas. A adaptaÃ§Ã£o para 9:16 deve constar em alterar, resolvendo recorte ou expansÃ£o das bordas sem recomposiÃ§Ã£o arbitrÃ¡ria.
Sem base adequada, retornar pendente sem prompts. Sem alteraÃ§Ã£o necessÃ¡ria, reutilizar o frame com gerar_imagem=false; reutilizaÃ§Ã£o de vÃ­deos prontos tambÃ©m continua permitida.
identidade.txt permanece como contexto e arquivo de apoio; manter referÃªncias necessÃ¡rias e orientaÃ§Ãµes naturais de personagem no prompt final.

Execute preparar novamente para adotar a regra. Pacotes anteriores nÃ£o sÃ£o modificados.

## Carrossel 9:16

Nao escreva "nao gerar video" em `instrucao`. A separacao e automatica: `gerar_carrossel=sim` autoriza somente o card; `aprovacao=aprovada` e a autorizacao exclusiva para consumir creditos com uma nova geracao de video.

REGRA ATUAL E PREVALENTE: `gerar_carrossel=sim` ja autoriza a imagem para o carrossel. Nao e necessario preencher `aprovacao` para criar o card. `aprovacao=aprovada` continua sendo exigida somente antes da geracao de video. Esta regra substitui qualquer orientacao anterior em conflito.

`papel_na_producao` tambem organiza os cards: `abertura` vira a capa, `principal` identifica os cards de conteudo e `cta` identifica o ultimo card. Se quiser controlar a chamada, preencha `cta_destino` e `cta_palavra` somente na linha com papel `cta`. Se deixar um ou ambos vazios, a IA escolhera os valores ausentes.

Em `cta_destino`, voce pode combinar opcoes separando-as por ponto e virgula. Exemplo: `link da bio; comentarios`. A lista suspensa oferece combinacoes prontas e tambem aceita texto personalizado.

As sete colunas finais controlam a capa renderizada localmente sobre a imagem aprovada:

- `gerar_carrossel`: preencha `sim` para solicitar o card; vazio ou `não` não gera.
- `cta_destino`: destino autorizado, por exemplo `grupo`, `direct` ou `link da bio`; vazio permite que a IA escolha uma acao segura.
- `cta_palavra`: palavra-chave da chamada; vazio permite que a IA escolha uma palavra coerente.
- `texto_carrossel` e `subtexto_carrossel`: preenchidos pela IA durante a classificação.
- `carrossel_status` e `carrossel_arquivo`: preenchidos pelo sistema.

Limites fixos: título com até 52 caracteres e 3 linhas; faixa de destaque com até 28 caracteres e 2 linhas; CTA com até 54 caracteres e 2 linhas. O arquivo final permanece em 1080 × 1920, com 96 px de margem lateral, 160 px no topo e 220 px na base. Ele é salvo em `entregas_flow/carrossel/<producao_id>/` somente depois que a aprovação estiver vinculada à imagem atual.

Para renderizar manualmente um plano já importado:

```powershell
python scripts/gerar_carrossel.py --producao "CAMINHO_DA_PRODUCAO" --clipe ID_DO_CLIPE
```

O comando automático `python scripts/rodar_pipeline.py` também gera o card assim que a imagem está aprovada.

As colunas `gerar_carrossel` e `cta_destino` possuem listas suspensas com respostas padronizadas. `cta_palavra` oferece sugestões comuns, mas também aceita uma palavra personalizada digitada diretamente na célula. No card `cta`, campos preenchidos são preservados literalmente; campos vazios são completados pela IA durante a classificação.
