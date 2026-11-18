# Painel das lojas

Todo dia, um GitHub Action baixa os **downloads** e a **receita** dos apps na App Store e na Google Play,
guarda o histórico **criptografado** no repositório e publica um painel HTML no GitHub Pages.
O painel pede uma senha e decifra os dados no próprio navegador: abre no celular ou em qualquer PC.

```
coletor/apple.py        App Store Connect API → relatório SALES diário
coletor/google_play.py  bucket do Play Console → installs + sales report
coletor/cofre.py        PBKDF2-SHA256 + AES-256-GCM (mesmo formato do WebCrypto)
coletor/historico.py    data/historico.enc — junta os dias recoletados
coletor/painel.py       painel/template.html + dados cifrados → site/index.html
coletor/main.py         orquestra; configurado só por variáveis de ambiente
.github/workflows/coleta-diaria.yml   07:00 (Brasília), todo dia
```

A cada execução, os **últimos 7 dias** são recoletados e substituem o que havia, porque as lojas
atrasam e ajustam números. Uma loja sem variáveis configuradas é pulada.

## Configuração (uma vez)

### 1. Repositório

Crie um repositório no GitHub e envie esta pasta. Pode ser **público**: o GitHub Pages é gratuito nesse
caso, e o histórico e o painel só têm dados cifrados. Os logs do Action mostram apenas contagens.
Mesmo assim, use uma **senha forte** (4+ palavras aleatórias), porque o arquivo cifrado fica público
e uma senha fraca pode ser quebrada por força bruta.

Em **Settings → Pages → Source**, escolha **GitHub Actions**.

### 2. Apple (App Store Connect)

1. App Store Connect → **Usuários e acesso → Integrações → App Store Connect API → Chaves da equipe** →
   gerar chave com função **Vendas** (ou Financeiro).
2. Anote o **Key ID** e o **Issuer ID** e baixe o `.p8` (só dá para baixar uma vez). Guarde-o fora desta pasta.
3. **Vendor number**: em **Pagamentos e relatórios financeiros**, no canto superior esquerdo.

### 3. Google Play

1. Google Cloud Console → crie (ou use) um projeto → **IAM → Contas de serviço** → criar → **Chaves → JSON**.
2. Play Console → **Usuários e permissões → Convidar** o e-mail da conta de serviço com
   **Ver informações do app e baixar relatórios em massa** e **Ver dados financeiros**.
   A permissão pode levar até 24 h para valer no bucket.
3. **Bucket**: Play Console → **Baixar relatórios → Estatísticas** → copiar o URI do Cloud Storage
   (`gs://pubsite_prod_XXXX/...`). O nome do bucket é a parte `pubsite_prod_XXXX`.

### 4. Secrets do repositório

Em **Settings → Secrets and variables → Actions**:

| Secret | Valor |
|---|---|
| `PAINEL_SENHA` | a senha do painel |
| `ASC_KEY_ID` | Key ID da Apple |
| `ASC_ISSUER_ID` | Issuer ID da Apple |
| `ASC_PRIVATE_KEY` | conteúdo inteiro do `.p8` (com as linhas BEGIN/END) |
| `ASC_VENDOR_NUMBER` | vendor number |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | conteúdo inteiro do JSON da conta de serviço |
| `GPLAY_BUCKET` | `pubsite_prod_XXXX` |
| `GPLAY_PACKAGES` | pacotes separados por vírgula: `br.com.app1,br.com.app2` |

Com o GitHub CLI, os arquivos podem ser enviados sem abrir o conteúdo:

```
gh secret set ASC_PRIVATE_KEY < caminho/da/chave.p8
gh secret set GOOGLE_SERVICE_ACCOUNT_JSON < caminho/da/conta.json
```

### 5. Primeira carga

**Actions → Coleta diária das lojas → Run workflow** com `days_back = 365` para trazer o histórico.
Depois disso, ele roda sozinho todo dia. O link do painel aparece no resumo da execução
(`https://<usuario>.github.io/<repo>/`).

Se a senha mudar, o histórico antigo não abre mais com a nova. Para trocar, apague `data/historico.enc`
e rode de novo com `days_back = 365`.

## Rodar localmente

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # no Mac: .venv/bin/python
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m coletor.demo     # site/index.html com dados fictícios, senha "demo"
python -m http.server 8765 --directory site
```

O painel precisa de `https`, `localhost` ou do arquivo aberto direto no Chrome, porque o navegador só
libera a criptografia (WebCrypto) em contexto seguro.

## O que os números significam (limitações conhecidas)

- **Downloads Apple**: primeiras instalações (tipos `1`, `1F`, `1T`, `F1`, `1E*`). Não inclui atualizações nem re-downloads.
- **Downloads Google**: coluna `Daily User Installs` (ou `Install events`, nos relatórios mais novos) do `installs_*_overview.csv`.
- **Receita Apple**: *proceeds* (líquido para você), na moeda de pagamento.
- **Receita Google**: valor **bruto** cobrado do cliente (`Charged`), na moeda da venda. Reembolsos não são descontados.
  O líquido só sai no relatório de *earnings* mensal, que não é diário.
- Moedas **não são convertidas**: o painel mostra cada moeda separada.
- O app aparece pelo **título** na Apple e pelo **pacote** no Google.
- A Apple publica o relatório de um dia por volta das 05:00 de Brasília do dia seguinte; o Google, com 1 a 2 dias de atraso.
