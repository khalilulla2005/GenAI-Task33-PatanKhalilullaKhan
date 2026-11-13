from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from langchain_community.utilities import SQLDatabase
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src.database import create_sqlite_database, create_sqlite_engine
from src.sql_tools import ReadOnlySQLQueryTool


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "company.db"
        create_sqlite_database(self.database_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_seed_data_has_ten_or_more_rows_in_both_tables(self):
        engine = create_sqlite_engine(self.database_path, read_only=True)
        try:
            with engine.connect() as connection:
                employee_count = connection.scalar(
                    text("SELECT COUNT(*) FROM employees")
                )
                sales_count = connection.scalar(text("SELECT COUNT(*) FROM sales"))
            self.assertGreaterEqual(employee_count, 10)
            self.assertGreaterEqual(sales_count, 10)
        finally:
            engine.dispose()

    def test_database_initialization_is_idempotent(self):
        create_sqlite_database(self.database_path)
        engine = create_sqlite_engine(self.database_path, read_only=True)
        try:
            with engine.connect() as connection:
                self.assertEqual(
                    connection.scalar(text("SELECT COUNT(*) FROM employees")),
                    12,
                )
                self.assertEqual(
                    connection.scalar(text("SELECT COUNT(*) FROM sales")),
                    15,
                )
        finally:
            engine.dispose()

    def test_langchain_sql_database_reads_schema_and_data(self):
        engine = create_sqlite_engine(self.database_path, read_only=True)
        try:
            database = SQLDatabase(
                engine=engine,
                include_tables=["employees", "sales"],
                sample_rows_in_table_info=1,
            )
            self.assertEqual(set(database.get_usable_table_names()), {"employees", "sales"})
            self.assertIn("employees", database.get_table_info())
            self.assertIn("Ava Patel", database.run("SELECT name FROM employees WHERE id = 1"))
        finally:
            engine.dispose()

    def test_read_only_query_tool_returns_rows_but_rejects_writes(self):
        engine = create_sqlite_engine(self.database_path, read_only=True)
        try:
            query_tool = ReadOnlySQLQueryTool(engine=engine, name="sqlite_query")
            result = json.loads(
                query_tool.invoke(
                    {"query": "SELECT name, salary FROM employees WHERE id = 1"}
                )
            )
            self.assertEqual(result["rows"][0]["name"], "Ava Patel")
            with self.assertRaises(ValueError):
                query_tool.invoke(
                    {"query": "UPDATE employees SET salary = 1 WHERE id = 1"}
                )
        finally:
            engine.dispose()

    def test_sqlite_engine_itself_blocks_writes(self):
        engine = create_sqlite_engine(self.database_path, read_only=True)
        try:
            with engine.connect() as connection:
                with self.assertRaises(OperationalError):
                    connection.execute(
                        text("UPDATE employees SET salary = 1 WHERE id = 1")
                    )
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
