# Notas de Corte - Transferência Externa USP (FUVEST)

Dashboard web com histórico de notas de corte, concorrência, vagas e inscritos da Transferência Externa da USP, com base nos editais oficiais da FUVEST.

Hoje o foco do projeto é o uso direto no navegador, via GitHub Pages. O repositório foi reorganizado para refletir isso: o site publicado fica separado dos scripts de manutenção e dos PDFs-fonte.

## Acesse o dashboard

Quando o GitHub Pages estiver habilitado, o site poderá ser acessado em:

[https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/](https://qedxyzyt-dot.github.io/notas-de-corte-transferencia-usp/)

## Consulte também o edital oficial

Para conferir a página oficial da FUVEST sobre Transferência Externa, acesse:

[https://www.fuvest.br/transferencia/](https://www.fuvest.br/transferencia/)

## Estrutura atual do repositório

```text
notas_de_corte/
  docs/                      # Site publicado no GitHub Pages
    index.html
    dados.json
    .nojekyll
  scripts/                   # Scripts de manutenção do projeto
    extrair_dados.py
    legacy/
      notas_de_corte.py
  data/
    raw/                     # PDFs originais da FUVEST usados para extração
  README.md
  requirements.txt
  .gitignore
```

## O que o usuário encontra no site

- Busca por curso com sugestões.
- Filtros por curso específico, localização e período.
- Cards-resumo com os principais indicadores.
- Tabela histórica por ano.
- Gráficos de evolução das notas, concorrência e demanda.
- Análise automática com destaques dos dados.
- Link direto para a página oficial da FUVEST.

## Publicação no GitHub Pages

Este repositório está estruturado para publicar o site a partir da pasta `docs/`.

No GitHub:

1. Abra `Settings` > `Pages`.
2. Em `Build and deployment`, selecione `Deploy from a branch`.
3. Escolha:
   - Branch: `main`
   - Folder: `/docs`
4. Salve e aguarde alguns minutos.

Depois disso, o GitHub Pages servirá o conteúdo de `docs/index.html` e `docs/dados.json`.

## Fluxo de manutenção dos dados

Para atualizar os dados do site localmente:

```bash
pip install -r requirements.txt
python scripts/extrair_dados.py
```

Esse processo:

- lê os PDFs oficiais em `data/raw/`
- extrai os registros relevantes
- atualiza `docs/dados.json`, que é o arquivo consumido pelo dashboard

## Sobre os scripts legados

O arquivo `scripts/legacy/notas_de_corte.py` foi mantido apenas como referência técnica de uma fase anterior do projeto, quando havia experimentos de geração local de relatórios em PDF via terminal.

Ele não faz parte da experiência principal atual do produto e não é necessário para uso via GitHub Pages.

## Contribuições

Encontrou algum erro nos dados, alguma inconsistência visual ou quer sugerir melhorias no dashboard? Abra uma issue ou envie um pull request.

## Licença

MIT
