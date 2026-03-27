"""
Sample Database Generator

Creates a multi-domain sample SQLite database for testing the NL2SQL agent.
Domains: E-commerce, HR, Finance
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random


def create_sample_database(db_path: str = "./sample.db"):
    """Create a comprehensive sample database with multiple domains."""
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ==========================================
    # E-COMMERCE DOMAIN
    # ==========================================
    
    # Customers table
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            city TEXT,
            country TEXT,
            signup_date DATE,
            is_premium BOOLEAN DEFAULT 0
        )
    """)
    
    # Products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock_quantity INTEGER,
            rating REAL
        )
    """)
    
    # Orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            total_amount REAL,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)
    
    # Order items table
    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # ==========================================
    # HR DOMAIN
    # ==========================================
    
    # Departments table
    cursor.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL,
            manager_id INTEGER
        )
    """)
    
    # Employees table
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            department_id INTEGER,
            position TEXT,
            salary REAL,
            hire_date DATE,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)
    
    # Leaves table
    cursor.execute("""
        CREATE TABLE leaves (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            leave_type TEXT,
            start_date DATE,
            end_date DATE,
            days INTEGER,
            status TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)
    
    # ==========================================
    # FINANCE DOMAIN
    # ==========================================
    
    # Accounts table
    cursor.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            account_name TEXT NOT NULL,
            account_type TEXT,
            balance REAL,
            created_date DATE
        )
    """)
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            account_id INTEGER,
            transaction_date DATE,
            transaction_type TEXT,
            amount REAL,
            description TEXT,
            category TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    
    # Budgets table
    cursor.execute("""
        CREATE TABLE budgets (
            id INTEGER PRIMARY KEY,
            category TEXT,
            allocated_amount REAL,
            spent_amount REAL,
            fiscal_year INTEGER,
            quarter INTEGER
        )
    """)
    
    # ==========================================
    # INSERT SAMPLE DATA
    # ==========================================
    
    # Customers
    customers = [
        ("Rahul Sharma", "rahul@email.com", "Mumbai", "India", "2023-01-15", 1),
        ("Priya Patel", "priya@email.com", "Delhi", "India", "2023-02-20", 0),
        ("Amit Kumar", "amit@email.com", "Bangalore", "India", "2023-03-10", 1),
        ("Sneha Reddy", "sneha@email.com", "Hyderabad", "India", "2023-04-05", 0),
        ("Vikram Singh", "vikram@email.com", "Chennai", "India", "2023-05-12", 1),
        ("Ananya Gupta", "ananya@email.com", "Pune", "India", "2023-06-18", 0),
        ("Rohit Joshi", "rohit@email.com", "Kolkata", "India", "2023-07-22", 0),
        ("Kavya Nair", "kavya@email.com", "Kochi", "India", "2023-08-30", 1),
        ("Arjun Menon", "arjun@email.com", "Jaipur", "India", "2023-09-14", 0),
        ("Divya Iyer", "divya@email.com", "Ahmedabad", "India", "2023-10-25", 1),
        ("Karan Malhotra", "karan@email.com", "Lucknow", "India", "2023-11-08", 0),
        ("Meera Krishnan", "meera@email.com", "Chandigarh", "India", "2023-12-01", 0),
        ("Sanjay Verma", "sanjay@email.com", "Indore", "India", "2024-01-10", 1),
        ("Pooja Saxena", "pooja@email.com", "Bhopal", "India", "2024-01-20", 0),
        ("Nikhil Rao", "nikhil@email.com", "Nagpur", "India", "2024-02-05", 0)
    ]
    cursor.executemany("INSERT INTO customers (name, email, city, country, signup_date, is_premium) VALUES (?, ?, ?, ?, ?, ?)", customers)
    
    # Products
    products = [
        ("Laptop Pro 15", "Electronics", 75000, 50, 4.5),
        ("Wireless Headphones", "Electronics", 5000, 200, 4.2),
        ("Smart Watch", "Electronics", 15000, 100, 4.0),
        ("Smartphone X", "Electronics", 45000, 75, 4.6),
        ("Tablet Air", "Electronics", 35000, 60, 4.3),
        ("Cotton T-Shirt", "Clothing", 800, 500, 4.1),
        ("Denim Jeans", "Clothing", 2500, 300, 4.4),
        ("Running Shoes", "Footwear", 4500, 150, 4.5),
        ("Formal Shirt", "Clothing", 1800, 400, 4.0),
        ("Office Chair", "Furniture", 12000, 40, 4.2),
        ("Study Desk", "Furniture", 8000, 30, 4.3),
        ("Coffee Maker", "Appliances", 6000, 80, 4.1),
        ("Air Purifier", "Appliances", 18000, 45, 4.4),
        ("Book: Python Programming", "Books", 600, 200, 4.7),
        ("Book: Data Science", "Books", 750, 150, 4.5)
    ]
    cursor.executemany("INSERT INTO products (name, category, price, stock_quantity, rating) VALUES (?, ?, ?, ?, ?)", products)
    
    # Departments
    departments = [
        ("Engineering", 5000000, 1),
        ("Sales", 3000000, 6),
        ("Marketing", 2000000, 11),
        ("Human Resources", 1500000, 16),
        ("Finance", 2500000, 21),
        ("Operations", 2000000, 26)
    ]
    cursor.executemany("INSERT INTO departments (name, budget, manager_id) VALUES (?, ?, ?)", departments)
    
    # Employees
    employees = [
        ("Rajesh Kumar", "rajesh@company.com", 1, "Engineering Manager", 150000, "2020-01-15", 1),
        ("Sunita Sharma", "sunita@company.com", 1, "Senior Developer", 120000, "2020-03-20", 1),
        ("Arun Patel", "arun@company.com", 1, "Developer", 80000, "2021-06-10", 1),
        ("Neha Singh", "neha@company.com", 1, "Developer", 75000, "2022-01-05", 1),
        ("Vijay Reddy", "vijay@company.com", 1, "Junior Developer", 50000, "2023-04-12", 1),
        ("Priya Menon", "priyam@company.com", 2, "Sales Manager", 130000, "2019-08-18", 1),
        ("Suresh Iyer", "suresh@company.com", 2, "Sales Executive", 70000, "2020-11-22", 1),
        ("Kavitha Nair", "kavitha@company.com", 2, "Sales Executive", 65000, "2021-09-30", 1),
        ("Ramesh Gupta", "ramesh@company.com", 2, "Sales Trainee", 40000, "2023-02-14", 1),
        ("Deepa Joshi", "deepa@company.com", 2, "Sales Executive", 68000, "2022-05-25", 1),
        ("Anita Verma", "anita@company.com", 3, "Marketing Manager", 125000, "2019-04-08", 1),
        ("Manoj Saxena", "manoj@company.com", 3, "Marketing Specialist", 85000, "2020-07-01", 1),
        ("Rita Kapoor", "rita@company.com", 3, "Content Writer", 55000, "2021-12-10", 1),
        ("Sanjay Rao", "sanjay@company.com", 3, "SEO Specialist", 60000, "2022-08-20", 1),
        ("Pooja Malhotra", "poojam@company.com", 3, "Social Media Manager", 70000, "2023-01-15", 1),
        ("Harish Krishnan", "harish@company.com", 4, "HR Manager", 110000, "2018-06-25", 1),
        ("Lakshmi Pillai", "lakshmi@company.com", 4, "HR Executive", 60000, "2020-10-05", 1),
        ("Ganesh Murthy", "ganesh@company.com", 4, "Recruiter", 55000, "2021-03-18", 1),
        ("Bhavana Reddy", "bhavana@company.com", 4, "HR Trainee", 35000, "2023-06-01", 1),
        ("Kiran Desai", "kiran@company.com", 4, "Payroll Specialist", 65000, "2022-02-28", 1),
        ("Ashwin Nair", "ashwin@company.com", 5, "Finance Manager", 140000, "2017-09-12", 1),
        ("Meenakshi Iyer", "meenakshi@company.com", 5, "Accountant", 75000, "2019-12-20", 1),
        ("Ravi Shankar", "ravi@company.com", 5, "Financial Analyst", 90000, "2020-05-15", 1),
        ("Geetha Suresh", "geetha@company.com", 5, "Accounts Executive", 55000, "2022-04-10", 1),
        ("Mohan Das", "mohan@company.com", 5, "Tax Specialist", 85000, "2021-08-22", 1),
        ("Venkat Rao", "venkat@company.com", 6, "Operations Manager", 120000, "2018-11-30", 1),
        ("Sarala Devi", "sarala@company.com", 6, "Operations Executive", 65000, "2020-02-14", 1),
        ("Prakash Nair", "prakash@company.com", 6, "Logistics Coordinator", 58000, "2021-07-08", 1),
        ("Usha Rani", "usha@company.com", 6, "Inventory Manager", 72000, "2022-09-25", 1),
        ("Balaji Krishnan", "balaji@company.com", 6, "Quality Analyst", 68000, "2023-03-05", 1)
    ]
    cursor.executemany("INSERT INTO employees (name, email, department_id, position, salary, hire_date, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", employees)
    
    # Generate Orders
    orders = []
    order_items = []
    order_id = 1
    item_id = 1
    
    statuses = ["Delivered", "Processing", "Shipped", "Cancelled", "Pending"]
    
    for customer_id in range(1, 16):
        num_orders = random.randint(1, 5)
        for _ in range(num_orders):
            order_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 30))
            status = random.choice(statuses)
            total = 0
            
            # Generate 1-4 items per order
            num_items = random.randint(1, 4)
            for _ in range(num_items):
                product_id = random.randint(1, 15)
                quantity = random.randint(1, 3)
                unit_price = products[product_id - 1][2]  # Get price from products list
                item_total = quantity * unit_price
                total += item_total
                
                order_items.append((item_id, order_id, product_id, quantity, unit_price))
                item_id += 1
            
            orders.append((order_id, customer_id, order_date.strftime("%Y-%m-%d"), total, status))
            order_id += 1
    
    cursor.executemany("INSERT INTO orders (id, customer_id, order_date, total_amount, status) VALUES (?, ?, ?, ?, ?)", orders)
    cursor.executemany("INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)", order_items)
    
    # Leaves
    leave_types = ["Sick", "Casual", "Earned", "Maternity", "Paternity"]
    leave_statuses = ["Approved", "Pending", "Rejected"]
    leaves = []
    
    for emp_id in range(1, 31):
        num_leaves = random.randint(0, 3)
        for _ in range(num_leaves):
            leave_type = random.choice(leave_types)
            start = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 30))
            days = random.randint(1, 5)
            end = start + timedelta(days=days)
            status = random.choice(leave_statuses)
            leaves.append((emp_id, leave_type, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), days, status))
    
    cursor.executemany("INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, status) VALUES (?, ?, ?, ?, ?, ?)", leaves)
    
    # Accounts
    accounts = [
        ("Main Operating Account", "Checking", 5000000, "2020-01-01"),
        ("Savings Reserve", "Savings", 10000000, "2020-01-01"),
        ("Petty Cash", "Cash", 50000, "2020-01-01"),
        ("Marketing Fund", "Checking", 1000000, "2021-06-15"),
        ("Emergency Fund", "Savings", 2500000, "2020-01-01")
    ]
    cursor.executemany("INSERT INTO accounts (account_name, account_type, balance, created_date) VALUES (?, ?, ?, ?)", accounts)
    
    # Transactions
    transaction_types = ["Credit", "Debit"]
    categories = ["Salary", "Utilities", "Marketing", "Equipment", "Travel", "Office Supplies", "Revenue", "Rent"]
    transactions = []
    
    for _ in range(50):
        account_id = random.randint(1, 5)
        trans_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 30))
        trans_type = random.choice(transaction_types)
        amount = random.randint(5000, 500000)
        category = random.choice(categories)
        description = f"{category} - {trans_type}"
        transactions.append((account_id, trans_date.strftime("%Y-%m-%d"), trans_type, amount, description, category))
    
    cursor.executemany("INSERT INTO transactions (account_id, transaction_date, transaction_type, amount, description, category) VALUES (?, ?, ?, ?, ?, ?)", transactions)
    
    # Budgets
    budgets = [
        ("Salary", 8000000, 7500000, 2024, 1),
        ("Marketing", 2000000, 1800000, 2024, 1),
        ("Equipment", 1000000, 750000, 2024, 1),
        ("Travel", 500000, 400000, 2024, 1),
        ("Office Supplies", 200000, 180000, 2024, 1),
        ("Utilities", 300000, 280000, 2024, 1),
        ("Training", 400000, 250000, 2024, 1),
        ("Rent", 1200000, 1200000, 2024, 1)
    ]
    cursor.executemany("INSERT INTO budgets (category, allocated_amount, spent_amount, fiscal_year, quarter) VALUES (?, ?, ?, ?, ?)", budgets)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Sample database created at: {db_path}")
    print("📊 Tables created:")
    print("   E-commerce: customers, products, orders, order_items")
    print("   HR: departments, employees, leaves")
    print("   Finance: accounts, transactions, budgets")
    

if __name__ == "__main__":
    create_sample_database()
