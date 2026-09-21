# Fluxo Operacional do Pipeline Flow

Este documento descreve a jornada diaria do pipeline, da planilha ate as
entregas. Ele complementa o guia de preenchimento da planilha e o contrato de
insumos.

## Visao geral

O fluxo completo e:

```text
planilha e arquivos
-> preparacao dos pacotes
-> classificacao pela IA
-> importacao da resposta
-> imagem ou frame
-> revisao humana
-> carrossel local, quando solicitado
-> video, quando aprovado
-> entrega e auditoria
```

Operacoes concluidas devem ser retomaveis. Repetir o comando principal nao deve
reenviar etapas ja finalizadas nem substituir ativos historicos.

## Preparar insumos

1. Coloque imagens, frames ou materiais em `entradas/` ou nas pastas de
   referencia previstas.
2. Preencha `entradas/controle_pipeline_flow.xlsx`.
3. Feche o Excel antes de rodar comandos que atualizam a planilha.
4. Execute:

```powershell
python scripts/preparar_insumos.py preparar
```

O resultado fica em `preparados/pacotes/<producao_id>/<revisao>/` e o ZIP
consolidado mais recente fica em `preparados/pacotes_ia/ULTIMO_PACOTE_IA.zip`.

Somente linhas com `classifica=sim` entram na rodada. Linhas com
`classifica=nao` permanecem catalogadas e nao devem ser apagadas.

## Classificar com IA

A IA deve ler:

- `entradas/CLASSIFICADOR_UNIVERSAL.txt`;
- `CONTRATO_INSUMOS.md`;
- `identidade.txt`, quando disponivel;
- `manifesto.json`;
- anexos reais do pacote.

A resposta deve ser JSON puro em `preparados/respostas_ia/`, preservando
`pacote_sha256`. Cada clipe precisa manter `id_clipe`, `producao_id`,
`produto_id` e `ordem` do manifesto.

Nao gerar imagem, video ou aprovacao durante a classificacao.

## Importar resposta

Importar valida o JSON, exporta planos e prompts para `preparados/flow/` e
atualiza os campos de sistema da planilha.

```powershell
$Pacote = (Resolve-Path 'preparados/pacotes/PRODUCAO/REVISAO').Path
$Resposta = (Resolve-Path 'preparados/respostas_ia/ARQUIVO.json').Path
python scripts/preparar_insumos.py importar --pacote $Pacote --resposta $Resposta --atualizar-excel
```

A importacao nao chama o Flow e nao consome creditos.

Se uma nova revisao reaproveitar imagem existente, a aprovacao anterior e limpa
e o frame precisa ser revisado de novo. Revisoes antigas e midias historicas
permanecem preservadas.

## Rodar o pipeline completo

O comando cotidiano e:

```powershell
python -m pipeline_flow
```

O wrapper historico continua disponivel:

```powershell
python scripts/rodar_pipeline.py
```

O comando prepara pacotes, procura respostas correspondentes, importa revisoes
validas, registra imagens fornecidas, gera imagens pendentes, cria carrosseis
autorizados e gera videos liberados.

Use `--sem-preparar` para retomar somente revisoes ja importadas.

## Registrar ou gerar imagem

Quando o plano pede imagem (`gerar_imagem=true`), o executor usa o metodo e as
referencias do plano. Toda nova imagem do contrato 2.3 deve editar uma base
existente: a Referencia 1 e a imagem-base e o prompt deve comecar com:

```text
Edite a Referencia 1 como imagem-base. Nao recrie a cena do zero.
```

Para registrar uma imagem entregue manualmente:

```powershell
$Imagem = (Resolve-Path 'CAMINHO/DA/IMAGEM.png').Path
python scripts/executar_flow.py registrar-imagem --producao $Producao --clipe ID_DO_CLIPE --arquivo $Imagem
```

O arquivo original nao e movido. O sistema copia a imagem para a pasta
versionada do clipe, calcula SHA-256, atualiza `execucao.json` e revoga vinculo
tecnico de aprovacao anterior.

## Aprovar ou rejeitar

Abra o caminho de `imagem_arquivo`, revise produto, anatomia, identidade,
cenario, composicao, texto visual e fidelidade ao plano.

Se estiver correto, marque `aprovacao=aprovada` e execute:

```powershell
python scripts/executar_flow.py aprovar --producao $Producao --clipe ID_DO_CLIPE
```

O comando registra o vinculo tecnico em `execucao.json`: revisao, pacote,
fingerprint, caminho e SHA-256 do frame. O video so e liberado enquanto esses
dados continuarem iguais.

Se rejeitar, informe `aprovacao=rejeitada`, preserve o motivo e nao execute
`video`.

## Gerar carrossel

`gerar_carrossel=sim` autoriza somente o card local. Essa autorizacao nao exige
`aprovacao=aprovada` e nunca libera video.

O card e renderizado sobre a imagem 9:16 atual e salvo em:

```text
entregas_flow/carrossel/<producao_id>/
```

Para renderizar manualmente:

```powershell
python scripts/gerar_carrossel.py --producao $Producao --clipe ID_DO_CLIPE
```

Regenerar cria outro arquivo versionado e preserva o anterior.

## Gerar video

Geracao de video pode consumir creditos e exige:

- plano com `gerar_video=true`;
- imagem atual registrada;
- `aprovacao=aprovada`;
- vinculo tecnico valido;
- `GFLOW_PROJECT_ID` configurado ou `--projeto`;
- `gflow.exe` disponivel;
- ausencia de tentativa pendente;
- trava global de credito livre.

Comando manual:

```powershell
python scripts/executar_flow.py video --producao $Producao --clipe ID_DO_CLIPE --modelo-video omni-flash
```

Pelo painel, a acao tambem exige checkbox, dialogo final e a frase exata
`GERAR VIDEO`.

## Painel local

Inicie com:

```powershell
python scripts/servir_painel.py
```

Endereco padrao:

```text
http://127.0.0.1:8765
```

O painel mostra producoes, clipes, pacotes, revisao, carrossel, videos,
entregas e logs. Operacoes de escrita exigem confirmacao explicita e validam
revisao, hash, caminhos e limites de upload.

## Migrar estados antigos

Simule primeiro:

```powershell
python scripts/migrar_estados.py
```

Aplique somente depois de revisar:

```powershell
python scripts/migrar_estados.py --aplicar
```

A migracao nao chama o Flow. Ela usa locks, valida hashes, cria backup em
`logs/migrations/` e preserva estados arquivados em `antigos/`.

## Testes

Execute:

```powershell
python -m pytest
```

Os testes devem usar diretorios temporarios e mocks. Nao instalar dependencias
nem chamar servicos pagos apenas para validar uma alteracao documental.
