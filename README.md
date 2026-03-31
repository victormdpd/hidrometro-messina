# Monitoramento de Hidrômetro — Messina Automação

Sistema de leitura automática diária do hidrômetro com dashboard público e painel administrativo.

## Estrutura do repositório

```
hidrometro-messina/
├── index.html                    # Página pública (cliente)
├── admin.html                    # Painel administrativo (senha)
├── dados/
│   ├── config.json               # Configuração do ciclo atual
│   ├── historico.csv             # Histórico de leituras diárias
│   └── log.txt                   # Log de execuções
├── scripts/
│   └── leitura.py                # Script de captura automática
└── .github/
    └── workflows/
        └── leitura.yml           # Agendamento diário (GitHub Actions)
```

## Como funciona

- Todo dia às **08h** (horário de Brasília) o GitHub Actions executa o script
- O script acessa o site do hidrômetro, captura o valor e salva em `dados/historico.csv`
- A página `index.html` lê o CSV e exibe os dados atualizados

## Acessos

- **Página do cliente:** `https://victormdpd.github.io/hidrometro-messina/`
- **Painel admin:** `https://victormdpd.github.io/hidrometro-messina/admin.html`

## Atualizar o ciclo de leitura

1. Acesse o painel admin com a senha
2. Preencha os novos dados (data da leitura, valor, próxima leitura)
3. Clique em "Salvar" — o arquivo `config.json` será baixado
4. Faça upload do novo `config.json` para a pasta `dados/` no GitHub

## Configuração inicial (feita uma vez)

1. Ativar GitHub Pages: Settings → Pages → Source: `main` / `/ (root)`
2. Garantir que o workflow tem permissão de escrita: Settings → Actions → General → Workflow permissions → Read and write
