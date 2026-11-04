from agent_noticias.deduplication_service import DB_NAME, listar_noticias_processadas


def mostrar_noticias_processadas() -> None:
    linhas = listar_noticias_processadas()

    dia_atual = None
    for linha in linhas:
        dia = linha["data_processamento"][:10]
        if dia != dia_atual:
            dia_atual = dia
            print(f"\n=== Processadas em {dia} (UTC) ===")
        print(f"{linha['id']:>4}  [{linha['fonte'] or 'sem fonte'}] {linha['titulo']}")
        print(f"      {linha['link']}")

    print(f"\nTotal: {len(linhas)} notícias em {DB_NAME}")


if __name__ == "__main__":
    mostrar_noticias_processadas()
