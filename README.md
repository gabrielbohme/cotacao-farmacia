# 💊 Sistema de Cotação de Medicamentos – Farmácia

Sistema em nuvem **100% gratuito** para cotação de medicamentos entre várias distribuidoras.

## Funcionalidades

- Login com 2 usuários
- Cadastro ilimitado de distribuidoras
- Importação de tabelas de preços (Excel/CSV)
- Cotação rápida (melhor preço automático)
- Separação por Loja 1 e Loja 2
- Pedidos montados automaticamente por distribuidora
- Histórico de cotações
- Exportação para Excel

---

## Como colocar no ar (Streamlit Cloud – grátis)

### 1. Crie uma conta no GitHub (se ainda não tiver)
https://github.com

### 2. Crie um repositório novo
- Nome sugerido: `cotacao-farmacia`
- Deixe **público** (necessário para o plano gratuito do Streamlit)

### 3. Envie os arquivos deste projeto para o repositório
Arquivos necessários:
- `app.py`
- `database.py`
- `config.yaml`
- `requirements.txt`
- `README.md`

### 4. Acesse o Streamlit Community Cloud
https://share.streamlit.io

- Faça login com a conta do GitHub
- Clique em **New app**
- Selecione o repositório `cotacao-farmacia`
- Branch: `main`
- Main file path: `app.py`
- Clique em **Deploy**

Pronto! Em 1–2 minutos o sistema estará online com um link tipo:
`https://cotacao-farmacia-seuusuario.streamlit.app`

---

## Login padrão

| Usuário    | Senha     |
|------------|-----------|
| admin      | admin123  |
| comprador  | admin123  |

**Troque as senhas** depois de subir (edite o `config.yaml` e faça commit novamente).

---

## Rodar localmente (opcional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Observação importante sobre o plano gratuito

No Streamlit Cloud gratuito o aplicativo “dorme” após um tempo sem uso e o banco SQLite pode ser reiniciado.  

**Solução prática:** sempre baixe o Excel das cotações importantes.  
O histórico serve como apoio rápido do dia a dia.
