from datetime import datetime

import agendador


def test_proxima_execucao_ainda_hoje(monkeypatch):
    monkeypatch.setattr(agendador, "HORARIO_EXECUCAO", "07:00")

    assert agendador.proxima_execucao(datetime(2026, 11, 4, 6, 59)) == datetime(2026, 11, 4, 7, 0)


def test_proxima_execucao_passa_para_amanha(monkeypatch):
    monkeypatch.setattr(agendador, "HORARIO_EXECUCAO", "07:00")

    assert agendador.proxima_execucao(datetime(2026, 11, 4, 7, 0)) == datetime(2026, 11, 5, 7, 0)


def test_falha_no_pipeline_nao_derruba_o_agendador(monkeypatch, capsys):
    async def pipeline_com_erro():
        raise RuntimeError("402 sem crédito")

    monkeypatch.setattr(agendador, "executar_pipeline_agente", pipeline_com_erro)

    agendador.rodar_pipeline()

    assert "402 sem crédito" in capsys.readouterr().err
