#!/usr/bin/env python3
"""
Notas de Corte — Transferência Externa USP (FUVEST)

O usuário digita o nome do curso e o programa gera um relatório PDF
de página única (via LaTeX + pgfplots) com gráficos de evolução de
notas, concorrência e vagas vs inscritos.

Uso:
    python scripts/legacy/notas_de_corte.py                    # modo interativo
    python scripts/legacy/notas_de_corte.py "engenharia civil" # direto
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
DADOS_PATH = os.path.join(ROOT_DIR, "docs", "dados.json")
OUT_DIR = os.path.join(ROOT_DIR, "out")
DEBUG_DIR = os.path.join(OUT_DIR, "debug")

# Cores ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"


def cor(texto, c):
    return f"{c}{texto}{RESET}"


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def nome_arquivo_seguro(texto: str) -> str:
    """Converte nome de curso para nome de arquivo sem acentos/especiais."""
    s = normalizar(texto)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def escapar_latex(texto: str) -> str:
    """Escapa caracteres especiais para LaTeX."""
    mapa = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    for char, esc in mapa.items():
        texto = texto.replace(char, esc)
    texto = texto.replace("\u2212", "--")
    texto = texto.replace("\u2013", "--")
    texto = texto.replace("\u2014", "---")
    return texto


def carregar_dados() -> dict:
    if not os.path.exists(DADOS_PATH):
        print(cor("Erro: dados.json não encontrado!", RED))
        print("Execute primeiro: python scripts/extrair_dados.py")
        sys.exit(1)
    with open(DADOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def buscar_cursos(dados: dict, termo: str) -> list[tuple[str, dict]]:
    """Retorna lista de (ano, registro) que casam com o termo."""
    termo_norm = normalizar(termo)
    resultados = []
    for ano, registros in sorted(dados.items()):
        for r in registros:
            if termo_norm in normalizar(r["curso"]):
                resultados.append((ano, r))
    return resultados


def calcular_concorrencia(r: dict) -> float:
    """Calcula concorrência como (inscritos - ausentes) / vagas."""
    vagas = r.get("vagas", 0)
    if vagas <= 0:
        return 0.0
    inscritos = r.get("inscritos", 0)
    ausentes = r.get("ausentes", 0)
    return (inscritos - ausentes) / vagas


# ---------------------------------------------------------------------------
# Consolidação de dados para os gráficos
# ---------------------------------------------------------------------------
def consolidar_dados(registros_por_ano: list[tuple[str, dict]]) -> dict:
    """
    Consolida múltiplos registros por ano (quando há variações de nome)
    pegando o de maior concorrência como representativo.
    Retorna dict com anos como chave.
    """
    por_ano = {}
    for ano, r in registros_por_ano:
        ano_int = int(ano)
        if ano_int not in por_ano:
            por_ano[ano_int] = r
        else:
            # Manter o de maior concorrência (mais representativo)
            conc_atual = calcular_concorrencia(por_ano[ano_int])
            conc_novo = calcular_concorrencia(r)
            if conc_novo > conc_atual:
                por_ano[ano_int] = r
    return dict(sorted(por_ano.items()))


# ---------------------------------------------------------------------------
# Geração do LaTeX com pgfplots (página única, sem imagens externas)
# ---------------------------------------------------------------------------
def gerar_coordenadas_notas(dados_consolidados: dict) -> tuple[str, str]:
    """Gera strings de coordenadas pgfplots para notas mín e máx."""
    coords_min = []
    coords_max = []
    for ano, r in dados_consolidados.items():
        minimo = r.get("pontos_minimo") or r.get("nota_de_corte")
        maximo = r.get("pontos_maximo") or r.get("nota_de_corte")
        if minimo is not None:
            coords_min.append(f"({ano},{minimo})")
        if maximo is not None:
            coords_max.append(f"({ano},{maximo})")
    return " ".join(coords_min), " ".join(coords_max)


def gerar_coordenadas_concorrencia(dados_consolidados: dict) -> str:
    """Gera coordenadas para gráfico de barras de concorrência."""
    coords = []
    for ano, r in dados_consolidados.items():
        conc = calcular_concorrencia(r)
        coords.append(f"({ano},{conc:.2f})")
    return " ".join(coords)


def gerar_coordenadas_vagas_inscritos(dados_consolidados: dict) -> tuple[str, str]:
    """Gera coordenadas para vagas e inscritos."""
    coords_vagas = []
    coords_insc = []
    for ano, r in dados_consolidados.items():
        if "vagas" in r:
            coords_vagas.append(f"({ano},{r['vagas']})")
            coords_insc.append(f"({ano},{r['inscritos']})")
    return " ".join(coords_vagas), " ".join(coords_insc)


def gerar_labels_concorrencia(dados_consolidados: dict) -> str:
    """Gera nodes com rótulos detalhados acima das barras de concorrência."""
    nodes = []
    for ano, r in dados_consolidados.items():
        conc = calcular_concorrencia(r)
        vagas = r.get("vagas", "?")
        insc = r.get("inscritos", "?")
        nodes.append(
            f"\\node[above, font=\\tiny] at (axis cs:{ano},{conc:.2f}) "
            f"{{{conc:.2f}}};"
        )
    return "\n        ".join(nodes)


def gerar_labels_vagas_inscritos(dados_consolidados: dict) -> str:
    """Gera nodes com valores acima das barras."""
    nodes = []
    for ano, r in dados_consolidados.items():
        if "vagas" in r:
            nodes.append(
                f"\\node[above, font=\\tiny, green!60!black] at (axis cs:{ano}-0.15,{r['vagas']}) {{{r['vagas']}}};"
            )
            nodes.append(
                f"\\node[above, font=\\tiny, red!70!black] at (axis cs:{ano}+0.15,{r['inscritos']}) {{{r['inscritos']}}};"
            )
    return "\n        ".join(nodes)


def gerar_xtick_list(dados_consolidados: dict) -> str:
    """Gera lista de anos para xtick."""
    return ",".join(str(a) for a in dados_consolidados.keys())


def fmt_br(valor: float, casas: int = 2) -> str:
    """Formata número com separador decimal brasileiro (vírgula)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def gerar_insights(nome_curso: str, dados_consolidados: dict) -> str:
    """Gera comentários analíticos personalizados sobre os dados do curso."""
    nome_esc = escapar_latex(nome_curso)
    anos = sorted(dados_consolidados.keys())
    insights = []

    # Coletar séries
    notas_min = {}
    notas_max = {}
    concorrencias = {}
    vagas_dict = {}
    inscritos_dict = {}
    for ano, r in dados_consolidados.items():
        mn = r.get("pontos_minimo") or r.get("nota_de_corte")
        mx = r.get("pontos_maximo") or r.get("nota_de_corte")
        if mn is not None:
            notas_min[ano] = mn
        if mx is not None:
            notas_max[ano] = mx
        conc = calcular_concorrencia(r) if "vagas" in r else 0
        if conc > 0:
            concorrencias[ano] = conc
        if "vagas" in r:
            vagas_dict[ano] = r["vagas"]
            inscritos_dict[ano] = r["inscritos"]

    # Tendência da nota mínima
    if len(notas_min) >= 2:
        primeiro_ano = min(notas_min)
        ultimo_ano = max(notas_min)
        primeira = notas_min[primeiro_ano]
        ultima = notas_min[ultimo_ano]
        diff = ultima - primeira
        if diff > 0:
            insights.append(
                f"A nota mínima de convocação apresentou tendência de \\textbf{{alta}}, "
                f"saindo de {primeira} pontos em {primeiro_ano} para {ultima} em {ultimo_ano} "
                f"(+{diff} pontos)."
            )
        elif diff < 0:
            insights.append(
                f"A nota mínima de convocação apresentou tendência de \\textbf{{queda}}, "
                f"saindo de {primeira} pontos em {primeiro_ano} para {ultima} em {ultimo_ano} "
                f"({diff} pontos)."
            )
        else:
            insights.append(
                f"A nota mínima de convocação manteve-se \\textbf{{estável}} em "
                f"{ultima} pontos entre {primeiro_ano} e {ultimo_ano}."
            )

    # Ano mais e menos concorrido
    if concorrencias:
        ano_max_conc = max(concorrencias, key=concorrencias.get)
        ano_min_conc = min(concorrencias, key=concorrencias.get)
        media_conc = sum(concorrencias.values()) / len(concorrencias)
        insights.append(
            f"A maior concorrência registrada foi de \\textbf{{{fmt_br(concorrencias[ano_max_conc])}}} "
            f"candidatos por vaga em {ano_max_conc}, enquanto a menor foi de "
            f"\\textbf{{{fmt_br(concorrencias[ano_min_conc])}}} em {ano_min_conc}. "
            f"A média histórica é de {fmt_br(media_conc)} cand./vaga."
        )

    # Vagas — variação e tendência
    if len(vagas_dict) >= 2:
        total_vagas = sum(vagas_dict.values())
        total_insc = sum(inscritos_dict.values())
        ultimo_ano_v = max(vagas_dict)
        insights.append(
            f"Ao longo dos editais com dados completos, foram ofertadas "
            f"\\textbf{{{total_vagas}}} vagas no total e registradas "
            f"\\textbf{{{total_insc}}} inscrições. "
            f"No último edital ({ultimo_ano_v}), foram "
            f"{vagas_dict[ultimo_ano_v]} vagas para {inscritos_dict[ultimo_ano_v]} inscritos."
        )

    # Nota máxima recorde
    if notas_max:
        ano_recorde = max(notas_max, key=notas_max.get)
        insights.append(
            f"A maior nota entre os convocados foi de \\textbf{{{notas_max[ano_recorde]}}} pontos, "
            f"registrada no edital de {ano_recorde}."
        )

    # Montar LaTeX
    if not insights:
        return ""
    itens = "\n".join(f"\\item {s}" for s in insights)
    return (
        r"\vspace{0.1cm}" "\n"
        r"{\small" "\n"
        r"\textbf{\textcolor{uspazul}{Análise dos dados:}}" "\n"
        r"\begin{itemize}\setlength{\itemsep}{1pt}\setlength{\parskip}{0pt}" "\n"
        + itens + "\n"
        r"\end{itemize}}" "\n"
    )


