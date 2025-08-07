import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
from tkinter import ttk as tkttk
from PIL import Image, ImageTk
import sqlite3
import json
import os
import pandas as pd
import threading
import time
import sys

# ==== Translator class ====

class Translator:
    def __init__(self, lang="en"):
        self.lang = lang
        self.translations = self.load_translations()

    def load_translations(self):
        filename = f"{self.lang}.json"
        if not os.path.exists(filename):
            filename = "en.json"
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def t(self, key):
        return self.translations.get(key, key)

# ==== Database Handler ====

class Database:
    def __init__(self, db_file="car_sales.db"):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT,
            model TEXT,
            year INTEGER,
            price REAL,
            color TEXT,
            type TEXT,
            condition TEXT,
            drive_trains TEXT,
            engine_power INTEGER,
            liter_capacity INTEGER,
            salesperson TEXT
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def insert_car(self, car_data):
        query = """
        INSERT INTO cars 
        (make, model, year, price, color, type, condition, drive_trains, engine_power, liter_capacity, salesperson)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, car_data)
        self.conn.commit()

    def fetch_all_cars(self):
        cursor = self.conn.execute("SELECT * FROM cars")
        return cursor.fetchall()

    def fetch_cars_by_make(self, make):
        cursor = self.conn.execute("SELECT * FROM cars WHERE make LIKE ?", ('%'+make+'%',))
        return cursor.fetchall()

    def update_car(self, car_id, updates):
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        params = list(updates.values())
        params.append(car_id)
        query = f"UPDATE cars SET {set_clause} WHERE id = ?"
        self.conn.execute(query, params)
        self.conn.commit()

# ==== Splash Screen ====

class SplashScreen(ttk.Toplevel):
    def __init__(self, parent, translator):
        super().__init__(parent)
        self.translator = translator
        self.geometry("400x250+600+300")
        self.overrideredirect(True)  # No title bar
        self.config(bg="#2c3e50")

        label = ttk.Label(self, text=self.translator.t("welcome_msg"), font=("Segoe UI", 20), foreground="white", background="#2c3e50")
        label.pack(expand=True)

        # Auto close splash after 3 seconds
        self.after(3000, self.destroy)

# ==== Main Application ====

class CarSalesApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Car Sales Management System")
        self.geometry("1100x700")
        self.minsize(900,600)

        self.lang = "en"
        self.translator = Translator(self.lang)

        self.db = Database()

        self.app_style = ttk.Style()

        self.create_widgets()

        # Show splash screen before main window
        self.withdraw()
        splash = SplashScreen(self, self.translator)
        self.after(3100, self.deiconify)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def create_widgets(self):
        # Create sidebar frame
        self.sidebar = ttk.Frame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        # Buttons on sidebar
        self.btn_dashboard = ttk.Button(self.sidebar, text=self.translator.t("dashboard"), bootstyle="info", command=self.show_dashboard)
        self.btn_add_car = ttk.Button(self.sidebar, text=self.translator.t("add_car"), bootstyle="success", command=self.show_add_car)
        self.btn_search = ttk.Button(self.sidebar, text=self.translator.t("search"), bootstyle="primary", command=self.show_search)
        self.btn_export = ttk.Button(self.sidebar, text=self.translator.t("export"), bootstyle="warning", command=self.export_to_excel)
        self.btn_toggle_theme = ttk.Button(self.sidebar, text=self.translator.t("toggle_theme"), bootstyle="secondary", command=self.toggle_theme)
        self.btn_toggle_lang = ttk.Button(self.sidebar, text=self.translator.t("toggle_language"), bootstyle="secondary", command=self.toggle_language)
        self.btn_exit = ttk.Button(self.sidebar, text=self.translator.t("exit"), bootstyle="danger", command=self.on_exit)

        for btn in [self.btn_dashboard, self.btn_add_car, self.btn_search, self.btn_export, self.btn_toggle_theme, self.btn_toggle_lang, self.btn_exit]:
            btn.pack(fill="x", pady=8, padx=10)

        # Main content frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Start at dashboard
        self.show_dashboard()

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ==== Dashboard ====
    def show_dashboard(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("dashboard"), font=("Segoe UI", 20, "bold")).pack(pady=10)
        cars = self.db.fetch_all_cars()
        if not cars:
            ttk.Label(self.main_frame, text=self.translator.t("no_cars")).pack(pady=20)
            return

        headers = ["ID", "Make", "Model", "Year", "Price", "Color", "Type", "Condition", "Drive Trains", "Engine Power", "Liter Capacity", "Salesperson"]
        tree = ttk.Treeview(self.main_frame, columns=headers, show="headings", height=20)
        tree.pack(fill="both", expand=True)

        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, anchor="center", width=80)

        for car in cars:
            tree.insert("", "end", values=car)

    # ==== Add Car ====
    def show_add_car(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("add_car"), font=("Segoe UI", 20, "bold")).pack(pady=10)

        fields = [
            ("make", self.translator.t("make")),
            ("model", self.translator.t("model")),
            ("year", self.translator.t("year")),
            ("price", self.translator.t("price")),
            ("color", self.translator.t("color")),
            ("type", self.translator.t("type")),
            ("condition", self.translator.t("condition")),
            ("drive_trains", self.translator.t("drive_trains")),
            ("engine_power", self.translator.t("engine_power")),
            ("liter_capacity", self.translator.t("liter_capacity")),
            ("salesperson", self.translator.t("salesperson")),
        ]

        self.entries = {}
        form_frame = ttk.Frame(self.main_frame)
        form_frame.pack(pady=10)

        for i, (field, label) in enumerate(fields):
            ttk.Label(form_frame, text=label + ":").grid(row=i, column=0, sticky="e", pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=30)
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.entries[field] = entry

        submit_btn = ttk.Button(self.main_frame, text=self.translator.t("submit"), bootstyle="success", command=self.add_car_to_db)
        submit_btn.pack(pady=20)

    def add_car_to_db(self):
        try:
            car_data = (
                self.entries["make"].get(),
                self.entries["model"].get(),
                int(self.entries["year"].get()),
                float(self.entries["price"].get()),
                self.entries["color"].get(),
                self.entries["type"].get(),
                self.entries["condition"].get(),
                self.entries["drive_trains"].get(),
                int(self.entries["engine_power"].get()),
                int(self.entries["liter_capacity"].get()),
                self.entries["salesperson"].get()
            )
        except ValueError:
            messagebox.showerror(self.translator.t("error"), self.translator.t("invalid_input"))
            return

        self.db.insert_car(car_data)
        messagebox.showinfo(self.translator.t("success"), self.translator.t("car_added"))
        self.show_dashboard()

    # ==== Search ====
    def show_search(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("search"), font=("Segoe UI", 20, "bold")).pack(pady=10)

        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(pady=10)

        ttk.Label(search_frame, text=self.translator.t("search_make")).grid(row=0, column=0, sticky="e", padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)

        search_btn = ttk.Button(search_frame, text=self.translator.t("search_btn"), bootstyle="primary", command=self.perform_search)
        search_btn.grid(row=0, column=2, padx=5)

        self.search_results_frame = ttk.Frame(self.main_frame)
        self.search_results_frame.pack(fill="both", expand=True, pady=10)

    def perform_search(self):
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        make = self.search_entry.get()
        if not make.strip():
            messagebox.showerror(self.translator.t("error"), self.translator.t("enter_make"))
            return

        cars = self.db.fetch_cars_by_make(make)
        if not cars:
            ttk.Label(self.search_results_frame, text=self.translator.t("no_cars_found")).pack()
            return

        headers = ["ID", "Make", "Model", "Year", "Price", "Color", "Type", "Condition", "Drive Trains", "Engine Power", "Liter Capacity", "Salesperson"]
        tree = ttk.Treeview(self.search_results_frame, columns=headers, show="headings", height=10)
        tree.pack(fill="both", expand=True)

        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, anchor="center", width=80)

        for car in cars:
            tree.insert("", "end", values=car)

    # ==== Export to Excel ====
    def export_to_excel(self):
        cars = self.db.fetch_all_cars()
        if not cars:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("no_data_export"))
            return

        df = pd.DataFrame(cars, columns=["ID","Make","Model","Year","Price","Color","Type","Condition","Drive Trains","Engine Power","Liter Capacity","Salesperson"])
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                 filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            df.to_excel(file_path, index=False)
            messagebox.showinfo(self.translator.t("success"), self.translator.t("export_success"))
        except Exception as e:
            messagebox.showerror(self.translator.t("error"), f"{self.translator.t('export_fail')}: {str(e)}")

    # ==== Theme and Language toggle ====
    def toggle_theme(self):
        current = self.app_style.theme_use()
        if current == "darkly":
            self.app_style.theme_use("flatly")
        else:
            self.app_style.theme_use("darkly")

    def toggle_language(self):
        self.lang = "ar" if self.lang == "en" else "en"
        self.translator = Translator(self.lang)
        self.btn_dashboard.config(text=self.translator.t("dashboard"))
        self.btn_add_car.config(text=self.translator.t("add_car"))
        self.btn_search.config(text=self.translator.t("search"))
        self.btn_export.config(text=self.translator.t("export"))
        self.btn_exit.config(text=self.translator.t("exit"))
        self.btn_toggle_theme.config(text=self.translator.t("toggle_theme"))
        self.btn_toggle_lang.config(text=self.translator.t("toggle_language"))
        self.show_dashboard()

    # ==== Exit handling ====
    def on_exit(self):
        if messagebox.askokcancel(self.translator.t("exit"), self.translator.t("confirm_exit")):
            self.destroy()

if __name__ == "__main__":
    # Check or create translation files
    for lang_file in ["en.json", "ar.json"]:
        if not os.path.exists(lang_file):
            en_content = {
                "dashboard": "Dashboard",
                "add_car": "Add New Car",
                "search": "Search Cars",
                "export": "Export to Excel",
                "exit": "Exit",
                "toggle_theme": "Toggle Light/Dark Mode",
                "toggle_language": "Toggle Language",
                "no_cars": "No cars in inventory.",
                "make": "Make",
                "model": "Model",
                "year": "Year",
                "price": "Price",
                "color": "Color",
                "type": "Type",
                "condition": "Condition",
                "drive_trains": "Drive Trains",
                "engine_power": "Engine Power (CC)",
                "liter_capacity": "Liter Capacity (L)",
                "salesperson": "Salesperson",
                "submit": "Submit",
                "error": "Error",
                "invalid_input": "Invalid input. Please check your data.",
                "success": "Success",
                "car_added": "Car added successfully!",
                "search_make": "Enter make to search:",
                "search_btn": "Search",
                "no_cars_found": "No cars found for this make.",
                "warning": "Warning",
                "no_data_export": "No data to export.",
                "export_success": "Export completed successfully!",
                "export_fail": "Export failed",
                "confirm_exit": "Are you sure you want to exit?",
                "welcome_msg": "Welcome to Car Sales System",
                "enter_make": "Please enter a make to search."
            }
            ar_content = {
                "dashboard": "الرئيسية",
                "add_car": "إضافة سيارة جديدة",
                "search": "البحث عن سيارات",
                "export": "تصدير إلى إكسل",
                "exit": "خروج",
                "toggle_theme": "تبديل الوضع الليلي/الفاتح",
                "toggle_language": "تبديل اللغة",
                "no_cars": "لا توجد سيارات في المخزون.",
                "make": "الماركة",
                "model": "الموديل",
                "year": "السنة",
                "price": "السعر",
                "color": "اللون",
                "type": "النوع",
                "condition": "الحالة",
                "drive_trains": "نظام الدفع",
                "engine_power": "قوة المحرك (سي سي)",
                "liter_capacity": "سعة الوقود (لتر)",
                "salesperson": "البائع",
                "submit": "حفظ",
                "error": "خطأ",
                "invalid_input": "المدخلات غير صحيحة. تحقق من البيانات.",
                "success": "نجاح",
                "car_added": "تمت إضافة السيارة بنجاح!",
                "search_make": "أدخل الماركة للبحث:",
                "search_btn": "بحث",
                "no_cars_found": "لم يتم العثور على سيارات لهذه الماركة.",
                "warning": "تحذير",
                "no_data_export": "لا توجد بيانات للتصدير.",
                "export_success": "تم التصدير بنجاح!",
                "export_fail": "فشل التصدير",
                "confirm_exit": "هل تريد الخروج؟",
                "welcome_msg": "مرحبًا بك في نظام بيع السيارات",
                "enter_make": "يرجى إدخال ماركة للبحث."
            }
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(en_content if "en" in lang_file else ar_content, f, ensure_ascii=False, indent=4)

    app = CarSalesApp()
    app.mainloop()
