import html
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google.genai import errors as genai_errors
from pydub import AudioSegment

from .deduplication_service import listar_ultimo_lote
from .feed_collector import FEEDS_CONFIG
from .script_agent import MODELO_GEMINI, traduzir_noticias
from .tts_service import VOZ_BEATRIZ, VOZ_LUCAS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
AUDIO_DIR = FRONTEND_DIR / "audio"
DATA_DIR = FRONTEND_DIR / "data"
ACERVO_PATH = DATA_DIR / "episodios.json"
EPISODIO_PATH = DATA_DIR / "episodio.json"
PODCAST_PATH = PROJECT_ROOT / "podcast_ia_hoje.mp3"
ROTEIRO_PATH = PROJECT_ROOT / "dados" / "roteiro_hoje.txt"
LIMITE_RESUMO = 280
VOZES = {"Lucas": VOZ_LUCAS, "Beatriz": VOZ_BEATRIZ}

load_dotenv(PROJECT_ROOT / ".env")


def _limpar_resumo(texto: Optional[str]) -> str:
    texto = html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > LIMITE_RESUMO:
        texto = texto[:LIMITE_RESUMO].rsplit(" ", 1)[0] + "…"
    return texto


def _falas_do_roteiro(roteiro: str) -> List[Dict[str, str]]:
    falas = []
    for linha in roteiro.splitlines():
        encontrado = re.match(r"^\s*(Lucas|Beatriz)\s*:\s*(.+)$", linha)
        if encontrado:
            apresentador, fala = encontrado.groups()
            falas.append({"apresentador": apresentador, "voz": VOZES[apresentador], "fala": fala.strip()})
    return falas


def _duracao_segundos(caminho: Path) -> Optional[int]:
    try:
        return round(AudioSegment.from_mp3(caminho).duration_seconds)
    except Exception as exc:
        print(f"Não foi possível medir a duração de {caminho.name}: {exc}")
        return None


def _noticias_em_ptbr(noticias: List[Dict[str, str]]) -> List[dict]:
    originais = [
        {
            "fonte": n.get("fonte") or "Sem fonte",
            "titulo_original": n["titulo"],
            "resumo_original": _limpar_resumo(n.get("resumo")),
            "link": n["link"],
            "data_publicacao": n.get("data_publicacao"),
        }
        for n in noticias
    ]
    try:
        traducoes = traduzir_noticias(
            [{"titulo": n["titulo_original"], "resumo": n["resumo_original"]} for n in originais]
        )
    except (RuntimeError, genai_errors.APIError) as exc:
        print(f"Aviso: notícias da landing page ficaram no idioma original ({exc}).")
        traducoes = [None] * len(originais)

    return [
        {
            "fonte": n["fonte"],
            "titulo": t.titulo if t else n["titulo_original"],
            "resumo": t.resumo if t else n["resumo_original"],
            **n,
        }
        for n, t in zip(originais, traducoes)
    ]


def _ler_episodio_atual() -> dict:
    if not EPISODIO_PATH.exists():
        return {}
    try:
        return json.loads(EPISODIO_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ler_acervo() -> List[dict]:
    if not ACERVO_PATH.exists():
        return []
    try:
        return json.loads(ACERVO_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _salvar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def exportar_dados_frontend(
    noticias: List[Dict[str, str]],
    roteiro: str,
    podcast_path: Path = PODCAST_PATH,
    data_episodio: Optional[datetime] = None,
) -> Optional[Path]:
    if not FRONTEND_DIR.exists():
        print(f"Pasta {FRONTEND_DIR} não encontrada; dados da landing page não exportados.")
        return None

    momento = data_episodio or datetime.now()
    data = momento.date().isoformat()
    acervo = _ler_acervo()
    existente = next((e for e in acervo if e.get("data") == data), None)
    numero = existente["numero"] if existente else max((e["numero"] for e in acervo), default=0) + 1

    audio_url = None
    duracao = None
    if podcast_path.exists():
        destino_audio = AUDIO_DIR / f"{data}.mp3"
        destino_audio.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(podcast_path, destino_audio)
        # O parâmetro muda a cada exportação para o navegador não tocar uma versão antiga do cache.
        audio_url = f"audio/{data}.mp3?v={datetime.now():%Y%m%d%H%M%S}"
        duracao = _duracao_segundos(destino_audio)

    resumo_episodio = {
        "numero": numero,
        "data": data,
        "data_formatada": f"{momento:%d/%m/%Y}",
        "titulo": f"Episódio de {momento:%d/%m/%Y} · {len(noticias)} notícia{'s' if len(noticias) != 1 else ''} de IA",
        "audio": audio_url,
        "duracao_segundos": duracao,
        "total_noticias": len(noticias),
    }
    acervo = [e for e in acervo if e.get("data") != data] + [resumo_episodio]
    acervo.sort(key=lambda e: e["data"], reverse=True)

    bot = os.getenv("TELEGRAM_BOT_USERNAME", "sintonia_ia_toni_bot")
    episodio = {
        **resumo_episodio,
        "podcast": "Sintonia IA",
        "apresentadores": ["Lucas", "Beatriz"],
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "telegram": f"https://t.me/{bot}",
        "modelo": MODELO_GEMINI,
        "modelo_nome": MODELO_GEMINI.replace("-", " ").title(),
        "noticias": _noticias_em_ptbr(noticias),
        "roteiro": _falas_do_roteiro(roteiro),
        "feeds": [{"nome": f["fonte"], "url": f["url"]} for f in FEEDS_CONFIG],
    }

    _salvar_json(EPISODIO_PATH, episodio)
    _salvar_json(ACERVO_PATH, acervo)
    (AUDIO_DIR / "episodio.mp3").unlink(missing_ok=True)
    print(f"Landing page atualizada: episódio #{numero} ({len(acervo)} no acervo).")
    return EPISODIO_PATH


if __name__ == "__main__":
    roteiro_atual = ROTEIRO_PATH.read_text(encoding="utf-8") if ROTEIRO_PATH.exists() else ""
    data_audio = (
        datetime.fromtimestamp(PODCAST_PATH.stat().st_mtime) if PODCAST_PATH.exists() else None
    )
    # O banco não guarda resumo nem data de publicação; reaproveita os da última exportação.
    anteriores = {n["link"]: n for n in _ler_episodio_atual().get("noticias", [])}
    lote = []
    for noticia in listar_ultimo_lote():
        anterior = anteriores.get(noticia["link"], {})
        lote.append({
            **noticia,
            "resumo": anterior.get("resumo_original", anterior.get("resumo")),
            "data_publicacao": anterior.get("data_publicacao"),
        })
    exportar_dados_frontend(lote, roteiro_atual, PODCAST_PATH, data_audio)
