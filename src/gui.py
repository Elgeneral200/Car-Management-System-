import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
from tkinter import ttk as tkttk
from tkinter.ttk import Combobox
from PIL import Image, ImageTk
import sqlite3
import json
import os
import pandas as pd


class Translator:
    """
    Handles loading translation text from JSON files and returning translated strings.
    """
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
        """
        Return translation for the given key, or the key itself if not found.
        """
        return self.translations.get(key, key)


class Database:
    """
    Encapsulates SQLite database operations for the car sales system.
    """
    def __init__(self, db_file="car_sales.db"):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        """
        Create the 'cars' table if it doesn't exist.
        """
        try:
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
        except sqlite3.Error as e:
            print(f"DB Error in create_tables: {e}")

    def insert_car(self, car_data):
        """
        Insert a new car record into the database.
        """
        try:
            query = """
            INSERT INTO cars 
            (make, model, year, price, color, type, condition, drive_trains, engine_power, liter_capacity, salesperson)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.conn.execute(query, car_data)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"DB Error in insert_car: {e}")
            raise

    def fetch_all_cars(self):
        """
        Fetch all car records.
        """
        try:
            cursor = self.conn.execute("SELECT * FROM cars")
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB Error in fetch_all_cars: {e}")
            return []

    def fetch_cars_by_make(self, make):
        """
        Fetch cars filtered by 'make'.
        """
        try:
            cursor = self.conn.execute("SELECT * FROM cars WHERE make LIKE ?", ('%' + make + '%',))
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"DB Error in fetch_cars_by_make: {e}")
            return []

    def update_car(self, car_id, updates):
        """
        Update car row by id with fields in updates dictionary.
        """
        try:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            params = list(updates.values()) + [car_id]
            query = f"UPDATE cars SET {set_clause} WHERE id = ?"
            self.conn.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"DB Error in update_car: {e}")


class SplashScreen(ttk.Toplevel):
    """
    Displays a splash screen at application startup.
    """
    def __init__(self, parent, translator):
        super().__init__(parent)
        self.translator = translator
        self.geometry("500x350+550+250")
        self.overrideredirect(True)

        main_frame = ttk.Frame(self, style='primary.TFrame')
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)

        try:
            logo_img = Image.open("logo.png").resize((150, 150))
            self.logo = ImageTk.PhotoImage(logo_img)
            logo_label = ttk.Label(main_frame, image=self.logo)
            logo_label.pack(pady=(25, 15))
        except Exception:
            # If logo loading fails, silently pass
            pass

        label = ttk.Label(
            main_frame,
            text="Welcome to our system",
            font=("Segoe UI", 24, "bold"),
            foreground="#ffffff",
            style='primary.Inverse.TLabel'
        )
        label.pack(pady=10)

        sub_label = ttk.Label(
            main_frame,
            text="Car Sales Management System",
            font=("Segoe UI", 12),
            foreground="#cccccc",
            style='primary.TLabel'
        )
        sub_label.pack(pady=5)

        self.progress = ttk.Progressbar(
            main_frame,
            orient='horizontal',
            length=300,
            mode='determinate',
            bootstyle="success-striped"
        )
        self.progress.pack(pady=20)
        self.update_progress()
        self.after(3000, self.destroy)

    def update_progress(self, value=0):
        """
        Increment progress bar until complete.
        """
        self.progress['value'] = value
        if value < 100:
            self.after(30, lambda: self.update_progress(value + 2))


class CarSalesApp(ttk.Window):
    """
    Main application window containing the car sales management GUI.
    """
    # Use class-level constant for Treeview column headers to avoid duplication
    TREEVIEW_HEADERS = [
        "ID", "Make", "Model", "Year", "Price", "Color", "Type", "Condition",
        "Drive Trains", "Engine Power", "Liter Capacity", "Salesperson"
    ]

    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Car Sales Management System")
        self.geometry("1100x700")
        self.minsize(900, 600)

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
        """
        Create sidebar buttons and main content frame.
        """
        self.sidebar = ttk.Frame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        # Sidebar buttons with translated text
        self.btn_dashboard = ttk.Button(
            self.sidebar, text=self.translator.t("dashboard"),
            bootstyle="info", command=self.show_dashboard)
        self.btn_add_car = ttk.Button(
            self.sidebar, text=self.translator.t("add_car"),
            bootstyle="success", command=self.show_add_car)
        self.btn_search = ttk.Button(
            self.sidebar, text=self.translator.t("search"),
            bootstyle="primary", command=self.show_search)
        self.btn_export = ttk.Button(
            self.sidebar, text=self.translator.t("export"),
            bootstyle="warning", command=self.export_to_excel)
        self.btn_toggle_theme = ttk.Button(
            self.sidebar, text=self.translator.t("toggle_theme"),
            bootstyle="secondary", command=self.toggle_theme)
        self.btn_toggle_lang = ttk.Button(
            self.sidebar, text=self.translator.t("toggle_language"),
            bootstyle="secondary", command=self.toggle_language)
        self.btn_exit = ttk.Button(
            self.sidebar, text=self.translator.t("exit"),
            bootstyle="danger", command=self.on_exit)

        for btn in [self.btn_dashboard, self.btn_add_car, self.btn_search, self.btn_export,
                    self.btn_toggle_theme, self.btn_toggle_lang, self.btn_exit]:
            btn.pack(fill="x", pady=8, padx=10)

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.show_dashboard()

    def clear_main(self):
        """
        Clear all widgets inside main_frame.
        """
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ---- Dashboard ----
    def show_dashboard(self):
        """
        Display dashboard with all cars in a sortable Treeview.
        """
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("dashboard"),
                  font=("Segoe UI", 20, "bold")).pack(pady=10)
        cars = self.db.fetch_all_cars()
        if not cars:
            ttk.Label(self.main_frame, text=self.translator.t("no_cars")).pack(pady=20)
            return

        tree = ttk.Treeview(self.main_frame, columns=self.TREEVIEW_HEADERS, show="headings", height=20)
        tree.pack(fill="both", expand=True)

        # Setup columns
        for h in self.TREEVIEW_HEADERS:
            tree.heading(h, text=h, command=lambda c=h: self.treeview_sort_column(tree, c, False))
            tree.column(h, anchor="center", width=80)

        # Insert data
        for car in cars:
            tree.insert("", "end", values=car)

    def treeview_sort_column(self, tv, col, reverse):
        """
        Sort the Treeview column when the header is clicked.
        """
        try:
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            # Attempt numeric sort, else string sort
            try:
                l.sort(key=lambda t: float(t[0]), reverse=reverse)
            except ValueError:
                l.sort(key=lambda t: t[0], reverse=reverse)
            # Rearrange items in sorted positions
            for index, (_, k) in enumerate(l):
                tv.move(k, '', index)
            # Reverse sort next time
            tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))
        except Exception as e:
            print(f"Error sorting Treeview column: {e}")

    # ---- Add Car ----
    def show_add_car(self):
        """
        Show form to add a new car, with improved inputs and validation.
        """
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("add_car"),
                  font=("Segoe UI", 20, "bold")).pack(pady=10)

        # Fields with labels - Some replaced with Combobox for fixed options
        fields = [
            ("make", self.translator.t("make"), "entry"),
            ("model", self.translator.t("model"), "entry"),
            ("year", self.translator.t("year"), "entry"),
            ("price", self.translator.t("price"), "entry"),
            ("color", self.translator.t("color"), "entry"),
            ("type", self.translator.t("type"), "combobox", ["Sedan", "SUV", "Hatchback", "Convertible", "Coupe", "Truck", "Van"]),
            ("condition", self.translator.t("condition"), "combobox", ["New", "Used", "Certified"]),
            ("drive_trains", self.translator.t("drive_trains"), "combobox", ["FWD", "RWD", "AWD", "4WD"]),
            ("engine_power", self.translator.t("engine_power"), "entry"),
            ("liter_capacity", self.translator.t("liter_capacity"), "entry"),
            ("salesperson", self.translator.t("salesperson"), "entry"),
        ]

        self.entries = {}
        form_frame = ttk.Frame(self.main_frame)
        form_frame.pack(pady=10)

        for i, field in enumerate(fields):
            key = field[0]
            label = field[1]
            widget_type = field[2]
            ttk.Label(form_frame, text=label + ":").grid(row=i, column=0, sticky="e", pady=5, padx=5)

            if widget_type == "entry":
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=i, column=1, pady=5, padx=5)
                self.entries[key] = entry
            elif widget_type == "combobox":
                combo = Combobox(form_frame, values=field[3], state="readonly", width=28)
                combo.current(0)
                combo.grid(row=i, column=1, pady=5, padx=5)
                self.entries[key] = combo

        submit_btn = ttk.Button(
            self.main_frame,
            text=self.translator.t("submit"),
            bootstyle="success",
            command=self.add_car_to_db)
        submit_btn.pack(pady=20)

    def add_car_to_db(self):
        """
        Validate inputs and add a new car record to the database.
        """
        try:
            make = self.entries["make"].get().strip()
            model = self.entries["model"].get().strip()
            year = int(self.entries["year"].get())
            price = float(self.entries["price"].get())
            color = self.entries["color"].get().strip()
            car_type = self.entries["type"].get()
            condition = self.entries["condition"].get()
            drive_trains = self.entries["drive_trains"].get()
            engine_power = int(self.entries["engine_power"].get())
            liter_capacity = int(self.entries["liter_capacity"].get())
            salesperson = self.entries["salesperson"].get().strip()

            # Input validation with meaningful ranges
            if not (1886 <= year <= 2050):  # First car invented 1886
                raise ValueError(self.translator.t("invalid_year_range"))
            if price <= 0 or engine_power <= 0 or liter_capacity <= 0:
                raise ValueError(self.translator.t("invalid_positive_value"))
            if not (make and model and color and salesperson):
                raise ValueError(self.translator.t("all_fields_required"))

            car_data = (
                make, model, year, price, color, car_type, condition,
                drive_trains, engine_power, liter_capacity, salesperson
            )
        except ValueError as e:
            # Show specific error message if from ValueError, else generic
            msg = str(e) if str(e) else self.translator.t("invalid_input")
            messagebox.showerror(self.translator.t("error"), msg)
            return
        except Exception:
            messagebox.showerror(self.translator.t("error"), self.translator.t("invalid_input"))
            return

        try:
            self.db.insert_car(car_data)
            messagebox.showinfo(self.translator.t("success"), self.translator.t("car_added"))
            self.show_dashboard()
        except Exception as e:
            messagebox.showerror(self.translator.t("error"), f"{self.translator.t('error')}: {e}")

    # ---- Search ----
    def show_search(self):
        """
        Show a form to search cars by make.
        """
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("search"),
                  font=("Segoe UI", 20, "bold")).pack(pady=10)

        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(pady=10)

        ttk.Label(search_frame, text=self.translator.t("search_make")).grid(row=0, column=0, sticky="e", padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)

        search_btn = ttk.Button(
            search_frame,
            text=self.translator.t("search_btn"),
            bootstyle="primary",
            command=self.perform_search)
        search_btn.grid(row=0, column=2, padx=5)

        self.search_results_frame = ttk.Frame(self.main_frame)
        self.search_results_frame.pack(fill="both", expand=True, pady=10)

    def perform_search(self):
        """
        Perform search in database by make and show results.
        """
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        make = self.search_entry.get().strip()
        if not make:
            messagebox.showerror(self.translator.t("error"), self.translator.t("enter_make"))
            return

        cars = self.db.fetch_cars_by_make(make)
        if not cars:
            ttk.Label(self.search_results_frame, text=self.translator.t("no_cars_found")).pack()
            return

        tree = ttk.Treeview(self.search_results_frame, columns=self.TREEVIEW_HEADERS, show="headings", height=10)
        tree.pack(fill="both", expand=True)

        for h in self.TREEVIEW_HEADERS:
            tree.heading(h, text=h, command=lambda c=h: self.treeview_sort_column(tree, c, False))
            tree.column(h, anchor="center", width=80)

        for car in cars:
            tree.insert("", "end", values=car)

    # ---- Export to Excel ----
    def export_to_excel(self):
        """
        Export all car data to an Excel file.
        """
        cars = self.db.fetch_all_cars()
        if not cars:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("no_data_export"))
            return

        df = pd.DataFrame(cars, columns=self.TREEVIEW_HEADERS)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            df.to_excel(file_path, index=False)
            messagebox.showinfo(self.translator.t("success"), self.translator.t("export_success"))
        except Exception as e:
            messagebox.showerror(self.translator.t("error"), f"{self.translator.t('export_fail')}: {e}")

    # ---- Theme and Language Toggle ----
    def toggle_theme(self):
        """
        Toggle between darkly and flatly themes.
        """
        current = self.app_style.theme_use()
        if current == "darkly":
            self.app_style.theme_use("flatly")
        else:
            self.app_style.theme_use("darkly")

    def toggle_language(self):
        """
        Toggle application language between English and Arabic.
        """
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

    # ---- Exit Handling ----
    def on_exit(self):
        """
        Confirm exit and close application.
        """
        if messagebox.askokcancel(self.translator.t("exit"), self.translator.t("confirm_exit")):
            self.destroy()


if __name__ == "__main__":
    # Create translation JSON files with correct content only if missing
    if not os.path.exists("en.json"):
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
            "invalid_year_range": "Year must be between 1886 and 2050.",
            "invalid_positive_value": "Price, Engine Power, and Liter Capacity must be positive numbers.",
            "all_fields_required": "All fields must be filled out.",
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
        with open("en.json", "w", encoding="utf-8") as f:
            json.dump(en_content, f, ensure_ascii=False, indent=4)

    if not os.path.exists("ar.json"):
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
            "invalid_year_range": "يجب أن تكون السنة بين 1886 و2050.",
            "invalid_positive_value": "يجب أن تكون السعر، قوة المحرك، والسعة موجبة.",
            "all_fields_required": "يجب ملء جميع الحقول.",
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
        with open("ar.json", "w", encoding="utf-8") as f:
            json.dump(ar_content, f, ensure_ascii=False, indent=4)

    app = CarSalesApp()
    app.mainloop()
