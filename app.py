"""
Sistema de Cotação de Medicamentos - Farmácia
100% gratuito | Login | Histórico | Multi-loja
"""
import streamlit as st
import pandas as pd
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from datetime import datetime
import io
import json

import database as db

# Configuração da página
st.set_page_config(
    page_title="Cotação Farmácia",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializa banco
db.init_db()

# ========== AUTENTICAÇÃO ==========
CONFIG_PATH = Path(__file__).parent / "config.yaml"

def carregar_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)

def verificar_login(username, password):
    """Login simples (sem streamlit-authenticator para evitar dependência extra)"""
    config = carregar_config()
    users = config["credentials"]["usernames"]
    if username not in users:
        return False, None
    import bcrypt
    stored = users[username]["password"].encode()
    if bcrypt.checkpw(password.encode(), stored):
        return True, users[username]["name"]
    return False, None


# ========== ESTILOS ==========
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1F4E79;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #666;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f0f7ff;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #1F4E79;
    }
    .stButton>button {
        border-radius: 8px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
</style>
""", unsafe_allow_html=True)


# ========== LOGIN ==========
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.nome = None

if not st.session_state.autenticado:
    st.markdown('<p class="main-header">💊 Sistema de Cotação de Medicamentos</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Faça login para continuar</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="admin ou comprador")
            password = st.text_input("Senha", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if submitted:
                try:
                    ok, nome = verificar_login(username.strip(), password)
                    if ok:
                        st.session_state.autenticado = True
                        st.session_state.usuario = username.strip()
                        st.session_state.nome = nome
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception as e:
                    # Fallback se bcrypt não estiver disponível
                    if username.strip() in ["admin", "comprador"] and password == "admin123":
                        st.session_state.autenticado = True
                        st.session_state.usuario = username.strip()
                        st.session_state.nome = "Administrador" if username == "admin" else "Comprador"
                        st.rerun()
                    else:
                        st.error(f"Erro no login: {e}")

        st.info("""
        **Usuários padrão:**
        - Usuário: `admin` | Senha: `admin123`
        - Usuário: `comprador` | Senha: `admin123`
        """)
    st.stop()


# ========== APP LOGADO ==========
st.sidebar.markdown(f"### 👤 {st.session_state.nome}")
st.sidebar.caption(f"@{st.session_state.usuario}")

if st.sidebar.button("Sair", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.nome = None
    st.rerun()

st.sidebar.divider()

pagina = st.sidebar.radio(
    "Menu",
    ["🏠 Início", "📋 Nova Cotação", "📜 Histórico", "🏢 Distribuidoras", "💰 Tabelas de Preços", "❓ Ajuda"],
    label_visibility="collapsed"
)

# ============================================================
# PÁGINA: INÍCIO
# ============================================================
if pagina == "🏠 Início":
    st.markdown('<p class="main-header">💊 Sistema de Cotação de Medicamentos</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Compare preços de várias distribuidoras e monte pedidos automaticamente</p>', unsafe_allow_html=True)

    cotacoes = db.listar_cotacoes(10)
    dists = db.listar_distribuidoras()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distribuidoras ativas", len(dists))
    c2.metric("Cotações salvas", len(cotacoes))
    total_itens = sum(c["qtd_itens"] or 0 for c in cotacoes)
    c3.metric("Itens cotados (histórico)", total_itens)
    valor = sum(c["valor_total"] or 0 for c in cotacoes)
    c4.metric("Valor total histórico", f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.divider()
    st.subheader("Últimas cotações")
    if cotacoes:
        for c in cotacoes[:5]:
            with st.expander(f"📌 {c['titulo']} — {c['data_criacao'][:16].replace('T',' ')} | {c['status'].upper()} | R$ {(c['valor_total'] or 0):,.2f}"):
                st.write(f"**Usuário:** {c['usuario']} | **Itens:** {c['qtd_itens']}")
                if c.get("observacao"):
                    st.caption(c["observacao"])
    else:
        st.info("Nenhuma cotação ainda. Vá em **Nova Cotação** para começar.")

# ============================================================
# PÁGINA: NOVA COTAÇÃO
# ============================================================
elif pagina == "📋 Nova Cotação":
    st.markdown('<p class="main-header">📋 Nova Cotação</p>', unsafe_allow_html=True)

    dists = db.listar_distribuidoras()
    if not dists:
        st.warning("Cadastre pelo menos uma distribuidora antes de cotar.")
        st.stop()

    # Inicializa itens da cotação na sessão
    if "itens_cotacao" not in st.session_state:
        st.session_state.itens_cotacao = []

    col_t, col_o = st.columns([2, 2])
    with col_t:
        titulo = st.text_input("Título da cotação", value=f"Cotação {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    with col_o:
        observacao_geral = st.text_input("Observação geral (opcional)")

    st.divider()
    st.subheader("Adicionar item")

    # Busca de preços cadastrados
    with st.form("add_item", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        produto = c1.text_input("Produto / Medicamento *")
        loja = c2.selectbox("Loja", ["1", "2", ""])
        qtd = c3.number_input("Qtd", min_value=0.01, value=1.0, step=1.0)

        obs = st.text_input("Observação do item")

        # Preços manuais por distribuidora
        st.caption("Preços unitários por distribuidora (deixe em branco se não tiver)")
        precos_cols = st.columns(min(len(dists), 6))
        precos_input = {}
        for i, d in enumerate(dists):
            with precos_cols[i % len(precos_cols)]:
                val = st.number_input(
                    d["nome"],
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"preco_{d['id']}"
                )
                if val > 0:
                    precos_input[d["nome"]] = val

        submitted = st.form_submit_button("➕ Adicionar à cotação", type="primary")

        if submitted:
            if not produto.strip():
                st.error("Informe o nome do produto.")
            elif not precos_input:
                st.error("Informe pelo menos um preço.")
            else:
                melhor_dist = min(precos_input, key=precos_input.get)
                melhor_preco = precos_input[melhor_dist]
                total = qtd * melhor_preco
                st.session_state.itens_cotacao.append({
                    "produto": produto.strip(),
                    "loja": loja,
                    "observacao": obs,
                    "quantidade": qtd,
                    "melhor_preco": melhor_preco,
                    "melhor_distribuidora": melhor_dist,
                    "total": total,
                    "precos": precos_input.copy()
                })
                st.success(f"Adicionado: {produto} → {melhor_dist} R$ {melhor_preco:.2f}")

    # Lista de itens
    st.divider()
    st.subheader(f"Itens da cotação ({len(st.session_state.itens_cotacao)})")

    if st.session_state.itens_cotacao:
        df_itens = pd.DataFrame(st.session_state.itens_cotacao)
        df_show = df_itens[["produto", "loja", "quantidade", "melhor_preco", "melhor_distribuidora", "total"]].copy()
        df_show.columns = ["Produto", "Loja", "Qtd", "Melhor Preço", "Distribuidora", "Total"]
        df_show["Melhor Preço"] = df_show["Melhor Preço"].map(lambda x: f"R$ {x:,.2f}")
        df_show["Total"] = df_show["Total"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        total_geral = sum(i["total"] for i in st.session_state.itens_cotacao)
        st.metric("Total da cotação", f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Pedidos por distribuidora
        st.subheader("📦 Pedidos por Distribuidora")
        grupos = {}
        for item in st.session_state.itens_cotacao:
            d = item["melhor_distribuidora"]
            if d not in grupos:
                grupos[d] = []
            grupos[d].append(item)

        for dist_nome, itens in grupos.items():
            valor = sum(i["total"] for i in itens)
            with st.expander(f"**{dist_nome}** — {len(itens)} item(ns) — R$ {valor:,.2f}"):
                df_p = pd.DataFrame(itens)[["produto", "loja", "quantidade", "melhor_preco", "total"]]
                df_p.columns = ["Produto", "Loja", "Qtd", "Preço", "Total"]
                st.dataframe(df_p, use_container_width=True, hide_index=True)

        # Botões de ação
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💾 Salvar cotação no histórico", type="primary", use_container_width=True):
                cot_id = db.criar_cotacao(titulo, st.session_state.usuario, observacao_geral)
                for item in st.session_state.itens_cotacao:
                    db.adicionar_item_cotacao(
                        cot_id,
                        item["produto"],
                        item["loja"],
                        item["observacao"],
                        item["quantidade"],
                        item["melhor_preco"],
                        item["melhor_distribuidora"],
                        item["total"],
                        item["precos"]
                    )
                st.session_state.itens_cotacao = []
                st.success(f"Cotação #{cot_id} salva com sucesso!")
                st.balloons()
                st.rerun()
        with c2:
            # Exportar Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_export = pd.DataFrame(st.session_state.itens_cotacao)
                df_export.to_excel(writer, sheet_name="Itens", index=False)
                for dist_nome, itens in grupos.items():
                    pd.DataFrame(itens).to_excel(writer, sheet_name=dist_nome[:31], index=False)
            st.download_button(
                "📥 Baixar Excel",
                data=output.getvalue(),
                file_name=f"cotacao_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with c3:
            if st.button("🗑️ Limpar cotação", use_container_width=True):
                st.session_state.itens_cotacao = []
                st.rerun()
    else:
        st.info("Nenhum item adicionado ainda. Preencha o formulário acima.")

# ============================================================
# PÁGINA: HISTÓRICO
# ============================================================
elif pagina == "📜 Histórico":
    st.markdown('<p class="main-header">📜 Histórico de Cotações</p>', unsafe_allow_html=True)

    cotacoes = db.listar_cotacoes(100)
    if not cotacoes:
        st.info("Nenhuma cotação salva ainda.")
    else:
        for c in cotacoes:
            data_fmt = c["data_criacao"][:16].replace("T", " ")
            with st.expander(f"#{c['id']} — {c['titulo']} | {data_fmt} | {c['status'].upper()} | R$ {(c['valor_total'] or 0):,.2f}"):
                st.write(f"**Usuário:** {c['usuario']} | **Itens:** {c['qtd_itens']}")
                if c.get("observacao"):
                    st.caption(c["observacao"])

                cotacao, itens = db.obter_cotacao(c["id"])
                if itens:
                    df = pd.DataFrame(itens)
                    df_show = df[["produto", "loja", "quantidade", "melhor_preco", "melhor_distribuidora", "total"]].copy()
                    df_show.columns = ["Produto", "Loja", "Qtd", "Preço", "Distribuidora", "Total"]
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

                    # Pedidos por dist
                    grupos = {}
                    for item in itens:
                        d = item["melhor_distribuidora"] or "N/A"
                        grupos.setdefault(d, []).append(item)
                    st.markdown("**Pedidos por distribuidora:**")
                    for dn, its in grupos.items():
                        valor = sum(i["total"] or 0 for i in its)
                        st.write(f"- **{dn}**: {len(its)} item(ns) — R$ {valor:,.2f}")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Marcar como finalizada", key=f"fin_{c['id']}"):
                        db.finalizar_cotacao(c["id"])
                        st.rerun()
                with c2:
                    if st.button("🗑️ Excluir", key=f"del_{c['id']}"):
                        db.excluir_cotacao(c["id"])
                        st.rerun()

# ============================================================
# PÁGINA: DISTRIBUIDORAS
# ============================================================
elif pagina == "🏢 Distribuidoras":
    st.markdown('<p class="main-header">🏢 Distribuidoras</p>', unsafe_allow_html=True)

    dists = db.listar_distribuidoras(apenas_ativas=False)

    st.subheader("Cadastradas")
    if dists:
        for d in dists:
            status = "✅ Ativa" if d["ativo"] else "❌ Inativa"
            with st.expander(f"{d['nome']} — {status}"):
                st.write(f"Contato: {d.get('contato') or '-'} | Tel: {d.get('telefone') or '-'} | Email: {d.get('email') or '-'}")

                if d["ativo"]:
                    # Formulário de edição
                    with st.form(key=f"edit_dist_{d['id']}"):
                        st.markdown("**Editar dados**")
                        novo_nome = st.text_input("Nome *", value=d["nome"], key=f"nome_{d['id']}")
                        c1, c2 = st.columns(2)
                        novo_contato = c1.text_input("Contato", value=d.get("contato") or "", key=f"contato_{d['id']}")
                        novo_telefone = c2.text_input("Telefone", value=d.get("telefone") or "", key=f"tel_{d['id']}")
                        novo_email = st.text_input("E-mail", value=d.get("email") or "", key=f"email_{d['id']}")

                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            salvar = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
                        with col_btn2:
                            desativar = st.form_submit_button("Desativar", use_container_width=True)

                        if salvar:
                            if novo_nome.strip():
                                ok, msg = db.editar_distribuidora(
                                    d["id"], novo_nome, novo_contato, novo_telefone, novo_email
                                )
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.error("O nome não pode ficar em branco.")

                        if desativar:
                            db.remover_distribuidora(d["id"])
                            st.rerun()
    else:
        st.info("Nenhuma distribuidora cadastrada.")

    st.divider()
    st.subheader("Adicionar nova")
    with st.form("nova_dist"):
        nome = st.text_input("Nome da distribuidora *")
        c1, c2 = st.columns(2)
        contato = c1.text_input("Contato")
        telefone = c2.text_input("Telefone")
        email = st.text_input("E-mail")
        if st.form_submit_button("Adicionar", type="primary"):
            if nome.strip():
                ok, msg = db.adicionar_distribuidora(nome, contato, telefone, email)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Informe o nome.")

# ============================================================
# PÁGINA: TABELAS DE PREÇOS
# ============================================================
elif pagina == "💰 Tabelas de Preços":
    st.markdown('<p class="main-header">💰 Tabelas de Preços</p>', unsafe_allow_html=True)
    st.caption("Importe a tabela de cada distribuidora (Excel/CSV com colunas: produto, preco). Opcional: codigo, apresentacao.")

    dists = db.listar_distribuidoras()
    if not dists:
        st.warning("Cadastre distribuidoras primeiro.")
        st.stop()

    dist_sel = st.selectbox("Selecione a distribuidora", options=dists, format_func=lambda x: x["nome"])

    uploaded = st.file_uploader("Arquivo Excel ou CSV", type=["xlsx", "xls", "csv"])

    if uploaded and dist_sel:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            # Normaliza nomes de colunas
            df.columns = [str(c).strip().lower() for c in df.columns]
            # Tenta mapear colunas comuns
            rename_map = {}
            for col in df.columns:
                if col in ["produto", "medicamento", "nome", "descrição", "descricao", "item"]:
                    rename_map[col] = "produto"
                elif col in ["preco", "preço", "valor", "price", "preço unitário", "preco unitario"]:
                    rename_map[col] = "preco"
                elif col in ["codigo", "código", "ean", "cod", "sku"]:
                    rename_map[col] = "codigo"
                elif col in ["apresentacao", "apresentação", "embalagem"]:
                    rename_map[col] = "apresentacao"
            df = df.rename(columns=rename_map)

            if "produto" not in df.columns or "preco" not in df.columns:
                st.error("O arquivo precisa ter colunas 'produto' e 'preco' (ou equivalentes).")
                st.write("Colunas encontradas:", list(df.columns))
            else:
                st.write(f"Prévia ({len(df)} linhas):")
                st.dataframe(df.head(10), use_container_width=True)
                if st.button("Importar / Substituir tabela desta distribuidora", type="primary"):
                    count = db.importar_precos(dist_sel["id"], df)
                    st.success(f"{count} preços importados para **{dist_sel['nome']}**!")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.divider()
    st.subheader("Preços cadastrados (amostra)")
    todos = db.listar_todos_precos()
    if todos:
        df_p = pd.DataFrame(todos)[["distribuidora", "produto", "preco", "data_tabela"]]
        st.dataframe(df_p.head(100), use_container_width=True, hide_index=True)
        st.caption(f"Total de registros: {len(todos)}")
    else:
        st.info("Nenhum preço importado ainda. Você também pode digitar os preços manualmente na Nova Cotação.")

# ============================================================
# PÁGINA: AJUDA
# ============================================================
elif pagina == "❓ Ajuda":
    st.markdown('<p class="main-header">❓ Como usar o sistema</p>', unsafe_allow_html=True)

    st.markdown("""
### Fluxo básico

1. **Distribuidoras** → Cadastre as distribuidoras que você trabalha  
2. **Tabelas de Preços** (opcional) → Importe a tabela de preços de cada uma (Excel/CSV)  
3. **Nova Cotação** →  
   - Digite o produto, escolha a Loja (1 ou 2), quantidade  
   - Informe o preço de cada distribuidora (ou deixe em branco se não tiver)  
   - O sistema escolhe automaticamente o **mais barato**  
   - Adicione quantos itens quiser  
4. Veja os **pedidos já separados por distribuidora**  
5. **Salve no histórico** ou baixe em Excel  

### Login padrão
| Usuário    | Senha     |
|------------|-----------|
| admin      | admin123  |
| comprador  | admin123  |

> **Importante:** Troque as senhas depois (edite o arquivo `config.yaml`).

### Dados e nuvem
- Os dados ficam salvos no arquivo `cotacao.db` (SQLite).  
- No Streamlit Cloud (plano gratuito) o banco **pode ser reiniciado** quando o app dormir.  
- **Recomendação:** sempre baixe o Excel das cotações importantes e use o Histórico como apoio.

### Separação por Loja
Na cotação use o campo **Loja** (1 ou 2) para indicar para qual das suas farmácias é o item.  
Isso aparece nos pedidos e no histórico.
    """)
EOF