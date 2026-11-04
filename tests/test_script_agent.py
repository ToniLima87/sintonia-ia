from types import SimpleNamespace

import pytest

from agent_noticias import script_agent
from agent_noticias.script_agent import NoticiaTraduzida


def _cliente_falso(traducoes):
    resposta = SimpleNamespace(parsed=traducoes)
    modelos = SimpleNamespace(generate_content=lambda **kwargs: resposta)
    return SimpleNamespace(models=modelos)


def test_traducao_preserva_a_ordem(monkeypatch):
    traducoes = [NoticiaTraduzida(titulo="Novo modelo", resumo="Resumo")]
    monkeypatch.setattr(script_agent, "_cliente_gemini", lambda: _cliente_falso(traducoes))

    resultado = script_agent.traduzir_noticias([{"titulo": "New model", "resumo": "Summary"}])

    assert resultado == traducoes


def test_traducao_incompleta_e_rejeitada(monkeypatch):
    monkeypatch.setattr(script_agent, "_cliente_gemini", lambda: _cliente_falso([]))

    with pytest.raises(RuntimeError):
        script_agent.traduzir_noticias([{"titulo": "A"}, {"titulo": "B"}])


def test_lista_vazia_nao_chama_o_gemini(monkeypatch):
    def nao_deveria_ser_chamado():
        raise AssertionError("o Gemini não deveria ser chamado")

    monkeypatch.setattr(script_agent, "_cliente_gemini", nao_deveria_ser_chamado)

    assert script_agent.traduzir_noticias([]) == []


def test_sem_chave_do_gemini_gera_erro_claro(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        script_agent._cliente_gemini()
