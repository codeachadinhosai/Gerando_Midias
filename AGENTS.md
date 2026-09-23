# Orientações para agentes

Este repositório contém o pipeline local de preparação, classificação, geração,
aprovação, carrossel e entrega de mídias produzidas com o Flow.

Antes de alterar o projeto, leia:

1. `docs/PLANO_MODERNIZACAO.md`;
2. `docs/ARQUITETURA.md`;
3. `docs/PLANILHA.md` e `docs/IA_E_CLASSIFICACAO.md`;
4. `CONTRATO_INSUMOS.md`.

## Regras de preservação

- Não apagar nem sobrescrever mídias históricas.
- Não gerar vídeo sem `aprovacao=aprovada`.
- Preservar hashes, revisões, locks e retomada idempotente.
- Não versionar segredos, produções reais ou arquivos pesados.
- Manter compatibilidade com os comandos atuais durante a modernização.
- Executar testes proporcionais antes de concluir alterações.

## Continuidade

O plano oficial de reorganização, configuração por `.env`, Git e interface
HTML está em `docs/PLANO_MODERNIZACAO.md`. Atualize esse documento ao concluir
cada fase ou mudar uma decisão arquitetural.

## Gate obrigatório de modelo

Antes de iniciar uma nova fase ou atividade material do plano:

1. classifique a atividade usando a matriz de
   `docs/PLANO_MODERNIZACAO.md#15-gate-de-modelo-por-atividade`;
2. informe o modelo e o esforço recomendados;
3. dirija-se à usuária como Gabi;
4. aguarde confirmação antes de alterar arquivos ou executar a fase.

Use exatamente este formato:

> Gabi, agora vamos fazer **[atividade]**. Configure para **GPT-5.6 Sol,
> esforço [low|medium|high]**. Motivo: [uma frase]. Quando estiver configurado,
> me avise para eu continuar.

Não chame o nível `low` de `light`. Não peça troca para um nível inferior
quando a sessão já estiver usando o mesmo modelo com esforço superior. Leituras,
diagnósticos e verificações sem alteração podem ser feitos antes do gate.
