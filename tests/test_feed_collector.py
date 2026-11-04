from types import SimpleNamespace

from agent_noticias import feed_collector


def _feed(entradas, bozo=False):
    return SimpleNamespace(entries=entradas, bozo=bozo)


def test_respeita_limite_e_normaliza_campos(monkeypatch):
    entradas = [
        {
            "title": f"Notícia {i}",
            "link": f"https://exemplo.com/{i}",
            "summary": "<p>Resumo</p>",
            "published_parsed": (2026, 11, 3, 10, 30, 0, 0, 0, 0),
        }
        for i in range(10)
    ]
    monkeypatch.setattr(feed_collector, "FEEDS_CONFIG", [{"fonte": "Fonte A", "url": "https://a/rss"}])
    monkeypatch.setattr(feed_collector.feedparser, "parse", lambda url: _feed(entradas))

    noticias = feed_collector.extrair_noticias(limite_por_feed=3)

    assert len(noticias) == 3
    assert noticias[0].fonte == "Fonte A"
    assert noticias[0].data_publicacao == "2026-11-03T10:30:00+00:00"


def test_feed_fora_do_ar_e_ignorado(monkeypatch):
    feeds = [{"fonte": "Quebrado", "url": "https://quebrado"}, {"fonte": "Ok", "url": "https://ok"}]
    respostas = {
        "https://quebrado": _feed([], bozo=True),
        "https://ok": _feed([{"title": "Ok", "link": "https://ok/1"}]),
    }
    monkeypatch.setattr(feed_collector, "FEEDS_CONFIG", feeds)
    monkeypatch.setattr(feed_collector.feedparser, "parse", lambda url: respostas[url])

    noticias = feed_collector.extrair_noticias()

    assert [n.fonte for n in noticias] == ["Ok"]
    assert noticias[0].resumo == ""
