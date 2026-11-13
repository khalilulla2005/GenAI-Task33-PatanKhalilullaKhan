from __future__ import annotations

import re

_QUOTED_TEXT = re.compile(
    r"""'(?:''|\\.|[^'])*'|"(?:\"\"|\\.|[^"])*"|`(?:``|[^`])*`""",
    re.DOTALL,
)
_FORBIDDEN_WORDS = {
    "ALTER",
    "ATTACH",
    "BEGIN",
    "CALL",
    "COMMIT",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "INSERT",
    "INTO",
    "LOAD",
    "LOCK",
    "REPLACE",
    "REVOKE",
    "ROLLBACK",
    "SET",
    "TRUNCATE",
    "UNLOCK",
    "UPDATE",
    "USE",
    "VACUUM",
}
_FORBIDDEN_FUNCTIONS = {
    "BENCHMARK",
    "LOAD_FILE",
    "LOAD_EXTENSION",
    "READFILE",
    "SLEEP",
    "WRITEFILE",
}


def validate_read_only_query(query: str) -> str:
    """Allow one SELECT/CTE statement and reject writes, comments, and risky functions."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("SQL query must not be empty.")
    if len(query) > 10_000:
        raise ValueError("SQL query exceeds the 10,000-character limit.")

    unquoted = _QUOTED_TEXT.sub(" ", query).strip()
    if any(marker in unquoted for marker in ("--", "/*", "*/", "#")):
        raise ValueError("SQL comments are not allowed.")

    statement = unquoted[:-1].rstrip() if unquoted.endswith(";") else unquoted
    if ";" in statement:
        raise ValueError("Only one SQL statement may be executed at a time.")
    if not re.match(r"^(SELECT|WITH)\b", statement, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    words = set(re.findall(r"\b[A-Z_]+\b", statement.upper()))
    forbidden = words.intersection(_FORBIDDEN_WORDS)
    if forbidden:
        raise ValueError(
            "Read-only SQL restriction blocked keyword(s): "
            + ", ".join(sorted(forbidden))
        )

    for function_name in _FORBIDDEN_FUNCTIONS:
        if re.search(rf"\b{function_name}\s*\(", statement, flags=re.IGNORECASE):
            raise ValueError(f"Read-only SQL restriction blocked {function_name}().")
    return query.strip()
