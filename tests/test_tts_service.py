import asyncio
from pathlib import Path

from agent_noticias import tts_service


class SegmentoFalso:
    def __init__(self, duracao: int = 0):
        self.duracao = duracao

    def __add__(self, outro):
        return SegmentoFalso(self.duracao + outro.duracao)

    def __radd__(self, outro):
        return self if outro == 0 else self + outro

    def export(self, caminho, format):
        Path(caminho).write_text(f"{format}:{self.duracao}")


class AudioSegmentFalso:
    from_mp3 = staticmethod(lambda caminho: SegmentoFalso(1000))
    silent = staticmethod(lambda duration: SegmentoFalso(duration))


def test_cada_apresentador_recebe_a_sua_voz(tmp_path, monkeypatch):
    sintetizadas = []

    async def sintetizar(texto, voz, arquivo_saida):
        sintetizadas.append((voz, texto))
        Path(arquivo_saida).write_bytes(b"")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tts_service, "gerar_audio_linha", sintetizar)
    monkeypatch.setattr(tts_service, "AudioSegment", AudioSegmentFalso)
    roteiro = "Lucas: Bom dia!\nlinha sem apresentador\nBeatriz: Olá!"

    asyncio.run(tts_service.processar_roteiro_para_audio(roteiro, str(tmp_path / "ep.mp3")))

    assert sintetizadas == [(tts_service.VOZ_LUCAS, "Bom dia!"), (tts_service.VOZ_BEATRIZ, "Olá!")]
    assert (tmp_path / "ep.mp3").read_text() == "mp3:2600"
    assert not list(tmp_path.glob("temp_*.mp3"))
