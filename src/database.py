import sqlite3
from sqlite3 import Error

class Database:
    def __init__(self, db_file="car_sales.db"):
        # Establish connection to the database and create necessary tables
        self.conn = self.create_connection(db_file)
        self.create_tables()

    def create_connection(self, db_file):
        # Connect to SQLite database (or create it if it doesn't exist)
        try:
            conn = sqlite3.connect(db_file)
            print(f"Connected to database: {db_file}")
            return conn
        except Error as e:
            print(f"Connection error: {e}")
            return None

    def create_tables(self):
        # SQL statement to create the cars table if it doesn't exist
        create_cars_table = """
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER,
            price REAL,
            color TEXT,
            type TEXT,
            condition TEXT,
            drive_trains TEXT,
            engine_power INTEGER,
            liter_capacity INTEGER,
            salesperson TEXT
        );"""
        self.execute_query(create_cars_table)

    def execute_query(self, query, params=None):
        # Execute any SQL query (insert, update, delete, etc.)
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except Error as e:
            print(f"Query error: {e}")
            return None

    def add_car(self, car_data):
        # Insert a new car record into the database
        query = """
        INSERT INTO cars
        (make, model, year, price, color, type, condition, drive_trains, engine_power, liter_capacity, salesperson)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.execute_query(query, tuple(car_data.values()))

    def fetch_all_cars(self):
        # Retrieve all cars from the database
        query = "SELECT * FROM cars"
        cursor = self.execute_query(query)
        if cursor:
            return cursor.fetchall()
        return []

    def fetch_cars_by_make(self, make):
        # Retrieve cars from the database by specific make
        query = "SELECT * FROM cars WHERE make=?"
        cursor = self.execute_query(query, (make,))
        if cursor:
            return cursor.fetchall()
        return []

    def update_car(self, car_id, updates):
        # Update fields of a specific car based on its ID
        set_clause = ", ".join([f"{key}=?" for key in updates.keys()])
        params = list(updates.values()) + [car_id]
        query = f"UPDATE cars SET {set_clause} WHERE id=?"
        return self.execute_query(query, params)

    def delete_car(self, car_id):
        # Delete a car record from the database by ID
        query = "DELETE FROM cars WHERE id=?"
        return self.execute_query(query, (car_id,))
