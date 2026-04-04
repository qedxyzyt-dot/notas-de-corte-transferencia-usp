"""
Audita o JSON do vestibular para localizar possiveis fragilidades de leitura.

Foco:
- modalidades com campos oficialmente em branco (---)
- inconsistencias publicadas no proprio PDF, como minimo > maximo
- grupos com quantidade inesperada de modalidades
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_PATH = ROOT_DIR / "docs" / "dados_vestibular.json"


def carregar() -> dict[str, list[dict]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def auditar(dados: dict[str, list[dict]]) -> None:
    for ano in sorted(dados, key=int):
        registros = [registro for registro in dados[ano] if registro.get("modalidade")]
        if not registros:
            continue

        faltas = [
            registro
            for registro in registros
            if registro.get("convocados_por_vaga") is None
            or registro.get("pontos_minimo") is None
            or registro.get("pontos_maximo") is None
        ]
        inconsistencias = [
            registro
            for registro in registros
            if registro.get("pontos_minimo") is not None
            and registro.get("pontos_maximo") is not None
            and registro["pontos_minimo"] > registro["pontos_maximo"]
        ]

        grupos = defaultdict(set)
        for registro in registros:
            grupos[(registro["codigo"], registro["curso"])].add(registro["modalidade"])
        tamanhos = Counter(len(modalidades) for modalidades in grupos.values())

        print(
            f"{ano}: {len(registros)} linhas de modalidade | "
            f"grupos={len(grupos)} | tamanhos={dict(sorted(tamanhos.items()))} | "
            f"faltas={len(faltas)} | inconsistencias={len(inconsistencias)}"
        )

        for registro in faltas:
            print(
                "  falta:",
                registro["codigo"],
                registro["curso"],
                "|",
                registro["modalidade"],
                "| vagas",
                registro.get("vagas"),
                "| inscritos",
                registro.get("inscritos"),
                "| ausentes",
                registro.get("ausentes"),
                "| convocados",
                registro.get("convocados_2fase"),
                "| prop",
                registro.get("convocados_por_vaga"),
                "| min",
                registro.get("pontos_minimo"),
                "| max",
                registro.get("pontos_maximo"),
            )

        for registro in inconsistencias:
            print(
                "  inconsistencia oficial:",
                registro["codigo"],
                registro["curso"],
                "|",
                registro["modalidade"],
                "| minimo",
                registro["pontos_minimo"],
                "| maximo",
                registro["pontos_maximo"],
            )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"JSON nao encontrado: {DATA_PATH}")
    auditar(carregar())


if __name__ == "__main__":
    main()
