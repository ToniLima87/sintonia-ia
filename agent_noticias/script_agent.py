import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from .feed_collector import NoticiasBrutas, extrair_noticias

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODELO_GEMINI = "gemini-2.5-flash"

PROMPT_ROTEIRISTA_PTBR = """
Você é um roteirista de elite especialista em criar diálogos Hiper-Humanizados para podcasts no estilo conversa ao vivo e integrada, SEM DELAY E SEM GÍRIAS.
Sua tarefa é ler as notícias brutas sobre tecnologia em inglês e transformá-las em um episódio fluido e dinâmico para o podcast "Sintonia IA", falado em PORTUGUÊS DO BRASIL.

---
### PERFIS DOS APRESENTADORES
- Lucas: Analista e entusiasta de tecnologia. Comunica-se de forma clara, ágil e articulada, usando metáforas simples e acessíveis para traduzir conceitos complexos.
- Beatriz: Questionadora e prática. Traça o ponto de vista de quem nos acompanha, reage com inteligência e bom humor sutil, focando no impacto real do tema na sociedade.

---
### REGRAS DE HUMANIZAÇÃO, LINGUAGEM NEUTRA E FLUIDEZ (MUITO IMPORTANTE)

1. ELIMINAÇÃO DE DELAY E ARTIFICIALIDADE (FALA DIRETAMANTE INTEGRADA):
   - Elimine hesitações longas ou falsas pausas de processamento (NÃO use "hum...", "é...", "érrr...").
   - Escreva de forma que as interrupções e trocas de turno entre Lucas e Beatriz pareçam imediatas, como duas pessoas com extrema sintonia na mesma mesa.
   - Use ganchos diretos de conexão entre falas: "Exatamente por isso...", "E tem outro ponto...", "Concordo totalmente.", "Faz todo sentido."

2. LINGUAGEM NEUTRA E INCLUSIVA (ZERO GÍRIAS OU VÍCIOS DE LINGUAGEM):
   - BANA completamente gírias ou marcas excessivas de informalidade (NÃO use "cara", "tipo", "tá", "né", "galera", "mano").
   - Aplique a linguagem neutra e inclusiva através de estruturas gramaticais naturais do português:
     * Substantivos coletivos e neutros: "quem nos acompanha", "quem nos ouve", "nossa audiência", "equipe de desenvolvimento", "comunidade".
     * Frases direcionadas ou impessoais: "se você tiver interesse", "para quem estuda a área".
     * Reestruturações verbais no infinitivo para evitar flexão desnecessária de gênero.

3. RITMO E PONTUAÇÃO PARA SÍNTESE DE VOZ (TTS NATURAL):
   - Evite frases gramaticalmente rígidas ou longas demais; divida em orações curtas e diretas.
   - Use pontuação natural (vírgulas, pontos e travessões) para marcar a cadência real do som da voz humana.
   - Use CAIXA ALTA apenas em palavras curtas que exigem ênfase vocal genuína (ex: "MUITO", "NADA", "TUDO").
   - Escreva números grandes por extenso ou de forma simplificada para leitura fluida da TTS (ex: "mais de três milhões").
   - Escreva siglas como são pronunciadas quando necessário (ex: "I-A").

4. DINÂMICA DO EPISÓDIO:
   - Abertura direta, acolhedora e sem delongas (ex: "Boas-vindas a quem está na nossa companhia hoje!").
   - Troca de ideias orgânica e cruzada sobre 2 a 3 notícias principais do bloco.
   - Encerramento conciso com despedida amigável e inclusiva.

5. FORMATO ESTRITO DE SAÍDA:
   - Não adicione introduções fora do diálogo, títulos de blocos ou marcações como [Música] ou [Risos].
   - Saída puramente no formato:
     Lucas: [Fala do Lucas]
     Beatriz: [Fala da Beatriz]

---
Notícias brutas coletadas hoje:
{conteudo_noticias}
"""

PROMPT_TRADUCAO_PTBR = """
Traduza para português do Brasil o "titulo" e o "resumo" de cada notícia da lista JSON abaixo.
- Escreva de forma natural, como uma manchete de portal brasileiro de tecnologia.
- Mantenha nomes de empresas, produtos e modelos como estão (OpenAI, GPT-6, Gemini, Hugging Face...).
- Se o resumo vier vazio, devolva o resumo vazio.
- Devolva exatamente a mesma quantidade de itens, na mesma ordem.

{itens}
"""


class NoticiaTraduzida(BaseModel):
    titulo: str
    resumo: str


def _cliente_gemini() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "A variável GEMINI_API_KEY não foi definida. Configure-a no arquivo .env."
        )
    return genai.Client(api_key=api_key)


def traduzir_noticias(noticias: List[Dict[str, str]]) -> List[NoticiaTraduzida]:
    """Traduz título e resumo de cada notícia para pt-BR, preservando a ordem."""
    if not noticias:
        return []

    itens = [{"titulo": n["titulo"], "resumo": n.get("resumo") or ""} for n in noticias]
    client = _cliente_gemini()
    response = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=PROMPT_TRADUCAO_PTBR.format(itens=json.dumps(itens, ensure_ascii=False)),
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=list[NoticiaTraduzida],
        ),
    )

    traducoes = response.parsed
    if not traducoes or len(traducoes) != len(noticias):
        raise RuntimeError("O Gemini não devolveu uma tradução para cada notícia.")
    return traducoes


def gerar_roteiro_podcast(noticias: List[NoticiasBrutas]) -> str:
    client = _cliente_gemini()

    # Prepara o texto consolidado com as notícias brutas para o Gemini
    bloco_noticias = ""
    for idx, n in enumerate(noticias, 1):
        bloco_noticias += f"--- NOTÍCIA {idx} ---\n"
        bloco_noticias += f"Fonte: {n.fonte}\nTítulo: {n.titulo}\nResumo: {n.resumo}\nLink: {n.link}\n\n"

    print("Gemini está traduzindo, filtrando e criando o roteiro fluido em Português do Brasil...")
    
    response = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=PROMPT_ROTEIRISTA_PTBR.format(conteudo_noticias=bloco_noticias),
        config=types.GenerateContentConfig(
            temperature=0.7,
        ),
    )
    
    try:
        roteiro = response.text
    except ValueError as exc:
        raise RuntimeError("O Gemini não retornou texto para o roteiro.") from exc

    if not roteiro:
        raise RuntimeError("O Gemini retornou um roteiro vazio.")
    return roteiro

if __name__ == "__main__":
    # Teste de ponta a ponta da coleta até o roteiro
    noticias = extrair_noticias(limite_por_feed=5)
    if noticias:
        roteiro_ptbr = gerar_roteiro_podcast(noticias)
        print("\n=== ROTEIRO GERADO EM PORTUGUÊS DO BRASIL ===\n")
        print(roteiro_ptbr)
        
        # Salva o roteiro para inspeção
        output_dir = PROJECT_ROOT / "dados"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "roteiro_hoje.txt"
        with output_path.open("w", encoding="utf-8") as f:
            f.write(roteiro_ptbr)
        print(f"\nRoteiro salvo em '{output_path}'")