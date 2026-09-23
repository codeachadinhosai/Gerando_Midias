## Automação de geração

A conexão dos planos importados ao gflow existente está em [AUTOMACAO_FLOW.md](AUTOMACAO_FLOW.md). Use scripts/executar_flow.py para listar, gerar imagens, vincular aprovações e gerar vídeos, com registro e retomada.

# Pipeline atual — contrato 2.2-insumos

Use [GUIA_INSUMOS_FLOW.md](GUIA_INSUMOS_FLOW.md) para preparar pacotes e importar a resposta do Classificador Universal. A fonte canônica atual é entradas/CLASSIFICADOR_UNIVERSAL.txt.

O classificador entrega plano e prompts de imagem e vídeo na mesma resposta. O preparador valida e salva os arquivos aplicáveis; não chama uma IA nem gera mídia. A imagem real deve ser aprovada antes do vídeo quando o plano exigir. Pacotes antigos e mídia existente são preservados.

---

O conteúdo abaixo documenta a biblioteca v1 histórica; não é o procedimento atual do preparador.

# Biblioteca de fluxos — versão 1

Esta pasta prepara instruções e contextos para geração. Não executa Google Flow sozinha.

## Organização
- CLASSIFICADOR_UNIVERSAL.txt: prompt autossuficiente para enviar a uma IA com as imagens.
- identidade/: cópias intactas da identidade e referências existentes.
- entradas/: uma subpasta por produto/lote, para receber as imagens.
- fluxos/: nove pastas com fluxo.txt, modelo.txt, prompt de vídeo por categoria e contexto.txt de orientação.
- preparados/: um diretório por execução/clipe com encaminhamento.json e contexto.txt resolvido.

Os arquivos antigos da raiz e proposta_pov/ foram preservados como histórico. Não misturar suas instruções com esta biblioteca. A proposta POV anterior exige Bora em todos os clipes; esta biblioteca a substitui para os novos fluxos: Bora somente na abertura.

## Uso com qualquer IA
1. Coloque imagens em entradas/<produto>/, separando variantes.
2. Entregue CLASSIFICADOR_UNIVERSAL.txt e os anexos reais à IA. Anexe referências de Júlia quando ela aparecer. Texto de caminho não equivale a anexar.
3. Por padrão a IA prepara um clipe principal. Peça "sequência completa" para abertura + principal + CTA.
4. Salve cada par encaminhamento.json/contexto.txt em preparados/<execucao>/<clipe>/.
5. O contexto resolvido substitui o contexto de orientação SOMENTE na cópia da execução.
6. Envie identidade aplicável + modelo.txt + contexto resolvido + referências ao gerador de imagem.
7. Envie imagem inicial validada + prompt de vídeo da categoria + o mesmo contexto ao gerador de vídeo.
8. Configure 9:16, oito segundos e os modelos também no executor. Verifique o resultado.

Não há fotos de produto cadastradas como exemplo. InicioJuliaCTA_05.jpg continua na raiz: é referência de cena; sua caneca não é automaticamente um produto-alvo.

## Copiar para Fila Flow
Copie fluxos/, identidade/, preparados/ e CLASSIFICADOR_UNIVERSAL.txt mantendo a estrutura da biblioteca. Use uma pasta exclusiva por execução; não sobrescreva Julia_01 ou Julia_02_CTA.
Para usar o carregador atual, a execução precisará estar em uma pasta própria, selecionada com --pasta; ele não percorre recursivamente esta biblioteca.
Nomes modelo.txt, identidade.txt, contexto.txt e <Categoria>_NN.ext + <Categoria>.txt seguem as convenções do projeto. Os nomes de categoria desta biblioteca são explícitos; CTAFinal não usa o prefixo InicioJulia.
Nenhum arquivo foi copiado para o outro projeto nesta implementação.

**Copiar os arquivos não torna a biblioteca imediatamente executável pelo código atual.** Não execute um lote assumindo que a integração já foi feita. O carregador existente não lê encaminhamento.json e pode acrescentar regras indevidas a categorias novas.

## Integração necessária no gflow-videos
1. Ler encaminhamento e contexto resolvido; validar status, categoria/fluxo e caminhos.
2. Anexar o MESMO contexto às etapas imagem e vídeo para todos os fluxos.
3. Encaminhar categorias explicitamente. CTAFinal não é abertura nem vestuário; detalhes/ambientação não recebem exigências de rosto ou roupa.
4. Resolver referências por papel. Rosto/corpo obrigatórios somente quando necessários; foto de mão não é obrigatória.
5. Eliminar decisões específicas de ambiente, fala e produto acrescentadas pelo runner; mantê-las no contexto.
6. Fixar/validar modelos e parâmetros reais no provedor. O código atualmente usa o alias omni-flash; não há confirmação aqui de equivalência a uma versão específica.
7. Usar IDs únicos para saídas e registro; considerar contexto, prompts, referências e modelo ao decidir reprocessamento.
8. Verificar duração/aspecto, anatomia, produto, fala e finalização. Em falha, tentativas limitadas e registro; mudar variáveis somente no contexto.
9. Para sequência completa, montar clipes em ordem e verificar continuidade. Essa montagem ainda não existe nesta biblioteca.
10. Remover dependência de revisão humana opcional apenas depois de implementar critérios automáticos equivalentes.

## Regras editoriais
Identidade imutável. CTA com mãos descritas de forma simples. Nenhuma foto extra de mão exigida.
Abertura começa com Bora; CTA não. Produto principal não repete a abertura.
Imagem = estado inicial; vídeo = uma ação realizável em oito segundos.
Não levantar produtos fixos/pesados nem inventar funcionamento, atributos ou resultado.
Nenhum texto de exemplo dos contratos é um contexto válido de produção.