def _gerar_breakdown_latex(nome_curso: str, breakdowns: dict) -> str:
    """Gera página(s) de detalhamento por subcategoria."""
    if not breakdowns:
        return ""

    nome_esc = escapar_latex(nome_curso)
    blocos = []

    for categoria, subcats in breakdowns.items():
        cat_esc = escapar_latex(categoria)
        blocos.append(r"\newpage")
        blocos.append(r"\enlargethispage{1cm}")
        blocos.append(r"\begin{center}")
        blocos.append(
            r"{\large\bfseries\textcolor{uspazul}{Detalhamento por "
            + cat_esc + r" --- " + nome_esc + r"}}"
        )
        blocos.append(r"\end{center}")
        blocos.append(r"\vspace{0.2cm}")

        # Tabela comparativa: cada subcategoria com média de concorrência,
        # total de vagas, total de inscritos, faixa de notas
        blocos.append(r"\begin{center}")
        blocos.append(r"\small")
        blocos.append(r"\begin{tabular}{l c c c c c c}")
        blocos.append(r"    \toprule")
        blocos.append(
            r"    \textbf{" + cat_esc + r"} & \textbf{Anos} & "
            r"\textbf{Vagas} & \textbf{Inscritos} & "
            r"\textbf{Conc. média} & \textbf{Nota mín.} & \textbf{Nota máx.} \\"
        )
        blocos.append(r"    \midrule")

        subcat_dados = {}
        for subcat_nome, registros in sorted(subcats.items()):
            dados_c = consolidar_dados(registros)
            total_vagas = 0
            total_insc = 0
            total_aus = 0
            concs = []
            notas_min_list = []
            notas_max_list = []
            for ano, r in dados_c.items():
                if "vagas" in r:
                    total_vagas += r["vagas"]
                    total_insc += r["inscritos"]
                    total_aus += r.get("ausentes", 0)
                    c = calcular_concorrencia(r)
                    if c > 0:
                        concs.append(c)
                mn = r.get("pontos_minimo") or r.get("nota_de_corte")
                mx = r.get("pontos_maximo") or r.get("nota_de_corte")
                if mn is not None:
                    notas_min_list.append(mn)
                if mx is not None:
                    notas_max_list.append(mx)

            media_conc = sum(concs) / len(concs) if concs else 0
            nota_min_s = str(min(notas_min_list)) if notas_min_list else "---"
            nota_max_s = str(max(notas_max_list)) if notas_max_list else "---"
            n_anos = len(dados_c)
            sub_esc = escapar_latex(subcat_nome)

            blocos.append(
                f"    {sub_esc} & {n_anos} & {total_vagas} & {total_insc} & "
                f"{fmt_br(media_conc)} & {nota_min_s} & {nota_max_s} \\\\"
            )
            subcat_dados[subcat_nome] = {
                "dados": dados_c,
                "media_conc": media_conc,
                "total_vagas": total_vagas,
                "total_insc": total_insc,
            }

        blocos.append(r"    \bottomrule")
        blocos.append(r"\end{tabular}")
        blocos.append(r"\end{center}")

        # Gráfico comparativo de concorrência média por subcategoria
        if len(subcat_dados) >= 2:
            bar_entries = []
            symbolic = []
            for i, (nome, info) in enumerate(sorted(subcat_dados.items())):
                bar_entries.append(f"({i},{info['media_conc']:.2f})")
                symbolic.append(escapar_latex(nome))

            xtick_str = ",".join(str(i) for i in range(len(symbolic)))
            xticklabels = ",".join(symbolic)
            coords_str = " ".join(bar_entries)
            max_val = max(info["media_conc"] for info in subcat_dados.values())
            ymax_bd = f"{max(max_val * 1.35, 1):.1f}"

            blocos.append(r"\vspace{0.3cm}")
            blocos.append(r"\begin{center}")
            blocos.append(r"\begin{tikzpicture}")
            blocos.append(r"\begin{axis}[")
            blocos.append(r"    width=0.85\textwidth, height=5.5cm,")
            blocos.append(
                r"    title={\footnotesize\bfseries Concorrência média por "
                + cat_esc + r"},"
            )
            blocos.append(r"    ybar=4pt, bar width=14pt,")
            blocos.append(f"    xtick={{{xtick_str}}},")
            blocos.append(f"    xticklabels={{{xticklabels}}},")
            blocos.append(r"    xticklabel style={font=\small},")
            blocos.append(
                r"    yticklabel style={font=\small, /pgf/number format/use comma},"
            )
            blocos.append(r"    ylabel style={font=\small},")
            blocos.append(r"    ylabel={Cand./vaga},")
            blocos.append(f"    ymin=0, ymax={ymax_bd},")
            blocos.append(r"    grid=major, grid style={gray!20},")
            blocos.append(r"    nodes near coords,")
            blocos.append(
                r"    nodes near coords style={font=\small, /pgf/number format/fixed,"
            )
            blocos.append(
                r"        /pgf/number format/precision=2, /pgf/number format/use comma},"
            )
            blocos.append(r"]")
            blocos.append(
                r"\addplot[fill=blue!50, draw=blue!80!black] coordinates {"
                + coords_str + r"};"
            )
            blocos.append(r"\end{axis}")
            blocos.append(r"\end{tikzpicture}")
            blocos.append(r"\end{center}")

        # Gráficos de evolução da nota mínima por subcategoria (sobrepostos)
        if len(subcat_dados) >= 2:
            cores = [
                "red!70!black", "blue!70!black", "green!60!black",
                "orange!80!black", "purple!70!black", "cyan!60!black",
            ]
            all_anos = set()
            series = {}
            for nome_s, info in sorted(subcat_dados.items()):
                pts = []
                for ano, r in info["dados"].items():
                    mn = r.get("pontos_minimo") or r.get("nota_de_corte")
                    if mn is not None:
                        pts.append((ano, mn))
                        all_anos.add(ano)
                series[nome_s] = pts

            if all_anos and any(series.values()):
                xticks_bd = ",".join(str(a) for a in sorted(all_anos))
                all_vals = [v for pts in series.values() for _, v in pts]
                mn_v = min(all_vals)
                mx_v = max(all_vals)
                mg = max((mx_v - mn_v) * 0.18, 5)
                ymin_bd = f"{max(0, mn_v - mg):.0f}"
                ymax_bd2 = f"{mx_v + mg:.0f}"

                blocos.append(r"\vspace{0.3cm}")
                blocos.append(r"\begin{center}")
                blocos.append(r"\begin{tikzpicture}")
                blocos.append(r"\begin{axis}[")
                blocos.append(r"    width=0.85\textwidth, height=5.5cm,")
                blocos.append(
                    r"    title={\footnotesize\bfseries Evolução da nota mínima por "
                    + cat_esc + r"},"
                )
                blocos.append(f"    xtick={{{xticks_bd}}},")
                blocos.append(
                    r"    xticklabel style={font=\small, /pgf/number format/1000 sep={}},"
                )
                blocos.append(r"    yticklabel style={font=\small},")
                blocos.append(r"    ylabel style={font=\small},")
                blocos.append(r"    ylabel={Pontos},")
                blocos.append(f"    ymin={ymin_bd}, ymax={ymax_bd2},")
                blocos.append(r"    grid=major, grid style={gray!20},")
                blocos.append(
                    r"    legend style={font=\small, at={(0.02,0.98)}, anchor=north west,"
                )
                blocos.append(
                    r"        fill opacity=0.7, text opacity=1},"
                )
                blocos.append(r"    mark size=2.5pt,")
                blocos.append(r"]")

                for i, (nome_s, pts) in enumerate(sorted(series.items())):
                    cor_i = cores[i % len(cores)]
                    coords = " ".join(f"({a},{v})" for a, v in pts)
                    nome_leg = escapar_latex(nome_s)
                    blocos.append(
                        f"\\addplot[color={cor_i}, mark=*, thick] coordinates {{{coords}}};"
                    )
                    blocos.append(f"\\addlegendentry{{{nome_leg}}}")

                blocos.append(r"\end{axis}")
                blocos.append(r"\end{tikzpicture}")
                blocos.append(r"\end{center}")

    return "\n".join(blocos)


