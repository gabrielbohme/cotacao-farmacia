"""
Banco de dados SQLite para o Sistema de Cotação de Medicamentos
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent / "cotacao.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se não existirem"""
    conn = get_connection()
    cur = conn.cursor()

    # Distribuidoras
    cur.execute("""
        CREATE TABLE IF NOT EXISTS distribuidoras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            contato TEXT,
            telefone TEXT,
            email TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT
        )
    """)

    # Tabelas de preços (cada linha = um medicamento de uma distribuidora)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distribuidora_id INTEGER NOT NULL,
            codigo TEXT,
            produto TEXT NOT NULL,
            apresentacao TEXT,
            preco REAL NOT NULL,
            data_tabela TEXT,
            FOREIGN KEY (distribuidora_id) REFERENCES distribuidoras(id)
        )
    """)

    # Cotações (cabeçalho)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            usuario TEXT,
            data_criacao TEXT,
            status TEXT DEFAULT 'aberta',
            observacao TEXT
        )
    """)

    # Itens da cotação
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao_id INTEGER NOT NULL,
            produto TEXT NOT NULL,
            loja TEXT,
            observacao TEXT,
            quantidade REAL DEFAULT 1,
            melhor_preco REAL,
            melhor_distribuidora TEXT,
            total REAL,
            precos_json TEXT,
            FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id)
        )
    """)

    # Distribuidoras padrão
    cur.execute("SELECT COUNT(*) FROM distribuidoras")
    if cur.fetchone()[0] == 0:
        padrao = [
            ("STOCK", "", "", ""),
            ("ORIENTE", "", "", ""),
            ("E.M.S", "", "", ""),
            ("farmix", "", "", ""),
            ("ECO", "", "", ""),
        ]
        agora = datetime.now().isoformat()
        for nome, contato, tel, email in padrao:
            cur.execute(
                "INSERT INTO distribuidoras (nome, contato, telefone, email, criado_em) VALUES (?,?,?,?,?)",
                (nome, contato, tel, email, agora)
            )

    conn.commit()
    conn.close()


# ========== DISTRIBUIDORAS ==========

def listar_distribuidoras(apenas_ativas=True):
    conn = get_connection()
    if apenas_ativas:
        rows = conn.execute("SELECT * FROM distribuidoras WHERE ativo=1 ORDER BY nome").fetchall()
    else:
        rows = conn.execute("SELECT * FROM distribuidoras ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def adicionar_distribuidora(nome, contato="", telefone="", email=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO distribuidoras (nome, contato, telefone, email, criado_em) VALUES (?,?,?,?,?)",
            (nome.strip(), contato, telefone, email, datetime.now().isoformat())
        )
        conn.commit()
        return True, "Distribuidora adicionada!"
    except sqlite3.IntegrityError:
        return False, "Já existe uma distribuidora com esse nome."
    finally:
        conn.close()


def remover_distribuidora(dist_id):
    conn = get_connection()
    conn.execute("UPDATE distribuidoras SET ativo=0 WHERE id=?", (dist_id,))
    conn.commit()
    conn.close()


def editar_distribuidora(dist_id, nome, contato="", telefone="", email=""):
    """Edita nome e dados de contato de uma distribuidora.
    Também atualiza o nome salvo nos itens de cotação (melhor_distribuidora).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Pega o nome antigo para atualizar o histórico
        row = cur.execute("SELECT nome FROM distribuidoras WHERE id=?", (dist_id,)).fetchone()
        if not row:
            return False, "Distribuidora não encontrada."
        nome_antigo = row["nome"]
        nome_novo = nome.strip()

        cur.execute(
            "UPDATE distribuidoras SET nome=?, contato=?, telefone=?, email=? WHERE id=?",
            (nome_novo, contato, telefone, email, dist_id)
        )
        # Atualiza o nome nos itens de cotação já salvos
        if nome_antigo != nome_novo:
            cur.execute(
                "UPDATE cotacao_itens SET melhor_distribuidora=? WHERE melhor_distribuidora=?",
                (nome_novo, nome_antigo)
            )
        conn.commit()
        return True, "Distribuidora atualizada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Já existe outra distribuidora com esse nome."
    finally:
        conn.close()


