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

# Diferenciações oficiais consultadas nos guias e listagens da própria FUVEST
# para carreiras com o mesmo nome-base e códigos distintos.
DESAMBIGUACOES_CODIGO: dict[int, dict[str, dict[str, str]]] = {
    2024: {
        "105": {"curso": "Arquitetura (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "106": {"curso": "Arquitetura (São Carlos)", "campus": "São Carlos"},
        "120": {
            "curso": "Biblioteconomia e Ciência da Informação (São Paulo Butantã)",
            "campus": "São Paulo Butantã",
        },
        "121": {
            "curso": "Biblioteconomia e Ciência da Informação (Ribeirão Preto)",
            "campus": "Ribeirão Preto",
        },
        "205": {"curso": "Música (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "206": {"curso": "Música (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "210": {"curso": "Pedagogia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "211": {"curso": "Pedagogia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "445": {
            "curso": "Fisioterapia (São Paulo Butantã/Quadrilátero)",
            "campus": "São Paulo Butantã/Quadrilátero",
        },
        "446": {"curso": "Fisioterapia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "450": {
            "curso": "Fonoaudiologia (São Paulo Butantã/Quadrilátero)",
            "campus": "São Paulo Butantã/Quadrilátero",
        },
        "451": {
            "curso": "Fonoaudiologia (Bauru e Ribeirão Preto)",
            "campus": "Bauru e Ribeirão Preto",
        },
        "460": {"curso": "Medicina (São Paulo Quadrilátero)", "campus": "São Paulo Quadrilátero"},
        "461": {"curso": "Medicina (Bauru)", "campus": "Bauru"},
        "462": {"curso": "Medicina (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "465": {"curso": "Medicina Veterinária (Pirassununga)", "campus": "Pirassununga"},
        "466": {"curso": "Medicina Veterinária (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "485": {"curso": "Psicologia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "486": {"curso": "Psicologia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "495": {
            "curso": "Terapia Ocupacional (São Paulo Butantã/Quadrilátero)",
            "campus": "São Paulo Butantã/Quadrilátero",
        },
        "496": {"curso": "Terapia Ocupacional (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "800": {
            "curso": "Química (São Paulo Butantã e Ribeirão Preto)",
            "campus": "São Paulo Butantã e Ribeirão Preto",
        },
        "801": {"curso": "Química (Ribeirão Preto)", "campus": "Ribeirão Preto"},
    },
    2025: {
        "116": {"curso": "Psicologia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "117": {"curso": "Psicologia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "320": {"curso": "Química (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "321": {
            "curso": "Química (São Paulo Butantã e São Carlos)",
            "campus": "São Paulo Butantã e São Carlos",
        },
        "504": {"curso": "Arquitetura (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "505": {"curso": "Arquitetura (São Carlos)", "campus": "São Carlos"},
        "509": {
            "curso": "Biblioteconomia e Ciência da Informação (São Paulo Butantã)",
            "campus": "São Paulo Butantã",
        },
        "510": {
            "curso": "Biblioteconomia e Ciência da Informação (Ribeirão Preto)",
            "campus": "Ribeirão Preto",
        },
        "524": {"curso": "Música (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "525": {"curso": "Música (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "526": {"curso": "Pedagogia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "527": {"curso": "Pedagogia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
    },
    2026: {
        "116": {"curso": "Psicologia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "117": {"curso": "Psicologia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "320": {"curso": "Química (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "321": {
            "curso": "Química (São Paulo Butantã e São Carlos)",
            "campus": "São Paulo Butantã e São Carlos",
        },
        "504": {"curso": "Arquitetura (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "505": {"curso": "Arquitetura (São Carlos)", "campus": "São Carlos"},
        "523": {"curso": "Música (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "524": {"curso": "Música (Ribeirão Preto)", "campus": "Ribeirão Preto"},
        "525": {"curso": "Pedagogia (São Paulo Butantã)", "campus": "São Paulo Butantã"},
        "526": {"curso": "Pedagogia (Ribeirão Preto)", "campus": "Ribeirão Preto"},
    },
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


def aplicar_desambiguacoes_oficiais(dados: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    resumo: dict[str, dict[str, int]] = {}

    for ano, registros in dados.items():
        mapa_ano = DESAMBIGUACOES_CODIGO.get(int(ano), {})
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
    ) -> str | None:
        candidatos = [
            word
            for word in words
            if top_min <= word["top"] < top_max
            and x_min <= word["x0"] < x_max
            and pattern.fullmatch(word["text"])
        ]
        if not candidatos:
            return None
        melhor = min(
            candidatos,
            key=lambda item: (abs(item["top"] - top_referencia), item["x0"]),
        )
        return melhor["text"]

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

                vagas = pegar_token_coluna(words, 300, 325, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)
                inscritos = pegar_token_coluna(words, 340, 365, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)
                ausentes = pegar_token_coluna(words, 388, 407, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)
                convocados = pegar_token_coluna(words, 425, 452, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)
                proporcao = pegar_token_coluna(words, 468, 492, top, faixa_top_min, faixa_top_max, LINE_RE_DECIMAL)
                pontos_minimo = pegar_token_coluna(words, 515, 540, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)
                pontos_maximo = pegar_token_coluna(words, 560, 580, top, faixa_top_min, faixa_top_max, LINE_RE_NUMERO)

                if not all([vagas, inscritos, ausentes, convocados, proporcao, pontos_maximo]):
                    continue

                registros.append(
                    {
                        "codigo": carreira_atual[0],
                        "curso": carreira_atual[1],
                        "modalidade": rotulo,
                        "vagas": int(vagas),
                        "inscritos": int(inscritos),
                        "ausentes": int(ausentes),
                        "convocados_2fase": int(convocados),
                        "convocados_por_vaga": float(proporcao.replace(",", ".")),
                        "pontos_maximo": int(pontos_maximo),
                        "pontos_minimo": int(pontos_minimo) if pontos_minimo and pontos_minimo.isdigit() else None,
                    }
                )

    return registros


def copiar_pdfs(arquivos: dict[int, Path]) -> None:
    PDF_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for caminho in arquivos.values():
        shutil.copy2(caminho, PDF_OUT_DIR / caminho.name)


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
    resumo_desambiguacoes = aplicar_desambiguacoes_oficiais(dados)
    remover_flags_vazias(dados)
    copiar_pdfs(arquivos)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)

    for ano, registros in dados.items():
        info = resumo[ano]
        info_desambiguacao = resumo_desambiguacoes[ano]
        print(
            f"{ano}: {len(registros)} registros | "
            f"{info['canonizados']} nomes ajustados | "
            f"{info_desambiguacao['desambiguados']} desambiguados por codigo | "
            f"{info['truncados_restantes']} truncados"
        )

    print(f"\nArquivo gerado com sucesso em: {OUT_PATH}")
    print(f"PDFs copiados para: {PDF_OUT_DIR}")


if __name__ == "__main__":
    main()
