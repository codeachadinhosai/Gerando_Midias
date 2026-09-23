# Como continuar em um novo chat ou usar outra IA

Este procedimento não depende do histórico da conversa. O script prepara e valida arquivos; a IA analisa as imagens e escreve os planos e prompts. A geração de mídia acontece manualmente no Flow.

## 1. Colocar as imagens e preencher a planilha

Salve as imagens em entradas/ e preencha entradas/controle_pipeline_flow.xlsx, aba Controle, a partir da linha 4.

- Uma linha representa um clipe.
- classifica = sim inclui a linha na rodada; não exclui a linha da planilha quando marcado como não.
- arquivo deve corresponder ao nome real da imagem.
- produto_id identifica o produto/modelo, não a foto. Fotos do mesmo produto usam o mesmo ID.
- producao_id reúne os clipes de um mesmo vídeo; ordem determina a sequência.
- papel_na_producao informa abertura, principal, cta ou automático.
- tipo_referencia distingue produto, inspiração, detalhe, ambiente ou outro.
- usar_com associa referências adicionais ao mesmo clipe, separadas por ponto e vírgula.
- instrucao registra o que deseja mostrar e as restrições.

Se uma imagem de inspiração mostrar outro modelo, indique em usar_com a foto do produto anunciado e explique em instrucao que apenas a composição deve ser aproveitada.

Marque classifica = não nas linhas que não devem participar desta rodada. Salve e feche a planilha.

## 2. Preparar o pacote

Abra o terminal na pasta prompts, a pasta que contém scripts/ e entradas/. Execute:

```powershell
python scripts/preparar_insumos.py preparar
```

O comando informa o caminho de cada pacote:

```text
preparados/pacotes/<producao_id>/<revisao>/
```

Consulte preparados/relatorio_preparacao.json para identificar os pacotes e eventuais pendências. Corrija as pendências antes de continuar com a produção afetada.

## 3. Entregar o pacote à IA no novo chat

Envie os arquivos da revisão informada pelo comando:

- CLASSIFICADOR_UNIVERSAL.txt
- CONTRATO_INSUMOS.md
- manifesto.json
- identidade.txt, quando presente
- As imagens reais de anexos/, incluindo as referências da Júlia.

Use os arquivos que estão dentro do pacote, pois pertencem à mesma revisão. Não misture contratos ou anexos de revisões diferentes.

Informar caminhos não substitui anexar os arquivos. Se a IA tiver acesso à pasta, ela pode lê-los diretamente. Confirme que ela consegue visualizar as imagens; nomes de arquivos não bastam para analisar o produto. Para materiais em vídeo, a IA também precisa conseguir analisá-los.

Cole a seguinte instrução:

```text
Classifique esta produção seguindo CLASSIFICADOR_UNIVERSAL.txt e CONTRATO_INSUMOS.md. Leia o manifesto e examine os anexos reais.

Entregue resposta_ia.json com o plano da produção, os planos dos clipes e os prompts completos de imagem e vídeo quando aplicáveis, conforme o contrato.

Respeite os IDs, a ordem, os papéis das referências e as instruções humanas. Preserve o produto anunciado e use imagens de inspiração somente para os aspectos autorizados. Não confunda pessoas incidentais com a identidade da Júlia.

Não gere mídia nem registre aprovação. Não invente características do produto ou alegue consultar links sem tê-los consultado. Se faltar informação indispensável ou não conseguir visualizar uma referência necessária, registre a pendência.

Entregue JSON puro, sem cercas Markdown, pronto para salvar como resposta_ia.json.
```

## 4. Salvar e importar a resposta

Salve o JSON completo em preparados/respostas_ia/, com um nome que identifique a produção. O arquivo deve conter apenas o JSON, sem explicações fora dele.

Na pasta prompts, execute o comando abaixo, substituindo os caminhos pelos reais:

```powershell
python scripts/preparar_insumos.py importar --pacote "preparados/pacotes/PRODUCAO/REVISAO" --resposta "preparados/respostas_ia/resposta_ia.json" --atualizar-excel
```

O preparador valida a resposta, exporta os arquivos e atualiza a planilha com backup. Em caso de erro de validação, entregue a mensagem à IA para corrigir a resposta conforme o mesmo pacote.

Se os campos humanos da planilha mudaram desde a preparação, prepare um novo pacote e obtenha uma resposta correspondente à nova revisão.

O resultado fica em:

```text
preparados/flow/<producao_id>/<revisao_da_resposta>/<id_clipe>/
```

Cada clipe recebe, quando aplicável:

- plano_clipe.json: decisões do classificador.
- prompt_imagem.txt: texto para gerar a imagem.
- prompt_video.txt: texto para gerar o vídeo.
- referencias/: anexos selecionados e numerados.
- insumos_flow.json e insumos_video.json: orientações técnicas da exportação.
- COMO_USAR.txt: instruções do clipe.

Clipe pendente recebe PENDENCIA.txt e não deve seguir para geração.

## 5. Gerar e aprovar a imagem

Siga o COMO_USAR.txt do clipe. Cole prompt_imagem.txt no Flow e anexe somente as referências indicadas, na ordem informada. Configure o formato e o modelo solicitado conforme a disponibilidade real do Flow.

Salve o resultado na pasta do clipe como imagem_gerada, mantendo a extensão real do download, por exemplo imagem_gerada.jpeg. Trocar a extensão não converte o formato.

Na linha correspondente da planilha, registre:

- imagem_arquivo: caminho real da imagem.
- imagem_status: gerada.
- status: aguardando_aprovacao.

Confira fidelidade do produto, identidade quando aplicável, anatomia, composição e ausência de deformações. Registre aprovacao = aprovada ou rejeitada.

Se aprovada e o plano prevê vídeo, registre status = pronto_para_video. Se rejeitada, descreva o problema em erro e corrija a imagem antes de seguir. Uma nova versão da imagem precisa ser revisada novamente.

## 6. Gerar o vídeo

O prompt de vídeo já foi entregue pelo classificador. Sua existência não representa aprovação da imagem.

Quando a aprovação for exigida, só continue depois de aprovada. Para i2v, use a imagem aprovada como frame inicial e cole prompt_video.txt. Para outros métodos, siga o plano do clipe. Configure 9:16 e oito segundos para os vídeos novos previstos neste contrato.

Se a imagem não corresponder ao plano, corrija a imagem ou revise plano e prompts antes de gerar o vídeo.

Após gerar e conferir o resultado, salve video_gerado.mp4 na pasta do clipe, se esse for o formato real do download, e registre:

- video_arquivo: caminho real do vídeo.
- video_status: gerado.
- status: concluido.

Não marque como gerado algo que ainda não foi produzido. A montagem dos clipes em um vídeo final não é executada por este preparador.

## Preservação e retomada

Não sobrescreva revisões anteriores nem reimporte sobre clipes com mídia em andamento ou já gerada para tentar atualizar seus estados. Preserve imagens e vídeos aprovados. Para uma nova produção, use uma nova producao_id.

Os novos pacotes usam o contrato 2.2-insumos, que exige os dois prompts quando aplicáveis. Pacotes antigos 2.1 podem não conter prompt de vídeo.

Mais detalhes: [Guia dos insumos](../documentacao_v1/GUIA_INSUMOS_FLOW.md), [Contrato](../../CONTRATO_INSUMOS.md) e [Guia da planilha](GUIA_PREENCHIMENTO_CONTROLE_PIPELINE_FLOW.md).


Para processar diretamente neste projeto em um novo chat, veja [Como processar aqui](02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md).


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
