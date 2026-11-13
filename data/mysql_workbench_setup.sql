CREATE DATABASE IF NOT EXISTS company_db;
USE company_db;

CREATE TABLE IF NOT EXISTS employees (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(80) NOT NULL,
    salary INT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INT PRIMARY KEY,
    employee_id INT NOT NULL,
    amount INT NOT NULL,
    sale_date DATE NOT NULL,
    CONSTRAINT fk_sales_employee
        FOREIGN KEY (employee_id) REFERENCES employees (id)
);

INSERT INTO employees (id, name, department, salary) VALUES
    (1, 'Ava Patel', 'Engineering', 128000),
    (2, 'Liam Chen', 'Sales', 92000),
    (3, 'Mia Johnson', 'Marketing', 88000),
    (4, 'Noah Garcia', 'Engineering', 134000),
    (5, 'Isabella Kim', 'Finance', 105000),
    (6, 'Ethan Brown', 'Sales', 97000),
    (7, 'Amara Okafor', 'Human Resources', 91000),
    (8, 'Oliver Smith', 'Engineering', 121000),
    (9, 'Zara Ahmed', 'Marketing', 94000),
    (10, 'Lucas Martin', 'Finance', 112000),
    (11, 'Priya Nair', 'Sales', 101000),
    (12, 'Mateo Silva', 'Operations', 86000)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    department = VALUES(department),
    salary = VALUES(salary);

INSERT INTO sales (sale_id, employee_id, amount, sale_date) VALUES
    (1, 2, 18200, '2025-01-15'),
    (2, 6, 24600, '2025-01-22'),
    (3, 11, 31500, '2025-02-04'),
    (4, 2, 12750, '2025-02-18'),
    (5, 6, 28900, '2025-03-02'),
    (6, 11, 17400, '2025-03-12'),
    (7, 2, 22100, '2025-03-25'),
    (8, 6, 19800, '2025-04-03'),
    (9, 11, 35200, '2025-04-19'),
    (10, 2, 16400, '2025-05-01'),
    (11, 6, 27300, '2025-05-16'),
    (12, 11, 23800, '2025-06-07'),
    (13, 2, 19400, '2025-06-21'),
    (14, 6, 32700, '2025-07-09'),
    (15, 11, 21100, '2025-07-22')
ON DUPLICATE KEY UPDATE
    employee_id = VALUES(employee_id),
    amount = VALUES(amount),
    sale_date = VALUES(sale_date);
