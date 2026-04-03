# Notas de Corte - Transferência Externa USP (FUVEST)

Ferramenta para consultar **notas de corte**, **concorrência**, **vagas**, **inscritos** e gerar gráficos sobre o exame de **Transferência Externa da USP**, organizado pela FUVEST.

Dados disponíveis: **2019, 2020, 2021, 2023, 2024, 2025 e 2026**.

---

## Como usar

### Opção 1: Rodar direto com Python

```bash
# Instalar dependências
pip install -r requirements.txt

# Extrair dados dos PDFs (já incluso o dados.json no repo)
python extrair_dados.py

# Abrir menu interativo
python notas_de_corte.py

# Ou usar comandos diretos:
python notas_de_corte.py buscar "medicina"
python notas_de_corte.py grafico "engenharia civil"
python notas_de_corte.py concorrencia "direito"
python notas_de_corte.py histograma 2026
python notas_de_corte.py ranking 2026 15
```

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

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Busca por curso** | Busca flexível por nome (ignora acentos) |
| **Evolução de notas** | Gráfico com nota mínima e máxima ao longo dos anos |
| **Concorrência** | Gráfico de barras mostrando inscritos/vaga por ano |
| **Histograma** | Distribuição das notas de corte de todos os cursos em um ano |
| **Vagas vs Inscritos** | Comparação visual entre vagas ofertadas e inscritos |
| **Ranking** | Top N cursos mais concorridos de um ano |

---

## Exemplos

```
$ python notas_de_corte.py buscar "direito"

  2026  60018  Direito - Ribeirão Preto (Bacharelado)
         Vagas: 8  |  Inscritos: 199  |  Ausentes: 41  |  Convocados: 25
         Concorrência: 3.13  |  Nota mín: 69  |  Nota máx: 77
```

```
$ python notas_de_corte.py ranking 2026 5

  Top 5 cursos mais concorridos - 2026
   1. Relações Internacionais - São Paulo    Conc: 4.00  Vagas: 1  Min: 72
   2. Odontologia - Bauru                    Conc: 3.67  Vagas: 6  Min: 47
   3. Engenharia Mecatrônica - São Carlos    Conc: 3.67  Vagas: 3  Min: 49
   4. Ciências Biológicas - São Paulo        Conc: 3.50  Vagas: 6  Min: 49
   5. Arquitetura e Urbanismo - São Carlos   Conc: 3.50  Vagas: 4  Min: 65
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
  transferencia_2019_nota_de_corte.pdf   # PDF original FUVEST
  transferencia_2020_nota_de_corte.pdf
  transferencia_2021_notas_de_corte.pdf
  transferencia_2023_nota-corte.pdf
  transferencia_2024_notas_de_corte.pdf
  transferencia_2025_notas_de_corte.pdf
  transferencia_2026_notas_de_corte.pdf
  extrair_dados.py                        # Extrai dados dos PDFs
  dados.json                              # Dados estruturados (gerado)
  notas_de_corte.py                       # Ferramenta principal
  requirements.txt
  build.bat                               # Gerar .exe no Windows
```

---

## Contribuições

Encontrou algum erro nos dados? Quer adicionar o PDF de um ano que falta? Abra uma issue ou mande um PR!

## Licença

MIT
