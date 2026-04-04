"""
Audita o JSON do vestibular e gera um relatorio operacional de cobertura.

O objetivo principal e monitorar:
- a faixa prioritaria de 2020 a 2026, onde queremos o maximo de aderencia
- a serie historica completa desde 2000, respeitando o escopo de cada PDF

Saidas padrao:
- reports/vestibular_auditoria.json
- reports/vestibular_auditoria.md
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys
import unicodedata


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_PATH = ROOT_DIR / "docs" / "dados_vestibular.json"
REPORTS_DIR = ROOT_DIR / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "vestibular_auditoria.json"
MD_REPORT_PATH = REPORTS_DIR / "vestibular_auditoria.md"

PRIORITY_START = 2020
PRIORITY_END = 2026


def carregar(caminho: Path) -> dict[str, list[dict]]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    decomposed = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(sem_acentos.lower().split())


def perfil_ano(ano: int) -> dict[str, object]:
    if 2000 <= ano <= 2002:
        return {
            "nome": "serie_base_completa",
            "descricao": "PDFs com vagas, inscritos, ausentes, convocados e notas finais.",
            "esperados": [
                "vagas",
                "inscritos",
                "ausentes",
                "convocados_2fase",
                "convocados_por_vaga",
                "pontos_minimo",
                "pontos_maximo",
            ],
            "usa_modalidade": False,
        }
    if 2003 <= ano <= 2018:
        return {
            "nome": "serie_base_resumida",
            "descricao": "PDFs resumidos, sem vagas, inscritos e ausentes por linha.",
            "esperados": [
                "convocados_2fase",
                "convocados_por_vaga",
                "pontos_minimo",
                "pontos_maximo",
            ],
            "usa_modalidade": False,
        }
    return {
        "nome": "serie_modalidades",
        "descricao": "PDFs com modalidades e recortes mais detalhados.",
        "esperados": [
            "modalidade",
            "vagas",
            "inscritos",
            "ausentes",
            "convocados_2fase",
            "convocados_por_vaga",
            "pontos_minimo",
            "pontos_maximo",
        ],
        "usa_modalidade": True,
    }


def campos_esperados_registro(ano: int, registro: dict, perfil: dict[str, object]) -> list[str]:
    esperados = list(perfil["esperados"])
    if not perfil["usa_modalidade"]:
        return esperados

    if registro.get("metricas_finais_em_branco_oficialmente"):
        esperados = [
            campo
            for campo in esperados
            if campo not in {"convocados_por_vaga", "pontos_minimo", "pontos_maximo"}
        ]

    if registro.get("registro_sintetico"):
        esperados = [campo for campo in esperados if campo != "ausentes"]
        if registro.get("escopo_inscritos") != "curso":
            esperados = [campo for campo in esperados if campo != "inscritos"]

    return esperados


def identificar_grupo_modalidade(registro: dict) -> tuple[str, str, str, str, str]:
    return (
        str(registro.get("codigo") or ""),
        str(registro.get("curso") or ""),
        str(registro.get("campus") or ""),
        str(registro.get("carreira_oficial") or ""),
        "1" if registro.get("registro_sintetico") else "0",
    )


def coletar_pendencias(ano: int, registros: list[dict], perfil: dict[str, object]) -> tuple[list[dict], dict[str, int]]:
    pendencias: list[dict] = []
    faltas_por_campo: Counter[str] = Counter()
    for registro in registros:
        esperados = campos_esperados_registro(ano, registro, perfil)
        faltando = [campo for campo in esperados if registro.get(campo) is None]
        if not faltando:
            continue
        faltas_por_campo.update(faltando)
        pendencias.append(
            {
                "codigo": registro.get("codigo"),
                "curso": registro.get("curso"),
                "campus": registro.get("campus"),
                "modalidade": registro.get("modalidade"),
                "faltando": faltando,
                "registro_sintetico": bool(registro.get("registro_sintetico")),
            }
        )
    return pendencias, dict(sorted(faltas_por_campo.items()))


def resumir_ano(ano: int, registros: list[dict]) -> dict[str, object]:
    perfil = perfil_ano(ano)
    usa_modalidade = bool(perfil["usa_modalidade"])

    inconsistencias = [
        registro
        for registro in registros
        if registro.get("pontos_minimo") is not None
        and registro.get("pontos_maximo") is not None
        and registro["pontos_minimo"] > registro["pontos_maximo"]
    ]

    registros_modalidade = [registro for registro in registros if registro.get("modalidade")]
    grupos_modalidade = defaultdict(set)
    if usa_modalidade:
        for registro in registros_modalidade:
            grupos_modalidade[identificar_grupo_modalidade(registro)].add(registro["modalidade"])
    distribuicao_modalidades = Counter(len(modalidades) for modalidades in grupos_modalidade.values())
    grupos_com_tamanho_incomum = [
        {
            "codigo": grupo[0],
            "curso": grupo[1],
            "campus": grupo[2] or None,
            "carreira_oficial": grupo[3] or None,
            "registro_sintetico": grupo[4] == "1",
            "modalidades": sorted(modalidades),
        }
        for grupo, modalidades in grupos_modalidade.items()
        if len(modalidades) not in {0, 3}
    ]

    cursos_multi_campus = defaultdict(set)
    for registro in registros:
        curso_busca = registro.get("curso_busca")
        campus = registro.get("campus")
        if not curso_busca or not campus:
            continue
        cursos_multi_campus[normalizar(curso_busca)].add(campus)

    pendencias, faltas_por_campo = coletar_pendencias(ano, registros, perfil)

    return {
        "ano": ano,
        "perfil": perfil["nome"],
        "descricao_perfil": perfil["descricao"],
        "prioridade_alta": PRIORITY_START <= ano <= PRIORITY_END,
        "total_registros": len(registros),
        "total_registros_modalidade": len(registros_modalidade),
        "total_registros_sinteticos": sum(1 for registro in registros if registro.get("registro_sintetico")),
        "total_registros_desambiguados": sum(1 for registro in registros if registro.get("curso_desambiguado")),
        "total_registros_truncados": sum(1 for registro in registros if registro.get("curso_truncado")),
        "total_metricas_em_branco_oficialmente": sum(
            1 for registro in registros if registro.get("metricas_finais_em_branco_oficialmente")
        ),
        "total_ocultos_busca": sum(1 for registro in registros if registro.get("ocultar_busca")),
        "total_registros_localizados": sum(1 for registro in registros if registro.get("campus")),
        "total_cursos_multi_campus": sum(1 for campi in cursos_multi_campus.values() if len(campi) > 1),
        "campos_esperados": list(perfil["esperados"]),
        "faltas_por_campo": faltas_por_campo,
        "total_pendencias": len(pendencias),
        "pendencias_exemplo": pendencias[:12],
        "total_inconsistencias_oficiais": len(inconsistencias),
        "inconsistencias_exemplo": [
            {
                "codigo": registro.get("codigo"),
                "curso": registro.get("curso"),
                "campus": registro.get("campus"),
                "modalidade": registro.get("modalidade"),
                "pontos_minimo": registro.get("pontos_minimo"),
                "pontos_maximo": registro.get("pontos_maximo"),
            }
            for registro in inconsistencias[:12]
        ],
        "grupos_modalidade": len(grupos_modalidade),
        "distribuicao_tamanho_modalidades": {
            str(chave): valor for chave, valor in sorted(distribuicao_modalidades.items())
        },
        "grupos_modalidade_incomuns": grupos_com_tamanho_incomum[:12],
    }


def agregar_faixa(relatorios: list[dict]) -> dict[str, object]:
    faltas_por_campo: Counter[str] = Counter()
    distribuicao_modalidades: Counter[str] = Counter()
    for relatorio in relatorios:
        faltas_por_campo.update(relatorio["faltas_por_campo"])
        distribuicao_modalidades.update(relatorio["distribuicao_tamanho_modalidades"])

    return {
        "anos": [relatorio["ano"] for relatorio in relatorios],
        "total_registros": sum(relatorio["total_registros"] for relatorio in relatorios),
        "total_registros_modalidade": sum(relatorio["total_registros_modalidade"] for relatorio in relatorios),
        "total_registros_sinteticos": sum(relatorio["total_registros_sinteticos"] for relatorio in relatorios),
        "total_registros_desambiguados": sum(relatorio["total_registros_desambiguados"] for relatorio in relatorios),
        "total_registros_truncados": sum(relatorio["total_registros_truncados"] for relatorio in relatorios),
        "total_metricas_em_branco_oficialmente": sum(
            relatorio["total_metricas_em_branco_oficialmente"] for relatorio in relatorios
        ),
        "total_registros_localizados": sum(relatorio["total_registros_localizados"] for relatorio in relatorios),
        "total_cursos_multi_campus": sum(relatorio["total_cursos_multi_campus"] for relatorio in relatorios),
        "total_ocultos_busca": sum(relatorio["total_ocultos_busca"] for relatorio in relatorios),
        "total_pendencias": sum(relatorio["total_pendencias"] for relatorio in relatorios),
        "total_inconsistencias_oficiais": sum(relatorio["total_inconsistencias_oficiais"] for relatorio in relatorios),
        "faltas_por_campo": dict(sorted(faltas_por_campo.items())),
        "distribuicao_tamanho_modalidades": dict(sorted(distribuicao_modalidades.items())),
    }


def montar_relatorio(dados: dict[str, list[dict]]) -> dict[str, object]:
    anos = sorted((int(ano) for ano in dados.keys()))
    relatorios = [resumir_ano(ano, dados[str(ano)]) for ano in anos]
    prioridade = [relatorio for relatorio in relatorios if relatorio["prioridade_alta"]]
    historico = [relatorio for relatorio in relatorios if not relatorio["prioridade_alta"]]

    return {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "fonte_json": str(DATA_PATH),
        "faixa_prioritaria": [PRIORITY_START, PRIORITY_END],
        "resumo_global": agregar_faixa(relatorios),
        "resumo_2020_2026": agregar_faixa(prioridade),
        "resumo_2000_2019": agregar_faixa(historico),
        "anos": {str(relatorio["ano"]): relatorio for relatorio in relatorios},
    }


def formatar_numero(valor: int | float | None) -> str:
    if valor is None:
        return "0"
    return f"{valor:,}".replace(",", ".")


def linha_tabela_ano(relatorio: dict) -> str:
    faltas = relatorio["faltas_por_campo"]
    faltas_principais = (
        f"prop {faltas.get('convocados_por_vaga', 0)}"
        f" / min {faltas.get('pontos_minimo', 0)}"
        f" / max {faltas.get('pontos_maximo', 0)}"
    )
    return (
        f"| {relatorio['ano']} | {formatar_numero(relatorio['total_registros'])} | "
        f"{formatar_numero(relatorio['total_registros_sinteticos'])} | "
        f"{formatar_numero(relatorio['total_registros_localizados'])} | "
        f"{formatar_numero(relatorio['total_pendencias'])} | "
        f"{formatar_numero(relatorio['total_inconsistencias_oficiais'])} | "
        f"{faltas_principais} |"
    )


def renderizar_markdown(relatorio: dict[str, object]) -> str:
    resumo_global = relatorio["resumo_global"]
    resumo_prioridade = relatorio["resumo_2020_2026"]
    resumo_historico = relatorio["resumo_2000_2019"]
    anos = relatorio["anos"]

    linhas = [
        "# Auditoria do Vestibular FUVEST",
        "",
        f"Gerado em UTC: `{relatorio['gerado_em_utc']}`",
        "",
        "## Visão geral",
        "",
        f"- Registros totais auditados: `{formatar_numero(resumo_global['total_registros'])}`",
        f"- Registros na faixa prioritária `2020–2026`: `{formatar_numero(resumo_prioridade['total_registros'])}`",
        f"- Registros na série histórica `2000–2019`: `{formatar_numero(resumo_historico['total_registros'])}`",
        f"- Entradas sintéticas por campus/localidade: `{formatar_numero(resumo_global['total_registros_sinteticos'])}`",
        f"- Registros com localização explícita: `{formatar_numero(resumo_global['total_registros_localizados'])}`",
        f"- Cursos multi-campus detectados: `{formatar_numero(resumo_global['total_cursos_multi_campus'])}`",
        f"- Linhas com métricas finais oficialmente em branco no PDF: `{formatar_numero(resumo_global['total_metricas_em_branco_oficialmente'])}`",
        f"- Pendências totais de campos esperados: `{formatar_numero(resumo_global['total_pendencias'])}`",
        f"- Inconsistências oficiais preservadas do PDF: `{formatar_numero(resumo_global['total_inconsistencias_oficiais'])}`",
        "",
        "## Faixa prioritária 2020–2026",
        "",
        f"- Registros auditados: `{formatar_numero(resumo_prioridade['total_registros'])}`",
        f"- Sintéticos por campus: `{formatar_numero(resumo_prioridade['total_registros_sinteticos'])}`",
        f"- Localizações explícitas: `{formatar_numero(resumo_prioridade['total_registros_localizados'])}`",
        f"- Linhas oficialmente em branco: `{formatar_numero(resumo_prioridade['total_metricas_em_branco_oficialmente'])}`",
        f"- Pendências remanescentes: `{formatar_numero(resumo_prioridade['total_pendencias'])}`",
        "",
        "| Ano | Registros | Sintéticos | Localizados | Pendências | Inconsistências | Faltas principais |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for ano in range(PRIORITY_START, PRIORITY_END + 1):
        linhas.append(linha_tabela_ano(anos[str(ano)]))

    linhas.extend(
        [
            "",
            "## Série histórica 2000–2019",
            "",
        f"- Registros auditados: `{formatar_numero(resumo_historico['total_registros'])}`",
        f"- Linhas oficialmente em branco: `{formatar_numero(resumo_historico['total_metricas_em_branco_oficialmente'])}`",
        f"- Pendências remanescentes: `{formatar_numero(resumo_historico['total_pendencias'])}`",
            "",
            "| Ano | Registros | Sintéticos | Localizados | Pendências | Inconsistências | Faltas principais |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for ano in range(2000, PRIORITY_START):
        linhas.append(linha_tabela_ano(anos[str(ano)]))

    linhas.extend(
        [
            "",
            "## Pendências prioritárias por ano",
            "",
        ]
    )

    for ano in range(PRIORITY_START, PRIORITY_END + 1):
        relatorio_ano = anos[str(ano)]
        linhas.append(f"### {ano}")
        linhas.append("")
        linhas.append(f"- Perfil: `{relatorio_ano['perfil']}`")
        linhas.append(f"- Descrição: {relatorio_ano['descricao_perfil']}")
        linhas.append(
            f"- Métricas finais oficialmente em branco: `{formatar_numero(relatorio_ano['total_metricas_em_branco_oficialmente'])}`"
        )
        linhas.append(f"- Pendências: `{formatar_numero(relatorio_ano['total_pendencias'])}`")
        linhas.append(f"- Inconsistências oficiais: `{formatar_numero(relatorio_ano['total_inconsistencias_oficiais'])}`")
        if relatorio_ano["pendencias_exemplo"]:
            for exemplo in relatorio_ano["pendencias_exemplo"][:5]:
                campus = f" | {exemplo['campus']}" if exemplo.get("campus") else ""
                modalidade = f" | {exemplo['modalidade']}" if exemplo.get("modalidade") else ""
                linhas.append(
                    f"- `{exemplo['codigo']}` | {exemplo['curso']}{campus}{modalidade} | faltando: {', '.join(exemplo['faltando'])}"
                )
        else:
            linhas.append("- Sem pendências de campos esperados.")
        if relatorio_ano["inconsistencias_exemplo"]:
            for exemplo in relatorio_ano["inconsistencias_exemplo"][:3]:
                linhas.append(
                    f"- Inconsistência oficial preservada: `{exemplo['codigo']}` | {exemplo['curso']} | "
                    f"{exemplo.get('modalidade') or 'sem modalidade'} | mínimo {exemplo['pontos_minimo']} | máximo {exemplo['pontos_maximo']}"
                )
        linhas.append("")

    linhas.extend(
        [
            "## Observações",
            "",
            "- A auditoria respeita o formato de cada período; anos antigos não são penalizados por campos que não existem no PDF original.",
            "- A faixa 2020–2026 recebe destaque porque concentra modalidades, OCR mais complexo e desambiguações por campus.",
            "- Inconsistências marcadas como oficiais são mantidas porque estão impressas no PDF da própria FUVEST.",
            "",
        ]
    )

    return "\n".join(linhas)


def escrever_relatorios(relatorio: dict[str, object], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(renderizar_markdown(relatorio) + "\n", encoding="utf-8")


def imprimir_resumo(relatorio: dict[str, object]) -> None:
    resumo_prioridade = relatorio["resumo_2020_2026"]
    resumo_historico = relatorio["resumo_2000_2019"]
    print(
        "Faixa 2020-2026:",
        f"{resumo_prioridade['total_registros']} registros | "
        f"{resumo_prioridade['total_registros_sinteticos']} sinteticos | "
        f"{resumo_prioridade['total_registros_localizados']} localizados | "
        f"{resumo_prioridade['total_metricas_em_branco_oficialmente']} em branco oficiais | "
        f"{resumo_prioridade['total_pendencias']} pendencias | "
        f"{resumo_prioridade['total_inconsistencias_oficiais']} inconsistencias oficiais"
    )
    print(
        "Faixa 2000-2019:",
        f"{resumo_historico['total_registros']} registros | "
        f"{resumo_historico['total_metricas_em_branco_oficialmente']} em branco oficiais | "
        f"{resumo_historico['total_pendencias']} pendencias | "
        f"{resumo_historico['total_inconsistencias_oficiais']} inconsistencias oficiais"
    )

    for ano in range(PRIORITY_START, PRIORITY_END + 1):
        relatorio_ano = relatorio["anos"][str(ano)]
        print(
            f"{ano}: {relatorio_ano['total_registros']} registros | "
            f"{relatorio_ano['total_registros_sinteticos']} sinteticos | "
            f"{relatorio_ano['total_registros_localizados']} localizados | "
            f"{relatorio_ano['total_metricas_em_branco_oficialmente']} em branco oficiais | "
            f"{relatorio_ano['total_pendencias']} pendencias | "
            f"{relatorio_ano['total_inconsistencias_oficiais']} inconsistencias"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita a cobertura do JSON do vestibular.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="Caminho do JSON auditado.")
    parser.add_argument("--json-out", type=Path, default=JSON_REPORT_PATH, help="Saida do relatorio JSON.")
    parser.add_argument("--md-out", type=Path, default=MD_REPORT_PATH, help="Saida do relatorio Markdown.")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Nao grava arquivos; apenas imprime o resumo no terminal.",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    if not args.data.exists():
        raise FileNotFoundError(f"JSON nao encontrado: {args.data}")

    relatorio = montar_relatorio(carregar(args.data))
    imprimir_resumo(relatorio)

    if not args.no_write:
        escrever_relatorios(relatorio, args.json_out, args.md_out)
        print(f"Relatorio JSON: {args.json_out}")
        print(f"Relatorio Markdown: {args.md_out}")


if __name__ == "__main__":
    main()
