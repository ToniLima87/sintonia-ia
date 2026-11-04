import asyncio
from pathlib import Path

from agent_noticias.canvas_export import exportar_canvas_noticias
from agent_noticias.deduplication_service import (
    filtrar_noticias_inéditas,
    registrar_noticias_processadas,
)
from agent_noticias.feed_collector import extrair_noticias
from agent_noticias.frontend_export import exportar_dados_frontend
from agent_noticias.script_agent import gerar_roteiro_podcast
from agent_noticias.telegram_service import enviar_episodio, telegram_configurado
from agent_noticias.tts_service import processar_roteiro_para_audio

PROJECT_ROOT = Path(__file__).resolve().parent
DADOS_DIR = PROJECT_ROOT / "dados"
PODCAST_PATH = PROJECT_ROOT / "podcast_ia_hoje.mp3"

async def executar_pipeline_agente():
    print("🚀 === INICIANDO AGENTE AUTÔNOMO DE PODCAST DE IA ===")
    
    # 1. Coleta
    noticias_brutas = extrair_noticias(limite_por_feed=5)
    
    # 2. Deduplicação
    noticias_ineditas = filtrar_noticias_inéditas(noticias_brutas)
    if not noticias_ineditas:
        print("💤 Nenhuma notícia nova encontrada hoje. Finalizando execução.")
        return

    # 3. Roteirização com Gemini (em pt-BR)
    roteiro = gerar_roteiro_podcast(noticias_ineditas)
    
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    roteiro_path = DADOS_DIR / "roteiro_hoje.txt"
    roteiro_path.write_text(roteiro, encoding="utf-8")
        
    # 4. Geração do Áudio Final
    await processar_roteiro_para_audio(roteiro, str(PODCAST_PATH))
    
    # 5. Registra notícias como processadas no DB
    registrar_noticias_processadas(noticias_ineditas)

    noticias_episodio = [
        {
            "fonte": n.fonte,
            "titulo": n.titulo,
            "link": n.link,
            "resumo": n.resumo,
            "data_publicacao": n.data_publicacao,
        }
        for n in noticias_ineditas
    ]

    # 6. Atualiza o canvas com links e fontes
    exportar_canvas_noticias()

    # 7. Atualiza os dados da landing page
    exportar_dados_frontend(noticias_episodio, roteiro, PODCAST_PATH)

    # 8. Envia o episódio para o Telegram
    if telegram_configurado():
        try:
            enviar_episodio(PODCAST_PATH, noticias_episodio)
        except (RuntimeError, OSError) as exc:
            print(f"⚠️ Não foi possível enviar ao Telegram: {exc}")
    else:
        print("Telegram não configurado (TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env); envio pulado.")
    
    print("✅ Pipeline autônomo concluído!")

if __name__ == "__main__":
    asyncio.run(executar_pipeline_agente())
