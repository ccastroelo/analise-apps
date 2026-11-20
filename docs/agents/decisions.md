# Decisões e estado do projeto

## Estado em 2026-11-20

**Pronto e validado localmente**
- Coleta da Apple (`coletor/apple.py`) e do Google Play (`coletor/google_play.py`), histórico cifrado
  (`coletor/historico.py`, `coletor/cofre.py`) e painel (`painel/template.html`).
- 7 testes passando (`tests/test_coletor.py`), sem rede: parsers das duas lojas, criptografia, junção do histórico.
- Painel conferido no navegador com dados fictícios (`python -m coletor.demo`, senha `demo`), em desktop e celular.

**Observado nas execuções no GitHub Actions (19 e 20/11, antes da mudança para o Mac)**
- Apple funcionou com credenciais reais: 150 dias com relatório numa janela de 365 (dias sem venda não
  têm relatório; não confirmado se a API também corta dias antigos).
- Google falhou com `403 storage.objects.get`: a conta de serviço (a do Codemagic) ainda sem as
  permissões de relatório no Play Console. O nome do bucket já estava certo (`pubsite_prod_rev_...`).
- `data/historico.enc` já tem dados reais da Apple, da execução de 20/11 16:37 UTC (Google veio com 0 dias
  por bucket errado). A execução seguinte, com o 403, caiu antes de salvar.

**Ainda NÃO feito / não verificado**
- Primeira coleta local com `DAYS_BACK=365`.
- No GitHub (feito pelo usuário): apagar os secrets, desativar o Pages e, se quiser, apagar as execuções
  antigas do Actions (o log do erro mostra o e-mail da conta de serviço).
- Pontos a confirmar na primeira coleta real do Google:
  - nomes das colunas do `installs_*_overview.csv` (o código aceita `Daily User Installs` e `Install events`);
  - valores de `Financial Status` no sales report do Google (hoje só `Charged` é somado);
  - formato de data de `Order Charged Date` (o código assume ISO `yyyy-mm-dd`).
- Histórico desde 2010: pedido pelo usuário, sem decisão. A Apple só guarda 365 dias de relatório diário
  (anuais por 10 anos); o alcance do bucket do Google ainda não foi verificado.

## Decisões

Tomadas com o usuário. Sem data indicada: 2026-11-18.

| Decisão | Escopo | Motivo |
|---|---|---|
| Script em Python, não um MCP | coleta | Rotina diária determinística, sem custo de LLM e sem depender de terceiros. Não há MCP oficial da Apple nem do Google. |
| ~~Execução no GitHub Actions (cron diário)~~ — substituída em 2026-11-20 | agendamento | — |
| Coleta manual no Mac, credenciais na pasta `credenciais/`, ignorada pelo Git (2026-11-20) | execução | Tirar as chaves das lojas do GitHub; a conta do Google em uso (Codemagic) pode publicar apps. Agendamento (launchd) fica para depois. |
| Painel em HTML único e autocontido, sem CDN | painel | Abre em qualquer lugar. Foi pedido pelo usuário no lugar do Google Sheets (descartado). |
| Dados cifrados com senha (PBKDF2-SHA256 600k + AES-256-GCM), decifrados no navegador | painel e histórico | Repositório e Pages são públicos. O histórico fica no próprio repositório (`data/historico.enc`). |
| ~~Repositório público + GitHub Pages~~ — substituída em 2026-11-20 | hospedagem | — |
| Painel só local (`site/index.html` no Chrome), sem Pages (2026-11-20) | hospedagem | Escolha do usuário ao mover a coleta para o Mac. Perde o acesso pelo celular. |
| Métricas da v1: downloads e receita | escopo | Notas/reviews e crashes ficaram para depois. |
| Recoletar os últimos 7 dias a cada execução, substituindo por (data, loja) | histórico | As lojas atrasam e ajustam números. |
| Receita sem conversão de moeda; Apple = líquido (proceeds), Google = bruto (`Charged`) | métricas | É o que os relatórios diários oferecem. O líquido do Google só sai no earnings mensal. |
| Logs só com contagens | segurança | Regra mantida da época do Actions; o repositório segue público. Mensagens de erro podem incluir o texto da exceção (sem valores coletados). |
| Retentativa na Apple (rede, 429, 5xx; esperas 5–120 s) e token JWT novo a cada dia (2026-11-20) | coleta | A coleta de 365 dias caiu por timeout de conexão no meio; o token vale só 15 min. |
| Falha de uma loja não derruba a outra; sai com código 1 (2026-11-20) | coleta | Antes, o 403 do Google e o timeout da Apple descartavam tudo o que já tinha sido baixado. |

## Ideias registradas (não aprovadas)

- Converter moedas para BRL.
- Usar o earnings mensal do Google para ter o líquido.
- Incluir notas/reviews e crash/ANR (Play Developer Reporting API, Analytics Reports da Apple).