def gerar_latex_completo(nome_curso: str, registros_por_ano: list[tuple[str, dict]],
                         filtros_texto: str = "", breakdowns: dict = None) -> str:
    """Gera o documento LaTeX completo com pgfplots."""
    dados = consolidar_dados(registros_por_ano)
    nome_esc = escapar_latex(nome_curso)
    filtros_esc = escapar_latex(filtros_texto) if filtros_texto else ""

    anos_list = sorted(str(a) for a in dados.keys())
    xticks = gerar_xtick_list(dados)

    # Coordenadas dos gráficos
    coords_min, coords_max = gerar_coordenadas_notas(dados)
    coords_conc = gerar_coordenadas_concorrencia(dados)
    coords_vagas, coords_insc = gerar_coordenadas_vagas_inscritos(dados)

    # Determinar se temos dados completos (2020+) ou apenas nota de corte (2019)
    tem_completo = any("vagas" in r for r in dados.values())

    # --- Tabela compacta (resumo em uma linha por ano) ---
    linhas_tabela = []
    for ano, r in dados.items():
        if "vagas" in r:
            minimo = r.get("pontos_minimo")
            maximo = r.get("pontos_maximo")
            min_s = str(minimo) if minimo is not None else "---"
            max_s = str(maximo) if maximo is not None else "---"
            conc_s = fmt_br(calcular_concorrencia(r))
            aus_s = str(r.get("ausentes", "---"))
            linhas_tabela.append(
                f"        {ano} & {r['vagas']} & {r['inscritos']} & "
                f"{aus_s} & {conc_s} & {min_s} & {max_s} \\\\"
            )
        else:
            nota = r.get("nota_de_corte")
            nota_s = str(nota) if nota is not None else "---"
            linhas_tabela.append(
                f"        {ano} & --- & --- & --- & --- & {nota_s} & {nota_s} \\\\"
            )
    tabela_corpo = "\n".join(linhas_tabela)

    # --- Insights personalizados ---
    bloco_insights = gerar_insights(nome_curso, dados)

    # --- Estilo pgfplots compartilhado para eixo X sem separador de milhar ---
    # /pgf/number format/1000 sep={} impede "2.019" / "2,019"
    xstyle = r"font=\small, /pgf/number format/1000 sep={}"

    # --- Calcular ymin/ymax dinâmico para notas (evitar rótulos fora da área) ---
    all_notas = []
    for r in dados.values():
        mn = r.get("pontos_minimo") or r.get("nota_de_corte")
        mx = r.get("pontos_maximo") or r.get("nota_de_corte")
        if mn is not None:
            all_notas.append(mn)
        if mx is not None:
            all_notas.append(mx)
    if all_notas:
        nota_min_val = min(all_notas)
        nota_max_val = max(all_notas)
        margem = max((nota_max_val - nota_min_val) * 0.18, 5)
        ymin_notas = f"{max(0, nota_min_val - margem):.0f}"
        ymax_notas = f"{nota_max_val + margem:.0f}"
    else:
        ymin_notas = "0"
        ymax_notas = "100"

    # --- Calcular ymax dinâmico para concorrência ---
    max_conc = max((calcular_concorrencia(r) for r in dados.values()), default=1)
    ymax_conc = f"{max_conc * 1.25:.1f}"

    # --- Calcular ymax dinâmico para vagas/inscritos ---
    max_vi = max(
        (max(r.get("vagas", 0), r.get("inscritos", 0)) for r in dados.values()),
        default=1,
    )
    ymax_vi = str(int(max_vi * 1.25))

    # --- Bloco do gráfico de concorrência ---
    bloco_concorrencia = ""
    if tem_completo and coords_conc:
        bloco_concorrencia = r"""
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=0.92\textwidth, height=4.5cm,
    title={\footnotesize\bfseries Concorrência (candidatos/vaga)},
    ybar=2pt, bar width=10pt,
    xtick={""" + xticks + r"""},
    xticklabel style={""" + xstyle + r"""},
    yticklabel style={font=\small, /pgf/number format/use comma},
    ylabel style={font=\small},
    ylabel={Cand./vaga},
    ymin=0, ymax=""" + ymax_conc + r""",
    grid=major, grid style={gray!20},
    nodes near coords,
    nodes near coords style={font=\small, /pgf/number format/fixed,
        /pgf/number format/precision=1, /pgf/number format/use comma},
    every node near coord/.append style={above, font=\small},
]
\addplot[fill=orange!70, draw=orange!90!black] coordinates {""" + coords_conc + r"""};
\end{axis}
\end{tikzpicture}
\end{center}"""

    # --- Bloco do gráfico vagas vs inscritos ---
    bloco_vagas = ""
    if tem_completo and coords_vagas:
        bloco_vagas = r"""
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=0.92\textwidth, height=4.5cm,
    title={\footnotesize\bfseries Vagas ofertadas vs Inscritos},
    ybar=2pt, bar width=8pt,
    xtick={""" + xticks + r"""},
    xticklabel style={""" + xstyle + r"""},
    yticklabel style={font=\small},
    ylabel style={font=\small},
    ylabel={Quantidade},
    ymin=0, ymax=""" + ymax_vi + r""",
    grid=major, grid style={gray!20},
    legend style={font=\small, at={(0.02,0.98)}, anchor=north west,
        fill opacity=0.7, text opacity=1},
    nodes near coords, nodes near coords style={font=\small},
]
\addplot[fill=green!60, draw=green!80!black] coordinates {""" + coords_vagas + r"""};
\addplot[fill=red!60, draw=red!80!black] coordinates {""" + coords_insc + r"""};
\legend{Vagas, Inscritos}
\end{axis}
\end{tikzpicture}
\end{center}"""

    # Linha de filtros para o subtítulo
    linha_filtros = ""
    if filtros_esc:
        linha_filtros = r"\\[1pt]" "\n    " r"{\small\textit{" + filtros_esc + r"}}"

    tex = r"""\documentclass[11pt, a4paper]{article}

%% Pacotes
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazilian]{babel}
\usepackage[margin=1.5cm]{geometry}
\usepackage{pgfplots}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{hyperref}

\pgfplotsset{compat=1.18}
\pagestyle{empty}

%% Cores
\definecolor{uspazul}{HTML}{004A8D}

\hypersetup{colorlinks=true, urlcolor=uspazul}

\begin{document}
\enlargethispage{1cm}

%% -----------------------------------------------------------------------
%% Título
%% -----------------------------------------------------------------------
\begin{center}
    {\large\bfseries\textcolor{uspazul}{Relatório --- Transferência Externa USP (FUVEST)}}\\[3pt]
    {\Large\bfseries Curso: """ + nome_esc + r"""}""" + linha_filtros + r"""\\[2pt]
    {\small Dados disponíveis: """ + ", ".join(anos_list) + r"""}
\end{center}

\vspace{0.1cm}

%% -----------------------------------------------------------------------
%% Tabela resumo (centralizada)
%% -----------------------------------------------------------------------
\begin{center}
\small
\begin{tabular}{c c c c c c c}
    \toprule
    \textbf{Ano} & \textbf{Vagas} & \textbf{Inscritos} & \textbf{Ausentes} & \textbf{Concorrência} & \textbf{Nota Mínima} & \textbf{Nota Máxima} \\
    \midrule
""" + tabela_corpo + r"""
    \bottomrule
\end{tabular}
\end{center}

\vspace{0.1cm}

%% -----------------------------------------------------------------------
%% Gráfico 1: Evolução das Notas de Corte
%% -----------------------------------------------------------------------
\begin{center}
\begin{tikzpicture}
\begin{axis}[
    width=0.92\textwidth, height=5.2cm,
    title={\footnotesize\bfseries Evolução das Notas de Corte},
    xtick={""" + xticks + r"""},
    xticklabel style={font=\small, /pgf/number format/1000 sep={}},
    yticklabel style={font=\small},
    ylabel style={font=\small},
    ylabel={Pontos},
    ymin=""" + ymin_notas + r""", ymax=""" + ymax_notas + r""",
    grid=major, grid style={gray!20},
    legend style={font=\small, at={(0.02,0.98)}, anchor=north west,
        fill opacity=0.6, text opacity=1, draw opacity=0.5},
    clip=false,
    mark size=2.5pt,
]
\addplot[color=red!70!black, mark=*, thick,
    nodes near coords, nodes near coords style={font=\small, above, red!70!black}]
    coordinates {""" + coords_min + r"""};
\addplot[color=green!60!black, mark=square*, thick,
    nodes near coords, nodes near coords style={font=\small, below, green!60!black}]
    coordinates {""" + coords_max + r"""};
\legend{Nota mínima (convocado), Nota máxima (convocado)}
\end{axis}
\end{tikzpicture}
\end{center}

%% -----------------------------------------------------------------------
%% Gráfico 2: Concorrência
%% -----------------------------------------------------------------------
""" + bloco_concorrencia + r"""

%% -----------------------------------------------------------------------
%% Gráfico 3: Vagas vs Inscritos
%% -----------------------------------------------------------------------
""" + bloco_vagas + r"""

%% -----------------------------------------------------------------------
%% Análise / Insights
%% -----------------------------------------------------------------------
""" + bloco_insights + r"""

\vfill
\noindent\rule{\textwidth}{0.4pt}
\vspace{2pt}
{\centering\footnotesize\textcolor{gray}{Dados extraídos dos editais oficiais da FUVEST --- Gerado automaticamente}\par}
\vspace{1pt}
{\centering\footnotesize\textcolor{uspazul}{\url{https://github.com/qedxyzyt-dot/notas-de-corte-transferencia-usp}}\par}

""" + _gerar_breakdown_latex(nome_curso, breakdowns or {}) + r"""

\end{document}
"""
    return tex


