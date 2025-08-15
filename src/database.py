import sqlite3
from sqlite3 import Error
import os

class Database:
    def __init__(self, db_file="car_sales.db"):
        self.db_file = db_file
        self.conn = self.create_connection(db_file)
        self._apply_pragmas()
        self.create_tables()     # إنشاء إن لم يوجد
        self._migrate_schema()   # ترقية الأعمدة الناقصة (image_path)
        self._create_indexes()   # فهارس مفيدة
        self._debug_schema()     # Debug: اطبع الأعمدة عشان تتأكد

    def create_connection(self, db_file):
        try:
            # استخدم مسار مطلق لتفادي اللبس
            abs_path = os.path.abspath(db_file)
            print(f"[DB] Connecting to: {abs_path}")
            conn = sqlite3.connect(abs_path)
            return conn
        except Error as e:
            print(f"[DB] Connection error: {e}")
            return None

    def _apply_pragmas(self):
        if not self.conn:
            return
        try:
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")
        except Error as e:
            print(f"[DB] PRAGMA error: {e}")

    def create_tables(self):
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
            salesperson TEXT,
            image_path TEXT
        );
        """
        self.execute_query(create_cars_table)

        create_imgs = """
        CREATE TABLE IF NOT EXISTS car_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            path TEXT
        );
        """
        self.execute_query(create_imgs)

    def _migrate_schema(self):
        """أضف أي أعمدة ناقصة (خصوصًا image_path)"""
        try:
            cur = self.conn.execute("PRAGMA table_info(cars)")
            existing = {row[1] for row in cur.fetchall()}  # column names
            required = {
                "make": "TEXT",
                "model": "TEXT",
                "year": "INTEGER",
                "price": "REAL",
                "color": "TEXT",
                "type": "TEXT",
                "condition": "TEXT",
                "drive_trains": "TEXT",
                "engine_power": "INTEGER",
                "liter_capacity": "INTEGER",
                "salesperson": "TEXT",
                "image_path": "TEXT"
            }
            for name, sql_type in required.items():
                if name not in existing:
                    self.conn.execute(f"ALTER TABLE cars ADD COLUMN {name} {sql_type}")
                    print(f"[DB] MIGRATION: Added column {name} {sql_type}")
            self.conn.commit()
        except Error as e:
            print(f"[DB] Migration error: {e}")

    def _create_indexes(self):
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cars_make ON cars(make);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cars_year ON cars(year);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cars_price ON cars(price);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cars_condition ON cars(condition);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cars_drive ON cars(drive_trains);")
            self.conn.commit()
        except Error as e:
            print(f"[DB] Index error: {e}")

    def _debug_schema(self):
        try:
            cur = self.conn.execute("PRAGMA table_info(cars)")
            cols = [row[1] for row in cur.fetchall()]
            print(f"[DB] cars columns: {cols}")
        except Exception as e:
            print(f"[DB] Debug schema error: {e}")

    def execute_query(self, query, params=None):
        try:
            cursor = self.conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except Error as e:
            print(f"[DB] Query error: {e}\nSQL: {query}\nParams: {params}")
            return None

    # ——— إدراج ———
    def add_car(self, car_data: dict):
        """
        يدعم dict بالمفاتيح:
        make, model, year, price, color, type, condition, drive_trains,
        engine_power, liter_capacity, salesperson, image_path (اختياري)
        """
        fields = [
            "make", "model", "year", "price", "color",
            "type", "condition", "drive_trains",
            "engine_power", "liter_capacity", "salesperson", "image_path"
        ]
        values = [
            car_data.get("make", "").strip(),
            car_data.get("model", "").strip(),
            car_data.get("year", None),
            car_data.get("price", None),
            car_data.get("color", "").strip(),
            car_data.get("type", "").strip(),
            car_data.get("condition", "").strip(),
            car_data.get("drive_trains", "").strip(),
            car_data.get("engine_power", None),
            car_data.get("liter_capacity", None),
            car_data.get("salesperson", "").strip(),
            car_data.get("image_path", "")
        ]
        q = f"INSERT INTO cars ({', '.join(fields)}) VALUES ({', '.join(['?']*len(fields))})"
        cur = self.execute_query(q, values)
        return cur.lastrowid if cur else None

    # متوافقة مع كود PySide6 اللي بيستخدم tuple بالترتيب الكامل
    def insert_car(self, car_tuple):
        """
        car_tuple: (make, model, year, price, color, type, condition, drive_trains,
                    engine_power, liter_capacity, salesperson, image_path)
        """
        q = """
        INSERT INTO cars
        (make, model, year, price, color, type, condition, drive_trains, engine_power, liter_capacity, salesperson, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cur = self.execute_query(q, car_tuple)
        return cur.lastrowid if cur else None

    # ——— قراءة ———
    def fetch_all_cars(self):
        cur = self.execute_query("SELECT * FROM cars")
        return cur.fetchall() if cur else []

    def fetch_cars_by_make(self, make):
        cur = self.execute_query("SELECT * FROM cars WHERE make=?", (make,))
        return cur.fetchall() if cur else []

    def fetch_car_by_id(self, car_id):
        cur = self.execute_query("SELECT * FROM cars WHERE id=?", (car_id,))
        return cur.fetchone() if cur else None

    # ——— تحديث ———
    def update_car(self, car_id, updates: dict):
        if not updates:
            return None
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        params = list(updates.values()) + [car_id]
        q = f"UPDATE cars SET {set_clause} WHERE id=?"
        return self.execute_query(q, params)

    # ——— حذف ———
    def delete_car(self, car_id):
        return self.execute_query("DELETE FROM cars WHERE id=?", (car_id,))

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass