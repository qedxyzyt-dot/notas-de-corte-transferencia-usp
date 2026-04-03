"""
Extrai dados de notas de corte dos PDFs da FUVEST (Transferência Externa USP)
e gera um arquivo dados.json estruturado.
"""
import json
import re
import pdfplumber

PASTA = "."


def extrair_2019(caminho: str) -> list[dict]:
    """PDF de 2019 tem formato diferente: só código, nome e nota de corte."""
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = linha.strip()
        # Padrão: código (5 dígitos) + nome + últimos dígitos = nota de corte
        m = re.match(r"^(\d{5})\s+(.+?)\s+(\d+)\s+(\d+)$", linha)
        if m:
            codigo = m.group(1)
            nome = m.group(2).strip()
            nota_str = m.group(3) + m.group(4)
            nota = int(nota_str)
            registros.append({
                "codigo": codigo,
                "curso": nome,
                "nota_de_corte": nota,
            })
            continue
        # Caso com traço (sem nota)
        m2 = re.match(r"^(\d{5})\s+(.+?)\s+-$", linha)
        if m2:
            registros.append({
                "codigo": m2.group(1),
                "curso": m2.group(2).strip(),
                "nota_de_corte": None,
            })
    return registros


def extrair_padrao(caminho: str) -> list[dict]:
    """PDFs de 2020-2026: formato com VAGAS, INSCRITOS, AUSENTES, etc."""
    registros = []
    with pdfplumber.open(caminho) as pdf:
        texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

    for linha in texto_completo.split("\n"):
        linha = linha.strip()
        if linha.startswith("Total"):
            continue
        # Padrão: código−nome  vagas inscritos ausentes convoc convoc_vaga min max
        m = re.match(
            r"^(\d{5})[−\-](.+?)\s+"
            r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
            r"(\d+[.,]\d+)\s+"
            r"([\d−\-]+)\s+([\d−\-]+)$",
            linha,
        )
        if m:
            minimo = m.group(8).replace("−", "").replace("-", "")
            maximo = m.group(9).replace("−", "").replace("-", "")
            registros.append({
                "codigo": m.group(1),
                "curso": m.group(2).strip().rstrip("." ),
                "vagas": int(m.group(3)),
                "inscritos": int(m.group(4)),
                "ausentes": int(m.group(5)),
                "convocados_2fase": int(m.group(6)),
                "concorrencia": float(m.group(7).replace(",", ".")),
                "pontos_minimo": int(minimo) if minimo else None,
                "pontos_maximo": int(maximo) if maximo else None,
            })
    return registros


def main():
    arquivos = {
        2019: f"{PASTA}/transferencia_2019_nota_de_corte.pdf",
        2020: f"{PASTA}/transferencia_2020_nota_de_corte.pdf",
        2024: f"{PASTA}/transferencia_2024_notas_de_corte.pdf",
        2025: f"{PASTA}/transferencia_2025_notas_de_corte.pdf",
        2026: f"{PASTA}/transferencia_2026_notas_de_corte.pdf",
    }

    dados = {}
    for ano, caminho in arquivos.items():
        if ano == 2019:
            registros = extrair_2019(caminho)
        else:
            registros = extrair_padrao(caminho)
        dados[str(ano)] = registros
        print(f"{ano}: {len(registros)} cursos extraídos")

    with open(f"{PASTA}/dados.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\nArquivo dados.json gerado com sucesso!")


if __name__ == "__main__":
    main()