# ---------------------------------------------------------------------------
# Compilação LaTeX → PDF
# ---------------------------------------------------------------------------
def compilar_pdf(tex_source: str, nome_arquivo: str) -> str | None:
    """Compila .tex → .pdf e retorna o caminho do PDF gerado."""
    tmpdir = tempfile.mkdtemp(prefix="relatorio_transf_")

    tex_path = os.path.join(tmpdir, "relatorio.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_source)

    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True, text=True, cwd=tmpdir, timeout=60
        )

    pdf_tmp = os.path.join(tmpdir, "relatorio.pdf")
    if not os.path.exists(pdf_tmp):
        print(cor("  Erro ao compilar o LaTeX. Linhas de erro:", RED))
        log_path = os.path.join(tmpdir, "relatorio.log")
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for linha in f:
                    if linha.startswith("!") or "Error" in linha:
                        print(f"    {linha.rstrip()}")
        print(f"\n  Diretório temporário: {tmpdir}")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    destino = os.path.join(OUT_DIR, f"{nome_arquivo}.pdf")
    shutil.move(pdf_tmp, destino)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return destino


# ---------------------------------------------------------------------------
# Pipeline: curso → relatório PDF
# ---------------------------------------------------------------------------
def gerar_relatorio(dados: dict, nome_curso: str, registros_por_ano: list[tuple[str, dict]],
                    filtros_texto: str = "", breakdowns: dict = None):
    """Gera o relatório PDF para um curso."""
    print(cor(f"\n  Gerando relatório para: {nome_curso}", CYAN))

    tex = gerar_latex_completo(nome_curso, registros_por_ano, filtros_texto, breakdowns)
    print(cor("    ✓ Código LaTeX gerado (pgfplots nativo)", GREEN))

    # Salvar tex para debug
    os.makedirs(DEBUG_DIR, exist_ok=True)
    debug_path = os.path.join(DEBUG_DIR, "_debug_tex.tex")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(tex)

    nome_arquivo = "relatorio_" + nome_arquivo_seguro(nome_curso)
    destino = compilar_pdf(tex, nome_arquivo)

    if destino:
        print(cor(f"\n  ✓ Relatório gerado: {destino}", GREEN + BOLD))
    else:
        print(cor("\n  ✗ Falha ao gerar o PDF.", RED))

    return destino


