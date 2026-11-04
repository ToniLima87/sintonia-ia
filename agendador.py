"""Mantém o agente no ar e executa o pipeline todos os dias no horário configurado.

Usado como processo principal do container Docker, no lugar do Agendador de Tarefas do Windows.
"""
import asyncio
import os
import time
import traceback
from datetime import datetime, timedelta

from main import executar_pipeline_agente

HORARIO_EXECUCAO = os.getenv("HORARIO_EXECUCAO", "07:00")
RODAR_AO_INICIAR = os.getenv("RODAR_AO_INICIAR", "false").lower() == "true"


def proxima_execucao(agora: datetime) -> datetime:
    hora, minuto = map(int, HORARIO_EXECUCAO.split(":"))
    alvo = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return alvo if alvo > agora else alvo + timedelta(days=1)


def rodar_pipeline() -> None:
    print(f"\n===== {datetime.now():%d/%m/%Y %H:%M:%S} =====", flush=True)
    try:
        asyncio.run(executar_pipeline_agente())
    except Exception:
        # Uma falha (ex.: Gemini sem crédito) não pode derrubar o agendador dos próximos dias.
        traceback.print_exc()


def main() -> None:
    print(f"⏰ Agendador ativo: episódio diário às {HORARIO_EXECUCAO} ({os.getenv('TZ', 'UTC')}).", flush=True)
    if RODAR_AO_INICIAR:
        rodar_pipeline()

    while True:
        alvo = proxima_execucao(datetime.now())
        print(f"Próxima execução: {alvo:%d/%m/%Y %H:%M}", flush=True)
        while (restante := (alvo - datetime.now()).total_seconds()) > 0:
            time.sleep(min(restante, 600))
        rodar_pipeline()


if __name__ == "__main__":
    main()
