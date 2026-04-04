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
  site_src/                  # Fontes do site standalone do vestibular
    vestibular/
      index.html
  scripts/                   # Scripts de manutenção do projeto
    extrair_dados.py
    extrair_dados_vestibular.py
    auditar_dados_vestibular.py
    exportar_site_vestibular.py
    vestibular_codigos_oficiais.json
    vestibular_opcoes_oficiais.json
    legacy/
      notas_de_corte.py
  fuvest_vestibular/         # PDFs do vestibular tradicional
  build/
    vestibular_pages/        # Export pronto para o GitHub Pages separado do vestibular
  README.md
  requirements.txt
  .gitignore
```

## O que o usuário encontra nos dashboards

- Busca por curso ou carreira com sugestões.
- Filtro de período antes da busca para evitar contaminação histórica.
- Filtros por campus e modalidade, conforme o relatório.
- Desambiguação de carreiras repetidas por código com apoio dos guias oficiais da FUVEST.
- Agrupamento por nome-base do curso quando a FUVEST distingue o mesmo curso por campus.
- Comparação por campus em cursos com oferta localizada, como Medicina, Psicologia, Arquitetura e Engenharia Civil.
- Sinalização explícita quando parte dos indicadores continua no escopo da carreira ampla oficial da FUVEST.
- Tabela histórica por ano.
- Link direto para a listagem oficial em PDF de cada ano.
- Gráficos de evolução das notas, da demanda e dos indicadores oficiais.
- Blocos com nomenclaturas oficiais do período e mudanças históricas relacionadas.
- Análise automática com destaques dos dados.
- Link direto para a página oficial da FUVEST.
- Suporte a tema claro e escuro.

## Repetições por código no vestibular

Quando a FUVEST publica o mesmo nome-base de carreira em mais de um código, o projeto usa o arquivo `scripts/vestibular_codigos_oficiais.json` para registrar a diferenciação oficial por campus ou escopo de oferta. Já os casos em que um curso aparece como opção localizada dentro de uma carreira mais ampla ficam registrados em `scripts/vestibular_opcoes_oficiais.json`.

O extrator valida automaticamente essa cobertura antes de gerar o JSON, para que uma repetição nova não passe despercebida. Na interface, o sistema procura reunir esses registros pelo nome-base do curso, mantendo a separação por campus e deixando explícito quando a nota de corte continua sendo publicada pela FUVEST no escopo da carreira ampla.

Para uma checagem rápida da robustez da extração das modalidades e dos campos que podem vir em branco no PDF, rode `python scripts/auditar_dados_vestibular.py`.

## Auditoria de cobertura do vestibular

Como a meta do projeto é refletir o máximo possível das listas oficiais, a auditoria do vestibular foi estruturada em duas faixas:

- `2020–2026`: faixa prioritária, com verificação reforçada de modalidades, OCR, desambiguações por campus e entradas sintéticas localizadas.
- `2000–2019`: série histórica completa, auditada respeitando o formato mais resumido dos PDFs antigos.

O script `scripts/auditar_dados_vestibular.py` gera dois relatórios versionáveis:

- `reports/vestibular_auditoria.json`
- `reports/vestibular_auditoria.md`

Esses relatórios resumem, por ano:

- total de registros extraídos
- pendências de campos esperados
- inconsistências oficiais preservadas do próprio PDF
- entradas sintéticas por campus
- registros com localização explícita
- distribuição dos grupos por modalidade

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
python scripts/auditar_dados_vestibular.py
python scripts/exportar_site_vestibular.py --site-url https://qedxyzyt-dot.github.io/notas-de-corte-fuvest-vestibular/
```

Esses processos:

- leem os PDFs oficiais do respectivo conjunto
- extraem os registros relevantes
- auditam a cobertura da série histórica e da faixa prioritária 2020–2026
- atualizam os JSONs consumidos pelos dashboards publicados
- geram um export standalone em `build/vestibular_pages/` para um GitHub Pages separado do vestibular

## Sobre os scripts legados

O arquivo `scripts/legacy/notas_de_corte.py` foi mantido apenas como referência técnica de uma fase anterior do projeto, quando havia experimentos de geração local de relatórios em PDF via terminal.

Ele não faz parte da experiência principal atual do produto e não é necessário para uso via GitHub Pages.

## Contribuições

Encontrou algum erro nos dados, alguma inconsistência visual ou quer sugerir melhorias no dashboard? Abra uma issue ou envie um pull request.

## Licença

MIT
