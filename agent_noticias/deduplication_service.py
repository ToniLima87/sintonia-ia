import sqlite3
from pathlib import Path
from typing import List

from .feed_collector import NoticiasBrutas

DB_NAME = Path(__file__).resolve().parent.parent / "dados" / "noticias_historico.db"

def inicializar_banco():
    DB_NAME.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noticias_processadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE,
            titulo TEXT,
            fonte TEXT,
            data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    colunas = {linha[1] for linha in cursor.execute("PRAGMA table_info(noticias_processadas)")}
    if "fonte" not in colunas:
        cursor.execute("ALTER TABLE noticias_processadas ADD COLUMN fonte TEXT")
    conn.commit()
    conn.close()

def filtrar_noticias_inéditas(noticias: List[NoticiasBrutas]) -> List[NoticiasBrutas]:
    inicializar_banco()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    noticias_novas = []
    for noticia in noticias:
        cursor.execute("SELECT 1 FROM noticias_processadas WHERE link = ?", (noticia.link,))
        if not cursor.fetchone():
            noticias_novas.append(noticia)

    conn.close()
    print(f"🧹 Filtragem de duplicadas: {len(noticias_novas)} de {len(noticias)} são inéditas.")
    return noticias_novas

def registrar_noticias_processadas(noticias: List[NoticiasBrutas]):
    inicializar_banco()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for noticia in noticias:
        try:
            cursor.execute(
                "INSERT INTO noticias_processadas (link, titulo, fonte) VALUES (?, ?, ?)",
                (noticia.link, noticia.titulo, noticia.fonte),
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()

def listar_noticias_processadas() -> List[dict]:
    inicializar_banco()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        "SELECT id, data_processamento, fonte, titulo, link "
        "FROM noticias_processadas ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(linha) for linha in linhas]

def listar_ultimo_lote() -> List[dict]:
    registros = listar_noticias_processadas()
    if not registros:
        return []
    ultimo_dia = registros[-1]["data_processamento"][:10]
    return [r for r in registros if r["data_processamento"].startswith(ultimo_dia)]
