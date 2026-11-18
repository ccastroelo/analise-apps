# analise-apps

Coleta diária de downloads e receita da App Store e do Google Play (GitHub Actions) → histórico cifrado → painel HTML com senha no GitHub Pages.

- Visão geral, configuração e limitações: @README.md
- Decisões, estado atual e pendências: @docs/agents/decisions.md

Modo: **projeto novo** (Python 3.12, sem framework). Comandos:

```
python -m venv .venv && <venv>/python -m pip install -r requirements.txt
<venv>/python -m pytest -q
<venv>/python -m coletor.demo   # painel com dados fictícios, senha "demo"
```

Regras específicas:
- Nunca imprimir valores coletados em log; o repositório é público.
- `data/historico.enc` é gravado pelo Action; não editar à mão.
- Mudou o formato cifrado → mudar `coletor/cofre.py` e o `decrypt` de `painel/template.html` juntos.
