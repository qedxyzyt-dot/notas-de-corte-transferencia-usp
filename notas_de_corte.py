#!/usr/bin/env python3
"""
Notas de Corte - Transferência Externa USP (FUVEST)

Ferramenta para consultar notas de corte, concorrência, vagas e
gerar gráficos sobre a transferência externa da USP.

Uso:
    python notas_de_corte.py                   # menu interativo
    python notas_de_corte.py buscar "medicina"  # busca direta
    python notas_de_corte.py grafico "direito"  # gráfico direto
"""
import json
import os
import re
import sys
import unicodedata

# Forçar UTF-8 no stdout (Windows usa cp1252 por padrão)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Detecção do diretório base (funciona tanto como .py quanto como .exe)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DADOS_PATH = os.path.join(BASE_DIR, "dados.json")

# ---------------------------------------------------------------------------
# Cores ANSI para terminal
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
DIM = "\033[2m"


def cor(texto, c):
    return f"{c}{texto}{RESET}"


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para busca."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


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


def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")


# ---------------------------------------------------------------------------
# Exibição de resultados
# ---------------------------------------------------------------------------
def exibir_resultado_2019(ano: str, r: dict):
    nota = r.get("nota_de_corte")
    nota_str = str(nota) if nota is not None else "---"
    print(f"  {cor(ano, CYAN)}  {cor(r['codigo'], DIM)}  {r['curso']}")
    print(f"         Nota de corte: {cor(nota_str, YELLOW)}")


def exibir_resultado_completo(ano: str, r: dict):
    minimo = r.get("pontos_minimo")
    maximo = r.get("pontos_maximo")
    min_str = str(minimo) if minimo is not None else "---"
    max_str = str(maximo) if maximo is not None else "---"
    conc = r.get("concorrencia", 0)

    if conc >= 3:
        conc_cor = RED
    elif conc >= 1:
        conc_cor = YELLOW
    else:
        conc_cor = GREEN

    print(f"  {cor(ano, CYAN)}  {cor(r['codigo'], DIM)}  {r['curso']}")
    print(
        f"         Vagas: {cor(r['vagas'], GREEN)}  |  "
        f"Inscritos: {cor(r['inscritos'], YELLOW)}  |  "
        f"Ausentes: {r['ausentes']}  |  "
        f"Convocados: {r['convocados_2fase']}"
    )
    print(
        f"         Concorrência: {cor(f'{conc:.2f}', conc_cor)}  |  "
        f"Nota mín: {cor(min_str, MAGENTA)}  |  "
        f"Nota máx: {cor(max_str, MAGENTA)}"
    )


def exibir_resultado(ano: str, r: dict):
    if "vagas" in r:
        exibir_resultado_completo(ano, r)
    else:
        exibir_resultado_2019(ano, r)
    print()


# ---------------------------------------------------------------------------
# Gráficos com matplotlib
# ---------------------------------------------------------------------------
def tentar_importar_matplotlib():
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams["figure.figsize"] = (12, 6)
        matplotlib.rcParams["axes.titlesize"] = 14
        matplotlib.rcParams["axes.labelsize"] = 12
        return plt
    except ImportError:
        print(cor("matplotlib não está instalado.", RED))
        print("Instale com: pip install matplotlib")
        return None


