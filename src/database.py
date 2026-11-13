from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    URL,
    create_engine,
    event,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "company.db"

metadata = MetaData()
employees = Table(
    "employees",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("department", String(80), nullable=False, index=True),
    Column("salary", Integer, nullable=False),
)
sales = Table(
    "sales",
    metadata,
    Column("sale_id", Integer, primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), nullable=False, index=True),
    Column("amount", Integer, nullable=False),
    Column("sale_date", String(10), nullable=False),
)

SAMPLE_EMPLOYEES = [
    {"id": 1, "name": "Ava Patel", "department": "Engineering", "salary": 128000},
    {"id": 2, "name": "Liam Chen", "department": "Sales", "salary": 92000},
    {"id": 3, "name": "Mia Johnson", "department": "Marketing", "salary": 88000},
    {"id": 4, "name": "Noah Garcia", "department": "Engineering", "salary": 134000},
    {"id": 5, "name": "Isabella Kim", "department": "Finance", "salary": 105000},
    {"id": 6, "name": "Ethan Brown", "department": "Sales", "salary": 97000},
    {"id": 7, "name": "Amara Okafor", "department": "Human Resources", "salary": 91000},
    {"id": 8, "name": "Oliver Smith", "department": "Engineering", "salary": 121000},
    {"id": 9, "name": "Zara Ahmed", "department": "Marketing", "salary": 94000},
    {"id": 10, "name": "Lucas Martin", "department": "Finance", "salary": 112000},
    {"id": 11, "name": "Priya Nair", "department": "Sales", "salary": 101000},
    {"id": 12, "name": "Mateo Silva", "department": "Operations", "salary": 86000},
]
SAMPLE_SALES = [
    {"sale_id": 1, "employee_id": 2, "amount": 18200, "sale_date": "2025-01-15"},
    {"sale_id": 2, "employee_id": 6, "amount": 24600, "sale_date": "2025-01-22"},
    {"sale_id": 3, "employee_id": 11, "amount": 31500, "sale_date": "2025-02-04"},
    {"sale_id": 4, "employee_id": 2, "amount": 12750, "sale_date": "2025-02-18"},
    {"sale_id": 5, "employee_id": 6, "amount": 28900, "sale_date": "2025-03-02"},
    {"sale_id": 6, "employee_id": 11, "amount": 17400, "sale_date": "2025-03-12"},
    {"sale_id": 7, "employee_id": 2, "amount": 22100, "sale_date": "2025-03-25"},
    {"sale_id": 8, "employee_id": 6, "amount": 19800, "sale_date": "2025-04-03"},
    {"sale_id": 9, "employee_id": 11, "amount": 35200, "sale_date": "2025-04-19"},
    {"sale_id": 10, "employee_id": 2, "amount": 16400, "sale_date": "2025-05-01"},
    {"sale_id": 11, "employee_id": 6, "amount": 27300, "sale_date": "2025-05-16"},
    {"sale_id": 12, "employee_id": 11, "amount": 23800, "sale_date": "2025-06-07"},
    {"sale_id": 13, "employee_id": 2, "amount": 19400, "sale_date": "2025-06-21"},
    {"sale_id": 14, "employee_id": 6, "amount": 32700, "sale_date": "2025-07-09"},
    {"sale_id": 15, "employee_id": 11, "amount": 21100, "sale_date": "2025-07-22"},
]


def create_sqlite_engine(
    path: str | Path = DEFAULT_SQLITE_PATH,
    *,
    read_only: bool = False,
) -> Engine:
    """Create the SQLite engine; agent connections can be forced read-only."""
    database_path = Path(path).resolve()
    url = URL.create("sqlite", database=str(database_path))
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if read_only:
            cursor.execute("PRAGMA query_only=ON")
        cursor.close()

    return engine


def create_sqlite_database(path: str | Path = DEFAULT_SQLITE_PATH) -> Path:
    """Create company.db and seed at least ten mock rows in each table."""
    database_path = Path(path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_sqlite_engine(database_path)
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            employee_count = connection.scalar(
                select(func.count()).select_from(employees)
            )
            if not employee_count:
                connection.execute(insert(employees), SAMPLE_EMPLOYEES)

            sales_count = connection.scalar(select(func.count()).select_from(sales))
            if not sales_count:
                connection.execute(insert(sales), SAMPLE_SALES)
    finally:
        engine.dispose()
    return database_path
