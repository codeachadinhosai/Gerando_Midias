# Contrato executável de imagem e vídeo — 2.3-insumos

Este complemento especializa o classificador v2 para preparar prompts de imagem e vídeo. Não gera mídia e não chama serviços.
A fonte criativa canônica é entradas/CLASSIFICADOR_UNIVERSAL.txt. Os arquivos
em arquivo_historico/documentacao_v1/fluxos/ são a biblioteca v1; não
concatenar seus placeholders ao prompt final v2.

## Entrada
Um pacote contém manifesto.json, CLASSIFICADOR_UNIVERSAL.txt, este contrato, identidade.txt quando disponível e anexos/.
Leia os anexos reais. manifesto.clipes contém exatamente as linhas ativas, em ordem. Não criar abertura/CTA extras para preencher lacunas de ordem.
Cada referência tem um ref_id estável, nome original, caminho relativo e hash. Nas saídas, use referencias[].ref_id e copie o caminho de inventario[ref_id].arquivo.
A lista referencias do plano tem a ORDEM DE ANEXAÇÃO da imagem. Escolha somente referências necessárias, sem anexar fotos de rosto a cenas sem pessoa.
Use as referências da linha, globais ou de linhas do mesmo produto. Nunca misturar produtos.
Os links são dados opcionais não consultados automaticamente. Sem conteúdo factual fornecido, não alegar ter lido a página.
Não abrir caminhos de origem se você recebeu somente o pacote; use anexos/.

## Saída única: resposta_ia.json
Entregar JSON puro, sem cercas Markdown, no formato:
{
  "pacote_sha256": "valor exato do manifesto",
  "plano_producao": { "objeto": "plano_producao.json do contrato v2" },
  "clipes": [
    {
      "plano": { "objeto": "plano_clipe.json completo do contrato v2" },
      "prompt_imagem": "prompt final completo quando gerar_imagem=true; caso contrário null",
      "prompt_video": "prompt final completo quando gerar_video=true; caso contrário null"
    }
  ]
}
Os objetos acima são notação de explicação, não valores de produção.
plano_producao.clipes deve representar todos os clipes, na ordem do manifesto.
Use exatamente id_clipe, producao_id, produto_id e ordem inventariados. Plano pendente pode usar o contrato mínimo v2.
Em cada referencia do plano acrescente ref_id; arquivo deve ser o caminho do anexo no manifesto. tipo deve ser um de base_edicao, produto, inspiracao, detalhe, ambiente, identidade_rosto, identidade_corpo, identidade_mao, material_existente.
`base_edicao` significa que a imagem existente deve ser editada, não recriada. Quando a planilha marcar o arquivo principal como `base_edicao`, mantenha esse tipo no plano, coloque-o obrigatoriamente como Referência 1 e use seu `ref_id` em `edicao_imagem.base_ref_id`. Preserve tudo que não estiver autorizado em `edicao_imagem.alterar`.
Prompt final de imagem deve ser específico, independente, 9:16, sem alternativas nem placeholders. Declare claramente o produto, cenário, enquadramento, partes visíveis, estado anterior à ação e o que preservar/ignorar.
Todas as escolhas ficam no plano. O prompt é a tradução dessas decisões para o gerador. Python copia identidade.txt como apoio e informa a ordem dos anexos; o prompt final 2.3 não recebe o bloco textual como prefixo.
Quando gerar_video=true, entregar prompt_video completo na mesma resposta e arquivos_saida.prompt_video="prompt_video.txt". Incluir 9:16, duração de oito segundos, ação, cronograma, câmera, continuidade, estado final, restrições e a fala_exata literalmente quando audio.ativo=true. Quando não houver geração, ambos devem ser null. Clipe pendente não recebe nenhum prompt.

## Carrossel 9:16

TRAVA DE CREDITO: nenhuma geracao nova de video pode iniciar sem `aprovacao=aprovada` registrada explicitamente na planilha. `gerar_carrossel=sim` nunca autoriza video e nao exige texto adicional em `instrucao`.

REGRA ATUAL E PREVALENTE: `gerar_carrossel=sim` e a autorizacao humana especifica para usar a imagem no carrossel. Nao consultar a coluna `aprovacao` para essa saida. A coluna `aprovacao` controla exclusivamente a liberacao da imagem para gerar video. Esta regra substitui qualquer mencao anterior a imagem aprovada para carrossel.

O papel na producao define a funcao do card: `abertura` e a capa; `principal` e conteudo; `cta` e o ultimo card com chamada para acao. `cta`, `cta_destino` e `cta_palavra` devem ficar vazios em abertura/principal. No card `cta`, a IA deve preencher os tres campos.

