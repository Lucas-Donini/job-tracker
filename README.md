# 🔎 Job Tracker

Ferramenta de linha de comando em Python que **coleta vagas de emprego**, guarda o **histórico em SQLite** (o que é novo, o que continua aberto, o que saiu do ar) e **exporta relatórios para Excel/CSV**.

## O que ele faz

- **Coleta** de duas fontes diferentes:
  - `fakejobs`: **web scraping** de HTML (BeautifulSoup) em um site de treino
  - `remotive`: consumo de uma **API JSON** pública de vagas remotas
- **Histórico em banco**: cada coleta é registrada; vagas ganham data de 1ª e última vez vistas e status ativa/encerrada
- **Sem duplicar**: rodar duas vezes não cria vagas repetidas (chave única fonte + id)
- **Consulta** pelo terminal com filtros (palavra-chave, empresa, local, só novas)
- **Exporta** para `.xlsx` (formatado, com filtros e links clicáveis) ou `.csv`

## Instalação

```bash
git clone <url-do-repositorio>
cd job-tracker
python -m venv .venv
.venv\Scripts\Activate.ps1        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python -m jobtracker collect                      # coleta a fonte padrão (fakejobs)
python -m jobtracker collect -s remotive -q python  # vagas remotas de Python
python -m jobtracker list -k python               # busca no título/empresa
python -m jobtracker list --new                   # só as inéditas da última coleta
python -m jobtracker stats                        # números gerais
python -m jobtracker export -o output/vagas.xlsx  # exporta (use .csv para CSV)
```

Exemplo de saída ao coletar duas vezes (entre elas, uma vaga saiu do site e outra entrou):

```
[fakejobs] 3 vagas | 3 novas | 0 já conhecidas | 0 encerradas
[fakejobs] 3 vagas | 1 novas | 2 já conhecidas | 1 encerradas
```

Veja um exemplo de exportação em [`docs/exemplo_vagas.xlsx`](docs/exemplo_vagas.xlsx). O banco fica em `data/jobs.db` (mude com `--db`).

## Estrutura

```
jobtracker/
├── sources/
│   ├── fakejobs.py   # scraping de HTML
│   └── remotive.py   # API JSON
├── db.py             # SQLite: esquema, gravação atômica, busca, estatísticas
├── export.py         # Excel (openpyxl) e CSV
├── http.py           # sessão HTTP com User-Agent, timeout e retry
├── models.py         # dataclass Job
└── cli.py            # comandos collect | list | stats | export
tests/                # pytest, roda offline
```

## Decisões de projeto

- **Fontes plugáveis**: cada fonte é um módulo com `collect()`; para adicionar outra basta criar o arquivo e registrá-lo em `sources/__init__.py`.
- **Gravação em transação**: uma coleta grava tudo ou nada, sem deixar o banco pela metade.
- **Fechamento seguro de vagas**: uma vaga só é marcada como encerrada em coleta **completa** e **não vazia**. Coleta com `-q` (parcial) ou que falhou e veio vazia não fecha nada por engano.
- **Parser separado da rede**: o parsing recebe texto/JSON, então é testado sem internet.
- **Boas práticas de coleta**: User-Agent identificado, retry com backoff, uso moderado de APIs.

## Testes

```bash
python -m pytest
```

Cobrem parsing das fontes, lógica de histórico (nova/atualizada/encerrada/reaberta), filtros de busca, exportação e CLI de ponta a ponta.

## Créditos

Vagas do `remotive` fornecidas por [Remotive](https://remotive.com) (a API pede uso moderado e citação da fonte). Vagas do `fakejobs` são fictícias, do site de treino do Real Python.

## Próximos passos possíveis

- Mais fontes (outros sites e APIs de vagas)
- Agendamento diário (Agendador de Tarefas do Windows / cron)
- Aviso por e-mail quando surgirem vagas novas com certa palavra-chave
