import pytest

from agent_noticias import deduplication_service as dedup


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "DB_NAME", tmp_path / "dados" / "historico.db")


def test_noticias_novas_passam_no_filtro(criar_noticia):
    noticias = [criar_noticia("https://a.com/1"), criar_noticia("https://a.com/2")]

    assert dedup.filtrar_noticias_inéditas(noticias) == noticias


def test_noticias_registradas_nao_se_repetem(criar_noticia):
    antiga = criar_noticia("https://a.com/antiga")
    nova = criar_noticia("https://a.com/nova")
    dedup.registrar_noticias_processadas([antiga])

    assert dedup.filtrar_noticias_inéditas([antiga, nova]) == [nova]


def test_registrar_o_mesmo_link_duas_vezes_nao_duplica(criar_noticia):
    noticia = criar_noticia("https://a.com/1")
    dedup.registrar_noticias_processadas([noticia])
    dedup.registrar_noticias_processadas([noticia])

    assert len(dedup.listar_noticias_processadas()) == 1


def test_historico_guarda_fonte_e_titulo(criar_noticia):
    dedup.registrar_noticias_processadas([criar_noticia("https://a.com/1", "Novo modelo", "Google DeepMind")])

    registro = dedup.listar_noticias_processadas()[0]
    assert (registro["fonte"], registro["titulo"], registro["link"]) == (
        "Google DeepMind",
        "Novo modelo",
        "https://a.com/1",
    )


def test_ultimo_lote_vazio_sem_historico():
    assert dedup.listar_ultimo_lote() == []
