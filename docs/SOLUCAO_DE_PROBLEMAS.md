# Solucao de Problemas do Pipeline Flow

Use este guia para diagnosticar falhas comuns sem apagar historico, reenviar
tentativas incertas ou consumir creditos sem querer.

## Checklist seguro

Antes de repetir qualquer comando:

- feche o Excel se a operacao atualiza planilha;
- confira se existe tentativa pendente em `execucao.json`;
- confira `logs/eventos.jsonl` do clipe;
- confira `gflow.log` quando uma chamada ao Flow foi submetida;
- preserve locks desconhecidos ate entender o estado real;
- nunca apague midias historicas para limpar o problema.

## Pacote novo sem resposta

Sintoma:

```text
pacote novo sem resposta_ia correspondente
```

Causa comum: o pacote foi preparado, mas nao existe `resposta_ia.json` em
`preparados/respostas_ia/` com o mesmo `pacote_sha256`.

Acao:

1. Abra `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip`.
2. Envie o pacote para classificacao.
3. Salve a resposta em `preparados/respostas_ia/`.
4. Rode novamente `python -m pipeline_flow`.

Nao renomeie revisoes tentando adivinhar hashes. O importador usa o conteudo do
JSON e o `pacote_sha256`.

## Erro ao salvar Excel

Sintoma: importacao ou execucao conclui parcialmente, mas `erro_excel` aparece
ou a planilha nao atualiza.

Causa comum: `controle_pipeline_flow.xlsx` esta aberto no Excel.

Acao:

1. Feche o Excel.
2. Repita o mesmo comando.

Operacoes idempotentes devem sincronizar a planilha sem reenviar midia ja
concluida.

## Arquivo ausente ou ambiguo

Sintoma: preparacao informa pendencias em uma linha.

Causas comuns:

- `arquivo`, `usar_com` ou `material_existente` aponta para nome inexistente;
- existe mais de um arquivo com o mesmo nome em fontes diferentes;
- `producao_id`, `ordem` ou `produto_id` esta incompleto para o uso desejado.

Acao:

1. Corrija a planilha ou os nomes dos arquivos.
2. Rode `python scripts/preparar_insumos.py preparar`.
3. Confira `preparados/relatorio_preparacao.json`.

Nao exclua linhas com `classifica=nao`; elas podem permanecer catalogadas.

## Resposta IA invalida

Sintomas:

- JSON invalido;
- `pacote_sha256` divergente;
- plano sem clipes esperados;
- prompt ausente quando `gerar_imagem=true` ou `gerar_video=true`;
- referencia inexistente.

Acao:

1. Corrija a resposta no classificador.
2. Preserve a resposta anterior.
3. Salve novo arquivo em `preparados/respostas_ia/`.
4. Importe novamente.

Nao edite manifestos de pacotes historicos. Prepare nova revisao para adotar
contrato novo.

## Imagem nao gera video

Sintomas:

- `video` fica bloqueado;
- painel informa que a imagem precisa estar aprovada e vinculada;
- `aprovacao=aprovada` existe na planilha, mas o video nao libera.

Causas comuns:

- aprovacao foi registrada antes do vinculo tecnico atual;
- a imagem mudou depois da aprovacao;
- nova revisao limpou a aprovacao;
- o SHA-256 esperado nao corresponde ao arquivo atual;
- `execucao.json` nao possui vinculo ativo.

Acao:

1. Abra a imagem atual em `imagem_arquivo`.
2. Revise visualmente.
3. Mantenha ou registre `aprovacao=aprovada` na planilha.
4. Execute `python scripts/executar_flow.py aprovar --producao $Producao --clipe ID_DO_CLIPE`.
5. Rode o video novamente.

Nao force edicao manual em `execucao.json` para liberar video.

## Carrossel nao gera

Causas comuns:

- `gerar_carrossel` nao esta como `sim`;
- plano importado nao tem `carrossel.ativo=true`;
- imagem atual nao existe ou mudou de hash;
- clipe nao pertence a revisao ativa;
- saida pretendida ficaria fora de `PIPELINE_DELIVERY_DIR`.

