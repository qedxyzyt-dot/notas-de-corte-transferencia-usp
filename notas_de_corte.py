#!/usr/bin/env python3
"""
Notas de Corte - Transferência Externa USP (FUVEST)

O usuário digita o nome do curso e o programa gera um relatório PDF
completo (via LaTeX) com gráficos de evolução de notas, concorrência,
vagas vs inscritos e tabela histórica.

Uso:
    python notas_de_corte.py                    # modo interativo
    python notas_de_corte.py "engenharia civil" # direto
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import matplotlib
matplotlib.use("Agg")  # backend sem janela (só salva arquivos)
import matplotlib.pyplot as plt

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

DADOS_PATH = os.path.join(BASE_DIR, "dados.json")

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
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, esc in mapa.items():
        texto = texto.replace(char, esc)
    # Substituir traço unicode por traço normal
    texto = texto.replace("\u2212", "--")
    texto = texto.replace("\u2013", "--")
    texto = texto.replace("\u2014", "---")
    return texto


def carregar_dados() -> dict:
    if not os.path.exists(DADOS_PATH):
        print(cor("Erro: dados.json não encontrado!", RED))
        print("Execute primeiro: python extrair_dados.py")
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


def agrupar_por_curso(resultados: list[tuple[str, dict]]) -> dict[str, list]:
    """Agrupa resultados por nome de curso."""
    grupos = {}
    for ano, r in resultados:
        nome = r["curso"]
        if nome not in grupos:
            grupos[nome] = []
        grupos[nome].append((ano, r))
    return grupos


# ---------------------------------------------------------------------------
# Geração de gráficos (salvos como imagem)
# ---------------------------------------------------------------------------
def gerar_grafico_notas(registros_por_ano: list[tuple[str, dict]], caminho: str):
    """Gráfico de evolução da nota mínima e máxima."""
    dados_plot = []
    for ano, r in registros_por_ano:
        minimo = r.get("pontos_minimo") or r.get("nota_de_corte")
        maximo = r.get("pontos_maximo") or r.get("nota_de_corte")
        dados_plot.append((int(ano), minimo, maximo))
    dados_plot.sort()

    fig, ax = plt.subplots(figsize=(7, 3.5))

    anos = [d[0] for d in dados_plot]
    mins_v = [(d[0], d[1]) for d in dados_plot if d[1] is not None]
    maxs_v = [(d[0], d[2]) for d in dados_plot if d[2] is not None]

    if mins_v:
        ax.plot([a for a, _ in mins_v], [v for _, v in mins_v],
                "o-", color="#c0392b", label="Nota mínima (convocado)", linewidth=2, markersize=7)
        for a, v in mins_v:
            ax.annotate(str(v), (a, v), textcoords="offset points",
                       xytext=(0, 10), ha="center", fontsize=9, fontweight="bold", color="#c0392b")

    if maxs_v:
        ax.plot([a for a, _ in maxs_v], [v for _, v in maxs_v],
                "s-", color="#27ae60", label="Nota máxima (convocado)", linewidth=2, markersize=7)
        for a, v in maxs_v:
            ax.annotate(str(v), (a, v), textcoords="offset points",
                       xytext=(0, -14), ha="center", fontsize=9, fontweight="bold", color="#27ae60")

    ax.set_xlabel("Ano da Transferência")
    ax.set_ylabel("Pontos")
    ax.set_title("Evolução das Notas de Corte")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(anos)
    plt.tight_layout()
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)


def gerar_grafico_concorrencia(registros_por_ano: list[tuple[str, dict]], caminho: str):
    """Gráfico de barras da concorrência."""
    dados_plot = []
    for ano, r in registros_por_ano:
        if "concorrencia" in r:
            dados_plot.append((int(ano), r["concorrencia"], r["vagas"], r["inscritos"]))
    dados_plot.sort()

    if not dados_plot:
        return False

    fig, ax = plt.subplots(figsize=(7, 3.5))

    anos = [str(d[0]) for d in dados_plot]
    concs = [d[1] for d in dados_plot]
    cores = ["#e74c3c" if c >= 3 else "#f39c12" if c >= 1 else "#27ae60" for c in concs]

    bars = ax.bar(anos, concs, color=cores, alpha=0.85, edgecolor="white", linewidth=1.5)
    for bar, (_, c, v, i) in zip(bars, dados_plot):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.08,
                f"{c:.2f}\n({i} insc / {v} vag)", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Ano da Transferência")
    ax.set_ylabel("Candidatos por Vaga")
    ax.set_title("Concorrência ao Longo dos Anos")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return True


def gerar_grafico_vagas_inscritos(registros_por_ano: list[tuple[str, dict]], caminho: str):
    """Gráfico de barras agrupadas: vagas vs inscritos."""
    dados_plot = []
    for ano, r in registros_por_ano:
        if "vagas" in r:
            dados_plot.append((int(ano), r["vagas"], r["inscritos"]))
    dados_plot.sort()

    if not dados_plot:
        return False

    fig, ax = plt.subplots(figsize=(7, 3.5))

    anos = [d[0] for d in dados_plot]
    vagas = [d[1] for d in dados_plot]
    inscritos = [d[2] for d in dados_plot]

    x = range(len(anos))
    w = 0.35
    b1 = ax.bar([i - w / 2 for i in x], vagas, w, label="Vagas", color="#27ae60", alpha=0.85)
    b2 = ax.bar([i + w / 2 for i in x], inscritos, w, label="Inscritos", color="#e74c3c", alpha=0.85)

    for bar, v in zip(b1, vagas):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")
    for bar, v in zip(b2, inscritos):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels([str(a) for a in anos])
    ax.set_xlabel("Ano da Transferência")
    ax.set_ylabel("Quantidade")
    ax.set_title("Vagas Ofertadas vs Inscritos")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return True


# ---------------------------------------------------------------------------
# Geração do relatório LaTeX → PDF
# ---------------------------------------------------------------------------
def gerar_tabela_latex(registros_por_ano: list[tuple[str, dict]]) -> str:
    """Gera código LaTeX de uma tabela histórica."""
    # Verificar se temos dados completos (2020+) ou simplificados (2019)
    tem_completo = any("vagas" in r for _, r in registros_por_ano)

    linhas = []
    if tem_completo:
        linhas.append(r"\begin{tabularx}{\textwidth}{c c c c c c c}")
        linhas.append(r"\toprule")
        linhas.append(r"\textbf{Ano} & \textbf{Vagas} & \textbf{Inscritos} & \textbf{Ausentes} & \textbf{Conc.} & \textbf{Nota Mín.} & \textbf{Nota Máx.} \\")
        linhas.append(r"\midrule")
        for ano, r in sorted(registros_por_ano, key=lambda x: x[0]):
            if "vagas" in r:
                minimo = r.get("pontos_minimo")
                maximo = r.get("pontos_maximo")
                min_str = str(minimo) if minimo is not None else "---"
                max_str = str(maximo) if maximo is not None else "---"
                conc = f"{r['concorrencia']:.2f}"
                linhas.append(
                    f"{ano} & {r['vagas']} & {r['inscritos']} & "
                    f"{r['ausentes']} & {conc} & {min_str} & {max_str} \\\\"
                )
            else:
                nota = r.get("nota_de_corte")
                nota_str = str(nota) if nota is not None else "---"
                linhas.append(
                    f"{ano} & --- & --- & --- & --- & {nota_str} & {nota_str} \\\\"
                )
        linhas.append(r"\bottomrule")
        linhas.append(r"\end{tabularx}")
    else:
        linhas.append(r"\begin{tabularx}{\textwidth}{c c}")
        linhas.append(r"\toprule")
        linhas.append(r"\textbf{Ano} & \textbf{Nota de Corte} \\")
        linhas.append(r"\midrule")
        for ano, r in sorted(registros_por_ano, key=lambda x: x[0]):
            nota = r.get("nota_de_corte")
            nota_str = str(nota) if nota is not None else "---"
            linhas.append(f"{ano} & {nota_str} \\\\")
        linhas.append(r"\bottomrule")
        linhas.append(r"\end{tabularx}")

    return "\n".join(linhas)


def gerar_latex(nome_curso: str, registros_por_ano: list[tuple[str, dict]],
                img_notas: str, img_conc: str | None, img_vagas: str | None) -> str:
    """Gera o código-fonte .tex completo do relatório."""
    nome_esc = escapar_latex(nome_curso)
    tabela = gerar_tabela_latex(registros_por_ano)

    anos_list = sorted(set(a for a, _ in registros_por_ano))
    periodo = f"{anos_list[0]}--{anos_list[-1]}" if len(anos_list) > 1 else anos_list[0]

    # Blocos dos gráficos de concorrência e vagas (se existirem)
    bloco_conc = ""
    if img_conc:
        bloco_conc = (
            r"\begin{figure}[H]" "\n"
            r"\centering" "\n"
            r"\includegraphics[width=0.85\textwidth]{" + img_conc + "}\n"
            r"\caption{Concorrência (candidatos por vaga) ao longo dos anos.}" "\n"
            r"\end{figure}" "\n"
        )

    bloco_vagas = ""
    if img_vagas:
        bloco_vagas = (
            r"\begin{figure}[H]" "\n"
            r"\centering" "\n"
            r"\includegraphics[width=0.85\textwidth]{" + img_vagas + "}\n"
            r"\caption{Vagas ofertadas versus número de inscritos por ano.}" "\n"
            r"\end{figure}" "\n"
        )

    tex = r"""
