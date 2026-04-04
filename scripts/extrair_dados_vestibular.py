"""
Extrai dados dos PDFs oficiais da FUVEST para o vestibular tradicional.

O JSON gerado alimenta um dashboard separado do site de transferencia externa.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import unicodedata

import pdfplumber


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
RAW_DIR = ROOT_DIR / "fuvest_vestibular"
OUT_PATH = ROOT_DIR / "docs" / "dados_vestibular.json"
PDF_OUT_DIR = ROOT_DIR / "docs" / "assets" / "pdfs" / "vestibular"
CODIGOS_PATH = SCRIPT_DIR / "vestibular_codigos_oficiais.json"

MINUS = "\u2212"
MINUS_CHARS = f"-{MINUS}\u2013\u2014"
MINUS_CLASS = re.escape(MINUS_CHARS)

LINE_RE_COMPLETO = re.compile(
    rf"^(\d{{3}})[{MINUS_CLASS}]\s*(.+?)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d+[.,]\d+)\s+(\d+)\s+(\d+)$"
)
LINE_RE_REDUZIDO = re.compile(
    rf"^(\d{{3}})[{MINUS_CLASS}]\s*(.+?)\s+"
    r"(\d+)\s+(\d+[.,]\d+)\s+(\d+)\s+(\d+)\s+(\d+)$"
)
LINE_RE_CARREIRA = re.compile(rf"^(\d{{3}})[{MINUS_CLASS}]\s*(.+)$")
LINE_RE_MODALIDADE_COMPLETA = re.compile(
    rf"^[{MINUS_CLASS}]\s*(.+?)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d+[.,]\d+)\s+(\d+)\s+(\d+)$"
)
LINE_RE_MODALIDADE_MAX = re.compile(
    rf"^[{MINUS_CLASS}]\s*(.+?)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d+[.,]\d+)\s+(\d+)$"
)
LINE_RE_NUMERO = re.compile(r"^\d+$")
LINE_RE_DECIMAL = re.compile(r"^\d+[.,]\d+$")
NUMERIC_TAIL_RE = re.compile(
    r"\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+[.,]\d+\s+\d+$"
)

def carregar_desambiguacoes_oficiais() -> dict[int, dict[str, dict[str, str]]]:
    bruto = json.loads(CODIGOS_PATH.read_text(encoding="utf-8"))
    return {
        int(ano): info.get("codigos", {})
        for ano, info in bruto.items()
    }


def limpar_texto(texto: str) -> str:
    texto = texto.replace("\u00a0", " ")
    texto = texto.replace("\u2011", "-")
    texto = texto.replace("\u2212", MINUS)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar(texto: str) -> str:
    decomposed = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", sem_acentos).strip().lower()


def nome_parece_truncado(nome: str) -> bool:
    return "..." in nome or nome.endswith("..")


def tem_diacriticos(texto: str) -> bool:
    decomposed = unicodedata.normalize("NFD", texto)
    return any(unicodedata.category(ch) == "Mn" for ch in decomposed)


def pontuar_nome(nome: str) -> tuple[int, int]:
    letras = [ch for ch in nome if ch.isalpha()]
    maiusculas = sum(1 for ch in letras if ch.isupper())
    minusculas = sum(1 for ch in letras if ch.islower())
    tem_acentos = tem_diacriticos(nome)
    score = 0
    if not nome_parece_truncado(nome):
        score += 20
    if minusculas:
        score += 6
    if minusculas and maiusculas and minusculas >= maiusculas:
        score += 4
    if tem_acentos:
        score += 3
    if nome.startswith("FUVEST"):
        score -= 50
    return score, len(nome)


def melhor_nome(candidato_atual: str, novo_candidato: str) -> str:
    return max([candidato_atual, novo_candidato], key=pontuar_nome)


def inferir_nome_truncado(nome: str, catalogo: list[str]) -> str | None:
    prefixo = normalizar(nome.replace("...", "").strip(" ."))
    if len(prefixo) < 6:
        return None

    candidatos = [item for item in catalogo if normalizar(item).startswith(prefixo)]
    if len(candidatos) == 1:
        return candidatos[0]
    return None


def canonizar_nomes(dados: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    todos = [registro for registros in dados.values() for registro in registros]

    nomes_exatos: dict[str, str] = {}
    nomes_completos: list[str] = []

    for registro in todos:
        bruto = limpar_texto(registro["curso"])
        registro["curso_pdf"] = bruto
        chave = normalizar(bruto)
        if chave:
            if chave in nomes_exatos:
                nomes_exatos[chave] = melhor_nome(nomes_exatos[chave], bruto)
            else:
                nomes_exatos[chave] = bruto
        if not nome_parece_truncado(bruto):
            nomes_completos.append(bruto)

    nomes_completos = sorted(set(nomes_completos), key=lambda item: (normalizar(item), item))

    resumo: dict[str, dict[str, int]] = {}
    for ano, registros in dados.items():
        info = {"canonizados": 0, "truncados_restantes": 0}
        for registro in registros:
            bruto = registro["curso_pdf"]
            chave = normalizar(bruto)
            final = nomes_exatos.get(chave, bruto)
            alterado = final != bruto

            if nome_parece_truncado(final):
                inferido = inferir_nome_truncado(final, nomes_completos)
                if inferido:
                    final = inferido
                    alterado = True

            registro["curso"] = final
            if alterado:
                registro["curso_canonizado"] = True
            if nome_parece_truncado(final):
                registro["curso_truncado"] = True
                info["truncados_restantes"] += 1
            if alterado:
                info["canonizados"] += 1
            if registro["curso"] == registro["curso_pdf"]:
                registro.pop("curso_pdf", None)
        resumo[ano] = info

    return resumo


def encontrar_repeticoes_por_codigo(dados: dict[str, list[dict]]) -> dict[str, list[dict[str, object]]]:
    repeticoes: dict[str, list[dict[str, object]]] = {}

    for ano, registros in dados.items():
        grupos: dict[str, dict[str, object]] = {}
        for registro in registros:
            curso = registro["curso"]
            grupo = grupos.setdefault(
                curso,
                {"curso": curso, "codigos": set(), "quantidade": 0},
            )
            grupo["codigos"].add(registro["codigo"])
            grupo["quantidade"] += 1

        repeticoes_ano = []
        for grupo in grupos.values():
            codigos = sorted(grupo["codigos"])
            if len(codigos) <= 1:
                continue
            repeticoes_ano.append(
                {
                    "curso": grupo["curso"],
                    "codigos": codigos,
                    "quantidade_registros": grupo["quantidade"],
                }
            )

        repeticoes[ano] = sorted(repeticoes_ano, key=lambda item: str(item["curso"]))

    return repeticoes


def validar_cobertura_desambiguacoes(
    repeticoes: dict[str, list[dict[str, object]]],
    desambiguacoes: dict[int, dict[str, dict[str, str]]],
) -> None:
    faltantes: list[str] = []

    for ano, grupos in repeticoes.items():
        mapa_ano = desambiguacoes.get(int(ano), {})
        for grupo in grupos:
            codigos = grupo["codigos"]
            faltando = [codigo for codigo in codigos if codigo not in mapa_ano]
            if not faltando:
                continue
            faltantes.append(
                f"{ano} | {grupo['curso']} | faltando: {', '.join(faltando)} | presentes: {', '.join(codigos)}"
            )

    if faltantes:
        detalhe = "\n".join(f"- {linha}" for linha in faltantes)
        raise RuntimeError(
            "Ha carreiras repetidas por codigo sem desambiguacao oficial cadastrada:\n"
            f"{detalhe}\nAtualize {CODIGOS_PATH.name} antes de gerar o JSON."
        )


def aplicar_desambiguacoes_oficiais(
    dados: dict[str, list[dict]],
    desambiguacoes: dict[int, dict[str, dict[str, str]]],
) -> dict[str, dict[str, int]]:
    resumo: dict[str, dict[str, int]] = {}

    for ano, registros in dados.items():
        mapa_ano = desambiguacoes.get(int(ano), {})
        info = {"desambiguados": 0}

        for registro in registros:
            spec = mapa_ano.get(registro["codigo"])
            if not spec:
                continue

            curso_original = registro["curso"]
            curso_final = spec["curso"]
            if curso_final != curso_original:
                if "curso_pdf" not in registro:
                    registro["curso_pdf"] = curso_original
                registro["curso"] = curso_final
                registro["curso_desambiguado"] = True
                info["desambiguados"] += 1

            registro["curso_busca"] = curso_final
            registro["campus"] = spec["campus"]

        resumo[ano] = info

    return resumo


def remover_flags_vazias(dados: dict[str, list[dict]]) -> None:
    for registros in dados.values():
        for registro in registros:
            if not registro.get("curso_canonizado"):
                registro.pop("curso_canonizado", None)
            if not registro.get("curso_desambiguado"):
                registro.pop("curso_desambiguado", None)
            if not registro.get("curso_truncado"):
                registro.pop("curso_truncado", None)
            if not registro.get("modalidade"):
                registro.pop("modalidade", None)
            if not registro.get("pontos_possiveis_2fase"):
                registro.pop("pontos_possiveis_2fase", None)


def ler_linhas_pdf(caminho: Path) -> list[str]:
    with pdfplumber.open(caminho) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return [limpar_texto(linha) for linha in texto.splitlines() if limpar_texto(linha)]


def extrair_completo(caminho: Path) -> list[dict]:
    registros: list[dict] = []
    for linha in ler_linhas_pdf(caminho):
        m = LINE_RE_COMPLETO.match(linha)
        if not m:
            continue
        registros.append(
            {
                "codigo": m.group(1),
                "curso": m.group(2).strip(),
                "vagas": int(m.group(3)),
                "inscritos": int(m.group(4)),
                "ausentes": int(m.group(5)),
                "convocados_2fase": int(m.group(6)),
                "convocados_por_vaga": float(m.group(7).replace(",", ".")),
                "pontos_minimo": int(m.group(8)),
                "pontos_maximo": int(m.group(9)),
            }
        )
    return registros


def extrair_reduzido(caminho: Path) -> list[dict]:
    registros: list[dict] = []
    for linha in ler_linhas_pdf(caminho):
        m = LINE_RE_REDUZIDO.match(linha)
        if not m:
            continue
        registros.append(
            {
                "codigo": m.group(1),
                "curso": m.group(2).strip(),
                "convocados_2fase": int(m.group(3)),
                "convocados_por_vaga": float(m.group(4).replace(",", ".")),
                "pontos_minimo": int(m.group(5)),
                "pontos_maximo": int(m.group(6)),
                "pontos_possiveis_2fase": int(m.group(7)),
            }
        )
    return registros


def limpar_nome_carreira(linha: str) -> tuple[str, str] | None:
    m = LINE_RE_CARREIRA.match(linha)
    if not m:
        return None

    codigo = m.group(1)
    nome = NUMERIC_TAIL_RE.sub("", m.group(2)).strip()
    return codigo, nome


def extrair_modalidades(caminho: Path) -> list[dict]:
    registros: list[dict] = []
    carreira_atual: tuple[str, str] | None = None

    def pegar_token_coluna(
        words: list[dict],
        x_min: float,
        x_max: float,
        top_referencia: float,
        top_min: float,
        top_max: float,
        pattern: re.Pattern[str],
        max_top_delta: float | None = None,
    ) -> dict | None:
        candidatos = [
            word
            for word in words
            if top_min <= word["top"] < top_max
            and x_min <= word["x0"] < x_max
            and pattern.fullmatch(word["text"])
        ]
        if not candidatos:
            return None
        if max_top_delta is not None:
            candidatos = [
                word for word in candidatos
                if abs(word["top"] - top_referencia) <= max_top_delta
            ]
        if not candidatos:
            return None
        melhor = min(
            candidatos,
            key=lambda item: (abs(item["top"] - top_referencia), item["x0"]),
        )
        return melhor

    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            words = [
                {**word, "text": limpar_texto(word["text"])}
                for word in page.extract_words(use_text_flow=False, keep_blank_chars=False)
            ]
            words.sort(key=lambda item: (item["top"], item["x0"]))

            anchors: list[dict] = []
            tops_carreira: set[float] = set()
            tops_total: set[float] = set()
            tops_modalidade: set[float] = set()

            for word in words:
                texto = word["text"]
                if not texto:
                    continue
                if word["x0"] < 32 and LINE_RE_CARREIRA.match(texto) and word["top"] not in tops_carreira:
                    tops_carreira.add(word["top"])
                    linha_carreira = [
                        item
                        for item in words
                        if abs(item["top"] - word["top"]) <= 1.8 and item["x0"] < 300
                    ]
                    linha_carreira.sort(key=lambda item: item["x0"])
                    carreira = limpar_nome_carreira(" ".join(item["text"] for item in linha_carreira))
                    if carreira:
                        anchors.append(
                            {
                                "kind": "carreira",
                                "top": word["top"],
                                "codigo": carreira[0],
                                "curso": carreira[1],
                            }
                        )
                elif word["x0"] < 40 and texto.lower().startswith("total") and word["top"] not in tops_total:
                    tops_total.add(word["top"])
                    anchors.append({"kind": "total", "top": word["top"]})
                elif 40 <= word["x0"] <= 50 and texto == MINUS and word["top"] not in tops_modalidade:
                    tops_modalidade.add(word["top"])
                    anchors.append({"kind": "modalidade", "top": word["top"]})

            anchors.sort(key=lambda item: item["top"])

            for index, anchor in enumerate(anchors):
                top = anchor["top"]
                proximo_top = anchors[index + 1]["top"] if index + 1 < len(anchors) else float("inf")

                if anchor["kind"] == "carreira":
                    carreira_atual = (anchor["codigo"], anchor["curso"])
                    continue
                if anchor["kind"] == "total":
                    carreira_atual = None
                    continue
                if anchor["kind"] != "modalidade" or not carreira_atual:
                    continue

                linha_mesmo_top = [
                    word
                    for word in words
                    if abs(word["top"] - top) <= 1.8 and word["x0"] < 300
                ]
                linha_mesmo_top.sort(key=lambda item: item["x0"])
                rotulo = " ".join(word["text"] for word in linha_mesmo_top).strip()
                rotulo = rotulo.lstrip(MINUS).strip()
                if not rotulo:
                    continue

                faixa_top_min = top - 7.5
                faixa_top_max = proximo_top

                vagas = pegar_token_coluna(
                    words, 300, 325, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=4.4
                )
                inscritos = pegar_token_coluna(
                    words, 338, 366, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=4.4
                )
                ausentes = pegar_token_coluna(
                    words, 386, 408, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=4.4
                )
                convocados = pegar_token_coluna(
                    words, 425, 452, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=4.8
                )
                proporcao = pegar_token_coluna(
                    words, 468, 492, top, faixa_top_min, faixa_top_max, LINE_RE_DECIMAL, max_top_delta=4.8
                )
                pontos_minimo = pegar_token_coluna(
                    words, 515, 540, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=6.2
                )
                pontos_maximo = pegar_token_coluna(
                    words, 560, 580, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO, max_top_delta=4.8
                )

                if not all([vagas, inscritos, ausentes, convocados]):
                    continue

                registros.append(
                    {
                        "codigo": carreira_atual[0],
                        "curso": carreira_atual[1],
                        "modalidade": rotulo,
                        "vagas": int(vagas["text"]),
                        "inscritos": int(inscritos["text"]),
                        "ausentes": int(ausentes["text"]),
                        "convocados_2fase": int(convocados["text"]),
                        "convocados_por_vaga": (
                            float(proporcao["text"].replace(",", ".")) if proporcao else None
                        ),
                        "pontos_maximo": int(pontos_maximo["text"]) if pontos_maximo else None,
                        "pontos_minimo": int(pontos_minimo["text"]) if pontos_minimo else None,
                    }
                )

    return registros


def copiar_pdfs(arquivos: dict[int, Path]) -> None:
    PDF_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for caminho in arquivos.values():
        shutil.copy2(caminho, PDF_OUT_DIR / caminho.name)


def resumir_auditoria_modalidades(dados: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    resumo: dict[str, dict[str, int]] = {}
    for ano, registros in dados.items():
        linhas_modalidade = [registro for registro in registros if registro.get("modalidade")]
        linhas_sem_proporcao = sum(1 for registro in linhas_modalidade if registro.get("convocados_por_vaga") is None)
        linhas_sem_minimo = sum(1 for registro in linhas_modalidade if registro.get("pontos_minimo") is None)
        linhas_sem_maximo = sum(1 for registro in linhas_modalidade if registro.get("pontos_maximo") is None)
        linhas_inconsistentes = sum(
            1
            for registro in linhas_modalidade
            if registro.get("pontos_minimo") is not None
            and registro.get("pontos_maximo") is not None
            and registro["pontos_minimo"] > registro["pontos_maximo"]
        )
        resumo[ano] = {
            "sem_proporcao": linhas_sem_proporcao,
            "sem_minimo": linhas_sem_minimo,
            "sem_maximo": linhas_sem_maximo,
            "minimo_maior_que_maximo": linhas_inconsistentes,
        }
    return resumo


def main() -> None:
    arquivos = {
        2000: RAW_DIR / "fuvest_2000_corte.pdf",
        2001: RAW_DIR / "fuvest_2001_corte.pdf",
        2002: RAW_DIR / "fuvest_2002_corte.pdf",
        2003: RAW_DIR / "fuvest_2003_corte.pdf",
        2004: RAW_DIR / "fuvest_2004_corte.pdf",
        2005: RAW_DIR / "fuvest_2005_corte.pdf",
        2006: RAW_DIR / "fuvest_2006_corte.pdf",
        2007: RAW_DIR / "fuvest_2007_corte.pdf",
        2008: RAW_DIR / "fuvest_2008_corte.pdf",
        2009: RAW_DIR / "fuvest_2009_corte.pdf",
        2010: RAW_DIR / "fuvest_2010_corte.pdf",
        2011: RAW_DIR / "fuvest_2011_corte.pdf",
        2012: RAW_DIR / "fuvest_2012_corte.pdf",
        2013: RAW_DIR / "fuvest_2013_corte.pdf",
        2014: RAW_DIR / "fuvest_2014_corte.pdf",
        2015: RAW_DIR / "fuvest_2015_corte.pdf",
        2016: RAW_DIR / "fuvest_2016_corte.pdf",
        2017: RAW_DIR / "fuvest_2017_corte.pdf",
        2018: RAW_DIR / "fuv2018_corte.pdf",
        2019: RAW_DIR / "fuvest_2019_notas_de_corte.pdf",
        2020: RAW_DIR / "fuvest_2020_nota_de_corte.pdf",
        2021: RAW_DIR / "fuvest_2021_notas_primeira_fase.pdf",
        2022: RAW_DIR / "fuvest_2022_notas_de_corte.pdf",
        2023: RAW_DIR / "fuvest2023_notas_de_corte.pdf",
        2024: RAW_DIR / "fuvest_2024_notas_de_corte.pdf",
        2025: RAW_DIR / "fuvest_2025_notas_de_corte.pdf",
        2026: RAW_DIR / "fuvest2026_notas_de_corte.pdf",
    }

    anos_reduzidos = set(range(2003, 2012))
    anos_modalidades = set(range(2019, 2027))
    desambiguacoes = carregar_desambiguacoes_oficiais()

    dados: dict[str, list[dict]] = {}
    for ano, caminho in arquivos.items():
        if not caminho.exists():
            raise FileNotFoundError(f"PDF nao encontrado: {caminho}")

        if ano in anos_modalidades:
            registros = extrair_modalidades(caminho)
        elif ano in anos_reduzidos:
            registros = extrair_reduzido(caminho)
        else:
            registros = extrair_completo(caminho)

        if not registros:
            raise RuntimeError(f"Nenhum registro extraido de {caminho.name}")
        dados[str(ano)] = registros

    resumo = canonizar_nomes(dados)
    repeticoes = encontrar_repeticoes_por_codigo(dados)
    validar_cobertura_desambiguacoes(repeticoes, desambiguacoes)
    resumo_desambiguacoes = aplicar_desambiguacoes_oficiais(dados, desambiguacoes)
    resumo_auditoria = resumir_auditoria_modalidades(dados)
    remover_flags_vazias(dados)
    copiar_pdfs(arquivos)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)

    for ano, registros in dados.items():
        info = resumo[ano]
        info_desambiguacao = resumo_desambiguacoes[ano]
        info_auditoria = resumo_auditoria[ano]
        print(
            f"{ano}: {len(registros)} registros | "
            f"{info['canonizados']} nomes ajustados | "
            f"{len(repeticoes[ano])} grupos repetidos auditados | "
            f"{info_desambiguacao['desambiguados']} desambiguados por codigo | "
            f"{info['truncados_restantes']} truncados | "
            f"{info_auditoria['sem_proporcao']} sem proporcao | "
            f"{info_auditoria['sem_minimo']} sem minimo | "
            f"{info_auditoria['sem_maximo']} sem maximo | "
            f"{info_auditoria['minimo_maior_que_maximo']} min>max"
        )

    print(f"\nArquivo gerado com sucesso em: {OUT_PATH}")
    print(f"PDFs copiados para: {PDF_OUT_DIR}")


if __name__ == "__main__":
    main()
