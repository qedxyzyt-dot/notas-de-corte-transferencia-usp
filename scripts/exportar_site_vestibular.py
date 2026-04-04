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
SOURCE_HTML = ROOT_DIR / "docs" / "vestibular" / "index.html"
SOURCE_JSON = ROOT_DIR / "docs" / "dados_vestibular.json"
SOURCE_FAVICON = ROOT_DIR / "docs" / "assets" / "favicon.svg"
SOURCE_PDFS = ROOT_DIR / "docs" / "assets" / "pdfs" / "vestibular"
DEFAULT_OUT_DIR = ROOT_DIR / "build" / "vestibular_pages"

TRANSFERENCIA_URL = "https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/"


def ajustar_html(html: str, site_url: str | None) -> str:
    html = html.replace('href="../assets/favicon.svg"', 'href="assets/favicon.svg"')
    html = html.replace('fetch("../dados_vestibular.json")', 'fetch("dados_vestibular.json")')
    html = html.replace('href="../">Ver transferência externa</a>', f'href="{TRANSFERENCIA_URL}">Ver transferência externa</a>')
    html = html.replace('"../assets/pdfs/vestibular/', '"assets/pdfs/vestibular/')

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
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def copiar_estrutura(out_dir: Path) -> None:
    (out_dir / "assets" / "pdfs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_JSON, out_dir / "dados_vestibular.json")
    shutil.copy2(SOURCE_FAVICON, out_dir / "assets" / "favicon.svg")
    shutil.copytree(SOURCE_PDFS, out_dir / "assets" / "pdfs" / "vestibular", dirs_exist_ok=True)
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")


def escrever_readme(out_dir: Path, site_url: str | None) -> None:
    linhas = [
        "# Vestibular FUVEST Pages",
        "",
        "Export standalone do dashboard do vestibular tradicional da FUVEST.",
        "",
        "## Publicacao sugerida",
        "",
        "1. Crie um novo repositorio no GitHub para o vestibular.",
        "2. Copie o conteudo desta pasta para a raiz do novo repositorio.",
        "3. Em `Settings > Pages`, selecione `Deploy from a branch`.",
        "4. Escolha a branch principal e a pasta `/(root)`.",
        "",
        "## Arquivos principais",
        "",
        "- `index.html`",
        "- `dados_vestibular.json`",
        "- `assets/`",
        "",
    ]
    if site_url:
        linhas.extend(
            [
                "## URL configurada",
                "",
                f"- `{site_url}`",
                "",
            ]
        )
    (out_dir / "README.md").write_text("\n".join(linhas), encoding="utf-8")


def exportar(out_dir: Path, site_url: str | None) -> None:
    if not SOURCE_HTML.exists():
        raise FileNotFoundError(f"Pagina fonte nao encontrada: {SOURCE_HTML}")
    if not SOURCE_JSON.exists():
        raise FileNotFoundError(f"JSON fonte nao encontrado: {SOURCE_JSON}")

    limpar_destino(out_dir)
    copiar_estrutura(out_dir)

    html = SOURCE_HTML.read_text(encoding="utf-8")
    html = ajustar_html(html, site_url)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    escrever_readme(out_dir, site_url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o site do vestibular para um repositorio GitHub Pages proprio.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Diretorio de saida do export.")
    parser.add_argument("--site-url", default=None, help="URL final do GitHub Pages do vestibular.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    exportar(out_dir, args.site_url)

    print(f"Export concluido em: {out_dir}")
    if args.site_url:
        print(f"URL configurada no HTML: {args.site_url}")
    else:
        print("URL canonica removida do export. Defina --site-url quando souber a URL final.")


if __name__ == "__main__":
    main()