# ---------------------------------------------------------------------------
# Parsing de atributos do curso (nome base, localização, período)
# ---------------------------------------------------------------------------
LOCALIZACOES_CONHECIDAS = [
    "São Paulo Quadrilátero", "São Paulo Leste",
    "São Paulo Butantã/ Quadrilátero", "São Paulo Butantã",
    "São Paulo", "São Carlos", "Ribeirão Preto",
    "Piracicaba", "Pirassununga", "Lorena", "Bauru",
]

# Mapa de normalização: variantes → nome canônico do campus
_LOC_NORMALIZAR = {
    "São Paulo Butantã": "São Paulo",
    "São Paulo Butantã/ Quadrilátero": "São Paulo",
}

PERIODOS_CONHECIDOS = [
    "Integral", "Diurno", "Noturno", "Matutino", "Vespertino",
]

# Separadores usados nos nomes dos cursos (hífen normal e en-dash)
_SEP_RE = re.compile(r"\s*[\-\u2212\u2013]\s*")


def _extrair_localizacao_raw(nome: str) -> str | None:
    """Extrai a localização bruta do nome do curso, se presente."""
    nome_norm = normalizar(nome)
    if "usp leste" in nome_norm:
        return "São Paulo Leste"
    for loc in LOCALIZACOES_CONHECIDAS:
        if normalizar(loc) in nome_norm:
            return loc
    return None