\documentclass[11pt, a4paper]{article}

%% Pacotes
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazilian]{babel}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{float}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titling}

\geometry{margin=2cm, top=2.5cm, bottom=2.5cm}

%% Cores
\definecolor{uspazul}{HTML}{004A8D}
\definecolor{cinzaclaro}{HTML}{F5F5F5}

%% Cabeçalho e rodapé
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{uspazul}{Relatório de Transferência Externa USP}}
\fancyhead[R]{\small\textcolor{uspazul}{FUVEST --- """ + periodo + r"""}}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\hypersetup{
    colorlinks=true,
    linkcolor=uspazul,
    urlcolor=uspazul,
}

\begin{document}

%% -----------------------------------------------------------------------
%% Título
%% -----------------------------------------------------------------------
\begin{center}
    {\LARGE\bfseries\textcolor{uspazul}{Relatório --- Transferência Externa USP}}\\[6pt]
    {\Large """ + nome_esc + r"""}\\[4pt]
    {\small Dados disponíveis: """ + ", ".join(anos_list) + r"""}
\end{center}

\vspace{0.5cm}

%% -----------------------------------------------------------------------
%% Tabela histórica
%% -----------------------------------------------------------------------
\section*{Histórico Completo}

\begin{center}
""" + tabela + r"""
\end{center}

