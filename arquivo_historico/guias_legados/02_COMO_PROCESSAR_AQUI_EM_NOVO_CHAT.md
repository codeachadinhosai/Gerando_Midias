# Como processar aqui em um novo chat

Abra esta pasta de projeto no Codex: `D:/04_APPs/Achadinhos_criativos/01_gflow-videos/prompts`.
O novo chat precisa ter acesso aos arquivos locais. O hist?rico desta conversa n?o ? necess?rio.

## Antes de come?ar

1. Coloque as imagens em `entradas/`.
2. Preencha `entradas/controle_pipeline_flow.xlsx`, aba `Controle`. Marque `classifica=sim` somente nas linhas a processar.
3. Em `instrucao`, diga o que preservar de cada refer?ncia: ambiente, composi??o, roupa, penteado, pose e express?o; indique qual imagem define o produto.
4. Salve e feche o Excel. A identidade usada pelo pipeline fica em `identidade/identidade.txt`.

## Mensagem pronta para colar no novo chat

```text
Processe as linhas com classifica=sim de entradas/controle_pipeline_flow.xlsx at? exportar os planos e os prompts completos de imagem e v?deo, atualizando a planilha.

Leia entradas/CLASSIFICADOR_UNIVERSAL.txt, CONTRATO_INSUMOS.md e identidade/identidade.txt. Execute python scripts/preparar_insumos.py preparar e use as revis?es retornadas em preparados/relatorio_preparacao.json; n?o escolha uma revis?o por uma aba aberta no editor.

Atue como o classificador: leia os manifestos e examine visualmente os anexos reais de cada pacote. Respeite as instru??es da planilha, a identidade de J?lia e os pap?is das refer?ncias. Penteado, roupa, pose e express?o seguem a cena. N?o invente dados de produto nem alegue consultar links que n?o leu.

Se existir resposta_ia.json correspondente ao hash do pacote, revise-a antes de importar. Confira produto, cen?rio, continuidade, roupa, penteado, ordem dos anexos, dura??o das falas e coer?ncia entre planos e prompts. Fa?a a classifica??o aqui; n?o me pe?a para levar o pacote a outra IA. Se n?o puder examinar uma refer?ncia necess?ria, informe a pend?ncia.

Salve cada resposta em preparados/respostas_ia/ com nome que inclua produ??o e revis?o, preservando respostas anteriores. Para a reda??o simples de personagem exigida pelo classificador atual, use incluir_bloco_identidade=false em cada objeto de clipe, ao lado de plano, prompt_imagem e prompt_video. A identidade continua sendo consultada e copiada como arquivo de apoio; mantenha as refer?ncias faciais/corporais necess?rias e as orienta??es visuais no prompt final.

Valide e importe com python scripts/preparar_insumos.py importar --pacote CAMINHO_REAL_DO_PACOTE --resposta CAMINHO_REAL_DA_RESPOSTA --atualizar-excel. Use os caminhos reais entre aspas.

Confira os arquivos exportados e se a planilha foi atualizada. N?o altere aprova??o humana nem force atualiza??o de linhas com m?dia em andamento ou j? gerada. Se houver bloqueio, preserve os ativos e explique exatamente o que falta.

Entregue links diretos para os novos prompts de imagem, as pastas de refer?ncias e o resultado da importa??o. Preserve as revis?es anteriores. N?o gere imagens ou v?deos, n?o publique nada e n?o registre aprova??o nesta etapa.
```

## O que voc? recebe

O processamento termina com planos, prompts e refer?ncias em `preparados/flow/PRODUCAO/REVISAO/CLIPE/`. O script prepara e valida; a an?lise das imagens e a reda??o dos planos e prompts s?o feitas pelo assistente.

A planilha aponta para os novos planos quando a importa??o com `--atualizar-excel` ? bem-sucedida. Confira `erro_excel` no resultado: exportar os arquivos n?o significa necessariamente que o Excel foi atualizado.

## Depois, no Flow

1. Abra o novo `prompt_imagem.txt` pelo link entregue.
2. Cole o texto e anexe os arquivos de `referencias/` na ordem de `insumos_flow.json` e do final do prompt. N?o misture revis?es.
3. Gere a imagem e salve o resultado na pasta desse clipe.
4. Confira a imagem e registre o caminho, `imagem_status=gerada` e sua decis?o em `aprovacao`.
5. Somente ap?s aprova??o, use o frame aprovado e o `prompt_video.txt` correspondente para gerar o v?deo.

## Nova rodada e hist?rico

Mudan?as nos insumos, identidade ou contratos geram outro pacote. Uma resposta diferente gera outra pasta de sa?da. Reimportar a mesma resposta reutiliza a pasta existente e preserva a m?dia. Arquivos antigos n?o s?o apagados. Os relat?rios de ?ltima execu??o e os campos operacionais da planilha podem ser atualizados.

N?o edite manifestos nem identidades dentro de pacotes antigos para for?ar uma revis?o. Prepare novamente a partir das fontes atuais.

O campo opcional `incluir_bloco_identidade` aceita somente booleano. Ausente ou `true` mant?m o comportamento antigo de acrescentar o bloco textual; `false` usa o prompt completo redigido pelo classificador, sem esse prefixo. O arquivo de identidade e as refer?ncias continuam preservados.


## Atualização: edição obrigatória em 2.3-insumos
Informe em arquivo a cena-base e em usar_com as referências para substituição. Em instrucao, liste alterações e preservações. Use material_existente com uso_material=adaptar para editar um ativo pronto, ou reutilizar para usá-lo sem mudanças.


CONTRATO LOCAL 2.3-insumos — EDIÇÃO OBRIGATÓRIA
Toda nova imagem deve editar uma base existente: origem_clipe.modo=adaptar, pipeline.metodo_imagem=i2i e incluir_bloco_identidade=false no objeto do clipe.
Registrar plano.edicao_imagem com base_ref_id (ID real), preservar (lista não vazia de elementos concretos) e alterar (lista não vazia de edições autorizadas).
A base deve ser a Referência 1; não usar referências de identidade como base de cena. Priorizar material_existente quando solicitado para adaptação; caso contrário, arquivo principal, se adequado. Outra base exige justificativa e coerência com a intenção humana.
Começar prompt_imagem literalmente com: Edite a Referência 1 como imagem-base. Não recrie a cena do zero.
Preservar tudo que não estiver listado para alteração. Não remover objetos, alimentos ou bebidas, nem substituir cenário, roupa ou penteado por escolhas genéricas. A adaptação para 9:16 deve constar em alterar, resolvendo recorte ou expansão das bordas sem recomposição arbitrária.
Sem base adequada, retornar pendente sem prompts. Sem alteração necessária, reutilizar o frame com gerar_imagem=false; reutilização de vídeos prontos também continua permitida.
identidade.txt permanece como contexto e arquivo de apoio; manter referências necessárias e orientações naturais de personagem no prompt final.

Execute preparar novamente para adotar a regra. Pacotes anteriores não são modificados.
