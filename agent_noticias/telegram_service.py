import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv

from .deduplication_service import listar_ultimo_lote

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PODCAST_PATH = PROJECT_ROOT / "podcast_ia_hoje.mp3"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
EPISODIO_FRONTEND_PATH = FRONTEND_DIR / "data" / "episodio.json"
LIMITE_MENSAGEM = 4000

load_dotenv(PROJECT_ROOT / ".env")


def telegram_configurado() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def _token_bot() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip("\"'").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não foi definido no .env.")
    if re.fullmatch(r"bot\d+:.+", token):
        token = token[3:]
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", token):
        problemas = []
        if ":" not in token:
            problemas.append("falta o ':' que separa o número do bot do código")
        if re.search(r"\s", token):
            problemas.append("há espaços ou quebras de linha no meio")
        if "cole_" in token:
            problemas.append("ainda está o texto de exemplo")
        detalhe = "; ".join(problemas) or f"o formato não confere ({len(token)} caracteres)"
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN no .env parece inválido: "
            f"{detalhe}. O formato esperado é 123456789:AAH... (número, dois-pontos, código), "
            "copiado inteiro da mensagem do @BotFather."
        )
    return token


def _chamar_api(metodo: str, timeout: int = 30, **kwargs) -> dict:
    token = _token_bot()
    try:
        resposta = requests.post(
            f"https://api.telegram.org/bot{token}/{metodo}", timeout=timeout, **kwargs
        )
    except requests.RequestException as exc:
        # A URL da requisição contém o token, então a exceção original não é repassada.
        raise RuntimeError(f"Falha de conexão com o Telegram ({type(exc).__name__}).") from None
    try:
        dados = resposta.json()
    except ValueError:
        raise RuntimeError(f"Resposta inválida do Telegram (HTTP {resposta.status_code}).") from None
    if not dados.get("ok"):
        descricao = dados.get("description", resposta.status_code)
        if resposta.status_code in (401, 404):
            descricao = (
                f"{descricao}. O Telegram não reconheceu o TELEGRAM_BOT_TOKEN: confira se ele foi "
                "copiado inteiro do @BotFather ou gere um novo com /token"
            )
        raise RuntimeError(f"Telegram recusou {metodo}: {descricao}")
    return dados["result"]


def _montar_mensagens_noticias(noticias: List[Dict[str, str]]) -> List[str]:
    linhas = [f"<b>Notícias do episódio ({len(noticias)})</b>"]
    for noticia in noticias:
        fonte = html.escape(noticia.get("fonte") or "Sem fonte")
        titulo = html.escape(noticia["titulo"])
        link = html.escape(noticia["link"], quote=True)
        linhas.append(f'• <i>{fonte}</i> — <a href="{link}">{titulo}</a>')

    mensagens: List[str] = []
    atual = ""
    for linha in linhas:
        if atual and len(atual) + len(linha) + 1 > LIMITE_MENSAGEM:
            mensagens.append(atual)
            atual = linha
        else:
            atual = f"{atual}\n{linha}" if atual else linha
    if atual:
        mensagens.append(atual)
    return mensagens


def enviar_episodio(arquivo_mp3: Path, noticias: List[Dict[str, str]]) -> None:
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID não foi definido no .env.")
    arquivo_mp3 = Path(arquivo_mp3)
    if not arquivo_mp3.exists():
        raise RuntimeError(f"Arquivo de áudio não encontrado: {arquivo_mp3}")

    agora = datetime.now()
    with arquivo_mp3.open("rb") as audio:
        _chamar_api(
            "sendAudio",
            timeout=180,
            data={
                "chat_id": chat_id,
                "caption": f"Sintonia IA · episódio de {agora:%d/%m/%Y}",
                "title": f"Sintonia IA {agora:%d/%m/%Y}",
                "performer": "Lucas e Beatriz",
            },
            files={"audio": (f"sintonia_ia_{agora:%Y-%m-%d}.mp3", audio, "audio/mpeg")},
        )

    if noticias:
        for texto in _montar_mensagens_noticias(noticias):
            _chamar_api(
                "sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": texto,
                    "parse_mode": "HTML",
                    "link_preview_options": {"is_disabled": True},
                },
            )
    print("📨 Episódio enviado ao Telegram.")


def mostrar_chats_recentes() -> None:
    bot = _chamar_api("getMe")
    print(f"Token do .env pertence ao bot @{bot.get('username')} ({bot.get('first_name')}).")

    chats: Dict[int, str] = {}
    for atualizacao in _chamar_api("getUpdates"):
        mensagem = atualizacao.get("message") or atualizacao.get("channel_post") or {}
        chat = mensagem.get("chat")
        if chat:
            chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("username") or ""

    if not chats:
        print(
            f"Nenhuma mensagem encontrada. No Telegram, abra https://t.me/{bot.get('username')}, "
            "toque em Iniciar, mande um 'oi' e rode de novo."
        )
        return
    for chat_id, nome in chats.items():
        print(f"TELEGRAM_CHAT_ID={chat_id}   ({nome})")


def reenviar_ultimo_episodio() -> None:
    # O acervo da landing page guarda o MP3 de cada dia; podcast_ia_hoje.mp3 não é atualizado
    # quando o episódio é gerado dentro do Docker.
    if EPISODIO_FRONTEND_PATH.exists():
        episodio = json.loads(EPISODIO_FRONTEND_PATH.read_text(encoding="utf-8"))
        if episodio.get("audio"):
            audio = FRONTEND_DIR / episodio["audio"].split("?")[0]
            enviar_episodio(audio, episodio.get("noticias", []))
            return
    enviar_episodio(PODCAST_PATH, listar_ultimo_lote())


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if comando == "chat-id":
            mostrar_chats_recentes()
        elif comando == "enviar":
            reenviar_ultimo_episodio()
        else:
            print("Uso: python -m agent_noticias.telegram_service [chat-id | enviar]")
    except RuntimeError as exc:
        print(f"Erro: {exc}")
        sys.exit(1)