Acao:

1. Confira a linha da planilha.
2. Confira o plano do clipe.
3. Atualize os dados do painel ou rode novamente o pipeline.
4. Para forcar uma nova versao local, use a acao de regenerar no painel.

`aprovacao=aprovada` nao e necessaria para carrossel. Ela controla somente
video.

## Video bloqueado por trava de credito

Sintoma:

```text
Outra geracao paga esta ativa ou requer revisao manual.
```

Causa: existe `preparados/.locks/video-credit.lock`.

Acao segura:

1. Confira se ha uma geracao em andamento no painel.
2. Confira `execucao.json` do clipe.
3. Confira `gflow.log`.
4. Confira no Flow se houve submissao.
5. Remova a trava manualmente somente depois de confirmar que nao ha efeito
   externo incerto.

Essa trava nao deve ser removida automaticamente porque uma chamada pode ter
consumido creditos mesmo sem arquivo local.

## Lock por clipe

Sintoma: operacao informa que o clipe esta em andamento.

Arquivo relacionado:

```text
<pasta_do_clipe>/.execucao.lock
```

Acao:

- se o processo local ainda existe, aguarde;
- se o processo local morreu, o sistema pode arquivar lock orfao em
  `logs/locks/`;
- se o lock pertence a outro host, esta malformado ou tem versao desconhecida,
  inspecione manualmente.

Nao substitua lock ativo para forcar duas operacoes no mesmo clipe.

## Tentativa submetida sem saida

Sintoma: `execucao.json` indica tentativa submetida, mas nao ha video local.

Risco: o Flow pode ter recebido a chamada e consumido creditos.

Acao:

1. Confira `gflow.log`.
2. Confira o projeto no Flow.
3. Procure saida local unica e valida.
4. Se nao houver evidencia segura, mantenha bloqueado e decida manualmente se
   prepara nova revisao.

Nao reenvie automaticamente.

## Erro de configuracao

Causas comuns:

- `GFLOW_PROJECT_ID` vazio para video;
- o `gflow-cli` não foi instalado na `.venv` do projeto ou `GFLOW_ROOT`
  aponta para uma instalação externa incorreta;
- `GFLOW_VIDEO_MODEL` fora da lista aceita;
- `GFLOW_TIMEOUT_SECONDS` nao e inteiro positivo;
- `WEB_HOST` nao e loopback.

Acao:

1. Confira `.env`.
2. Use `--projeto` ou `--gflow-raiz` somente como sobrescrita pontual.
3. Reinicie o painel apos mudar variaveis.

## Upload recusado no painel

Causas comuns:

- arquivo acima de 50 MiB;
- JSON invalido;
- imagem com extensao diferente do conteudo;
- imagem acima do limite seguro de pixels;
- origem externa ou contexto `cross-site`;
- ausencia de `X-Pipeline-Confirmation: confirmar`.

Acao:

1. Ajuste o arquivo.
2. Atualize o painel.
3. Repita a operacao confirmada.

## Estados antigos

Sintoma: planilha ou estado usa acentos, espacos ou nomes historicos.

Acao:

- a leitura normaliza grafias conhecidas em memoria;
- novas escritas usam `snake_case` ASCII;
- para modernizar `execucao.json`, rode primeiro:

```powershell
python scripts/migrar_estados.py
```

Depois de revisar:

```powershell
python scripts/migrar_estados.py --aplicar
```

A migracao preserva backups e nao promove aprovacoes legadas automaticamente.

## Testes falham

Acao inicial:

```powershell
python -m pytest
```

Se a falha envolver `TestClient`, verifique se e apenas o aviso conhecido de
depreciacao. Se falhar por dependencia ausente, instale dependencias de
desenvolvimento com:

```powershell
python -m pip install -e .[dev]
```

Testes nao devem chamar o Flow real, acessar producoes reais ou depender de
midias historicas.
