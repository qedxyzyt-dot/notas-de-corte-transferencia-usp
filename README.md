# Notas de Corte - Transferencia Externa USP (FUVEST)

Ferramenta para consultar **notas de corte**, **concorrencia**, **vagas**, **inscritos** e gerar graficos sobre o exame de **Transferencia Externa da USP**, organizado pela FUVEST.

Dados disponiveis: **2019, 2020, 2024, 2025 e 2026**.

---

## Como usar

### Opcao 1: Rodar direto com Python

```bash
# Instalar dependencias
pip install -r requirements.txt

# Extrair dados dos PDFs (ja incluso o dados.json no repo)
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

### Opcao 2: Baixar o executavel (.exe)

1. Va em [Releases](../../releases) e baixe `notas_de_corte.exe`
2. Baixe tambem o arquivo `dados.json` e coloque na mesma pasta
3. Execute `notas_de_corte.exe`

### Opcao 3: Gerar o .exe voce mesmo

```bash
pip install pyinstaller
pyinstaller --onefile --name notas_de_corte --add-data "dados.json;." notas_de_corte.py
```

O executavel sera gerado em `dist/notas_de_corte.exe`.

---

## Funcionalidades

| Funcionalidade | Descricao |
|---|---|
| **Busca por curso** | Busca flexivel por nome (ignora acentos) |
| **Evolucao de notas** | Grafico com nota minima e maxima ao longo dos anos |
| **Concorrencia** | Grafico de barras mostrando inscritos/vaga por ano |
| **Histograma** | Distribuicao das notas de corte de todos os cursos em um ano |
| **Vagas vs Inscritos** | Comparacao visual entre vagas ofertadas e inscritos |
| **Ranking** | Top N cursos mais concorridos de um ano |

---

## Exemplos

```
$ python notas_de_corte.py buscar "direito"

  2026  60018  Direito - Ribeirao Preto (Bacharelado)
         Vagas: 8  |  Inscritos: 199  |  Ausentes: 41  |  Convocados: 25
         Concorrencia: 3.13  |  Nota min: 69  |  Nota max: 77
```

```
$ python notas_de_corte.py ranking 2026 5

  Top 5 cursos mais concorridos - 2026
   1. Relacoes Internacionais - Sao Paulo    Conc: 4.00  Vagas: 1  Min: 72
   2. Odontologia - Bauru                    Conc: 3.67  Vagas: 6  Min: 47
   3. Engenharia Mecatronica - Sao Carlos    Conc: 3.67  Vagas: 3  Min: 49
   4. Ciencias Biologicas - Sao Paulo        Conc: 3.50  Vagas: 6  Min: 49
   5. Arquitetura e Urbanismo - Sao Carlos   Conc: 3.50  Vagas: 4  Min: 65
```

---

## Sobre

Este projeto foi criado para **facilitar a vida de quem esta se preparando para a Transferencia Externa da USP** - seja de humanas, biologicas ou exatas.

### Links uteis

- **YouTube** - Playlist com videos sobre Transferencia Externa (resolucoes de provas, dicas e mais): [Playlist Transferencia Externa](https://www.youtube.com/playlist?list=PLr9as5vz1dVykvwxlzq4M50GxrDallvMz)
- **Hotmart** - Material de estudo para a 1a fase (Matematica): [Primeira Fase Matematica](https://hotmart.com/pt-br/marketplace/produtos/primeira-fase-matematica-transferencia-2023-2024/C87159216E)

---

## Estrutura do projeto

```
notas_de_corte/
  transferencia_2019_nota_de_corte.pdf   # PDF original FUVEST
  transferencia_2020_nota_de_corte.pdf
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

## Contribuicoes

Encontrou algum erro nos dados? Quer adicionar o PDF de um ano que falta? Abra uma issue ou mande um PR!

## Licenca

MIT
