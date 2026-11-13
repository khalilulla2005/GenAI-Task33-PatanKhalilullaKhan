from __future__ import annotations

import argparse
import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from src.database import create_sqlite_database, create_sqlite_engine
from src.sql_tools import build_database_tools

logger = logging.getLogger(__name__)
ALLOWED_TABLES = ["employees", "sales"]
MAX_AGENT_STEPS = 12

SYSTEM_PROMPT = """You are a read-only business data assistant connected to SQL databases.
Answer natural-language questions by inspecting the available tables and generating SQL
at runtime. Never hardcode answers or assume a schema. Use the table-list and schema
tools before querying unfamiliar tables. Use the matching database's query-checker before
executing SQL, then use its query tool and base the answer only on returned rows.

Safety rules:
- Only issue one SELECT or WITH...SELECT statement at a time.
- Never create, update, delete, drop, attach, or otherwise modify database objects or rows.
- Never query tables outside the employee and sales data exposed by the tools.
- If a question is ambiguous (for example, an unspecified time period or definition),
  ask a concise clarification instead of guessing.
- If a result is empty or unavailable, explain that; do not invent facts.
- Return a concise answer and mention which database was queried when relevant.
"""


def create_chat_model(provider: str | None = None):
    """Create an OpenAI, Ollama, or Groq chat model from environment configuration."""
    provider_name = (provider or os.getenv("AGENT_PROVIDER", "ollama")).casefold()

    if provider_name == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider.")
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            api_key=api_key,
        )

    if provider_name == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )

    if provider_name == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for the Groq provider.")
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            api_key=api_key,
        )

    raise ValueError(f"Unsupported provider '{provider_name}'. Choose openai, ollama, or groq.")


def _create_mysql_engine(mysql_url: str | None) -> Engine:
    if not mysql_url:
        raise ValueError(
            "MYSQL_URL is required for the mysql or both backend. Configure a "
            "SELECT-only MySQL user in .env."
        )
    url = make_url(mysql_url)
    if url.drivername == "mysql":
        url = url.set(drivername="mysql+pymysql")
    if url.drivername != "mysql+pymysql":
        raise ValueError("MYSQL_URL must use the mysql+pymysql SQLAlchemy driver.")
    return create_engine(url, pool_pre_ping=True)


def create_database_tools(
    llm,
    backend: str = "sqlite",
    mysql_url: str | None = None,
) -> tuple[list, list[Engine]]:
    """Build SQL toolkit tools for SQLite, MySQL Workbench, or both."""
    if backend not in {"sqlite", "mysql", "both"}:
        raise ValueError("backend must be sqlite, mysql, or both.")

    engines: list[Engine] = []
    tools = []
    try:
        if backend in {"sqlite", "both"}:
            create_sqlite_database()
            sqlite_engine = create_sqlite_engine(read_only=True)
            engines.append(sqlite_engine)
            sqlite_db = SQLDatabase(
                engine=sqlite_engine,
                include_tables=ALLOWED_TABLES,
                sample_rows_in_table_info=2,
                max_string_length=1000,
            )
            tools.extend(
                build_database_tools(sqlite_db, sqlite_engine, llm, prefix="sqlite")
            )

        if backend in {"mysql", "both"}:
            mysql_engine = _create_mysql_engine(mysql_url)
            engines.append(mysql_engine)
            mysql_db = SQLDatabase(
                engine=mysql_engine,
                include_tables=ALLOWED_TABLES,
                sample_rows_in_table_info=2,
                max_string_length=1000,
            )
            tools.extend(
                build_database_tools(mysql_db, mysql_engine, llm, prefix="mysql")
            )
        return tools, engines
    except Exception:
        for engine in engines:
            engine.dispose()
        raise


def build_sql_agent(llm, tools: list):
    """Create a LangChain agent over the guarded SQL database toolkit tools."""
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )


def ask_sql_agent(agent, question: str) -> tuple[str, list[dict[str, Any]]]:
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    result = agent.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": MAX_AGENT_STEPS * 2 + 3},
    )
    trace_by_id: dict[str, dict[str, Any]] = {}
    trace: list[dict[str, Any]] = []
    messages = result.get("messages", [])
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                step = {
                    "tool": tool_call["name"],
                    "input": tool_call.get("args", {}),
                    "observation": "",
                }
                trace.append(step)
                if tool_call.get("id"):
                    trace_by_id[str(tool_call["id"])] = step
        elif isinstance(message, ToolMessage):
            step = trace_by_id.get(str(message.tool_call_id))
            if step is not None:
                step["observation"] = message.content

    final_message = next(
        (
            message
            for message in reversed(messages)
            if isinstance(message, AIMessage) and not message.tool_calls
        ),
        None,
    )
    if final_message is None:
        raise RuntimeError("The SQL agent did not produce a final answer.")
    answer = final_message.content
    if not isinstance(answer, str):
        answer = str(answer)
    return answer.strip(), trace


def _print_trace(trace: list[dict[str, Any]]) -> None:
    for index, step in enumerate(trace, start=1):
        tool_input = str(step["input"]).replace("\n", " ")
        observation = str(step["observation"]).replace("\n", " ")
        if len(observation) > 1000:
            observation = observation[:997] + "..."
        print(f"\n[Tool {index}] {step['tool']}: {tool_input}")
        if observation:
            print(f"Observation: {observation}")


def _answer_question(agent, question: str) -> None:
    answer, trace = ask_sql_agent(agent, question)
    _print_trace(trace)
    print(f"\nAnswer: {answer}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Ask natural-language questions over SQLite and MySQL databases."
    )
    parser.add_argument(
        "--provider",
        choices=("openai", "ollama", "groq"),
        default=None,
        help="LLM provider; defaults to AGENT_PROVIDER or ollama.",
    )
    parser.add_argument(
        "--backend",
        choices=("sqlite", "mysql", "both"),
        default="sqlite",
        help="Database target. The MySQL options require MYSQL_URL.",
    )
    parser.add_argument(
        "--question",
        "--query",
        dest="question",
        help="Ask one question instead of starting interactive mode.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create company.db and seed its mock employees and sales.",
    )
    args = parser.parse_args()

    if args.init_db:
        database_path = create_sqlite_database()
        print(f"SQLite database is ready: {database_path}")
        return

    engines: list[Engine] = []
    try:
        llm = create_chat_model(args.provider)
        tools, engines = create_database_tools(
            llm,
            backend=args.backend,
            mysql_url=os.getenv("MYSQL_URL"),
        )
        agent = build_sql_agent(llm, tools)
        if args.question:
            _answer_question(agent, args.question)
        else:
            print(
                "Company SQL Assistant. Ask about employees or sales; type 'exit' to quit."
            )
            while True:
                question = input("\nQuestion: ").strip()
                if question.casefold() in {"exit", "quit", "q"}:
                    break
                if not question:
                    print("Please enter a question.")
                    continue
                _answer_question(agent, question)
    except Exception as exc:
        logger.exception("The SQL agent run failed.")
        raise SystemExit(f"Agent error: {type(exc).__name__}: {exc}") from exc
    finally:
        for engine in engines:
            engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