def _extrair_localizacao(nome: str) -> str | None:
    """Extrai a localização normalizada do nome do curso."""
    raw = _extrair_localizacao_raw(nome)
    if raw is None:
        return None
    return _LOC_NORMALIZAR.get(raw, raw)


def _extrair_periodo(nome: str) -> str | None:
    """Extrai o período/turno do nome do curso, se presente."""
    nome_norm = normalizar(nome)
    for per in PERIODOS_CONHECIDOS:
        if normalizar(per) in nome_norm:
            return per
    return None


def _extrair_nome_base(nome: str) -> str:
    """
    Extrai o nome-base do curso removendo localização, período,
    informações de semestre, grau (Bacharelado/Licenciatura) e prefixos.
    """
    # Remover parênteses e seu conteúdo
    s = re.sub(r"\([^)]*\)", "", nome)
    # Separar por hífen/en-dash
    partes = _SEP_RE.split(s)

    partes_uteis = []
    ignorar = {normalizar(l) for l in LOCALIZACOES_CONHECIDAS}
    ignorar |= {normalizar(p) for p in PERIODOS_CONHECIDOS}

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        pn = normalizar(parte)
        # Ignorar semestres (ex: "2º semestre", "1º seme", "2º se", "1º s")
        if re.match(r"^\d+[ºo°]\s*s", pn):
            continue
        if pn in ignorar:
            continue
        partes_uteis.append(parte)

    resultado = " — ".join(partes_uteis) if partes_uteis else nome
    # Remover prefixo "Bacharelado em " / "Licenciatura e Bacharelado em " etc.
    resultado = re.sub(
        r"^(?:Bacharelado\s+e\s+Licenciatura\s+em\s+|"
        r"Licenciatura\s+e\s+Bacharelado\s+em\s+|"
        r"Bacharelado\s+em\s+|"
        r"Curso\s+de\s+Graduação\s+em\s+)",
        "", resultado, flags=re.IGNORECASE,
    )
    # Remover sufixos soltos de grau
    resultado = re.sub(
        r"\s*[—\-\u2013\u2212]\s*(?:Bacharelado|Licenciatura|"
        r"Bacharelado\s+e\s+Licenciatura|Licenciatura\s+e\s+Bacharelado)\s*$",
        "", resultado, flags=re.IGNORECASE,
    )
    resultado = re.sub(r"\s*(?:Bacharelado|Licenciatura)\s*$", "", resultado,
                       flags=re.IGNORECASE)
    return resultado.strip()


