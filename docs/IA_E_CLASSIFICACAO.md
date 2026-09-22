# IA e classificação

A classificação transforma os insumos declarados na planilha em um plano
validável. Ela não gera imagem ou vídeo, não aprova frames e não consome
créditos do Flow.

## Responsabilidades

- A pessoa informa fatos, arquivos, intenção criativa e permissões na
  planilha.
- O Python monta o pacote, calcula hashes e valida a resposta.
- A IA classifica cada clipe e produz planos e prompts dentro do contrato.
- O Flow só é chamado depois, por comandos explícitos de geração.

A fonte executável de verdade é o conjunto formado por
[`CONTRATO_INSUMOS.md`](../CONTRATO_INSUMOS.md), pelo validador em
`src/pipeline_flow/services/preparar_insumos.py` e pelo classificador incluído
no pacote. Orientações históricas não substituem essa validação.

## 1. Preparar o pacote

Com a planilha salva e fechada:

```powershell
python scripts\preparar_insumos.py preparar
```

O comando cria, entre outros arquivos:

- `preparados/relatorio_preparacao.json`;
- `preparados/pacotes/<producao_id>/<revisao>/manifest.json`;
- cópias verificadas dos anexos, contrato, classificador e identidade, quando
  necessária;
- `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip`;
- `ENVIAR_A_IA.txt` com a instrução daquela revisão.

Cada pacote recebe um `pacote_sha256`. Não renomeie revisões, substitua anexos
ou misture arquivos de pacotes diferentes.

## 2. Enviar para a IA

Anexe `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip` a uma IA capaz de ler o ZIP
e inspecionar as imagens. Peça que ela siga `ENVIAR_A_IA.txt` e devolva somente
o JSON solicitado.

Instrução curta recomendada:

```text
Analise este pacote, siga ENVIAR_A_IA.txt e os contratos incluídos e devolva
somente o JSON da resposta. Não gere mídia e não invente dados ausentes.
```

A IA precisa ter acesso visual aos anexos. Não classifique apenas pelos nomes
dos arquivos.

## 3. Conteúdo obrigatório da resposta

A resposta é um objeto JSON com esta estrutura geral:

```json
{
  "pacote_sha256": "hash-exato-do-pacote",
  "plano_producao": {
    "producao_id": "ID_DA_PRODUCAO",
    "versao": "2.0"
  },
  "clipes": [
    {
      "id_clipe": "ID_ESPERADO",
      "plano": {},
      "incluir_bloco_identidade": false
    }
  ]
}
```

O esquema completo está dentro do pacote. A resposta deve:

- repetir exatamente `pacote_sha256`, `producao_id`, IDs, produtos e ordem;
- representar todos os clipes uma única vez, sem itens extras;
- respeitar o papel, a categoria e o fluxo de cada clipe;
- usar somente referências declaradas e preservar seus `ref_id` e arquivos;
- marcar `pronto` apenas quando houver insumo suficiente;
- marcar `pendente` com motivo claro quando faltar informação;
- manter imagens e vídeos em `9:16`;
- preservar literalmente fatos e decisões humanas.

Não adicione extensões de esquema que o importador atual não reconheça. Pacotes
novos usam o contrato `2.3-insumos`; respostas legadas `2.1` e `2.2`
continuam aceitas quando correspondem ao pacote original.

## 4. Imagem pelo contrato 2.3

Quando o plano pedir uma imagem nova, ele deve editar uma base real:

- modo `adaptar` e método `i2i`;
- Referência 1 como imagem-base, nunca como identidade;
- `objeto_edicao`, `preservar` e `alterar` preenchidos;
- qualquer `base_edicao` informada pela pessoa preservada como primeira
  referência;
- apenas arquivos de imagem nas referências visuais;
- `prompt_imagem` iniciado exatamente por
  `Edite a Referência 1 como imagem-base. Não recrie a cena do zero.`

Quando não for necessário gerar imagem, o plano deve apontar para uma
referência existente válida, sem criar `prompt_imagem`.

## 5. Vídeo, áudio e aprovação

O plano pode incluir `prompt_video.txt`, mas isso não autoriza a geração. Uma
nova geração de vídeo sempre exige `aprovacao=aprovada` vinculada à imagem, ao
hash e à revisão corretos.

Para vídeo novo, o contrato exige:

- modelo operacional `omni-flash` na etapa de geração;
- duração de 8 segundos e proporção `9:16`;
- quatro intervalos de timeline: `0-1.2`, `1.2-3`, `3-6.5` e `6.5-8`;
- fala e regras de áudio compatíveis com o papel do clipe;
- texto falado preservado exatamente no prompt de vídeo.

O clipe de abertura começa com “Bora”. Um clipe principal pode não ter áudio;
abertura e CTA novos exigem fala conforme o plano validado.

## 6. Carrossel

`gerar_carrossel=sim` autoriza o card independentemente da aprovação de vídeo.
Quando solicitado, o plano deve conter os dados de carrossel; quando não
solicitado, não deve criá-los.

Limites validados:

- texto principal: até 52 caracteres;
- subtexto: até 28 caracteres;
- CTA: até 54 caracteres;
- dados de CTA somente no clipe com papel `cta`.

Valores humanos de `cta_destino` e `cta_palavra` são preservados. A IA
completa somente o que estiver vazio.

## 7. Salvar e importar

Salve o JSON puro em `preparados/respostas_ia/`. Depois use os caminhos reais
da revisão:

```powershell
$Pacote = (Resolve-Path 'preparados/pacotes/PRODUCAO/REVISAO').Path
$Resposta = (Resolve-Path 'preparados/respostas_ia/RESPOSTA.json').Path
python scripts\preparar_insumos.py importar --pacote $Pacote --resposta $Resposta --atualizar-excel
```

A importação confere hashes de pacote, anexos, contrato e identidade; valida o
esquema e as regras de cada clipe; preserva revisões; e recusa mudanças nos
campos humanos feitas depois da preparação. Com `--atualizar-excel`, cria
backup antes de sincronizar a planilha.

Se a validação falhar, não corrija hashes ou campos de controle manualmente.
Corrija a origem, prepare nova revisão quando necessário e classifique de novo.

Depois de uma importação válida, os planos ficam em
`preparados/flow/<producao_id>/<revisao>/`. Revise-os no painel antes de
qualquer geração.

Para instruções de uso em chats, consulte também
[`02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md`](../entradas/02_COMO_PROCESSAR_AQUI_EM_NOVO_CHAT.md)
e [`01_COMO_USAR_EM_OUTRA_IA.md`](../entradas/01_COMO_USAR_EM_OUTRA_IA.md).
