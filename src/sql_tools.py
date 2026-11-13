from __future__ import annotations

import json
from typing import Any

from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from sqlalchemy import Engine, text

from src.sql_guard import validate_read_only_query

MAX_RESULT_ROWS = 100


class ReadOnlySQLQueryTool(BaseTool):
    """Execute a single read-only SELECT and cap returned rows."""

    engine: Engine
    name: str = "sql_db_query"
    description: str = (
        "Execute one read-only SELECT query against the connected company database. "
        "Use the schema and query-checker tools before querying."
    )
    max_rows: int = MAX_RESULT_ROWS

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        safe_query = validate_read_only_query(query)
        with self.engine.connect() as connection:
            result = connection.execute(text(safe_query))
            if not result.returns_rows:
                raise ValueError("The SQL agent may only execute read-only SELECT queries.")
            columns = list(result.keys())
            rows = result.mappings().fetchmany(self.max_rows + 1)

        truncated = len(rows) > self.max_rows
        rows = rows[: self.max_rows]
        payload: dict[str, Any] = {
            "columns": columns,
            "rows": [dict(row) for row in rows],
            "truncated": truncated,
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


def build_database_tools(
    database: SQLDatabase,
    engine: Engine,
    llm,
    prefix: str,
) -> list[BaseTool]:
    """Build namespaced LangChain SQL toolkit tools with a guarded query executor."""
    toolkit = SQLDatabaseToolkit(db=database, llm=llm)
    tools: list[BaseTool] = []
    for selected_tool in toolkit.get_tools():
        if selected_tool.name == "sql_db_query":
            tools.append(
                ReadOnlySQLQueryTool(
                    engine=engine,
                    name=f"{prefix}_query",
                    description=(
                        f"Run one read-only SELECT query on the {prefix} company database. "
                        f"Use {prefix}_query_checker before executing a query."
                    ),
                )
            )
            continue

        short_name = selected_tool.name.removeprefix("sql_db_")
        tools.append(
            selected_tool.model_copy(
                update={
                    "name": f"{prefix}_{short_name}",
                    "description": f"{prefix.title()} database. {selected_tool.description}",
                }
            )
        )
    return tools
