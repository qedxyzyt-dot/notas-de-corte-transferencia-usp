"""
Extrai dados dos PDFs oficiais da FUVEST e atualiza o JSON consumido pelo site.

Esta versao preserva o nome bruto lido do PDF e aplica somente correcoes
seguras no nome exibido. Quando a camada de texto do PDF chega truncada e nao
ha inferencia univoca, o registro permanece sinalizado para revisao.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
import unicodedata

import pdfplumber


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
OUT_PATH = ROOT_DIR / "docs" / "dados.json"

MINUS = "\u2212"
MINUS_CHARS = f"-{MINUS}\u2013\u2014"
LINE_RE_2019 = re.compile(r"^(\d{5})\s+(.+?)\s+(\d+)\s+(\d+)$")
LINE_RE_2019_EMPTY = re.compile(r"^(\d{5})\s+(.+?)\s+-$")
LINE_RE_PADRAO = re.compile(
    rf"^(\d{{5}})[{re.escape(MINUS_CHARS)}](.+?)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d+[.,]\d+)\s+"
    rf"([\d{MINUS}-]+)\s+([\d{MINUS}-]+)$"
)
SEP_RE = re.compile(rf"\s*[{re.escape(MINUS_CHARS)}]\s*")
ELLIPSIS_RE = re.compile(r"\.{3,}$")
UNFINISHED_PAREN_RE = re.compile(r"\(([^()]*)$")
SEMESTER_FULL_RE = re.compile(r"^(\d+[\u00bao\u00b0])\s*semestre$", re.IGNORECASE)
SEMESTER_FRAGMENT_RE = re.compile(
    r"^(\d+[\u00bao\u00b0])(?:\s*s(?:e(?:m(?:e(?:s(?:t(?:r(?:e)?)?)?)?)?)?)?)?$",
    re.IGNORECASE,
)

KNOWN_LOCATIONS = [
    "S\u00e3o Carlos",
    "S\u00e3o Paulo",
    "S\u00e3o Paulo Butant\u00e3",
    "S\u00e3o Paulo Butant\u00e3/ Quadril\u00e1tero",
    "S\u00e3o Paulo Leste",
    "S\u00e3o Paulo Quadril\u00e1tero",
    "Bauru",
    "Lorena",
    "Piracicaba",
    "Pirassununga",
    "Ribeir\u00e3o Preto",
    "Santos",
]
KNOWN_PERIODS = ["Integral", "Diurno", "Noturno", "Matutino", "Vespertino"]
KNOWN_DEGREES = [
    "Bacharelado",
    "Licenciatura",
    "Bacharelado e Licenciatura",
    "Licenciatura e Bacharelado",
]
KNOWN_SEGMENTS = KNOWN_LOCATIONS + KNOWN_PERIODS + KNOWN_DEGREES


def normalizar(texto: str) -> str:
    decomposed = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", sem_acentos).strip().lower()


def limpar_texto_extraido(texto: str) -> str:
    texto = texto.replace("\u00a0", " ")
    texto = texto.replace("\u2011", "-")
    texto = texto.replace("\u2212", MINUS)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_segmento(segmento: str) -> str:
    return normalizar(segmento.rstrip(". ").strip())


def match_prefix_unico(fragmento: str, opcoes: list[str]) -> str | None:
    frag_norm = normalizar_segmento(fragmento)
    if len(frag_norm) < 3:
        return None

    candidatos = [opcao for opcao in opcoes if normalizar(opcao).startswith(frag_norm)]
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos[0]

    menor = min(candidatos, key=len)
    menor_norm = normalizar(menor)
    if all(normalizar(c).startswith(menor_norm) for c in candidatos):
        return menor
    return None


def segmentar_nome(nome: str) -> list[str]:
    return [parte.strip() for parte in SEP_RE.split(nome) if parte.strip()]


def expandir_segmento(segmento: str) -> tuple[str, bool]:
    original = limpar_texto_extraido(segmento).rstrip(". ").strip()
    if not original:
        return original, False

    corrigido = original
    alterado = False

    if ELLIPSIS_RE.search(corrigido):
        corrigido = ELLIPSIS_RE.sub("", corrigido).rstrip(". ").strip()
        alterado = True

    parentese_aberto = UNFINISHED_PAREN_RE.search(corrigido)
    if parentese_aberto:
        prefixo = corrigido[: parentese_aberto.start()].rstrip()
        fragmento = parentese_aberto.group(1).strip()
        completo = match_prefix_unico(fragmento, KNOWN_SEGMENTS)
        if completo:
            corrigido = f"{prefixo} ({completo})".strip()
            alterado = True

    semestre = SEMESTER_FRAGMENT_RE.fullmatch(corrigido)
    if semestre and not SEMESTER_FULL_RE.fullmatch(corrigido):
        corrigido = f"{semestre.group(1)} semestre"
        alterado = True

    completo = match_prefix_unico(corrigido, KNOWN_SEGMENTS)
    if completo and normalizar(corrigido) != normalizar(completo):
        corrigido = completo
        alterado = True

    return corrigido, alterado


def nome_parece_truncado(nome: str) -> bool:
    nome = limpar_texto_extraido(nome)
    if "..." in nome:
        return True
    if UNFINISHED_PAREN_RE.search(nome):
        return True

    segmentos = segmentar_nome(nome)
    if not segmentos:
        return False

    ultimo = segmentos[-1].rstrip(". ").strip()
    if SEMESTER_FRAGMENT_RE.fullmatch(ultimo) and not SEMESTER_FULL_RE.fullmatch(ultimo):
        return True

    completo = match_prefix_unico(ultimo, KNOWN_SEGMENTS)
    if completo and normalizar(ultimo) != normalizar(completo):
        return True

    return len(normalizar_segmento(ultimo)) <= 2


def sanear_nome_basico(nome_bruto: str) -> tuple[str, bool]:
    nome = limpar_texto_extraido(nome_bruto)
    nome_original = nome.strip(" .")
    segmentos = segmentar_nome(nome)
    if not segmentos:
        return nome_original, False

    alterado = False
    segmentos_saneados: list[str] = []
    for segmento in segmentos:
        novo, mudou = expandir_segmento(segmento)
        segmentos_saneados.append(novo)
        alterado = alterado or mudou

    if not alterado:
        return nome_original, False

    nome_saneado = f" {MINUS} ".join(seg for seg in segmentos_saneados if seg).strip()
    nome_saneado = re.sub(rf"\s*[{re.escape(MINUS_CHARS)}]\s*$", "", nome_saneado).strip()
    nome_saneado = nome_saneado.strip(" .")
    return nome_saneado, alterado


def inferir_por_catalogo(nome: str, catalogo: list[str]) -> str | None:
    nome_norm = normalizar(nome)
    if not nome_norm:
        return None

    candidatos = [item for item in catalogo if normalizar(item).startswith(nome_norm)]
    if len(candidatos) == 1:
        return candidatos[0]
    return None


def extrair_2019(caminho: Path) -> list[dict]:
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = limpar_texto_extraido(linha)
        if not linha:
            continue

        m = LINE_RE_2019.match(linha)
        if m:
            registros.append(
                {
                    "codigo": m.group(1),
                    "curso": m.group(2).strip(),
                    "nota_de_corte": int(m.group(3) + m.group(4)),
                }
            )
            continue

        m2 = LINE_RE_2019_EMPTY.match(linha)
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
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = limpar_texto_extraido(linha)
        if not linha or linha.startswith("Total"):
            continue

        m = LINE_RE_PADRAO.match(linha)
        if not m:
            continue

        minimo = m.group(8).replace(MINUS, "").replace("-", "")
        maximo = m.group(9).replace(MINUS, "").replace("-", "")
        registros.append(
            {
                "codigo": m.group(1),
                "curso": m.group(2).strip(),
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


def sanear_registros(dados: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    todos = [(ano, registro) for ano, registros in dados.items() for registro in registros]

    for _, registro in todos:
        bruto = limpar_texto_extraido(registro["curso"])
        saneado, mudou = sanear_nome_basico(bruto)
        registro["curso_pdf"] = bruto
        registro["curso"] = saneado
        if mudou:
            registro["curso_saneado"] = True

    catalogo = sorted(
        {
            registro["curso"]
            for _, registro in todos
            if not nome_parece_truncado(registro["curso"])
        }
    )

    resumo: dict[str, dict[str, int]] = {}
    for ano, registro in todos:
        resumo.setdefault(ano, {"saneados": 0, "pendentes": 0})

        if nome_parece_truncado(registro["curso"]):
            inferido = inferir_por_catalogo(registro["curso"], catalogo)
            if inferido and inferido != registro["curso"]:
                registro["curso"] = inferido
                registro["curso_saneado"] = True
                registro["curso_inferencia"] = "catalogo"

            if nome_parece_truncado(registro["curso"]):
                registro["curso_truncado"] = True
                resumo[ano]["pendentes"] += 1
        elif "..." in registro["curso_pdf"] and not registro.get("curso_saneado"):
            registro["curso_truncado"] = True
            resumo[ano]["pendentes"] += 1

        if registro.get("curso_saneado"):
            resumo[ano]["saneados"] += 1

    return resumo


def remover_flags_vazias(dados: dict[str, list[dict]]) -> None:
    for registros in dados.values():
        for registro in registros:
            if not registro.get("curso_saneado"):
                registro.pop("curso_saneado", None)
            if not registro.get("curso_truncado"):
                registro.pop("curso_truncado", None)
            if "curso_inferencia" not in registro:
                registro.pop("curso_inferencia", None)
            if registro.get("curso_pdf") == registro.get("curso") and not registro.get("curso_truncado"):
                registro.pop("curso_pdf", None)


def main() -> None:
    arquivos = {
        2019: RAW_DIR / "transferencia_2019_nota_de_corte.pdf",
        2020: RAW_DIR / "transferencia_2020_nota_de_corte.pdf",
        2021: RAW_DIR / "transferencia_2021_notas_de_corte.pdf",
        2023: RAW_DIR / "transferencia_2023_nota-corte.pdf",
        2024: RAW_DIR / "transferencia_2024_notas_de_corte.pdf",
        2025: RAW_DIR / "transferencia_2025_notas_de_corte.pdf",
        2026: RAW_DIR / "transferencia_2026_notas_de_corte.pdf",
    }

    dados: dict[str, list[dict]] = {}
    for ano, caminho in arquivos.items():
        if not caminho.exists():
            raise FileNotFoundError(f"PDF nao encontrado: {caminho}")

        registros = extrair_2019(caminho) if ano == 2019 else extrair_padrao(caminho)
        dados[str(ano)] = registros

    resumo = sanear_registros(dados)
    remover_flags_vazias(dados)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)

    for ano, registros in dados.items():
        info = resumo[ano]
        print(
            f"{ano}: {len(registros)} cursos extraidos | "
            f"{info['saneados']} saneados | {info['pendentes']} pendentes"
        )

    print(f"\nArquivo gerado com sucesso em: {OUT_PATH}")


if __name__ == "__main__":
    main()
