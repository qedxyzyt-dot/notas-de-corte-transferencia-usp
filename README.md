# Notas de Corte - FUVEST USP

Projeto com dashboards web baseados em relatórios oficiais da FUVEST para:

- Transferência Externa da USP
- Vestibular tradicional da USP

Hoje o foco do projeto é o uso direto no navegador, via GitHub Pages. O repositório foi reorganizado para refletir isso: o site publicado fica separado dos scripts de manutenção e dos PDFs-fonte.

Projeto independente criado e mantido por QED.

## Acesse os dashboards

Quando o GitHub Pages estiver habilitado, o site poderá ser acessado em:

- Transferência Externa:
  [https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/](https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/)
- Vestibular tradicional:
  [https://qedxyzyt-dot.github.io/notas-de-corte-fuvest-vestibular/](https://qedxyzyt-dot.github.io/notas-de-corte-fuvest-vestibular/)

## Consulte também as páginas oficiais

Para conferir a página oficial da FUVEST sobre Transferência Externa, acesse:

[https://www.fuvest.br/transferencia/](https://www.fuvest.br/transferencia/)

Para conferir a página oficial da FUVEST sobre o vestibular, acesse:

[https://www.fuvest.br/vestibular-da-usp/](https://www.fuvest.br/vestibular-da-usp/)

## Estrutura atual do repositório

```text
notas_de_corte/
  docs/                      # Site publicado no GitHub Pages
    index.html
    dados.json
    vestibular/
      index.html
    vestibular.html          # Redirecionamento para o site standalone
    dados_vestibular.json
    .nojekyll
  scripts/                   # Scripts de manutenção do projeto
    extrair_dados.py
    extrair_dados_vestibular.py
    legacy/
      notas_de_corte.py
  data/
    raw/                     # PDFs originais da FUVEST usados para extração
  fuvest_vestibular/         # PDFs do vestibular tradicional
  README.md
  requirements.txt
  .gitignore
```

## O que o usuário encontra nos dashboards

- Busca por curso ou carreira com sugestões.
- Filtros por campus, modalidade ou período, conforme o relatório.
- Tabela histórica por ano.
- Link direto para a listagem oficial em PDF de cada ano.
- Gráficos de evolução das notas, da demanda e dos indicadores oficiais.
- Análise automática com destaques dos dados.
- Link direto para a página oficial da FUVEST.
- Suporte a tema claro e escuro.

## Publicação no GitHub Pages

Este repositório está estruturado para publicar o site a partir da pasta `docs/`.

No GitHub:

1. Abra `Settings` > `Pages`.
2. Em `Build and deployment`, selecione `Deploy from a branch`.
3. Escolha:
   - Branch: `main`
   - Folder: `/docs`
4. Salve e aguarde alguns minutos.

Depois disso, o GitHub Pages servirá o conteúdo publicado em `docs/`, incluindo `docs/index.html`. As rotas locais do vestibular permanecem apenas como redirecionamento para o site standalone.

## Fluxo de manutenção dos dados

Para atualizar os dados do site localmente:

```bash
pip install -r requirements.txt
python scripts/extrair_dados.py
python scripts/extrair_dados_vestibular.py
python scripts/exportar_site_vestibular.py --site-url https://qedxyzyt-dot.github.io/notas-de-corte-fuvest-vestibular/
```

Esses processos:

- leem os PDFs oficiais do respectivo conjunto
- extraem os registros relevantes
- atualizam os JSONs consumidos pelos dashboards publicados
- geram um export standalone em `build/vestibular_pages/` para um GitHub Pages separado do vestibular

## Sobre os scripts legados

O arquivo `scripts/legacy/notas_de_corte.py` foi mantido apenas como referência técnica de uma fase anterior do projeto, quando havia experimentos de geração local de relatórios em PDF via terminal.

Ele não faz parte da experiência principal atual do produto e não é necessário para uso via GitHub Pages.

## Contribuições

Encontrou algum erro nos dados, alguma inconsistência visual ou quer sugerir melhorias no dashboard? Abra uma issue ou envie um pull request.

## Licença

MIT
