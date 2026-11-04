import os
import re

import edge_tts
from pydub import AudioSegment

# Vozes brasileiras usadas na síntese.
VOZ_LUCAS = "pt-BR-AntonioNeural"
VOZ_BEATRIZ = "pt-BR-FranciscaNeural"

async def gerar_audio_linha(texto: str, voz: str, arquivo_saida: str):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(arquivo_saida)

async def processar_roteiro_para_audio(roteiro_texto: str, arquivo_mp3_final: str = "podcast_diario.mp3"):
    linhas = roteiro_texto.strip().split("\n")
    segmentos_audio = []

    print("Iniciando síntese de voz multi-locutor...")

    for idx, linha in enumerate(linhas):
        linha = linha.strip()
        if not linha:
            continue

        if linha.startswith("Lucas:"):
            texto = re.sub(r"^Lucas:\s*", "", linha)
            voz = VOZ_LUCAS
        elif linha.startswith("Beatriz:"):
            texto = re.sub(r"^Beatriz:\s*", "", linha)
            voz = VOZ_BEATRIZ
        else:
            continue

        temp_file = f"temp_{idx}.mp3"
        await gerar_audio_linha(texto, voz, temp_file)

        audio_segmento = AudioSegment.from_mp3(temp_file)
        pausa = AudioSegment.silent(duration=300)
        segmentos_audio.append(audio_segmento + pausa)

        os.remove(temp_file)

    if segmentos_audio:
        podcast_completo = sum(segmentos_audio)
        podcast_completo.export(arquivo_mp3_final, format="mp3")
        print(f"Podcast salvo com sucesso em: {arquivo_mp3_final}")
    else:
        print("Nenhum segmento de áudio válido foi identificado no roteiro.")