def _inferir_atributos(resultados: list[tuple[str, dict]]) -> dict[int, dict]:
    """
    Para cada registro, infere localização e período a partir de outros
    registros do mesmo curso-base quando a informação está ausente.
    Retorna dict id(r) → {"loc": str, "per": str}.
    """
    # Agrupar por base
    por_base: dict[str, list[tuple[str, dict]]] = {}
    for ano, r in resultados:
        base = _extrair_nome_base(r["curso"])
        por_base.setdefault(base, []).append((ano, r))

    atributos: dict[int, dict] = {}
    for base, registros in por_base.items():
        # Coletar localizações e períodos conhecidos para essa base
        locs_conhecidas = set()
        pers_conhecidos = set()
        for _, r in registros:
            loc = _extrair_localizacao(r["curso"])
            per = _extrair_periodo(r["curso"])
            if loc:
                locs_conhecidas.add(loc)
            if per:
                pers_conhecidos.add(per)

        # Se há exatamente 1 localização conhecida, inferir para os que faltam
        loc_padrao = list(locs_conhecidas)[0] if len(locs_conhecidas) == 1 else None
        per_padrao = list(pers_conhecidos)[0] if len(pers_conhecidos) == 1 else None

        for _, r in registros:
            loc = _extrair_localizacao(r["curso"]) or loc_padrao
            per = _extrair_periodo(r["curso"]) or per_padrao
            atributos[id(r)] = {"loc": loc, "per": per}

    return atributos


def _escolher_multiplos(opcoes: list[str], titulo: str) -> list[str] | None:
    """
    Apresenta uma lista de opções e permite selecionar uma, várias ou todas.
    Retorna None se o usuário cancelar.
    """
    if len(opcoes) == 1:
        return opcoes  # sem necessidade de escolher

    print(cor(f"\n  {titulo}\n", BOLD))
    print(f"  {cor('  T.', YELLOW)} {cor('TODOS', BOLD)}")
    for i, op in enumerate(opcoes, 1):
        print(f"  {cor(f'{i:3d}.', CYAN)} {op}")
    print(f"  {cor('  0.', DIM)} Cancelar")
    print()

    entrada = input(cor("  Escolha (T=todos, números separados por vírgula, ou 0): ", GREEN)).strip().lower()

    if entrada == "0":
        return None
    if entrada == "t" or entrada == "":
        return opcoes

    # Parsear seleção múltipla: "1,3,5" ou "1 3 5" ou "1, 3, 5"
    indices = []
    for token in re.split(r"[,\s]+", entrada):
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(opcoes):
                indices.append(idx - 1)
    if not indices:
        return None

    return [opcoes[i] for i in sorted(set(indices))]


