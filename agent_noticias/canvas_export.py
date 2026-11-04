import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .deduplication_service import listar_noticias_processadas

# O Cursor só exibe canvases salvos nesta pasta do projeto. Use CANVAS_DIR no .env para trocar.
CANVAS_DIR_PADRAO = (
    Path.home() / ".cursor" / "projects"
    / "c-Users-Toni0709-OneDrive-rea-de-Trabalho-Agent-Noticias" / "canvases"
)
CANVAS_ARQUIVO = "noticias-historico.canvas.tsx"

TEMPLATE_CANVAS = """import { BarChart, Divider, H1, H2, Link, Row, Stack, Stat, Table, Text } from "cursor/canvas";

type Registro = { id: number; data: string; fonte: string; titulo: string; link: string };

const ATUALIZADO = __ATUALIZADO__;
const REGISTROS: Registro[] = __REGISTROS__;

export default function NoticiasHistorico() {
  const fontes = Array.from(new Set(REGISTROS.map((r) => r.fonte)));
  const dias = Array.from(new Set(REGISTROS.map((r) => r.data.slice(0, 10))));
  const recentes = [...REGISTROS].reverse();

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Links e fontes das notícias</H1>
        <Text tone="secondary">
          Gerado pelo main.py a partir de dados/noticias_historico.db. Atualizado em {ATUALIZADO}.
        </Text>
      </Stack>

      <Row gap={32} align="end">
        <Stat value={String(REGISTROS.length)} label="Notícias registradas" />
        <Stat value={String(fontes.length)} label="Fontes" />
        <Stat value={String(dias.length)} label="Dias com execução" />
      </Row>

      <Stack gap={8}>
        <H2>Notícias por fonte</H2>
        <BarChart
          horizontal
          stacked={dias.length > 1}
          height={60 + fontes.length * 36}
          categories={fontes}
          series={dias.map((dia) => ({
            name: dia,
            data: fontes.map(
              (fonte) => REGISTROS.filter((r) => r.fonte === fonte && r.data.startsWith(dia)).length,
            ),
          }))}
        />
        <Text size="small" tone="tertiary">
          Eixo horizontal: quantidade de notícias. Eixo vertical: fonte do feed. Cada série é um dia
          de processamento (UTC).
        </Text>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>Links registrados</H2>
        <Table
          headers={["ID", "Processado em (UTC)", "Fonte", "Título"]}
          columnAlign={["right", "left", "left", "left"]}
          striped
          stickyHeader
          rows={recentes.map((r) => [String(r.id), r.data, r.fonte, <Link href={r.link}>{r.titulo}</Link>])}
        />
        <Text size="small" tone="tertiary">Mais recentes primeiro. O título abre o link da notícia.</Text>
      </Stack>
    </Stack>
  );
}
"""


def exportar_canvas_noticias() -> Optional[Path]:
    canvas_dir = Path(os.getenv("CANVAS_DIR", CANVAS_DIR_PADRAO))
    if not canvas_dir.parent.exists():
        print(f"Pasta do projeto no Cursor não encontrada ({canvas_dir.parent}); canvas não gerado.")
        return None

    registros = [
        {
            "id": linha["id"],
            "data": linha["data_processamento"],
            "fonte": linha["fonte"] or "Fonte não registrada",
            "titulo": linha["titulo"],
            "link": linha["link"],
        }
        for linha in listar_noticias_processadas()
    ]
    if not registros:
        print("Nenhuma notícia no histórico; canvas não gerado.")
        return None

    conteudo = (
        TEMPLATE_CANVAS
        .replace("__ATUALIZADO__", json.dumps(datetime.now().strftime("%d/%m/%Y %H:%M")))
        .replace("__REGISTROS__", json.dumps(registros, ensure_ascii=False, indent=2))
    )

    canvas_dir.mkdir(exist_ok=True)
    destino = canvas_dir / CANVAS_ARQUIVO
    destino.write_text(conteudo, encoding="utf-8")
    print(f"Canvas de links e fontes atualizado: {destino}")
    return destino


if __name__ == "__main__":
    exportar_canvas_noticias()
