from agent_noticias import frontend_export
from agent_noticias.tts_service import VOZ_BEATRIZ, VOZ_LUCAS


def test_resumo_remove_html_e_entidades():
    assert frontend_export._limpar_resumo("<p>IA &amp; <b>robôs</b></p>") == "IA & robôs"


def test_resumo_longo_e_cortado_em_palavra_inteira():
    resumo = frontend_export._limpar_resumo("palavra " * 100)

    assert len(resumo) <= frontend_export.LIMITE_RESUMO + 1
    assert resumo.endswith("palavra…")


def test_resumo_vazio_ou_ausente():
    assert frontend_export._limpar_resumo(None) == ""


def test_falas_do_roteiro_reconhecem_os_dois_apresentadores():
    roteiro = "Título do episódio\nLucas: Olá!\n\nBeatriz:   Oi, Lucas.\nNarrador: ignorado"

    assert frontend_export._falas_do_roteiro(roteiro) == [
        {"apresentador": "Lucas", "voz": VOZ_LUCAS, "fala": "Olá!"},
        {"apresentador": "Beatriz", "voz": VOZ_BEATRIZ, "fala": "Oi, Lucas."},
    ]


def test_noticias_ficam_no_original_quando_a_traducao_falha(monkeypatch):
    def traducao_indisponivel(_):
        raise RuntimeError("sem crédito")

    monkeypatch.setattr(frontend_export, "traduzir_noticias", traducao_indisponivel)

    noticias = frontend_export._noticias_em_ptbr(
        [{"fonte": "OpenAI Blog", "titulo": "New model", "link": "https://a/1", "resumo": "<p>Text</p>"}]
    )

    assert noticias[0]["titulo"] == noticias[0]["titulo_original"] == "New model"
    assert noticias[0]["resumo"] == "Text"
