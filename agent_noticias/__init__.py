"""Coleta notícias de tecnologia e gera roteiros de podcast."""

import sys


def configurar_saida_utf8() -> None:
    """Envia stdout e stderr em UTF-8 para o terminal mostrar português."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except (AttributeError, OSError):
            pass

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


configurar_saida_utf8()
