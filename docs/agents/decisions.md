# Decisões e estado do projeto

## Estado em 2026-11-18

**Pronto e validado localmente**
- Coleta da Apple (`coletor/apple.py`) e do Google Play (`coletor/google_play.py`), histórico cifrado
  (`coletor/historico.py`, `coletor/cofre.py`) e painel (`painel/template.html`).
- 7 testes passando (`tests/test_coletor.py`), sem rede: parsers das duas lojas, criptografia, junção do histórico.
- Painel conferido no navegador com dados fictícios (`python -m coletor.demo`, senha `demo`), em desktop e celular.

**Publicado**
- Repositório público `ccastroelo/analise-apps`, branch `main`.
- GitHub Pages ativado com fonte "GitHub Actions". URL esperada: `https://ccastroelo.github.io/analise-apps/`.

**Ainda NÃO feito / não verificado**
- Secrets do repositório não cadastrados (lista no README). Até lá, a execução agendada falha.
- Nenhuma execução com as APIs reais. A primeira deve ser manual, com `days_back = 365`.
- Pontos a confirmar na primeira execução real:
  - nomes das colunas do `installs_*_overview.csv` (o código aceita `Daily User Installs` e `Install events`);
  - valores de `Financial Status` no sales report do Google (hoje só `Charged` é somado);
  - formato de data de `Order Charged Date` (o código assume ISO `yyyy-mm-dd`).

## Decisões

Todas de 2026-11-18, tomadas com o usuário.

| Decisão | Escopo | Motivo |
|---|---|---|
| Script em Python, não um MCP | coleta | Rotina diária determinística, sem custo de LLM e sem depender de terceiros. Não há MCP oficial da Apple nem do Google. |
| Execução no GitHub Actions (cron 10:00 UTC = 07:00 Brasília) | agendamento | Roda com o computador desligado. |
| Painel em HTML único e autocontido, sem CDN | painel | Abre em qualquer lugar. Foi pedido pelo usuário no lugar do Google Sheets (descartado). |
| Dados cifrados com senha (PBKDF2-SHA256 600k + AES-256-GCM), decifrados no navegador | painel e histórico | Repositório e Pages são públicos. O histórico fica no próprio repositório (`data/historico.enc`). |
| Repositório público + GitHub Pages grátis | hospedagem | O usuário avaliou um servidor HTTP próprio e preferiu o Pages. A segurança depende de uma senha forte em `PAINEL_SENHA`. |
| Métricas da v1: downloads e receita | escopo | Notas/reviews e crashes ficaram para depois. |
| Recoletar os últimos 7 dias a cada execução, substituindo por (data, loja) | histórico | As lojas atrasam e ajustam números. |
| Receita sem conversão de moeda; Apple = líquido (proceeds), Google = bruto (`Charged`) | métricas | É o que os relatórios diários oferecem. O líquido do Google só sai no earnings mensal. |
| Logs só com contagens | segurança | Os logs de um repositório público são públicos. |

## Ideias registradas (não aprovadas)

- Converter moedas para BRL.
- Usar o earnings mensal do Google para ter o líquido.
- Incluir notas/reviews e crash/ANR (Play Developer Reporting API, Analytics Reports da Apple).
