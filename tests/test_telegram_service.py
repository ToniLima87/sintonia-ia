import pytest

from agent_noticias import telegram_service

TOKEN_VALIDO = "123456789:" + "A" * 35


@pytest.mark.parametrize("valor", [TOKEN_VALIDO, f'"{TOKEN_VALIDO}"', f"bot{TOKEN_VALIDO}", f"  {TOKEN_VALIDO}\n"])
def test_token_e_normalizado(monkeypatch, valor):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", valor)

    assert telegram_service._token_bot() == TOKEN_VALIDO


def test_token_invalido_nao_aparece_na_mensagem_de_erro(monkeypatch):
    token_quebrado = "123456789:segredo com espaco"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token_quebrado)

    with pytest.raises(RuntimeError) as erro:
        telegram_service._token_bot()

    assert "segredo" not in str(erro.value)
    assert "espaços" in str(erro.value)


def test_telegram_configurado_exige_token_e_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN_VALIDO)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert telegram_service.telegram_configurado() is False

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    assert telegram_service.telegram_configurado() is True


def test_mensagem_de_noticias_escapa_html():
    mensagens = telegram_service._montar_mensagens_noticias(
        [{"fonte": "Lab <IA>", "titulo": "GPT & cia", "link": 'https://a.com/?q="x"'}]
    )

    assert len(mensagens) == 1
    assert "Lab &lt;IA&gt;" in mensagens[0]
    assert "GPT &amp; cia" in mensagens[0]
    assert 'href="https://a.com/?q=&quot;x&quot;"' in mensagens[0]


def test_lista_grande_e_dividida_no_limite_do_telegram():
    noticias = [{"fonte": "Fonte", "titulo": "T" * 150, "link": f"https://a.com/{i}"} for i in range(60)]

    mensagens = telegram_service._montar_mensagens_noticias(noticias)

    assert len(mensagens) > 1
    assert all(len(m) <= telegram_service.LIMITE_MENSAGEM for m in mensagens)
    assert sum(m.count("<a href") for m in mensagens) == 60