# ---------------------------------------------------------------------------
# Interface no terminal (com filtros multi-nível)
# ---------------------------------------------------------------------------
def selecionar_curso(dados: dict, termo: str) -> tuple[str, list, str] | None:
    """
    Busca cursos, agrupa por nome-base, e oferece filtros de
    localização e período. Retorna (nome, registros, filtros_texto) ou None.
    """
    resultados = buscar_cursos(dados, termo)
    if not resultados:
        print(cor(f"\n  Nenhum curso encontrado para '{termo}'.", RED))
        return None

    # Inferir localização e período para registros com informação ausente
    atribs = _inferir_atributos(resultados)

    # --- Passo 1: agrupar por nome-base ---
    bases: dict[str, list[tuple[str, dict]]] = {}
    for ano, r in resultados:
        base = _extrair_nome_base(r["curso"])
        bases.setdefault(base, []).append((ano, r))

    base_escolhidas: list[str]
    if len(bases) == 1:
        base_escolhidas = list(bases.keys())
    else:
        nomes_bases = list(bases.keys())
        sel = _escolher_multiplos(nomes_bases, "Cursos encontrados — selecione:")
        if sel is None:
            return None
        base_escolhidas = sel

    # Filtrar resultados pelas bases escolhidas
    filtrados = []
    for b in base_escolhidas:
        filtrados.extend(bases[b])

    # --- Passo 2: filtro de localização ---
    locs_set: dict[str, str] = {}
    for _, r in filtrados:
        loc = atribs[id(r)]["loc"]
        if loc:
            chave = normalizar(loc)
            if chave not in locs_set:
                locs_set[chave] = loc

    loc_escolhidas = list(locs_set.values())
    if len(locs_set) > 1:
        opcoes_loc = sorted(locs_set.values())
        sel = _escolher_multiplos(opcoes_loc, "Localização — selecione:")
        if sel is None:
            return None
        loc_escolhidas = sel

    # Aplicar filtro de localização
    loc_escolhidas_norm = {normalizar(l) for l in loc_escolhidas}
    filtrados2 = []
    for ano, r in filtrados:
        loc = atribs[id(r)]["loc"]
        if loc and normalizar(loc) in loc_escolhidas_norm:
            filtrados2.append((ano, r))
        elif not loc:
            # Sem localização inferida — incluir se não há filtro restritivo
            filtrados2.append((ano, r))
    filtrados = filtrados2

    if not filtrados:
        print(cor("\n  Nenhum registro após filtro de localização.", RED))
        return None

    # --- Passo 3: filtro de período ---
    per_set: dict[str, str] = {}
    for _, r in filtrados:
        per = atribs[id(r)]["per"]
        if per:
            chave = normalizar(per)
            if chave not in per_set:
                per_set[chave] = per

    per_escolhidos = list(per_set.values())
    if len(per_set) > 1:
        opcoes_per = sorted(per_set.values())
        sel = _escolher_multiplos(opcoes_per, "Período / Turno — selecione:")
        if sel is None:
            return None
        per_escolhidos = sel

    # Aplicar filtro de período
    per_escolhidos_norm = {normalizar(p) for p in per_escolhidos}
    filtrados3 = []
    for ano, r in filtrados:
        per = atribs[id(r)]["per"]
        if per and normalizar(per) in per_escolhidos_norm:
            filtrados3.append((ano, r))
        elif not per:
            filtrados3.append((ano, r))
    filtrados = filtrados3

    if not filtrados:
        print(cor("\n  Nenhum registro após filtro de período.", RED))
        return None

    # --- Montar nome e texto de filtros ---
    nome_titulo = " / ".join(base_escolhidas) if len(base_escolhidas) <= 2 else base_escolhidas[0]

    partes_filtro = []
    if len(loc_escolhidas) < len(locs_set):
        partes_filtro.append("Local: " + ", ".join(loc_escolhidas))
    if len(per_escolhidos) < len(per_set):
        partes_filtro.append("Período: " + ", ".join(per_escolhidos))

    filtros_texto = " | ".join(partes_filtro)

    # --- Detectar breakdowns necessários ---
    breakdowns: dict[str, dict[str, list]] = {}

    # Se TODAS as localizações foram selecionadas E havia >1 opção
    if len(locs_set) > 1 and len(loc_escolhidas) == len(locs_set):
        bd_loc: dict[str, list] = {}
        for ano, r in filtrados:
            loc = atribs[id(r)]["loc"] or "Outros"
            bd_loc.setdefault(loc, []).append((ano, r))
        breakdowns["Localização"] = bd_loc

    # Se TODOS os períodos foram selecionados E havia >1 opção
    if len(per_set) > 1 and len(per_escolhidos) == len(per_set):
        bd_per: dict[str, list] = {}
        for ano, r in filtrados:
            per = atribs[id(r)]["per"] or "Outros"
            bd_per.setdefault(per, []).append((ano, r))
        breakdowns["Período"] = bd_per

    # Resumo na tela
    total_anos = sorted(set(a for a, _ in filtrados))
    qtd = len(filtrados)
    print(cor(f"\n  → {qtd} registro(s) selecionado(s) nos anos: {', '.join(total_anos)}", CYAN))
    if filtros_texto:
        print(cor(f"    Filtros: {filtros_texto}", DIM))
    if breakdowns:
        cats = ", ".join(breakdowns.keys())
        print(cor(f"    Detalhamento por: {cats} (página adicional)", DIM))

    return nome_titulo, filtrados, filtros_texto, breakdowns


def modo_interativo(dados: dict):
    """Loop interativo: usuário digita cursos, programa gera PDFs."""
    anos_disponiveis = sorted(dados.keys())
    print(cor("\n  ╔══════════════════════════════════════════════════════════════╗", CYAN))
    print(cor("  ║", CYAN) + cor("    Notas de Corte — Transferência Externa USP (FUVEST)    ", BOLD) + cor("║", CYAN))
    print(cor("  ╚══════════════════════════════════════════════════════════════╝", CYAN))
    print(cor(f"  Anos disponíveis: {', '.join(anos_disponiveis)}", DIM))
    print()
    print(f"  Digite o nome do curso para gerar um relatório PDF.")
    print(f"  {cor('Digite 0 para sair.', DIM)}")

    while True:
        print()
        termo = input(cor("  Curso: ", GREEN)).strip()

        if not termo or termo == "0":
            print(cor("\n  Até mais! Boa sorte na transferência!\n", GREEN))
            break

        resultado = selecionar_curso(dados, termo)
        if resultado is None:
            continue

        nome_curso, registros, filtros_texto, breakdowns = resultado
        gerar_relatorio(dados, nome_curso, registros, filtros_texto, breakdowns)


def main():
    dados = carregar_dados()

    if len(sys.argv) >= 2:
        termo = " ".join(sys.argv[1:])
        resultado = selecionar_curso(dados, termo)
        if resultado:
            nome_curso, registros, filtros_texto, breakdowns = resultado
            gerar_relatorio(dados, nome_curso, registros, filtros_texto, breakdowns)
    else:
        modo_interativo(dados)


if __name__ == "__main__":
    main()
