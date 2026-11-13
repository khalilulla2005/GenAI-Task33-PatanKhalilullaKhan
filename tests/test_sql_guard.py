import unittest

from src.sql_guard import validate_read_only_query


class SQLGuardTests(unittest.TestCase):
    def test_select_and_read_only_cte_are_allowed(self):
        self.assertEqual(
            validate_read_only_query("SELECT COUNT(*) FROM employees;"),
            "SELECT COUNT(*) FROM employees;",
        )
        cte = "WITH department_totals AS (SELECT department, COUNT(*) n FROM employees GROUP BY department) SELECT * FROM department_totals"
        self.assertEqual(validate_read_only_query(cte), cte)

    def test_non_select_statements_are_rejected(self):
        for query in (
            "DELETE FROM employees",
            "UPDATE employees SET salary = 0",
            "DROP TABLE employees",
            "SELECT * FROM employees; DROP TABLE employees",
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                validate_read_only_query(query)

    def test_sql_comments_and_dangerous_functions_are_rejected(self):
        for query in (
            "SELECT * FROM employees -- bypass",
            "SELECT SLEEP(10)",
            "SELECT LOAD_FILE('/etc/passwd')",
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                validate_read_only_query(query)

    def test_empty_and_oversized_queries_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_read_only_query(" ")
        with self.assertRaises(ValueError):
            validate_read_only_query("SELECT " + "x" * 10_000)


if __name__ == "__main__":
    unittest.main()
