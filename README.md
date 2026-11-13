# Assignment 33 — Chat with SQL using LangChain

A command-line business data assistant that turns natural-language questions into runtime-generated SQL, executes read-only queries, and answers from database results. It supports the included SQLite database and an optional MySQL database managed through MySQL Workbench.

## Features

- Creates `company.db` with SQLAlchemy and seeds 12 employees plus 15 sales.
- Uses LangChain's `SQLDatabase` and `SQLDatabaseToolkit` for table discovery, schema inspection, and query checking.
- Uses a LangChain agent to select database tools and generate SQL from the user's question.
- Supports SQLite, MySQL Workbench, or both databases in one agent.
- Restricts query execution to one `SELECT`/read-only CTE and blocks write statements.
- Runs SQLite agent connections with `PRAGMA query_only=ON`.
- Limits SQL tool results to 100 rows.
- Supports Ollama, OpenAI, and Groq chat models.
- Prints tool calls and observations so generated SQL and returned rows are easy to inspect.

## Requirements

- Python 3.10+
- Ollama with a local chat model, or an API key for OpenAI or Groq
- MySQL Server and MySQL Workbench only if using the optional MySQL backend

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python main.py --init-db
```

The final command creates `company.db` in the project folder. Run an Ollama model locally:

```powershell
ollama pull llama3.1
python main.py --provider ollama --backend sqlite --question "Who has the highest salary?"
```

For OpenAI, add `OPENAI_API_KEY` to `.env`:

```powershell
python main.py --provider openai --backend sqlite --question "What is the total sales amount?"
```

The default provider is read from `AGENT_PROVIDER` in `.env` (defaults to Ollama). Provider keys and database credentials must stay local; `.env` is ignored by Git.

## MySQL Workbench setup

1. Start a local MySQL Server connection in MySQL Workbench.
2. Open and execute [`data/mysql_workbench_setup.sql`](data/mysql_workbench_setup.sql). It creates the `company_db` schema and matching `employees` and `sales` sample tables.
3. In Workbench, create a dedicated read-only account. Use a strong local password:

   ```sql
   CREATE USER 'company_reader'@'127.0.0.1' IDENTIFIED BY 'choose-a-strong-password';
   GRANT SELECT ON company_db.* TO 'company_reader'@'127.0.0.1';
   ```

4. Put the SQLAlchemy URL in `.env`:

   ```dotenv
   MYSQL_URL=mysql+pymysql://company_reader:URL_ENCODED_PASSWORD@127.0.0.1:3306/company_db
   ```

   URL-encode special characters in the password. Do not commit credentials.
5. Ask a MySQL question:

   ```powershell
   python main.py --provider ollama --backend mysql --question "How many employees are in each department?"
   ```

To let the agent choose tools across both databases, configure `MYSQL_URL` and run:

```powershell
python main.py --provider ollama --backend both --question "Which database has the employee sales data?"
```

The MySQL backend requires a reachable MySQL Server. Workbench is the client used to create and inspect that database; the Python app connects to the server through SQLAlchemy and PyMySQL.

## CLI options

```text
python main.py --init-db
python main.py --provider {ollama,openai,groq} --backend {sqlite,mysql,both} --question "..."
python main.py --provider ollama --backend sqlite
```

Omit `--question` to start an interactive chat. Example questions:

- `How many employees are there in each department?`
- `Who has the highest salary?`
- `What is the total sales amount?`
- `What is the average salary per department?`

## Data model

| Table | Columns |
|---|---|
| `employees` | `id` (primary key), `name`, `department`, `salary` |
| `sales` | `sale_id` (primary key), `employee_id` (foreign key), `amount`, `sale_date` |

Both tables contain more than the required 10 sample rows. The SQLite database is reproducibly initialized by `python main.py --init-db`; the MySQL setup script uses the same schema and data.

## How it works

```text
Natural-language question
  -> LangChain SQL toolkit lists tables / inspects schema
  -> model generates SQL at runtime
  -> query-checker reviews the SQL
  -> read-only guard validates the query
  -> SQLAlchemy executes it against the selected database
  -> model summarizes only returned rows
```

The SQL is generated from the question and schema at runtime; answers are not hardcoded. When `--backend both` is selected, toolkit names are prefixed with `sqlite_` or `mysql_`, allowing the agent to distinguish databases.

## Safety and privacy

- The query tool accepts only a single `SELECT` or read-only CTE and rejects comments, multiple statements, write keywords, and selected high-risk functions.
- SQLite connections used by the agent enable `PRAGMA query_only=ON`; database setup uses a separate writable connection.
- For MySQL, connect with a user granted only `SELECT` on `company_db`. Do not use a MySQL administrator account.
- The agent is limited to the `employees` and `sales` tables, and query output is capped at 100 rows.
- The model receives the question, selected schema, generated SQL, and query results. Review your provider's data-handling terms before sending sensitive data.

## Run tests

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases and make no LLM or network calls.

## Assignment observations

1. **Why SQL agents can help:** Users can ask questions without manually composing SQL; an agent can inspect schemas, generate a query, execute it, and explain the result.
2. **SQL agent vs. RAG:** A SQL agent answers from structured, live rows and can aggregate or filter data. RAG retrieves relevant passages from unstructured documents. Choose based on the source format; combine them when both structured and document data are needed.
3. **Risk of unrestricted SQL access:** A model could modify or delete data, expose sensitive columns, run expensive queries, or exploit database features. Read-only credentials, table allowlists, query validation, row limits, and human oversight reduce the risk.

## Project structure

```text
.
├── company.db
├── data/
│   └── mysql_workbench_setup.sql
├── src/
│   ├── agent.py
│   ├── database.py
│   ├── sql_guard.py
│   └── sql_tools.py
├── tests/
│   ├── test_database.py
│   └── test_sql_guard.py
├── .env.example
├── .gitignore
├── main.py
├── requirements-test.txt
└── requirements.txt
```
