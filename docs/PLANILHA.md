# Planilha operacional

Este guia descreve o preenchimento atual de
`entradas/controle_pipeline_flow.xlsx`. A planilha registra fatos e decisões
humanas; classificação, caminhos, estados e resultados são preenchidos pelo
pipeline.

## Criar a planilha local

Depois de instalar o projeto, copie o modelo sanitizado:

```powershell
Copy-Item exemplos\controle_pipeline_flow.modelo.xlsx entradas\controle_pipeline_flow.xlsx
```

O arquivo operacional é local e ignorado pelo Git. Não versione planilhas com
dados reais.

## Estrutura do arquivo

Na aba `Controle`:

- a linha 1 contém os nomes das colunas;
- a linha 2 indica quem preenche cada coluna;
- a linha 3 contém orientações rápidas;
- os dados começam na linha 4;
- cada linha representa um clipe.

As abas `Guia`, `Referencias_Identidade` e `Exemplo_Producao` servem para
consulta. Somente a aba `Controle` é processada.

Feche o Excel antes de executar comandos que leem ou atualizam a planilha.

## Campos preenchidos pela pessoa

### Seleção e identificação

| Campo | Como preencher |
|---|---|
| `classifica` | `sim` inclui a linha na próxima preparação; `não` não inclui. Não deixe vazio. |
| `arquivo` | Caminho de uma imagem real disponível em `entradas/` ou caminho aceito pelo projeto. |
| `produto_id` | Identificador estável do produto. É obrigatório para papéis `principal` e `automatico`; pode ficar vazio em `abertura` e `cta`. |
| `producao_id` | Identificador comum a todos os clipes da mesma produção. Use apenas caracteres seguros para nome de pasta. |
| `ordem` | Inteiro positivo e único dentro da produção. |
| `papel_na_producao` | `automatico`, `abertura`, `principal` ou `cta`. Vazio equivale a `automatico`. |

### Referências e intenção

| Campo | Como preencher |
|---|---|
| `link_produto` | Link de consulta do produto, quando existir. |
| `usar_com` | Referências adicionais separadas por `;`. |
| `tipo_referencia` | Vazio, `base_edicao`, `produto`, `inspiracao`, `detalhe`, `ambiente` ou `outro`. |
| `material_existente` | Ativo pronto que deve ser reutilizado, adaptado ou usado como referência. |
| `uso_material` | Vazio, `automatico`, `reutilizar`, `adaptar` ou `referencia`. Só informe quando houver `material_existente`. |
| `instrucao` | Descreva de forma objetiva o que preservar e o que alterar. Não invente características ausentes. |

### Decisões humanas

| Campo | Como preencher |
|---|---|
| `aprovacao` | Depois de revisar a imagem, use `aprovada` ou `rejeitada`. A aprovação é exclusiva para liberar vídeo. |
| `gerar_carrossel` | `sim` solicita o card; vazio ou `não` não solicita. Essa permissão é independente da aprovação de vídeo. |
| `cta_destino` | Destino da chamada, somente na linha `cta`. Pode conter opções separadas por `;`. |
| `cta_palavra` | Palavra de chamada, somente na linha `cta`. Se ficar vazia, a IA pode completar. |

Valores são normalizados sem diferenciar maiúsculas, acentos ou espaços nas
opções padronizadas. Ainda assim, prefira os valores literais mostrados acima.

## Distinções importantes

- `produto_id` identifica o item; `producao_id` agrupa os clipes que formam uma
  produção.
- `papel_na_producao` define a função do clipe; `tipo_referencia` descreve o
  papel de uma imagem usada como insumo.
- `usar_com` reúne referências adicionais; `material_existente` declara um
  ativo que já existe e `uso_material` diz como tratá-lo.
- `classifica` seleciona a próxima rodada; `status` é resultado do sistema.
- `gerar_carrossel=sim` autoriza somente o card. Apenas
  `aprovacao=aprovada`, vinculada ao frame e à revisão corretos, libera uma
  nova geração de vídeo.

## Exemplo mínimo

| classifica | arquivo | produto_id | producao_id | ordem | papel_na_producao | instrucao |
|---|---|---|---|---:|---|---|
| `sim` | `produto_capa.png` |  | `COZINHA_VIDEO_01` | 1 | `abertura` | Preservar o produto e criar abertura 9:16. |
| `sim` | `produto_principal.png` | `PANELA_01` | `COZINHA_VIDEO_01` | 2 | `principal` | Preservar forma, cor e logotipo; alterar apenas o cenário. |
| `sim` | `produto_cta.png` |  | `COZINHA_VIDEO_01` | 3 | `cta` | Preservar o produto e criar encerramento com CTA. |

Os arquivos do exemplo precisam existir. Nomes e instruções são apenas
ilustrativos.

## Regra para criar uma nova imagem

O contrato `2.3-insumos` exige edição de uma imagem-base real:

1. informe a cena-base em `arquivo`;
2. quando quiser declarar a base explicitamente, use
   `tipo_referencia=base_edicao`;
3. coloque imagens complementares em `usar_com`;
4. escreva em `instrucao` o que deve ser preservado e o que pode mudar;
5. mantenha a saída vertical `9:16`.

A IA deve tratar a Referência 1 como base e não recriar a cena do zero. Se não
houver base válida, a resposta deve ficar pendente em vez de improvisar.

## Campos do sistema e da IA

Não edite manualmente:

- `status`, `classificacao`, `fluxo` e `plano_arquivo`;
- `imagem_status` e `imagem_arquivo`;
- `video_status` e `video_arquivo`;
- `erro`, `atualizado_em` e `fala_audio`;
- `texto_carrossel`, `subtexto_carrossel`, `carrossel_status` e
  `carrossel_arquivo`.

Esses campos são sincronizados pelo pipeline. Alterá-los à mão pode quebrar o
vínculo entre hash, revisão, aprovação e mídia.

## Preparar e conferir

Salve e feche a planilha, depois execute:

```powershell
python scripts\preparar_insumos.py preparar
```

O comando não chama o Flow nem consome créditos. Confira
`preparados/relatorio_preparacao.json`. Corrija todas as pendências antes de
enviar o pacote para classificação.

Se um campo humano mudar depois da criação do pacote, prepare uma nova revisão.
A importação recusa respostas ligadas a valores humanos diferentes.

Para a descrição histórica e exaustiva de cada coluna, consulte o
[guia detalhado em `entradas/`](../entradas/GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md).
