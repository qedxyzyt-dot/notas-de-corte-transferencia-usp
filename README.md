# Notas de Corte — Transferência Externa USP (FUVEST)

Ferramenta que gera **relatórios em PDF** (via LaTeX) com o histórico completo de **notas de corte**, **concorrência**, **vagas** e **inscritos** de qualquer curso da **Transferência Externa da USP**, organizada pela FUVEST.

Dados disponíveis: **2019, 2020, 2021, 2023, 2024, 2025 e 2026**.

---

## Como funciona

1. Você digita o nome do curso (ou parte dele)
2. O programa gera automaticamente um **relatório PDF** contendo:
   - **Tabela histórica** com vagas, inscritos, ausentes, concorrência, nota mínima e máxima
   - **Gráfico de evolução das notas** de corte ao longo dos anos
   - **Gráfico de concorrência** (candidatos por vaga) por ano
   - **Gráfico de vagas vs inscritos** comparando a oferta e a demanda
3. O PDF é salvo na mesma pasta com o nome `relatorio_<curso>.pdf`

A busca é flexível: ignora acentos, maiúsculas e minúsculas. Você pode digitar `matematica`, `Matemática` ou `MATEMATICA` — o resultado é o mesmo.

---

## Como usar

### Opção 1: Rodar direto com Python

```bash
# Instalar dependências
pip install -r requirements.txt

# Modo interativo (digite cursos em sequência)
python notas_de_corte.py

# Ou gerar relatório direto pela linha de comando
python notas_de_corte.py "engenharia civil"
python notas_de_corte.py "direito"
python notas_de_corte.py "medicina veterinaria"
```

> **Requisito:** é necessário ter uma distribuição LaTeX instalada (TeX Live, MiKTeX, etc.) para a compilação do PDF.

### Opção 2: Baixar o executável (.exe)

1. Vá em [Releases](../../releases) e baixe `notas_de_corte.exe`
2. Baixe também o arquivo `dados.json` e coloque na mesma pasta
3. Execute `notas_de_corte.exe`

### Opção 3: Gerar o .exe você mesmo

```bash
pip install pyinstaller
pyinstaller --onefile --name notas_de_corte --add-data "dados.json;." notas_de_corte.py
```

O executável será gerado em `dist/notas_de_corte.exe`.

---

## O que está no relatório

| Seção | Descrição |
|---|---|
| **Tabela histórica** | Todos os anos disponíveis com vagas, inscritos, ausentes, concorrência, nota mínima e máxima |
| **Evolução das notas** | Gráfico de linhas com a nota mínima e máxima dos convocados ao longo dos anos |
| **Concorrência** | Gráfico de barras com candidatos por vaga, colorido por nível de dificuldade |
| **Vagas vs Inscritos** | Gráfico de barras agrupadas comparando oferta e demanda |

---

## Exemplo

```
$ python notas_de_corte.py "direito"

  7 variações de nome encontradas:

    T. TODOS — consolidar num único relatório
       Anos: 2019, 2020, 2021, 2023, 2024, 2025, 2026

    1. Direito - Ribeirão Preto - 3º semestre
    2. Direito − Integral (Ribeirão Preto) − 3º semestre
    ...

  Escolha (T para todos, número, ou 0): t

  Gerando relatório para: Direito
    ✓ Gráfico de evolução de notas
    ✓ Gráfico de concorrência
    ✓ Gráfico vagas vs inscritos
    ✓ Código LaTeX gerado

  ✓ Relatório gerado: relatorio_direito.pdf
```

---

## Sobre

Este projeto foi criado para **facilitar a vida de quem está se preparando para a Transferência Externa da USP** — seja de humanas, biológicas ou exatas.

### Links úteis

- **YouTube** — Playlist com vídeos sobre Transferência Externa (resoluções de provas, dicas e mais): [Playlist Transferência Externa](https://www.youtube.com/playlist?list=PLr9as5vz1dVykvwxlzq4M50GxrDallvMz)
- **Hotmart** — Material de estudo para a 1ª fase (Matemática): [Primeira Fase Matemática](https://hotmart.com/pt-br/marketplace/produtos/primeira-fase-matematica-transferencia-2023-2024/C87159216E)

---

## Estrutura do projeto

```
notas_de_corte/
  transferencia_20XX_*.pdf    # PDFs originais da FUVEST (7 anos)
  extrair_dados.py            # Extrai dados dos PDFs → dados.json
  dados.json                  # Dados estruturados
  notas_de_corte.py           # Ferramenta principal (gera relatórios PDF)
  requirements.txt
  build.bat                   # Gerar .exe no Windows
```

---

## Contribuições

Encontrou algum erro nos dados? Quer adicionar o PDF de um ano que falta? Abra uma issue ou mande um PR!

## Licença

MIT