\vspace{0.3cm}

%% -----------------------------------------------------------------------
%% Gráfico de evolução de notas
%% -----------------------------------------------------------------------
\section*{Evolução das Notas de Corte}

\begin{figure}[H]
\centering
\includegraphics[width=0.85\textwidth]{""" + img_notas + r"""}
\caption{Nota mínima e máxima dos convocados ao longo dos anos.}
\end{figure}

%% -----------------------------------------------------------------------
%% Gráfico de concorrência
%% -----------------------------------------------------------------------
""" + bloco_conc + r"""

%% -----------------------------------------------------------------------
%% Gráfico de vagas vs inscritos
%% -----------------------------------------------------------------------
""" + bloco_vagas + r"""

%% -----------------------------------------------------------------------
%% Rodapé informativo
%% -----------------------------------------------------------------------
\vfill
\begin{center}
\small\textcolor{gray}{Dados extraídos dos editais oficiais da FUVEST.}\\
\small\textcolor{gray}{Gerado automaticamente --- \url{https://github.com/qedxyzyt-dot/notas-de-corte-transferencia-usp}}
\end{center}

\end{document}
"""
    return tex


def compilar_pdf(tex_source: str, nome_arquivo: str) -> str | None:
    """Compila .tex → .pdf e retorna o caminho do PDF gerado."""
    tmpdir = tempfile.mkdtemp(prefix="relatorio_transf_")

    tex_path = os.path.join(tmpdir, "relatorio.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_source)

    # Compilar 2x para resolver referências
    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True, text=True, cwd=tmpdir, timeout=60
        )

    pdf_tmp = os.path.join(tmpdir, "relatorio.pdf")
    if not os.path.exists(pdf_tmp):
        print(cor("Erro ao compilar o LaTeX. Log:", RED))
        log_path = os.path.join(tmpdir, "relatorio.log")
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                linhas = f.readlines()
            # Mostrar apenas linhas de erro
            for linha in linhas:
                if linha.startswith("!") or "Error" in linha:
                    print(f"  {linha.rstrip()}")
        print(f"\n  Diretório temporário: {tmpdir}")
        return None

    # Mover PDF para a pasta de trabalho
    destino = os.path.join(BASE_DIR, f"{nome_arquivo}.pdf")
    shutil.move(pdf_tmp, destino)

    # Limpar temporários
    shutil.rmtree(tmpdir, ignore_errors=True)

    return destino


# ---------------------------------------------------------------------------
# Pipeline principal: curso → relatório PDF
# ---------------------------------------------------------------------------
def gerar_relatorio(dados: dict, nome_curso: str, registros_por_ano: list[tuple[str, dict]]):
    """Gera o relatório PDF completo para um curso."""
    print(cor(f"\n  Gerando relatório para: {nome_curso}", CYAN))

    # Diretório temporário para imagens
    tmpdir = tempfile.mkdtemp(prefix="graficos_transf_")

    # 1. Gráfico de notas (sempre gerado)
    img_notas = os.path.join(tmpdir, "notas.png")
    gerar_grafico_notas(registros_por_ano, img_notas)
    print(cor("    ✓ Gráfico de evolução de notas", GREEN))

    # 2. Gráfico de concorrência (só se houver dados)
    img_conc = os.path.join(tmpdir, "concorrencia.png")
    tem_conc = gerar_grafico_concorrencia(registros_por_ano, img_conc)
    if tem_conc:
        print(cor("    ✓ Gráfico de concorrência", GREEN))
    else:
        img_conc = None

    # 3. Gráfico vagas vs inscritos (só se houver dados)
    img_vagas = os.path.join(tmpdir, "vagas.png")
    tem_vagas = gerar_grafico_vagas_inscritos(registros_por_ano, img_vagas)
    if tem_vagas:
        print(cor("    ✓ Gráfico vagas vs inscritos", GREEN))
    else:
        img_vagas = None

    # 4. Gerar LaTeX
    tex = gerar_latex(nome_curso, registros_por_ano, img_notas, img_conc, img_vagas)
    print(cor("    ✓ Código LaTeX gerado", GREEN))

    # 5. Compilar PDF
    nome_arquivo = "relatorio_" + nome_arquivo_seguro(nome_curso)
    destino = compilar_pdf(tex, nome_arquivo)

    # Limpar imagens temporárias
    shutil.rmtree(tmpdir, ignore_errors=True)

    if destino:
        print(cor(f"\n  ✓ Relatório gerado: {destino}", GREEN + BOLD))
    else:
        print(cor("\n  ✗ Falha ao gerar o PDF.", RED))

    return destino


# ---------------------------------------------------------------------------
# Interface no terminal
# ---------------------------------------------------------------------------
def selecionar_curso(dados: dict, termo: str) -> tuple[str, list] | None:
    """Busca cursos e, se necessário, pede ao usuário para escolher."""
    resultados = buscar_cursos(dados, termo)
    if not resultados:
        print(cor(f"\n  Nenhum curso encontrado para '{termo}'.", RED))
        return None

    grupos = agrupar_por_curso(resultados)

    if len(grupos) == 1:
        nome = list(grupos.keys())[0]
        return nome, grupos[nome]

    # Múltiplos cursos encontrados — consolidar tudo ou escolher
    nomes = list(grupos.keys())
    print(cor(f"\n  {len(nomes)} variações de nome encontradas:\n", BOLD))

    # Opção T = TODOS (consolidar num único relatório)
    total_anos = sorted(set(a for a, _ in resultados))
    print(f"  {cor('  T.', YELLOW)} {cor('TODOS — consolidar num único relatório', BOLD)}")
    anos_str = ", ".join(total_anos)
    print(f"       {cor(f'Anos: {anos_str}', DIM)}")
    print()

    for i, nome in enumerate(nomes, 1):
        anos = ", ".join(a for a, _ in grupos[nome])
        print(f"  {cor(f'{i:3d}.', CYAN)} {nome}")
        print(f"       {cor(f'Anos: {anos}', DIM)}")

    print(f"\n  {cor('  0.', DIM)} Cancelar")
    print()

    escolha = input(cor("  Escolha (T para todos, número, ou 0): ", GREEN)).strip().lower()

    if escolha == "t" or escolha == "":
        # Consolidar todos os resultados com um nome genérico baseado no termo
        return termo.title(), resultados

    if not escolha.isdigit() or int(escolha) < 1 or int(escolha) > len(nomes):
        return None

    nome = nomes[int(escolha) - 1]
    return nome, grupos[nome]


def modo_interativo(dados: dict):
    """Loop interativo: usuário digita cursos, programa gera PDFs."""
    anos_disponiveis = sorted(dados.keys())
    print(cor("\n  ╔══════════════════════════════════════════════════════════════╗", CYAN))
    print(cor("  ║", CYAN) + cor("    Notas de Corte — Transferência Externa USP (FUVEST)    ", BOLD) + cor("║", CYAN))
    print(cor("  ╚══════════════════════════════════════════════════════════════╝", CYAN))
    print(cor(f"  Anos disponíveis: {', '.join(anos_disponiveis)}", DIM))
    print()
    print(f"  Digite o nome do curso para gerar um relatório PDF completo.")
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

        nome_curso, registros = resultado
        gerar_relatorio(dados, nome_curso, registros)


def main():
    dados = carregar_dados()

    if len(sys.argv) >= 2:
        termo = " ".join(sys.argv[1:])
        resultado = selecionar_curso(dados, termo)
        if resultado:
            nome_curso, registros = resultado
            gerar_relatorio(dados, nome_curso, registros)
    else:
        modo_interativo(dados)


if __name__ == "__main__":
    main()
