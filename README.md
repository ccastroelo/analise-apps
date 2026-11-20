# Painel das lojas

Um script em Python, rodado **manualmente no Mac**, baixa os **downloads** e a **receita** dos apps na
App Store e na Google Play, guarda o histórico **criptografado** em `data/historico.enc` e gera um painel
HTML (`site/index.html`). O painel pede uma senha e decifra os dados no próprio navegador.

As credenciais das lojas ficam **só no computador**, na pasta `credenciais/` (ignorada pelo Git). Nada roda no GitHub.

```
coletor/apple.py        App Store Connect API → relatório SALES diário
coletor/google_play.py  bucket do Play Console → installs + sales report
coletor/cofre.py        PBKDF2-SHA256 + AES-256-GCM (mesmo formato do WebCrypto)
coletor/historico.py    data/historico.enc — junta os dias recoletados
coletor/painel.py       painel/template.html + dados cifrados → site/index.html
coletor/main.py         orquestra; configurado só por variáveis de ambiente
```

A cada execução, os **últimos `DAYS_BACK` dias** (padrão 7) são recoletados e substituem o que havia,
porque as lojas atrasam e ajustam números. Uma loja sem variáveis configuradas é pulada.

## Configuração (uma vez)

### 1. Ambiente Python

Requer Python **3.12** (no Mac, o `python3` do sistema é 3.9 e não serve; use o do Homebrew):

```
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

### 2. Apple (App Store Connect)

1. App Store Connect → **Usuários e acesso → Integrações → App Store Connect API → Chaves da equipe** →
   gerar chave com função **Vendas** (ou Financeiro).
2. Anote o **Key ID** e o **Issuer ID** e baixe o `.p8` (só dá para baixar uma vez). Guarde-o fora desta pasta.
3. **Vendor number**: em **Pagamentos e relatórios financeiros**, no canto superior esquerdo.

### 3. Google Play

1. Google Cloud Console → crie (ou use) um projeto → **IAM → Contas de serviço** → criar → **Chaves → JSON**.
2. Play Console → **Usuários e permissões → Convidar** o e-mail da conta de serviço com as permissões
   **da conta** (não só de um app) **Ver informações do app e baixar relatórios em massa** e
   **Ver dados financeiros**. A permissão pode levar até 24 h para valer no bucket; até lá o Storage
   responde `403 ... storage.objects.get`.
3. **Bucket**: na tela da conta (fora de qualquer app), **Baixar relatórios → Estatísticas** →
   **Copiar URI do Cloud Storage** (`gs://pubsite_prod_rev_.../...`). O nome do bucket é o trecho entre
   `gs://` e a primeira `/`.

### 4. Pasta de credenciais (ignorada pelo Git)

Tudo fica em `credenciais/`, que o `.gitignore` exclui por inteiro: o arquivo `credenciais/env`, a chave
`.p8` da Apple (`credenciais/chave.p8`) e o JSON da conta de serviço (`credenciais/conta.json`).
Deixe a pasta legível só por você (`chmod 700 credenciais; chmod 600 credenciais/*`).
Confira antes de qualquer commit: `git check-ignore credenciais/env` deve imprimir o caminho.

`credenciais/env` (caminhos relativos à raiz do projeto):

```
PAINEL_SENHA='senha forte, 4+ palavras aleatórias'
ASC_KEY_ID='...'
ASC_ISSUER_ID='...'
ASC_VENDOR_NUMBER='...'
ASC_PRIVATE_KEY="$(cat credenciais/chave.p8)"
GOOGLE_SERVICE_ACCOUNT_JSON="$(cat credenciais/conta.json)"
GPLAY_BUCKET='pubsite_prod_rev_...'
GPLAY_PACKAGES='br.com.app1,br.com.app2'
```

A senha é a de `PAINEL_SENHA`: a primeira coleta cria `data/historico.enc` cifrado com ela, e o painel
pede a mesma. O coletor recusa senha vazia e confere a senha contra o histórico **antes** de coletar.
Se a senha mudar, o histórico antigo não abre mais com a nova. Para trocar, apague `data/historico.enc`
e rode de novo com `DAYS_BACK=365`.

### 5. Painel no iCloud (opcional)

Para abrir o painel de outro computador, `site/` pode ser um atalho para uma pasta do iCloud Drive
(o `.gitignore` ignora `site` como pasta ou atalho):

```
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/painel-lojas
ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/painel-lojas site
```

No outro PC, baixe `painel-lojas/index.html` do iCloud e abra no Chrome. No iPhone não funciona: o app
Arquivos mostra HTML sem rodar JavaScript.

## Rodar

Na raiz do projeto:

```
set -a; source credenciais/env; set +a
DAYS_BACK=7 .venv/bin/python -m coletor.main      # 365 na primeira vez
open -a "Google Chrome" site/index.html
```

O terminal mostra só contagens (dias com relatório por loja, linhas do histórico), nunca valores.

Falha de rede, HTTP 429 ou erro 5xx da Apple: o coletor espera e tenta de novo (até 5 vezes, de 5 s a 2 min).
Se uma loja falhar de vez, o que a outra trouxe é salvo mesmo assim, o histórico da que falhou fica
como estava, e o comando termina com código 1 e um aviso para rodar de novo.

O painel precisa de `https`, `localhost` ou do arquivo aberto direto no Chrome, porque o navegador só
libera a criptografia (WebCrypto) em contexto seguro. Alternativa:
`.venv/bin/python -m http.server 8765 --directory site` e abrir `http://localhost:8765`.

Painel com dados fictícios (senha `demo`): `.venv/bin/python -m coletor.demo`.

## O que os números significam (limitações conhecidas)

- **Downloads Apple**: primeiras instalações (tipos `1`, `1F`, `1T`, `F1`, `1E*`). Não inclui atualizações nem re-downloads.
- **Downloads Google**: coluna `Daily User Installs` (ou `Install events`, nos relatórios mais novos) do `installs_*_overview.csv`.
- **Receita Apple**: *proceeds* (líquido para você), na moeda de pagamento.
- **Receita Google**: valor **bruto** cobrado do cliente (`Charged`), na moeda da venda. Reembolsos não são descontados.
  O líquido só sai no relatório de *earnings* mensal, que não é diário.
- Moedas **não são convertidas**: o painel mostra cada moeda separada.
- O app aparece pelo **título** na Apple e pelo **pacote** no Google.
- A Apple publica o relatório de um dia por volta das 05:00 de Brasília do dia seguinte; o Google, com 1 a 2 dias de atraso.
