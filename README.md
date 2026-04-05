# Notas de Corte - Transferência Externa USP

Projeto focado na consulta de dados históricos da **Transferência Externa da USP (FUVEST)**, com dashboard publicado via GitHub Pages.

O objetivo deste repositório é concentrar, em um só lugar:

- notas de corte históricas
- vagas, inscritos, ausentes e concorrência
- gráficos e comparativos por curso
- links para listagens oficiais em PDF
- referências oficiais e institucionais das unidades da USP para acompanhar editais de transferência externa

Este repositório é **estritamente dedicado à transferência externa**. O vestibular tradicional possui site e repositório próprios.

## Acesse o site

[https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/](https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/)

## Página oficial da FUVEST

Para consultar a página oficial da FUVEST sobre transferência externa:

[https://www.fuvest.br/transferencia/](https://www.fuvest.br/transferencia/)

## O que o usuário encontra no dashboard

- busca por curso com sugestões
- filtros por localização e período
- tabela histórica por ano
- comparação de indicadores oficiais
- gráficos de evolução
- link direto para os PDFs oficiais de cada edição
- card de referências oficiais por curso/unidade
- suporte a tema claro e escuro

## Estrutura do repositório

```text
notas_de_corte/
  docs/                      # Site publicado no GitHub Pages
    index.html
    dados.json
    editais_transferencia.json
    assets/
  data/raw/                  # PDFs e insumos brutos usados na extração
  reports/                   # Relatórios auxiliares do projeto
  scripts/                   # Scripts de manutenção e extração
    extrair_dados.py
    legacy/
  README.md
  requirements.txt
  .gitignore
```

## Publicação no GitHub Pages

Este repositório publica o site a partir da pasta `docs/`.

No GitHub:

1. Abra `Settings` > `Pages`.
2. Em `Build and deployment`, selecione `Deploy from a branch`.
3. Escolha:
   - Branch: `main`
   - Folder: `/docs`
4. Salve e aguarde alguns minutos.

## Atualização dos dados

Para atualizar os dados localmente:

```bash
pip install -r requirements.txt
python scripts/extrair_dados.py
```

Depois disso, revise os arquivos publicados em `docs/`, especialmente:

- `docs/dados.json`
- `docs/editais_transferencia.json`
- `docs/index.html`

## Curadoria dos editais oficiais

O arquivo `docs/editais_transferencia.json` concentra o mapeamento editorial das referências oficiais por curso e unidade.

Ele permite:

- associar cursos a páginas institucionais estáveis
- priorizar editais mais recentes quando disponíveis
- manter fallback institucional quando não há oferta na edição vigente
- exibir múltiplos links oficiais para um mesmo curso, quando necessário

## Escopo

Este projeto trata exclusivamente de:

- transferência externa da USP

Ele não pretende cobrir neste repositório:

- vestibular tradicional
- SISU/ENEM-USP
- transferência interna
- outros processos seletivos sem relação direta com a transferência externa

## Contribuições

Se você encontrar erro de dados, link institucional desatualizado ou inconsistência visual, abra uma issue ou envie um pull request.

## Licença

MIT
