# Rotina de uso

Este guia serve para os acessos seguintes, depois que a instalacao inicial ja
foi concluida.

## Abrir o painel no Windows

Use o **Windows PowerShell**. No terminal do VS Code, confirme que o perfil
selecionado e `PowerShell`, e nao `Ubuntu`, `WSL` ou `bash`.

1. Entre na pasta do projeto:

```powershell
cd D:\04_APPs\Achadinhos_criativos\01_gflow-videos\prompts
```

2. Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Inicie o painel:

```powershell
python scripts\servir_painel.py
```

4. Abra no navegador:

```text
http://127.0.0.1:8765
```

Mantenha o terminal aberto enquanto estiver usando o painel. Para encerrar o
servidor, volte ao terminal e pressione `Ctrl+C`.

## O que nao precisa ser repetido

No uso cotidiano, nao e necessario clonar novamente o repositorio, recriar a
`.venv`, reinstalar as dependencias ou refazer o arquivo `.env`.

Essas etapas so precisam ser repetidas se a instalacao for removida, se houver
uma mudanca de configuracao ou se as instrucoes do projeto pedirem uma
atualizacao.

## Como saber se o terminal esta errado

Se o prompt tiver um formato parecido com este:

```text
gabybarros@DESKTOP-U3PF9KV:/mnt/d/...
```

voce esta no Linux via WSL. Nesse terminal, caminhos como `D:\...` e comandos
como `Activate.ps1` nao funcionam da forma mostrada acima. Abra um novo terminal
do tipo **PowerShell** e execute novamente os comandos da secao Abrir o painel
no Windows.

## Problemas comuns

### A execucao de scripts foi desabilitada

Libere a execucao apenas para a sessao atual do PowerShell e tente ativar a
`.venv` novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Essa configuracao deixa de valer quando o terminal e fechado.

### O comando `python` nao foi encontrado

Confirme que o PowerShell esta na pasta do projeto e que a `.venv` foi ativada.
Quando a ativacao funciona, o inicio da linha do terminal normalmente mostra
`(.venv)`.

Se a pasta `.venv` nao existir, retorne ao guia de instalacao em
`docs/PRIMEIRO_USO.md`.

### O painel nao abriu no navegador

Confira se o terminal continua aberto e se mostrou que o servidor esta rodando
em `http://127.0.0.1:8765`. Depois, digite esse endereco diretamente no
navegador.

### A planilha esta aberta no Excel

Antes de executar uma operacao que altere a planilha, feche o arquivo no Excel
para evitar bloqueios de escrita.

## Verificacoes opcionais

Quando precisar confirmar a autenticacao ou diagnosticar a configuracao, use:

```powershell
gflow auth status
python scripts\diagnosticar_configuracao.py
```

Para a rotina normal de apenas abrir o painel, essas verificacoes nao precisam
ser executadas todos os dias.
