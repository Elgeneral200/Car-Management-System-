import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog, simpledialog, Menu, StringVar, Toplevel
from tkinter import ttk as tkttk
from tkinter.ttk import Combobox
from PIL import Image, ImageTk
import sqlite3
import json
import os
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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
            salesperson TEXT,
            image_path TEXT
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def insert_car(self, car_data):
        query = """
        INSERT INTO cars 
        (make, model, year, price, color, type, condition, drive_trains, engine_power, liter_capacity, salesperson, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, car_data)
        self.conn.commit()

    def fetch_all_cars(self):
        cursor = self.conn.execute("SELECT * FROM cars")
        return cursor.fetchall()

    def fetch_cars_by_filters(self, make="", year_min=None, year_max=None, price_min=None, price_max=None,
                              condition=None, drive_trains=None):
        query = "SELECT * FROM cars WHERE 1=1 "
        params = []
        if make:
            query += "AND make LIKE ? "
            params.append('%' + make + '%')
        if year_min is not None:
            query += "AND year >= ? "
            params.append(year_min)
        if year_max is not None:
            query += "AND year <= ? "
            params.append(year_max)
        if price_min is not None:
            query += "AND price >= ? "
            params.append(price_min)
        if price_max is not None:
            query += "AND price <= ? "
            params.append(price_max)
        if condition and condition != "Any":
            query += "AND condition = ? "
            params.append(condition)
        if drive_trains and drive_trains != "Any":
            query += "AND drive_trains = ? "
            params.append(drive_trains)
        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def update_car(self, car_id, updates):
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        params = list(updates.values()) + [car_id]
        self.conn.execute(f"UPDATE cars SET {set_clause} WHERE id = ?", params)
        self.conn.commit()

    def delete_car(self, car_id):
        self.conn.execute("DELETE FROM cars WHERE id = ?", (car_id,))
        self.conn.commit()


class SplashScreen(ttk.Toplevel):
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
            pass

        ttk.Label(
            main_frame,
            text="Welcome to our system",
            font=("Segoe UI", 24, "bold"),
            foreground="#ffffff",
            style='primary.Inverse.TLabel'
        ).pack(pady=10)

        ttk.Label(
            main_frame,
            text="Car Sales Management System",
            font=("Segoe UI", 12),
            foreground="#cccccc",
            style='primary.TLabel'
        ).pack(pady=5)

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
        self.progress['value'] = value
        if value < 100:
            self.after(30, lambda: self.update_progress(value + 2))


class LoginDialog(simpledialog.Dialog):
    def __init__(self, parent, translator):
        self.translator = translator
        self.username = None
        self.role = None
        super().__init__(parent, title=self.translator.t("login_title"))

    def body(self, master):
        ttk.Label(master, text=self.translator.t("username")).grid(row=0, column=0, pady=5, padx=5)
        self.entry_username = ttk.Entry(master)
        self.entry_username.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(master, text=self.translator.t("password")).grid(row=1, column=0, pady=5, padx=5)
        self.entry_password = ttk.Entry(master, show="*")
        self.entry_password.grid(row=1, column=1, pady=5, padx=5)

        return self.entry_username

    def validate(self):
        username = self.entry_username.get()
        password = self.entry_password.get()

        valid_users = {
            "admin": {"password": "admin123", "role": "admin"},
            "sales": {"password": "sales123", "role": "salesperson"},
        }

        user = valid_users.get(username)
        if user and user["password"] == password:
            self.username = username
            self.role = user["role"]
            return True
        else:
            messagebox.showerror(self.translator.t("login_title"), self.translator.t("login_failed"))
            return False

    def apply(self):
        pass


class EditCarWindow(ttk.Toplevel):
    def __init__(self, parent, translator, db, car_data, refresh_callback):
        super().__init__(parent)
        self.translator = translator
        self.db = db
        self.car_data = car_data
        self.refresh_callback = refresh_callback

        self.title(f"{self.translator.t('edit')} - {car_data[1]} {car_data[2]}")
        self.geometry("520x640")
        self.resizable(False, False)

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
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
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10, padx=10)

        for i, field in enumerate(fields):
            key, label, widget_type = field[0], field[1], field[2]
            ttk.Label(form_frame, text=label + ":").grid(row=i, column=0, sticky="e", pady=5, padx=5)

            if widget_type == "entry":
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=i, column=1, pady=5, padx=5)
                entry.insert(0, str(self.car_data[i + 1]))
                self.entries[key] = entry
            else:
                combo = Combobox(form_frame, values=field[3], state="readonly", width=28)
                current_value = self.car_data[i + 1]
                if current_value in field[3]:
                    combo.current(field[3].index(current_value))
                else:
                    combo.current(0)
                combo.grid(row=i, column=1, pady=5, padx=5)
                self.entries[key] = combo

        img_frame = ttk.Frame(self)
        img_frame.pack(pady=10, padx=10)

        ttk.Label(img_frame, text=self.translator.t("upload_image")).pack(side="left", padx=5)
        self.img_path_var = ttk.StringVar(value=self.car_data[12])
        img_entry = ttk.Entry(img_frame, textvariable=self.img_path_var, width=40, state="readonly")
        img_entry.pack(side="left", padx=5)
        btn_browse_img = ttk.Button(img_frame, text=self.translator.t("browse"), command=self.browse_image)
        btn_browse_img.pack(side="left", padx=5)

        submit_btn = ttk.Button(self, text=self.translator.t("save"), bootstyle="success", command=self.save_changes)
        submit_btn.pack(pady=15)

    def browse_image(self):
        file_path = filedialog.askopenfilename(
            title=self.translator.t("select_image"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if file_path:
            self.img_path_var.set(file_path)

    def save_changes(self):
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
            image_path = self.img_path_var.get()

            if not (1886 <= year <= 2050):
                raise ValueError(self.translator.t("invalid_year_range"))
            if price <= 0 or engine_power <= 0 or liter_capacity <= 0:
                raise ValueError(self.translator.t("invalid_positive_value"))
            if not (make and model and color and salesperson):
                raise ValueError(self.translator.t("all_fields_required"))
        except ValueError as e:
            messagebox.showerror(self.translator.t("error"), str(e))
            return
        except Exception:
            messagebox.showerror(self.translator.t("error"), self.translator.t("invalid_input"))
            return

        stored_img_path = self.car_data[12]
        new_image_selected = image_path != stored_img_path and image_path != ""

        if new_image_selected and os.path.exists(image_path):
            try:
                img_dir = "car_images"
                os.makedirs(img_dir, exist_ok=True)
                ext = os.path.splitext(image_path)[1]
                unique_name = f"{make}_{model}_{year}_{int(pd.Timestamp.now().timestamp())}{ext}"
                stored_img_path = os.path.join(img_dir, unique_name)
                with open(image_path, "rb") as src_f, open(stored_img_path, "wb") as dst_f:
                    dst_f.write(src_f.read())
                if self.car_data[12] and os.path.exists(self.car_data[12]):
                    os.remove(self.car_data[12])
            except Exception as e:
                messagebox.showwarning(self.translator.t("warning"), f"{self.translator.t('image_save_fail')}: {e}")

        updates = {
            "make": make,
            "model": model,
            "year": year,
            "price": price,
            "color": color,
            "type": car_type,
            "condition": condition,
            "drive_trains": drive_trains,
            "engine_power": engine_power,
            "liter_capacity": liter_capacity,
            "salesperson": salesperson,
            "image_path": stored_img_path
        }

        try:
            self.db.update_car(self.car_data[0], updates)
            messagebox.showinfo(self.translator.t("success"), self.translator.t("car_updated"))
            self.refresh_callback()
            self.destroy()
        except Exception as e:
            messagebox.showerror(self.translator.t("error"), f"{self.translator.t('error')}: {e}")

    def on_close(self):
        self.destroy()


class CarSalesApp(ttk.Window):
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

        self.img_cache = {}  # for dashboard image previews

        self.current_user = None
        self.current_role = None  # 'admin' or 'salesperson'

        self.create_widgets()

        self.withdraw()
        splash = SplashScreen(self, self.translator)
        self.after(3100, self.show_login)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def show_login(self):
        self.deiconify()
        login_dialog = LoginDialog(self, self.translator)
        if login_dialog.username:
            self.current_user = login_dialog.username
            self.current_role = login_dialog.role
            self.update_title_user()
            self.show_dashboard()
        else:
            self.destroy()

    def update_title_user(self):
        self.title(f"Car Sales Management System - {self.current_user} ({self.current_role})")

    def create_widgets(self):
        self.sidebar = ttk.Frame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

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
        self.btn_analytics = ttk.Button(
            self.sidebar, text=self.translator.t("analytics") if self.lang == "en" else "التحليلات",
            bootstyle="secondary", command=self.show_analytics)
        self.btn_edit_car = ttk.Button(
            self.sidebar, text="Edit Selected Car" if self.lang == "en" else "تعديل السيارة المختارة",
            bootstyle="secondary", command=self.edit_selected_car)
        self.btn_delete_car = ttk.Button(
            self.sidebar, text="Delete Selected Car" if self.lang == "en" else "حذف السيارة المختارة",
            bootstyle="danger", command=self.delete_selected_car)
        self.btn_toggle_theme = ttk.Button(
            self.sidebar, text=self.translator.t("toggle_theme"),
            bootstyle="secondary", command=self.toggle_theme)
        self.btn_toggle_lang = ttk.Button(
            self.sidebar, text=self.translator.t("toggle_language"),
            bootstyle="secondary", command=self.toggle_language)
        self.btn_exit = ttk.Button(
            self.sidebar, text=self.translator.t("exit"),
            bootstyle="danger", command=self.on_exit)

        for btn in [
            self.btn_dashboard, self.btn_add_car, self.btn_search, self.btn_export,
            self.btn_analytics, self.btn_edit_car, self.btn_delete_car,
            self.btn_toggle_theme, self.btn_toggle_lang, self.btn_exit
        ]:
            btn.pack(fill="x", pady=6, padx=10)

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # Dashboard with double-click edit
    def show_dashboard(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("dashboard"),
                  font=("Segoe UI", 20, "bold")).pack(pady=10)

        cars = self.db.fetch_all_cars()
        if not cars:
            ttk.Label(self.main_frame, text=self.translator.t("no_cars")).pack(pady=20)
            return

        tree = ttk.Treeview(self.main_frame, columns=self.TREEVIEW_HEADERS, show="headings", height=20)
        tree.pack(fill="both", expand=True)

        for h in self.TREEVIEW_HEADERS:
            tree.heading(h, text=h, command=lambda c=h: self.treeview_sort_column(tree, c, False))
            tree.column(h, anchor="center", width=80)

        for car in cars:
            tree.insert("", "end", values=car)

        self.dashboard_tree = tree
        self.dashboard_cars = cars

        self.image_label = ttk.Label(self.main_frame)
        self.image_label.pack(pady=10)

        tree.bind("<<TreeviewSelect>>", self.on_dashboard_select)
        tree.bind("<Double-1>", lambda e: self.edit_selected_car())

    def on_dashboard_select(self, event):
        selected = self.dashboard_tree.selection()
        if not selected:
            self.image_label.configure(image='')
            return

        idx = self.dashboard_tree.index(selected[0])
        car = self.dashboard_cars[idx]
        img_path = car[-1]

        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((250, 250))
                photo = ImageTk.PhotoImage(img)
                self.img_cache["dashboard"] = photo
                self.image_label.configure(image=photo)
            except Exception:
                self.image_label.configure(image='')
        else:
            self.image_label.configure(image='')

    def edit_selected_car(self):
        selected = getattr(self, 'dashboard_tree', None)
        if not selected:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        sel = selected.selection()
        if not sel:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("select_car_edit"))
            return

        idx = selected.index(sel[0])
        car = self.dashboard_cars[idx]

        EditCarWindow(self, self.translator, self.db, car, self.show_dashboard)

    def delete_selected_car(self):
        if self.current_role != 'admin':
            messagebox.showwarning(self.translator.t("warning"), "You do not have permission to delete cars.")
            return

        selected = getattr(self, 'dashboard_tree', None)
        if not selected:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("select_car_delete"))
            return
        sel = selected.selection()
        if not sel:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("select_car_delete"))
            return

        if not messagebox.askyesno(self.translator.t("confirm_delete"), self.translator.t("confirm_delete")):
            return

        idx = selected.index(sel[0])
        car = self.dashboard_cars[idx]
        car_id = car[0]

        img_path = car[-1]
        try:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass

        self.db.delete_car(car_id)
        messagebox.showinfo(self.translator.t("success"), "Car deleted successfully.")
        self.show_dashboard()

    def treeview_sort_column(self, tv, col, reverse):
        try:
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            try:
                l.sort(key=lambda t: float(t[0]), reverse=reverse)
            except ValueError:
                l.sort(key=lambda t: t[0], reverse=reverse)
            for index, (_, k) in enumerate(l):
                tv.move(k, '', index)
            tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))
        except Exception as e:
            print(f"Error sorting Treeview column: {e}")

    # Add Car form with optional image upload (same as before, omitted here for brevity)
    # ... Use the add_car related methods from your previous code (you can copy from the last snippet) ...

    def show_add_car(self):
        # Exact same as your current "show_add_car" and "add_car_to_db" methods
        # including image upload option - please reuse from your code
        # to keep this answer tidy
        pass

    def add_car_to_db(self):
        pass

    # Enhanced multi-criteria search with condition, drivetrain filters
    def show_search(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("search"),
                  font=("Segoe UI", 20, "bold")).pack(pady=10)

        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(pady=10)

        ttk.Label(search_frame, text=self.translator.t("search_make")).grid(row=0, column=0, sticky="e", padx=5)
        self.search_make_entry = ttk.Entry(search_frame, width=20)
        self.search_make_entry.grid(row=0, column=1, padx=5)

        ttk.Label(search_frame, text=self.translator.t("year_min")).grid(row=1, column=0, sticky="e", padx=5)
        self.year_min_entry = ttk.Entry(search_frame, width=10)
        self.year_min_entry.grid(row=1, column=1, sticky='w', padx=5)

        ttk.Label(search_frame, text=self.translator.t("year_max")).grid(row=1, column=2, sticky="e", padx=5)
        self.year_max_entry = ttk.Entry(search_frame, width=10)
        self.year_max_entry.grid(row=1, column=3, sticky='w', padx=5)

        ttk.Label(search_frame, text=self.translator.t("price_min")).grid(row=2, column=0, sticky="e", padx=5)
        self.price_min_entry = ttk.Entry(search_frame, width=10)
        self.price_min_entry.grid(row=2, column=1, sticky='w', padx=5)

        ttk.Label(search_frame, text=self.translator.t("price_max")).grid(row=2, column=2, sticky="e", padx=5)
        self.price_max_entry = ttk.Entry(search_frame, width=10)
        self.price_max_entry.grid(row=2, column=3, sticky='w', padx=5)

        # New condition filter combobox
        ttk.Label(search_frame, text=self.translator.t("condition")).grid(row=3, column=0, sticky="e", padx=5)
        self.condition_cb = Combobox(search_frame, values=["Any", "New", "Used", "Certified"], state="readonly", width=18)
        self.condition_cb.current(0)
        self.condition_cb.grid(row=3, column=1, sticky='w', padx=5)

        # New drive trains filter combobox
        ttk.Label(search_frame, text=self.translator.t("drive_trains")).grid(row=3, column=2, sticky="e", padx=5)
        self.drive_trains_cb = Combobox(search_frame, values=["Any", "FWD", "RWD", "AWD", "4WD"], state="readonly", width=18)
        self.drive_trains_cb.current(0)
        self.drive_trains_cb.grid(row=3, column=3, sticky='w', padx=5)

        search_btn = ttk.Button(search_frame, text=self.translator.t("search_btn"), bootstyle="primary", command=self.perform_search)
        search_btn.grid(row=4, column=0, columnspan=4, pady=10)

        self.search_results_frame = ttk.Frame(self.main_frame)
        self.search_results_frame.pack(fill="both", expand=True, pady=10)

    def perform_search(self):
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        make = self.search_make_entry.get().strip()
        try:
            year_min = int(self.year_min_entry.get()) if self.year_min_entry.get().strip() else None
            year_max = int(self.year_max_entry.get()) if self.year_max_entry.get().strip() else None
            price_min = float(self.price_min_entry.get()) if self.price_min_entry.get().strip() else None
            price_max = float(self.price_max_entry.get()) if self.price_max_entry.get().strip() else None
        except ValueError:
            messagebox.showerror(self.translator.t("error"), self.translator.t("invalid_input"))
            return

        condition = self.condition_cb.get()
        drive_trains = self.drive_trains_cb.get()

        cars = self.db.fetch_cars_by_filters(
            make=make, year_min=year_min, year_max=year_max,
            price_min=price_min, price_max=price_max,
            condition=condition, drive_trains=drive_trains
        )

        if not cars:
            ttk.Label(self.search_results_frame, text=self.translator.t("no_cars_found")).pack()
            return

        tree = ttk.Treeview(self.search_results_frame, columns=self.TREEVIEW_HEADERS, show="headings", height=15)
        tree.pack(fill="both", expand=True)

        for h in self.TREEVIEW_HEADERS:
            tree.heading(h, text=h, command=lambda c=h: self.treeview_sort_column(tree, c, False))
            tree.column(h, anchor="center", width=80)

        for car in cars:
            tree.insert("", "end", values=car)

    # Analytics dashboard
    def show_analytics(self):
        self.clear_main()
        ttk.Label(self.main_frame, text=self.translator.t("analytics") if self.lang=="en" else "التحليلات",
                  font=("Segoe UI", 20, "bold")).pack(pady=10)

        cars = self.db.fetch_all_cars()
        if not cars:
            ttk.Label(self.main_frame, text=self.translator.t("no_cars")).pack(pady=20)
            return

        total_cars = len(cars)
        avg_price = sum(car[4] for car in cars) / total_cars if total_cars > 0 else 0

        ttk.Label(self.main_frame, text=f"{self.translator.t('total_cars') if self.lang=='en' else 'إجمالي السيارات'}: {total_cars}").pack(pady=5)
        ttk.Label(self.main_frame, text=f"{self.translator.t('average_price') if self.lang=='en' else 'متوسط السعر'}: ${avg_price:,.2f}").pack(pady=5)

        makes = [car[1] for car in cars]
        make_counts = Counter(makes)

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(make_counts.keys(), make_counts.values(), color='skyblue')
        ax.set_title(self.translator.t("cars_by_make") if self.lang == "en" else "السيارات حسب الماركة")
        ax.set_xlabel(self.translator.t("make") if self.lang=="en" else "الماركة")
        ax.set_ylabel(self.translator.t("count") if self.lang=="en" else "العدد")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.main_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)

    # Export to excel
    def export_to_excel(self):
        cars = self.db.fetch_all_cars()
        if not cars:
            messagebox.showwarning(self.translator.t("warning"), self.translator.t("no_data_export"))
            return

        cols = self.TREEVIEW_HEADERS + ["Image Path"]
        df = pd.DataFrame(cars, columns=cols)

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

    # Theme toggle
    def toggle_theme(self):
        current = self.app_style.theme_use()
        self.app_style.theme_use("flatly" if current == "darkly" else "darkly")

    # Language toggle
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
        self.btn_analytics.config(text=self.translator.t("analytics") if self.lang == "en" else "التحليلات")
        self.btn_edit_car.config(text="Edit Selected Car" if self.lang == "en" else "تعديل السيارة المختارة")
        self.btn_delete_car.config(text="Delete Selected Car" if self.lang == "en" else "حذف السيارة المختارة")

        self.show_dashboard()

    def on_exit(self):
        if messagebox.askokcancel(self.translator.t("exit"), self.translator.t("confirm_exit")):
            self.destroy()


if __name__ == "__main__":
    # Create translation JSON files if missing, with extended keys
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
            "save": "Save",
            "edit": "Edit",
            "delete": "Delete",
            "error": "Error",
            "invalid_input": "Invalid input. Please check your data.",
            "invalid_year_range": "Year must be between 1886 and 2050.",
            "invalid_positive_value": "Price, Engine Power, and Liter Capacity must be positive numbers.",
            "all_fields_required": "All fields must be filled out.",
            "success": "Success",
            "car_added": "Car added successfully!",
            "car_updated": "Car updated successfully!",
            "car_deleted": "Car deleted successfully.",
            "search_make": "Enter make:",
            "search_btn": "Search",
            "no_cars_found": "No cars found matching the criteria.",
            "warning": "Warning",
            "no_data_export": "No data to export.",
            "export_success": "Export completed successfully!",
            "export_fail": "Export failed",
            "confirm_exit": "Are you sure you want to exit?",
            "welcome_msg": "Welcome to Car Sales System",
            "enter_make": "Please enter a make to search.",
            "upload_image": "Car Image:",
            "browse": "Browse",
            "select_image": "Select Car Image",
            "confirm_delete": "Are you sure you want to delete the selected car?",
            "select_car_edit": "Please select a car to edit.",
            "select_car_delete": "Please select a car to delete.",
            "delete_permission_denied": "You do not have permission to delete cars.",
            "image_save_fail": "Failed to save the image",
            "login_title": "Login",
            "username": "Username",
            "password": "Password",
            "login_failed": "Invalid username or password.",
            "analytics": "Analytics",
            "total_cars": "Total Cars",
            "average_price": "Average Price",
            "cars_by_make": "Cars by Make",
            "count": "Count",
            "confirm": "Confirm",
            "year_min": "Year Min",
            "year_max": "Year Max",
            "price_min": "Price Min",
            "price_max": "Price Max",
            "about": "About",
            "help": "Help",
            "drive_trains": "Drive Trains",
        }
        with open("en.json", "w", encoding="utf-8") as f:
            json.dump(en_content, f, indent=4)

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
            "save": "حفظ",
            "edit": "تعديل",
            "delete": "حذف",
            "error": "خطأ",
            "invalid_input": "المدخلات غير صحيحة. تحقق من البيانات.",
            "invalid_year_range": "يجب أن تكون السنة بين 1886 و2050.",
            "invalid_positive_value": "يجب أن تكون السعر، قوة المحرك، والسعة موجبة.",
            "all_fields_required": "يجب ملء جميع الحقول.",
            "success": "نجاح",
            "car_added": "تمت إضافة السيارة بنجاح!",
            "car_updated": "تم تحديث بيانات السيارة بنجاح!",
            "car_deleted": "تم حذف السيارة.",
            "search_make": "أدخل الماركة:",
            "search_btn": "بحث",
            "no_cars_found": "لم يتم العثور على سيارات تطابق المعايير.",
            "warning": "تحذير",
            "no_data_export": "لا توجد بيانات للتصدير.",
            "export_success": "تم التصدير بنجاح!",
            "export_fail": "فشل التصدير",
            "confirm_exit": "هل تريد الخروج؟",
            "welcome_msg": "مرحبًا بك في نظام بيع السيارات",
            "enter_make": "يرجى إدخال ماركة للبحث.",
            "upload_image": "صورة السيارة:",
            "browse": "تصفح",
            "select_image": "اختر صورة السيارة",
            "confirm_delete": "هل أنت متأكد من حذف السيارة المحددة؟",
            "select_car_edit": "يرجى اختيار سيارة للتعديل.",
            "select_car_delete": "يرجى اختيار سيارة للحذف.",
            "delete_permission_denied": "ليس لديك صلاحية حذف السيارات.",
            "image_save_fail": "فشل حفظ الصورة",
            "login_title": "تسجيل الدخول",
            "username": "اسم المستخدم",
            "password": "كلمة المرور",
            "login_failed": "اسم المستخدم أو كلمة المرور غير صحيحة.",
            "analytics": "التحليلات",
            "total_cars": "إجمالي السيارات",
            "average_price": "متوسط السعر",
            "cars_by_make": "السيارات حسب الماركة",
            "count": "العدد",
            "confirm": "تأكيد",
            "year_min": "أدنى سنة",
            "year_max": "أعلى سنة",
            "price_min": "أدنى سعر",
            "price_max": "أعلى سعر",
            "about": "حول",
            "help": "مساعدة",
            "drive_trains": "نظام الدفع",
        }
        with open("ar.json", "w", encoding="utf-8") as f:
            json.dump(ar_content, f, indent=4)

    app = CarSalesApp()
    app.mainloop()