# ========== PREÇOS ==========

def limpar_precos_distribuidora(dist_id):
    conn = get_connection()
    conn.execute("DELETE FROM precos WHERE distribuidora_id=?", (dist_id,))
    conn.commit()
    conn.close()


def importar_precos(dist_id, df: pd.DataFrame):
    """
    df deve ter colunas: produto, preco (obrigatórias)
    opcionais: codigo, apresentacao
    """
    conn = get_connection()
    cur = conn.cursor()
    # limpa preços antigos dessa distribuidora
    cur.execute("DELETE FROM precos WHERE distribuidora_id=?", (dist_id,))

    data_tabela = datetime.now().strftime("%Y-%m-%d")
    count = 0
    for _, row in df.iterrows():
        produto = str(row.get("produto", "")).strip()
        if not produto:
            continue
        try:
            preco = float(row.get("preco", 0))
        except (ValueError, TypeError):
            continue
        if preco <= 0:
            continue
        codigo = str(row.get("codigo", "") or "")
        apresentacao = str(row.get("apresentacao", "") or "")
        cur.execute(
            "INSERT INTO precos (distribuidora_id, codigo, produto, apresentacao, preco, data_tabela) VALUES (?,?,?,?,?,?)",
            (dist_id, codigo, produto, apresentacao, preco, data_tabela)
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def buscar_precos_produto(produto: str):
    """Retorna dict {nome_distribuidora: preco} para um produto (busca parcial)"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT d.nome, p.preco, p.produto
        FROM precos p
        JOIN distribuidoras d ON d.id = p.distribuidora_id
        WHERE d.ativo=1 AND lower(p.produto) LIKE lower(?)
        ORDER BY p.preco
    """, (f"%{produto}%",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_todos_precos():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, d.nome as distribuidora
        FROM precos p
        JOIN distribuidoras d ON d.id = p.distribuidora_id
        WHERE d.ativo=1
        ORDER BY d.nome, p.produto
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== COTAÇÕES ==========

def criar_cotacao(titulo, usuario, observacao=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cotacoes (titulo, usuario, data_criacao, status, observacao) VALUES (?,?,?,?,?)",
        (titulo, usuario, datetime.now().isoformat(), "aberta", observacao)
    )
    cotacao_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cotacao_id


def adicionar_item_cotacao(cotacao_id, produto, loja, observacao, quantidade, melhor_preco, melhor_dist, total, precos_dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO cotacao_itens
        (cotacao_id, produto, loja, observacao, quantidade, melhor_preco, melhor_distribuidora, total, precos_json)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        cotacao_id, produto, loja, observacao, quantidade,
        melhor_preco, melhor_dist, total, json.dumps(precos_dict, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()


def listar_cotacoes(limit=50):
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, COUNT(i.id) as qtd_itens, COALESCE(SUM(i.total),0) as valor_total
        FROM cotacoes c
        LEFT JOIN cotacao_itens i ON i.cotacao_id = c.id
        GROUP BY c.id
        ORDER BY c.data_criacao DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obter_cotacao(cotacao_id):
    conn = get_connection()
    cotacao = conn.execute("SELECT * FROM cotacoes WHERE id=?", (cotacao_id,)).fetchone()
    itens = conn.execute("SELECT * FROM cotacao_itens WHERE cotacao_id=? ORDER BY id", (cotacao_id,)).fetchall()
    conn.close()
    if not cotacao:
        return None, []
    return dict(cotacao), [dict(i) for i in itens]


def finalizar_cotacao(cotacao_id):
    conn = get_connection()
    conn.execute("UPDATE cotacoes SET status='finalizada' WHERE id=?", (cotacao_id,))
    conn.commit()
    conn.close()


def excluir_cotacao(cotacao_id):
    conn = get_connection()
    conn.execute("DELETE FROM cotacao_itens WHERE cotacao_id=?", (cotacao_id,))
    conn.execute("DELETE FROM cotacoes WHERE id=?", (cotacao_id,))
    conn.commit()
    conn.close()