def grafico_notas(dados: dict, termo: str):
    """Gráfico de evolução da nota mínima e máxima ao longo dos anos."""
    plt = tentar_importar_matplotlib()
    if not plt:
        return

    resultados = buscar_cursos(dados, termo)
    if not resultados:
        print(cor(f"Nenhum curso encontrado para '{termo}'.", RED))
        return

    # Agrupar por nome similar
    cursos_agrupados = {}
    for ano, r in resultados:
        nome = r["curso"]
        if nome not in cursos_agrupados:
            cursos_agrupados[nome] = []
        minimo = r.get("pontos_minimo") or r.get("nota_de_corte")
        maximo = r.get("pontos_maximo") or r.get("nota_de_corte")
        cursos_agrupados[nome].append((int(ano), minimo, maximo))

    fig, axes = plt.subplots(1, min(len(cursos_agrupados), 3), squeeze=False,
                              figsize=(6 * min(len(cursos_agrupados), 3), 5))
    axes = axes.flatten()

    for idx, (nome, pontos) in enumerate(list(cursos_agrupados.items())[:3]):
        ax = axes[idx]
        pontos.sort()
        anos = [p[0] for p in pontos]
        mins = [p[1] for p in pontos]
        maxs = [p[2] for p in pontos]

        mins_validos = [(a, v) for a, v in zip(anos, mins) if v is not None]
        maxs_validos = [(a, v) for a, v in zip(anos, maxs) if v is not None]

        if mins_validos:
            ax.plot([a for a, _ in mins_validos], [v for _, v in mins_validos],
                    "o-", color="#e74c3c", label="Nota mínima", linewidth=2, markersize=8)
            for a, v in mins_validos:
                ax.annotate(str(v), (a, v), textcoords="offset points",
                           xytext=(0, 10), ha="center", fontweight="bold")

        if maxs_validos:
            ax.plot([a for a, _ in maxs_validos], [v for _, v in maxs_validos],
                    "s-", color="#2ecc71", label="Nota máxima", linewidth=2, markersize=8)
            for a, v in maxs_validos:
                ax.annotate(str(v), (a, v), textcoords="offset points",
                           xytext=(0, 10), ha="center", fontweight="bold")

        ax.set_title(nome, fontsize=10, wrap=True)
        ax.set_xlabel("Ano")
        ax.set_ylabel("Pontos")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xticks(anos)

    plt.suptitle(f"Evolução das Notas - Transferência USP", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()


def grafico_concorrencia(dados: dict, termo: str):
    """Gráfico de barras da concorrência ao longo dos anos."""
    plt = tentar_importar_matplotlib()
    if not plt:
        return

    resultados = buscar_cursos(dados, termo)
    resultados = [(a, r) for a, r in resultados if "concorrencia" in r]
    if not resultados:
        print(cor(f"Nenhum dado de concorrência para '{termo}'.", RED))
        return

    cursos_agrupados = {}
    for ano, r in resultados:
        nome = r["curso"]
        if nome not in cursos_agrupados:
            cursos_agrupados[nome] = []
        cursos_agrupados[nome].append((int(ano), r["concorrencia"], r["vagas"], r["inscritos"]))

    fig, axes = plt.subplots(1, min(len(cursos_agrupados), 3), squeeze=False,
                              figsize=(6 * min(len(cursos_agrupados), 3), 5))
    axes = axes.flatten()

    cores_barras = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"]

    for idx, (nome, pontos) in enumerate(list(cursos_agrupados.items())[:3]):
        ax = axes[idx]
        pontos.sort()
        anos = [str(p[0]) for p in pontos]
        concs = [p[1] for p in pontos]
        vagas = [p[2] for p in pontos]
        inscritos = [p[3] for p in pontos]

        bars = ax.bar(anos, concs, color=cores_barras[:len(anos)], alpha=0.8, edgecolor="white")
        for bar, c, v, i in zip(bars, concs, vagas, inscritos):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    f"{c:.2f}\n({i}/{v}v)", ha="center", va="bottom", fontsize=9)

        ax.set_title(nome, fontsize=10, wrap=True)
        ax.set_xlabel("Ano")
        ax.set_ylabel("Concorrência (inscritos/vaga)")
        ax.grid(True, alpha=0.3, axis="y")

    plt.suptitle(f"Concorrência - Transferência USP", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()


def grafico_histograma_notas(dados: dict, ano: str):
    """Histograma de notas mínimas de todos os cursos em um ano."""
    plt = tentar_importar_matplotlib()
    if not plt:
        return

    if ano not in dados:
        print(cor(f"Ano {ano} não disponível. Anos: {', '.join(sorted(dados.keys()))}", RED))
        return

    registros = dados[ano]
    if "pontos_minimo" in registros[0]:
        notas = [r["pontos_minimo"] for r in registros if r.get("pontos_minimo") is not None]
        label = "Nota mínima (pontos)"
    else:
        notas = [r["nota_de_corte"] for r in registros if r.get("nota_de_corte") is not None]
        label = "Nota de corte"

    if not notas:
        print(cor("Sem dados de notas para esse ano.", RED))
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(notas, bins=15, color="#3498db", edgecolor="white", alpha=0.8)
    ax.set_xlabel(label)
    ax.set_ylabel("Quantidade de cursos")
    ax.set_title(f"Distribuição das Notas de Corte - Transferência {ano}")
    ax.axvline(sum(notas) / len(notas), color="#e74c3c", linestyle="--",
               label=f"Média: {sum(notas)/len(notas):.1f}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def grafico_vagas_vs_inscritos(dados: dict, termo: str):
    """Gráfico comparando vagas e inscritos ao longo dos anos."""
    plt = tentar_importar_matplotlib()
    if not plt:
        return

    resultados = buscar_cursos(dados, termo)
    resultados = [(a, r) for a, r in resultados if "vagas" in r]
    if not resultados:
        print(cor(f"Nenhum dado de vagas/inscritos para '{termo}'.", RED))
        return

    cursos_agrupados = {}
    for ano, r in resultados:
        nome = r["curso"]
        if nome not in cursos_agrupados:
            cursos_agrupados[nome] = []
        cursos_agrupados[nome].append((int(ano), r["vagas"], r["inscritos"]))

    fig, axes = plt.subplots(1, min(len(cursos_agrupados), 3), squeeze=False,
                              figsize=(6 * min(len(cursos_agrupados), 3), 5))
    axes = axes.flatten()

    for idx, (nome, pontos) in enumerate(list(cursos_agrupados.items())[:3]):
        ax = axes[idx]
        pontos.sort()
        anos = [p[0] for p in pontos]
        vg = [p[1] for p in pontos]
        ins = [p[2] for p in pontos]

        x = range(len(anos))
        w = 0.35
        ax.bar([i - w/2 for i in x], vg, w, label="Vagas", color="#2ecc71", alpha=0.8)
        ax.bar([i + w/2 for i in x], ins, w, label="Inscritos", color="#e74c3c", alpha=0.8)
        ax.set_xticks(list(x))
        ax.set_xticklabels([str(a) for a in anos])
        ax.set_title(nome, fontsize=10, wrap=True)
        ax.set_xlabel("Ano")
        ax.set_ylabel("Quantidade")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

    plt.suptitle(f"Vagas vs Inscritos - Transferência USP", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
def ranking_concorrencia(dados: dict, ano: str, top_n: int = 15):
    """Mostra os cursos mais concorridos de um ano."""
    if ano not in dados:
        print(cor(f"Ano {ano} não disponível.", RED))
        return

    registros = [r for r in dados[ano] if r.get("concorrencia", 0) > 0]
    registros.sort(key=lambda r: r["concorrencia"], reverse=True)

    print(cor(f"\n  Top {top_n} cursos mais concorridos - {ano}", BOLD))
    print(cor("  " + "=" * 80, DIM))
    for i, r in enumerate(registros[:top_n], 1):
        conc = r["concorrencia"]
        if conc >= 3:
            c = RED
        elif conc >= 1:
            c = YELLOW
        else:
            c = GREEN
        print(
            f"  {cor(f'{i:2d}.', BOLD)} {r['curso'][:55]:<55} "
            f"Conc: {cor(f'{conc:.2f}', c)}  "
            f"Vagas: {cor(r['vagas'], GREEN)}  "
            f"Min: {cor(r.get('pontos_minimo', '---'), MAGENTA)}"
        )
    print()


# ---------------------------------------------------------------------------
# Menu interativo
# ---------------------------------------------------------------------------
def menu_principal(dados: dict):
    anos_disponiveis = sorted(dados.keys())
    while True:
        print(cor("\n  ╔══════════════════════════════════════════════════════════╗", CYAN))
        print(cor("  ║", CYAN) + cor("   Notas de Corte - Transferência Externa USP (FUVEST)  ", BOLD) + cor("║", CYAN))
        print(cor("  ╠══════════════════════════════════════════════════════════╣", CYAN))
        print(cor("  ║", CYAN) + "  1. Buscar curso por nome                              " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  2. Gráfico de evolução de notas                       " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  3. Gráfico de concorrência                            " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  4. Histograma de notas de um ano                      " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  5. Gráfico vagas vs inscritos                         " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  6. Ranking de concorrência de um ano                  " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  7. Listar todos os cursos de um ano                   " + cor("║", CYAN))
        print(cor("  ║", CYAN) + "  0. Sair                                               " + cor("║", CYAN))
        print(cor("  ╚══════════════════════════════════════════════════════════╝", CYAN))
        print(cor(f"  Anos disponíveis: {', '.join(anos_disponiveis)}", DIM))
        print()

        opcao = input(cor("  Escolha uma opção: ", GREEN)).strip()

        if opcao == "0":
            print(cor("\n  Até mais! Boa sorte na transferência! 🎓\n", GREEN))
            break

        elif opcao == "1":
            termo = input(cor("  Nome do curso (ou parte): ", GREEN)).strip()
            if not termo:
                continue
            resultados = buscar_cursos(dados, termo)
            if not resultados:
                print(cor(f"\n  Nenhum curso encontrado para '{termo}'.", RED))
            else:
                print(cor(f"\n  {len(resultados)} resultado(s) encontrado(s):\n", BOLD))
                for ano, r in resultados:
                    exibir_resultado(ano, r)

        elif opcao == "2":
            termo = input(cor("  Nome do curso: ", GREEN)).strip()
            if termo:
                grafico_notas(dados, termo)

        elif opcao == "3":
            termo = input(cor("  Nome do curso: ", GREEN)).strip()
            if termo:
                grafico_concorrencia(dados, termo)

        elif opcao == "4":
            ano = input(cor(f"  Ano ({'/'.join(anos_disponiveis)}): ", GREEN)).strip()
            grafico_histograma_notas(dados, ano)

        elif opcao == "5":
            termo = input(cor("  Nome do curso: ", GREEN)).strip()
            if termo:
                grafico_vagas_vs_inscritos(dados, termo)

        elif opcao == "6":
            ano = input(cor(f"  Ano ({'/'.join(anos_disponiveis)}): ", GREEN)).strip()
            if ano in dados:
                n = input(cor("  Quantos cursos no ranking? [15]: ", GREEN)).strip()
                n = int(n) if n.isdigit() else 15
                ranking_concorrencia(dados, ano, n)

        elif opcao == "7":
            ano = input(cor(f"  Ano ({'/'.join(anos_disponiveis)}): ", GREEN)).strip()
            if ano in dados:
                print(cor(f"\n  Cursos disponíveis em {ano}:\n", BOLD))
                for r in dados[ano]:
                    exibir_resultado(ano, r)

        input(cor("\n  Pressione Enter para continuar...", DIM))


# ---------------------------------------------------------------------------
# CLI direta
# ---------------------------------------------------------------------------
def cli():
    dados = carregar_dados()

    if len(sys.argv) < 2:
        menu_principal(dados)
        return

    comando = sys.argv[1].lower()

    if comando == "buscar" and len(sys.argv) >= 3:
        termo = " ".join(sys.argv[2:])
        resultados = buscar_cursos(dados, termo)
        if not resultados:
            print(cor(f"Nenhum curso encontrado para '{termo}'.", RED))
        else:
            print(cor(f"\n{len(resultados)} resultado(s):\n", BOLD))
            for ano, r in resultados:
                exibir_resultado(ano, r)

    elif comando == "grafico" and len(sys.argv) >= 3:
        termo = " ".join(sys.argv[2:])
        grafico_notas(dados, termo)

    elif comando == "concorrencia" and len(sys.argv) >= 3:
        termo = " ".join(sys.argv[2:])
        grafico_concorrencia(dados, termo)

    elif comando == "histograma" and len(sys.argv) >= 3:
        ano = sys.argv[2]
        grafico_histograma_notas(dados, ano)

    elif comando == "ranking" and len(sys.argv) >= 3:
        ano = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
        ranking_concorrencia(dados, ano, n)

    elif comando in ("ajuda", "help", "--help", "-h"):
        print(cor("\n  Notas de Corte - Transferência Externa USP", BOLD))
        print(cor("  " + "=" * 50, DIM))
        print("""
  Uso interativo:
    python notas_de_corte.py

  Comandos diretos:
    buscar <termo>        Busca cursos por nome
    grafico <termo>       Gráfico de evolução das notas
    concorrencia <termo>  Gráfico de concorrência
    histograma <ano>      Histograma de notas de um ano
    ranking <ano> [n]     Top N cursos mais concorridos
    ajuda                 Mostra esta ajuda
        """)
    else:
        print(cor("Comando não reconhecido. Use 'ajuda' para ver os comandos.", RED))


if __name__ == "__main__":
    cli()
