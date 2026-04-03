"""
Extrai dados dos PDFs oficiais da FUVEST e atualiza o JSON consumido pelo site.
"""

from pathlib import Path
import json
import re

import pdfplumber


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
OUT_PATH = ROOT_DIR / "docs" / "dados.json"


def extrair_2019(caminho: Path) -> list[dict]:
    """PDF de 2019 tem formato diferente: codigo, nome e nota de corte."""
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = linha.strip()
        m = re.match(r"^(\d{5})\s+(.+?)\s+(\d+)\s+(\d+)$", linha)
        if m:
            codigo = m.group(1)
            nome = m.group(2).strip()
            nota_str = m.group(3) + m.group(4)
            registros.append(
                {
                    "codigo": codigo,
                    "curso": nome,
                    "nota_de_corte": int(nota_str),
                }
            )
            continue

        m2 = re.match(r"^(\d{5})\s+(.+?)\s+-$", linha)
        if m2:
            registros.append(
                {
                    "codigo": m2.group(1),
                    "curso": m2.group(2).strip(),
                    "nota_de_corte": None,
                }
            )
    return registros


def extrair_padrao(caminho: Path) -> list[dict]:
    """PDFs de 2020-2026 com vagas, inscritos, ausentes e notas."""
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = linha.strip()
        if linha.startswith("Total"):
            continue

        m = re.match(
            r"^(\d{5})[−\-](.+?)\s+"
            r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
            r"(\d+[.,]\d+)\s+"
            r"([\d−\-]+)\s+([\d−\-]+)$",
            linha,
        )
        if not m:
            continue

        minimo = m.group(8).replace("−", "").replace("-", "")
        maximo = m.group(9).replace("−", "").replace("-", "")
        registros.append(
            {
                "codigo": m.group(1),
                "curso": m.group(2).strip().rstrip("."),
                "vagas": int(m.group(3)),
                "inscritos": int(m.group(4)),
                "ausentes": int(m.group(5)),
                "convocados_2fase": int(m.group(6)),
                "concorrencia": float(m.group(7).replace(",", ".")),
                "pontos_minimo": int(minimo) if minimo else None,
                "pontos_maximo": int(maximo) if maximo else None,
            }
        )
    return registros


def main():
    arquivos = {
        2019: RAW_DIR / "transferencia_2019_nota_de_corte.pdf",
        2020: RAW_DIR / "transferencia_2020_nota_de_corte.pdf",
        2021: RAW_DIR / "transferencia_2021_notas_de_corte.pdf",
        2023: RAW_DIR / "transferencia_2023_nota-corte.pdf",
        2024: RAW_DIR / "transferencia_2024_notas_de_corte.pdf",
        2025: RAW_DIR / "transferencia_2025_notas_de_corte.pdf",
        2026: RAW_DIR / "transferencia_2026_notas_de_corte.pdf",
    }

    dados = {}
    for ano, caminho in arquivos.items():
        if not caminho.exists():
            raise FileNotFoundError(f"PDF nao encontrado: {caminho}")
        registros = extrair_2019(caminho) if ano == 2019 else extrair_padrao(caminho)
        dados[str(ano)] = registros
        print(f"{ano}: {len(registros)} cursos extraidos")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\nArquivo gerado com sucesso em: {OUT_PATH}")


if __name__ == "__main__":
    main()
