import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_noticias.feed_collector import NoticiasBrutas  # noqa: E402


@pytest.fixture
def criar_noticia():
    def _criar(link: str, titulo: str = "Título", fonte: str = "OpenAI Blog") -> NoticiasBrutas:
        return NoticiasBrutas(
            titulo=titulo,
            link=link,
            resumo="Resumo da notícia",
            data_publicacao="2026-11-03T10:00:00+00:00",
            fonte=fonte,
        )

    return _criar
