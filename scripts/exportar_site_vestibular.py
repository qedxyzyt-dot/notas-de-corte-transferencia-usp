"""
Gera uma versao standalone do dashboard do vestibular, pronta para um
repositorio separado com GitHub Pages proprio.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import re
import shutil


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SOURCE_HTML = ROOT_DIR / "site_src" / "vestibular" / "index.html"
SOURCE_JSON = ROOT_DIR / "docs" / "dados_vestibular.json"
SOURCE_FAVICON = ROOT_DIR / "docs" / "assets" / "favicon.svg"
SOURCE_PDFS = ROOT_DIR / "docs" / "assets" / "pdfs" / "vestibular"
DEFAULT_OUT_DIR = ROOT_DIR / "build" / "vestibular_pages"

TRANSFERENCIA_URL = "https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/"


def ajustar_html(html: str, site_url: str | None) -> str:
    html = html.replace('href="../">Ver transferência externa</a>', f'href="{TRANSFERENCIA_URL}">Ver transferência externa</a>')

    if site_url:
        site_base = site_url.rstrip("/")
        html = re.sub(
            r'<link rel="canonical" href="[^"]+">',
            f'<link rel="canonical" href="{site_url}">',
            html,
        )
        html = re.sub(
            r'(<meta property="og:url" content=")[^"]+(">)',
            rf"\1{site_url}\2",
            html,
        )
        html = re.sub(
            r'("url":\s*")[^"]+(")',
            rf'\1{site_url}\2',
            html,
            count=1,
        )
        html = re.sub(
            r'(<meta property="og:image" content=")[^"]+(">)',
            rf"\1{site_base}/assets/favicon.svg\2",
            html,
        )
    else:
        html = re.sub(r'\n<link rel="canonical" href="[^"]+">', "", html, count=1)
        html = re.sub(r'\n<meta property="og:url" content="[^"]+">', "", html, count=1)
        html = re.sub(
            r'(\n\s*"url":\s*")[^"]+(",)',
            rf'\1\2',
            html,
            count=1,
        )

    return html


def limpar_destino(out_dir: Path) -> None:
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        return

    for child in out_dir.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copiar_estrutura(out_dir: Path) -> None:
    (out_dir / "assets" / "pdfs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_JSON, out_dir / "dados_vestibular.json")
    shutil.copy2(SOURCE_FAVICON, out_dir / "assets" / "favicon.svg")
    shutil.copytree(SOURCE_PDFS, out_dir / "assets" / "pdfs" / "vestibular", dirs_exist_ok=True)
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")


def escrever_readme(out_dir: Path, site_url: str | None) -> None:
    linhas = [
        "# Notas de Corte FUVEST Vestibular",
        "",
        "Site público com o histórico oficial das notas de corte da 1ª fase do vestibular tradicional da FUVEST.",
        "",
        "## Site online",
        "",
        f"- {site_url}" if site_url else "- Defina a URL final do GitHub Pages ao exportar com `--site-url`.",
        "",
        "## O que você encontra aqui",
        "",
        "- Série histórica de 2000 a 2026",
        "- Busca por carreira ou curso com recorte de período",
        "- Filtros por campus e modalidade",
        "- Desambiguação de carreiras repetidas por código nos anos recentes",
        "- Gráficos de evolução das notas de corte e da demanda",
        "- Tabela histórica com link direto para os PDFs oficiais",
        "- Resumo das nomenclaturas oficiais e das mudanças históricas relacionadas",
        "",
        "## Fonte dos dados",
        "",
        "Os dados exibidos neste site foram extraídos dos relatórios oficiais da própria FUVEST. Nos anos recentes, a diferenciação entre carreiras repetidas por código também foi conferida com os guias e listagens oficiais da FUVEST. Em caso de divergência, o PDF oficial do respectivo ano deve ser considerado a referência final.",
        "",
        "## Publicação no GitHub Pages",
        "",
        "Este repositório foi preparado para publicação direta a partir da raiz do projeto.",
        "",
        "1. Use a branch `main`.",
        "2. Em `Settings > Pages`, selecione `Deploy from a branch`.",
        "3. Escolha a pasta `/(root)`.",
        "",
        "## Arquivos principais",
        "",
        "- `index.html`",
        "- `dados_vestibular.json`",
        "- `assets/`",
        "",
        "## Atualização do conteúdo",
        "",
        "As futuras correções de OCR, ajustes visuais ou atualizações de dados devem ser exportadas novamente a partir do repositório-fonte deste projeto.",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(linhas), encoding="utf-8")


def exportar(out_dir: Path, site_url: str | None) -> None:
    if not SOURCE_HTML.exists():
        raise FileNotFoundError(f"Página-fonte não encontrada: {SOURCE_HTML}")
    if not SOURCE_JSON.exists():
        raise FileNotFoundError(f"JSON-fonte não encontrado: {SOURCE_JSON}")

    limpar_destino(out_dir)
    copiar_estrutura(out_dir)

    html = SOURCE_HTML.read_text(encoding="utf-8")
    html = ajustar_html(html, site_url)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    escrever_readme(out_dir, site_url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o site do vestibular para um repositório próprio no GitHub Pages.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Diretório de saída do export.")
    parser.add_argument("--site-url", default=None, help="URL final do GitHub Pages do vestibular.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    exportar(out_dir, args.site_url)

    print(f"Export concluído em: {out_dir}")
    if args.site_url:
        print(f"URL configurada no HTML: {args.site_url}")
    else:
        print("URL canônica removida do export. Defina --site-url quando souber a URL final.")


if __name__ == "__main__":
    main()
