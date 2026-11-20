# analise-apps

Coleta de downloads e receita da App Store e do Google Play, rodada manualmente no Mac → histórico cifrado → painel HTML local com senha.

- Visão geral, configuração e limitações: @README.md
- Decisões, estado atual e pendências: @docs/agents/decisions.md

Modo: **projeto novo** (Python 3.12, sem framework). Comandos:

```
python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m coletor.demo   # site/demo.html com dados fictícios, senha "demo"
```

Regras específicas:
- Nunca imprimir valores coletados no terminal/log; só contagens. O repositório é público.
- Credenciais ficam em `credenciais/` (ignorada pelo Git; ver README). Nunca ler, listar conteúdo nem copiar esses arquivos.
- `data/historico.enc` é gravado pelo coletor; não editar à mão.
- Mudou o formato cifrado → mudar `coletor/cofre.py` e o `decrypt` de `painel/template.html` juntos.