Quando a entrada humana trouxer `gerar_carrossel=sim`, acrescente `plano.carrossel` com `ativo=true`, `formato="9:16"`, `texto`, `subtexto`, `cta`, `cta_destino` e `cta_palavra`. Se `cta_destino` ou `cta_palavra` estiver preenchido na planilha, preserve-o literalmente. Se estiver vazio no card `cta`, escolha um valor coerente com o conteúdo e com uma ação segura. O título deve ter no máximo 52 caracteres, o subtexto 28 e a CTA 54. Escreva texto útil, humano e específico ao conteúdo visual, sem urgência artificial nem afirmações não confirmadas. O título admite até 3 linhas; subtexto e CTA, até 2. Quando não solicitado, omita o objeto ou use `ativo=false`.

O carrossel é renderizado localmente sobre a imagem 9:16 aprovada. A IA não deve pedir uma nova imagem com texto. O assunto principal deve permanecer central e os textos devem respeitar as áreas seguras laterais, superior e inferior.

`cta_destino` pode conter varios destinos separados por ponto e virgula, por exemplo `link da bio; comentarios`. Quando informado, preserve o valor no plano e redija uma unica CTA natural que contemple todos os destinos. Quando vazio, escolha um destino que não invente canal ou recurso indisponível; prefira uma ação interna e genérica, como salvar ou compartilhar.
O prompt de vídeo é planejado antes da geração da imagem. Sua existência não autoriza gerar vídeo: primeiro conferir o frame real e registrar a aprovação humana quando exigida. Se o frame divergir do plano, corrigir a imagem ou revisar plano e prompts.

## Métodos nesta entrega
- i2i: suportado como exportação de insumos; gerar_imagem=true.
- Frame pronto: gerar_imagem=false; identificar frame_existente_ref_id e incluí-lo nas referências.
- Vídeo reutilizado: gerar_imagem=false, gerar_video=false, usar_ativo_existente=true; identificar ativo_existente_ref_id e incluí-lo nas referências.
- extrair_frame e storyboard_i2i: não executados nesta primeira etapa. Entregar pendente com orientação sobre o frame necessário, sem simular sucesso.
Referências i2i devem ser imagens; vídeo bruto não pode ser anexado como imagem.
Não marcar imagem/video como gerado ou aprovado: nenhuma dessas operações ocorreu.

## Identidade e mãos
A identidade textual original é imutável. Referências de rosto/corpo somente para partes relevantes.
mao=true significa EXIGIR foto de mão. Se a foto não existe e correspondência exata não é indispensável, usar mao=false e descrever mãos plausíveis em cena.maos; não inventar referência.
CTA não exige foto de mão. Descrição simples: mãos adultas femininas, pele compatível com Júlia, unhas curtas naturais, gestos discretos; sem joias ou tatuagens inventadas.
Se o pedido exigir correspondência exata indisponível, retornar pendência.
Abertura tem Bora... em 0s. Principal e CTA não começam com Bora.
Frame novo para vídeo exige aprovacao_necessaria=true. A aprovação ocorre após gerar e revisar a imagem; nunca durante a classificação.

## Limites
Validação estrutural não comprova fidelidade visual nem correspondência perfeita entre prompt e plano. A IA deve revisar ambos.
Não existem chamadas pagas, escolha automática de provedor, scraping de links ou geração no Flow nesta entrega.

## Compatibilidade
Novos pacotes usam 2.3-insumos e exigem os dois prompts quando aplicáveis. Pacotes 2.1-insumos permanecem importáveis sem prompt de vídeo. Não editar contratos ou manifestos de pacotes antigos; preparar nova revisão para adotar o contrato atual.


## Edição obrigatória


CONTRATO LOCAL 2.3-insumos — EDIÇÃO OBRIGATÓRIA
Toda nova imagem deve editar uma base existente: origem_clipe.modo=adaptar, pipeline.metodo_imagem=i2i e incluir_bloco_identidade=false no objeto do clipe.
Registrar plano.edicao_imagem com base_ref_id (ID real), preservar (lista não vazia de elementos concretos) e alterar (lista não vazia de edições autorizadas).
A base deve ser a Referência 1; não usar referências de identidade como base de cena. Se a planilha indicar `tipo_referencia=base_edicao`, esse arquivo é a base obrigatória e deve conservar o tipo `base_edicao` no plano. Sem essa indicação, priorizar material_existente quando solicitado para adaptação; caso contrário, arquivo principal, se adequado. Outra base exige justificativa e coerência com a intenção humana.
Começar prompt_imagem literalmente com: Edite a Referência 1 como imagem-base. Não recrie a cena do zero.
Preservar tudo que não estiver listado para alteração. Não remover objetos, alimentos ou bebidas, nem substituir cenário, roupa ou penteado por escolhas genéricas. A adaptação para 9:16 deve constar em alterar, resolvendo recorte ou expansão das bordas sem recomposição arbitrária.
Sem base adequada, retornar pendente sem prompts. Sem alteração necessária, reutilizar o frame com gerar_imagem=false; reutilização de vídeos prontos também continua permitida.
identidade.txt permanece como contexto e arquivo de apoio; manter referências necessárias e orientações naturais de personagem no prompt final.

Pacotes históricos 2.1 e 2.2 continuam importáveis sob suas regras. Não editar seus manifestos. A validação estrutural não substitui revisão visual e semântica.
