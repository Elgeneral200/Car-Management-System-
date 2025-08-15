import os
import sys
import json
import sqlite3
import base64
import zipfile
from collections import Counter
import pandas as pd

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSize,
    QSortFilterProxyModel, QSettings, QTimer, QRect, QPoint,
    QByteArray, QBuffer, QIODevice
)
from PySide6.QtGui import (
    QPixmap, QPalette, QColor, QKeySequence, QShortcut, QPainter, QFont, QAction, QIcon, QCursor, QTextDocument
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
    QLabel, QFileDialog, QMessageBox, QTableView, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QStackedWidget, QMenu, QStyle, QListWidget, QListWidgetItem, QToolButton, QStatusBar
)
from PySide6.QtPrintSupport import QPrinter

# Matplotlib for Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# Optional deps
try:
    from babel.numbers import format_currency as babel_format_currency
except Exception:
    babel_format_currency = None

try:
    import requests
except Exception:
    requests = None


# --------- Constants ---------
ENUM_TYPES = ["Sedan", "SUV", "Hatchback", "Convertible", "Coupe", "Truck", "Van"]
ENUM_CONDITIONS = ["New", "Used", "Certified"]
ENUM_DRIVES = ["FWD", "RWD", "AWD", "4WD"]

DISPLAY_COLS = list(range(12))
HEADER_KEYS = [
    "ID", "make", "model", "year", "price", "color", "type", "condition",
    "drive_trains", "engine_power", "liter_capacity", "salesperson"
]
FIELD_MAP = {
    1: "make",
    2: "model",
    3: "year",
    4: "price",
    5: "color",
    6: "type",
    7: "condition",
    8: "drive_trains",
    9: "engine_power",
    10: "liter_capacity",
    11: "salesperson",
}
NUMERIC_COLS = {0, 3, 4, 9, 10}  # ID, Year, Price, Engine Power, Liter Capacity
INT_FIELDS = {"year", "engine_power", "liter_capacity"}
FLOAT_FIELDS = {"price"}


# --------- Utilities ---------
def format_price(value, lang):
    if isinstance(value, (int, float)):
        if babel_format_currency:
            locale = "ar" if lang == "ar" else "en_US"
            try:
                return babel_format_currency(value, "USD", locale=locale, format=u"¤#,##0")
            except Exception:
                pass
        return f"${value:,.0f}"
    return str(value)


def std_icon(sp):
    try:
        return QApplication.style().standardIcon(sp)
    except Exception:
        return QIcon()


def bytes_from_image_path(path, max_width=400):
    try:
        pm = QPixmap(path)
        if pm.isNull():
            return None
        if pm.width() > max_width:
            pm = pm.scaledToWidth(max_width, Qt.SmoothTransformation)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        pm.save(buf, "PNG")
        buf.close()
        return bytes(ba)
    except Exception:
        return None


# --------- Translator & Database ---------
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
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def reopen(self):
        self.close()
        self.conn = sqlite3.connect(self.db_file)

    def create_tables(self):
        q1 = """
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
        q2 = """
        CREATE TABLE IF NOT EXISTS car_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            path TEXT
        );
        """
        self.conn.execute(q1)
        self.conn.execute(q2)
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

    def fetch_car_by_id(self, car_id):
        cur = self.conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,))
        return cur.fetchone()

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

    # Gallery methods
    def add_image(self, car_id, path):
        self.conn.execute("INSERT INTO car_images (car_id, path) VALUES (?, ?)", (car_id, path))
        self.conn.commit()

    def fetch_images(self, car_id):
        cur = self.conn.execute("SELECT id, path FROM car_images WHERE car_id = ?", (car_id,))
        return cur.fetchall()

    def delete_image(self, img_id):
        self.conn.execute("DELETE FROM car_images WHERE id = ?", (img_id,))
        self.conn.commit()


# --------- Qt Table Model ---------
class CarTableModel(QAbstractTableModel):
    def __init__(self, translator: Translator, db: Database, cars=None, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.db = db
        self._data = cars if cars is not None else self.db.fetch_all_cars()
        self.highlight_query = ""

    def set_highlight_query(self, q):
        self.highlight_query = (q or "").lower().strip()
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount()-1, self.columnCount()-1), [Qt.BackgroundRole])

    def update_translator(self, translator: Translator):
        self.translator = translator
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount()-1, self.columnCount()-1), [Qt.DisplayRole])

    def load_data(self, cars=None):
        self.beginResetModel()
        self._data = cars if cars is not None else self.db.fetch_all_cars()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(DISPLAY_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        value = self._data[row][DISPLAY_COLS[col]]

        if role == Qt.DisplayRole:
            if col == 4 and isinstance(value, (int, float)):
                return format_price(value, self.translator.lang)
            return str(value)

        if role == Qt.TextAlignmentRole:
            if col in (1, 2, 5, 6, 7, 8, 11):  # texts
                return Qt.AlignVCenter | Qt.AlignLeft
            return Qt.AlignVCenter | Qt.AlignRight

        if role == Qt.BackgroundRole and self.highlight_query:
            try:
                text = str(value).lower()
                if self.highlight_query in text and self.highlight_query != "":
                    dark = QApplication.instance().palette().color(QPalette.Window).value() < 128
                    return QColor(60, 80, 140, 80) if dark else QColor(180, 205, 255, 120)
            except Exception:
                pass

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            key = HEADER_KEYS[section]
            return self.translator.t(key) if key != "ID" else "ID"
        else:
            return str(section + 1)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        flags = super().flags(index) | Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() != 0:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        row = index.row()
        col = index.column()
        if col == 0:
            return False
        car = self._data[row]
        car_id = car[0]
        field = FIELD_MAP.get(col)
        if not field:
            return False
        text = str(value).strip()

        # parse and validate
        try:
            if field in INT_FIELDS:
                new_val = int(text)
                if field == "year" and not (1886 <= new_val <= 2050):
                    return False
            elif field in FLOAT_FIELDS:
                new_val = float(text)
                if new_val <= 0:
                    return False
            else:
                new_val = text
                if field == "type" and new_val not in ENUM_TYPES:
                    return False
                if field == "condition" and new_val not in ENUM_CONDITIONS:
                    return False
                if field == "drive_trains" and new_val not in ENUM_DRIVES:
                    return False
                if field in {"make", "model", "color", "salesperson"} and not new_val:
                    return False
        except Exception:
            return False

        try:
            self.db.update_car(car_id, {field: new_val})
            car_list = list(self._data[row])
            car_list[col] = new_val
            self._data[row] = tuple(car_list)
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        except Exception:
            return False

    def sort(self, column, order):
        reverse = order == Qt.DescendingOrder
        idx = DISPLAY_COLS[column]

        def key_fn(rec):
            v = rec[idx]
            if column in NUMERIC_COLS:
                try:
                    return float(v)
                except Exception:
                    return float("inf")
            return str(v).lower()

        self.layoutAboutToBeChanged.emit()
        self._data.sort(key=key_fn, reverse=reverse)
        self.layoutChanged.emit()

    def get_row(self, row):
        return self._data[row] if 0 <= row < len(self._data) else None


# --------- Proxy for quick filter ---------
class CarFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query = ""

    def setQuery(self, text):
        self.query = (text or "").lower().strip()
        self.invalidateFilter()
        src = self.sourceModel()
        if hasattr(src, "set_highlight_query"):
            src.set_highlight_query(self.query)

    def filterAcceptsRow(self, src_row, src_parent):
        if not self.query:
            return True
        model = self.sourceModel()
        cols = model.columnCount()
        for c in range(cols):
            idx = model.index(src_row, c, src_parent)
            val = model.data(idx, Qt.DisplayRole)
            if val and self.query in str(val).lower():
                return True
        return False


# --------- Inline Editing Delegate ---------
from PySide6.QtWidgets import QStyledItemDelegate

class InlineDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        col = index.column()
        if col == 3:  # year
            w = QSpinBox(parent); w.setRange(1886, 2050); return w
        if col == 4:  # price
            w = QDoubleSpinBox(parent); w.setRange(0, 1e9); w.setDecimals(2); return w
        if col == 9:  # engine
            w = QSpinBox(parent); w.setRange(1, 100000); return w
        if col == 10:  # liter
            w = QSpinBox(parent); w.setRange(1, 10000); return w
        if col == 6:  # type
            w = QComboBox(parent); w.addItems(ENUM_TYPES); return w
        if col == 7:  # condition
            w = QComboBox(parent); w.addItems(ENUM_CONDITIONS); return w
        if col == 8:  # drive
            w = QComboBox(parent); w.addItems(ENUM_DRIVES); return w
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.DisplayRole)
        col = index.column()
        if isinstance(editor, QSpinBox):
            try: editor.setValue(int(str(val).replace(",", "").replace("$", "")))
            except Exception: editor.setValue(0)
        elif isinstance(editor, QDoubleSpinBox):
            try: editor.setValue(float(str(val).replace(",", "").replace("$", "")))
            except Exception: editor.setValue(0.0)
        elif isinstance(editor, QComboBox):
            i = editor.findText(str(val))
            editor.setCurrentIndex(i if i >= 0 else 0)
        elif isinstance(editor, QLineEdit):
            editor.setText(str(val))

    def setModelData(self, editor, model, index):
        if isinstance(editor, QSpinBox):
            model.setData(index, str(editor.value()))
        elif isinstance(editor, QDoubleSpinBox):
            model.setData(index, str(editor.value()))
        elif isinstance(editor, QComboBox):
            model.setData(index, editor.currentText())
        elif isinstance(editor, QLineEdit):
            model.setData(index, editor.text())


# --------- Drop-enabled label for image ---------
class ImageDropLabel(QLabel):
    def __init__(self, parent=None, on_drop=None, tooltip_text=""):
        super().__init__(parent)
        self.on_drop = on_drop
        self.setAcceptDrops(True)
        if tooltip_text:
            self.setToolTip(tooltip_text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                u = url.toString()
                if u.startswith("http"):
                    event.acceptProposedAction()
                    return
                p = url.toLocalFile()
                if p and os.path.splitext(p.lower())[1] in (".png", ".jpg", ".jpeg", ".bmp"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            u = url.toString()
            if u.startswith("http"):
                if requests is None:
                    QMessageBox.warning(self, "Info", "Install 'requests' to drop images from web.")
                    continue
                try:
                    r = requests.get(u, timeout=10)
                    if r.ok:
                        pm = QPixmap()
                        pm.loadFromData(r.content)
                        if not pm.isNull():
                            temp_path = os.path.join(os.getcwd(), "dropped_image.png")
                            pm.save(temp_path, "PNG")
                            if callable(self.on_drop):
                                self.on_drop(temp_path)
                                return
                except Exception:
                    pass
            else:
                p = url.toLocalFile()
                if p and os.path.splitext(p.lower())[1] in (".png", ".jpg", ".jpeg", ".bmp"):
                    if callable(self.on_drop):
                        self.on_drop(p)
                        return
        event.ignore()


# --------- Dialogs ---------
class CarFormDialog(QDialog):
    def __init__(self, translator: Translator, parent=None, car=None, prefill=None):
        super().__init__(parent)
        self.translator = translator
        self.car = car
        self.setWindowTitle(self.translator.t("edit") if car else self.translator.t("add_car"))
        self.setMinimumWidth(460)
        self.image_path = car[12] if car else ""
        self._build_ui()
        if prefill:
            self._apply_prefill(prefill)
        if car:
            self._fill_from_car()

    def _build_ui(self):
        form = QFormLayout(self)

        self.ed_make = QLineEdit()
        self.ed_model = QLineEdit()
        self.sp_year = QSpinBox(); self.sp_year.setRange(1886, 2050)
        self.dsp_price = QDoubleSpinBox(); self.dsp_price.setRange(0, 1e9); self.dsp_price.setDecimals(2)
        self.ed_color = QLineEdit()
        self.cb_type = QComboBox(); self.cb_type.addItems(ENUM_TYPES)
        self.cb_condition = QComboBox(); self.cb_condition.addItems(ENUM_CONDITIONS)
        self.cb_drive = QComboBox(); self.cb_drive.addItems(ENUM_DRIVES)
        self.sp_engine = QSpinBox(); self.sp_engine.setRange(1, 100000)
        self.sp_liter = QSpinBox(); self.sp_liter.setRange(1, 10000)
        self.ed_sales = QLineEdit()

        self.ed_make.setPlaceholderText("Toyota / BMW")
        self.ed_model.setPlaceholderText("Corolla / 3-Series")
        self.dsp_price.setPrefix("$")
        self.ed_color.setPlaceholderText("Red / Black")

        form.addRow(self.translator.t("make"), self.ed_make)
        form.addRow(self.translator.t("model"), self.ed_model)
        form.addRow(self.translator.t("year"), self.sp_year)
        form.addRow(self.translator.t("price"), self.dsp_price)
        form.addRow(self.translator.t("color"), self.ed_color)
        form.addRow(self.translator.t("type"), self.cb_type)
        form.addRow(self.translator.t("condition"), self.cb_condition)
        form.addRow(self.translator.t("drive_trains"), self.cb_drive)
        form.addRow(self.translator.t("engine_power"), self.sp_engine)
        form.addRow(self.translator.t("liter_capacity"), self.sp_liter)
        form.addRow(self.translator.t("salesperson"), self.ed_sales)

        img_row = QHBoxLayout()
        self.lbl_img_path = QLabel(self.image_path)
        btn_browse = QPushButton(self.translator.t("browse"))
        btn_browse.setIcon(std_icon(QStyle.SP_DialogOpenButton))
        btn_browse.clicked.connect(self.browse_image)
        img_row.addWidget(QLabel(self.translator.t("upload_image")))
        img_row.addWidget(self.lbl_img_path, 1)
        img_row.addWidget(btn_browse)
        form.addRow(img_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btns.button(QDialogButtonBox.Ok).setText(self.translator.t("save") if self.car else self.translator.t("submit"))
        btns.button(QDialogButtonBox.Ok).setIcon(std_icon(QStyle.SP_DialogApplyButton))
        btns.button(QDialogButtonBox.Cancel).setText(self.translator.t("cancel") if "cancel" in self.translator.translations else "Cancel")
        btns.button(QDialogButtonBox.Cancel).setIcon(std_icon(QStyle.SP_DialogCancelButton))
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _fill_from_car(self):
        c = self.car
        self.ed_make.setText(c[1])
        self.ed_model.setText(c[2])
        self.sp_year.setValue(int(c[3]))
        self.dsp_price.setValue(float(c[4]))
        self.ed_color.setText(c[5])
        idx = self.cb_type.findText(c[6]); self.cb_type.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.cb_condition.findText(c[7]); self.cb_condition.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.cb_drive.findText(c[8]); self.cb_drive.setCurrentIndex(idx if idx >= 0 else 0)
        self.sp_engine.setValue(int(c[9]))
        self.sp_liter.setValue(int(c[10]))
        self.ed_sales.setText(c[11])

    def _apply_prefill(self, c):
        self.ed_make.setText(c[1])
        self.ed_model.setText(c[2])
        self.sp_year.setValue(int(c[3]))
        self.dsp_price.setValue(float(c[4]))
        self.ed_color.setText(c[5])
        idx = self.cb_type.findText(c[6]); self.cb_type.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.cb_condition.findText(c[7]); self.cb_condition.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.cb_drive.findText(c[8]); self.cb_drive.setCurrentIndex(idx if idx >= 0 else 0)
        self.sp_engine.setValue(int(c[9]))
        self.sp_liter.setValue(int(c[10]))
        self.ed_sales.setText(c[11])
        self.image_path = ""
        self.lbl_img_path.setText(self.image_path)

    def browse_image(self):
        p, _ = QFileDialog.getOpenFileName(self, self.translator.t("select_image"),
                                           filter="Image files (*.png *.jpg *.jpeg *.bmp);;All files (*.*)")
        if p:
            self.image_path = p
            self.lbl_img_path.setText(p)

    def get_data(self):
        make = self.ed_make.text().strip()
        model = self.ed_model.text().strip()
        year = int(self.sp_year.value())
        price = float(self.dsp_price.value())
        color = self.ed_color.text().strip()
        car_type = self.cb_type.currentText()
        condition = self.cb_condition.currentText()
        drive = self.cb_drive.currentText()
        engine = int(self.sp_engine.value())
        liter = int(self.sp_liter.value())
        sales = self.ed_sales.text().strip()

        if not (1886 <= year <= 2050):
            raise ValueError(self.translator.t("invalid_year_range"))
        if price <= 0 or engine <= 0 or liter <= 0:
            raise ValueError(self.translator.t("invalid_positive_value"))
        if not (make and model and color and sales):
            raise ValueError(self.translator.t("all_fields_required"))

        return (make, model, year, price, color, car_type, condition, drive, engine, liter, sales, self.image_path)


class GalleryDialog(QDialog):
    def __init__(self, translator: Translator, db: Database, car_id: int, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.db = db
        self.car_id = car_id
        self.setWindowTitle(self.translator.t("gallery") if "gallery" in self.translator.translations else "Gallery")
        self.resize(640, 420)
        self._build_ui()
        self._load_images()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.listw = QListWidget()
        self.listw.setViewMode(QListWidget.IconMode)
        self.listw.setIconSize(QSize(140, 120))
        self.listw.setResizeMode(QListWidget.Adjust)
        self.listw.setSpacing(8)
        layout.addWidget(self.listw, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton(self.translator.t("add") if "add" in self.translator.translations else "Add")
        self.btn_add.setIcon(std_icon(QStyle.SP_FileDialogNewFolder))
        self.btn_add.clicked.connect(self.add_images)

        self.btn_remove = QPushButton(self.translator.t("delete"))
        self.btn_remove.setIcon(std_icon(QStyle.SP_TrashIcon))
        self.btn_remove.clicked.connect(self.remove_selected)

        self.btn_set_main = QPushButton(self.translator.t("set_as_main") if "set_as_main" in self.translator.translations else "Set as main")
        self.btn_set_main.setIcon(std_icon(QStyle.SP_DialogApplyButton))
        self.btn_set_main.clicked.connect(self.set_main)

        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_set_main)
        row.addStretch(1)
        layout.addLayout(row)

    def _load_images(self):
        self.listw.clear()
        for img_id, path in self.db.fetch_images(self.car_id):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, (img_id, path))
            pm = QPixmap(path)
            if not pm.isNull():
                item.setIcon(QIcon(pm.scaled(140, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            item.setText(os.path.basename(path))
            self.listw.addItem(item)

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.translator.t("select_image"),
                                                filter="Image files (*.png *.jpg *.jpeg *.bmp)")
        if not files:
            return
        img_dir = "car_images"
        os.makedirs(img_dir, exist_ok=True)
        for p in files:
            try:
                ext = os.path.splitext(p)[1]
                unique = f"car{self.car_id}_{int(pd.Timestamp.now().timestamp())}{ext}"
                dst = os.path.join(img_dir, unique)
                with open(p, "rb") as src, open(dst, "wb") as out:
                    out.write(src.read())
                self.db.add_image(self.car_id, dst)
            except Exception as ex:
                QMessageBox.warning(self, self.translator.t("warning"), f"{self.translator.t('image_save_fail')}: {ex}")
        self._load_images()

    def remove_selected(self):
        item = self.listw.currentItem()
        if not item: return
        img_id, path = item.data(Qt.UserRole)
        if QMessageBox.question(self, self.translator.t("confirm"), self.translator.t("confirm_delete")) != QMessageBox.Yes:
            return
        try:
            self.db.delete_image(img_id)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        self._load_images()

    def set_main(self):
        item = self.listw.currentItem()
        if not item: return
        _, path = item.data(Qt.UserRole)
        try:
            self.db.update_car(self.car_id, {"image_path": path})
            QMessageBox.information(self, self.translator.t("success"), self.translator.t("image_updated") if "image_updated" in self.translator.translations else "Image updated.")
            self.accept()
        except Exception as ex:
            QMessageBox.critical(self, self.translator.t("error"), str(ex))


class LoginDialog(QDialog):
    def __init__(self, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.username = None
        self.role = None
        self.setWindowTitle(self.translator.t("login_title"))
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit(); self.ed_pass.setEchoMode(QLineEdit.Password)
        layout.addRow(self.translator.t("username"), self.ed_user)
        layout.addRow(self.translator.t("password"), self.ed_pass)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _validate(self):
        username = self.ed_user.text().strip()
        password = self.ed_pass.text()
        users = {
            "admin": {"password": "admin123", "role": "admin"},
            "sales": {"password": "sales123", "role": "salesperson"}
        }
        user = users.get(username)
        if user and user["password"] == password:
            self.username = username
            self.role = user["role"]
            self.accept()
        else:
            QMessageBox.critical(self, self.translator.t("login_title"), self.translator.t("login_failed"))


# --------- Toast ---------
class Toast(QWidget):
    def __init__(self, parent, text, duration=2000):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        label = QLabel(text)
        label.setStyleSheet("color: white;")
        layout.addWidget(label)
        self.setStyleSheet("background: rgba(0,0,0,0.8); border-radius: 6px; padding: 8px;")
        self.adjustSize()
        gp = parent.geometry()
        self.move(gp.right() - self.width() - 20, gp.bottom() - self.height() - 20)
        self.show()
        QTimer.singleShot(duration, self.close)


# --------- Main Window ---------
class MainWindow(QMainWindow):
    def __init__(self, current_user="admin", current_role="admin", lang="en"):
        super().__init__()
        self.settings = QSettings("YourOrg", "CarSales")
        self.lang = lang
        self.translator = Translator(self.lang)
        self.db = Database()
        self.current_user = current_user
        self.current_role = current_role

        self.setWindowTitle("Car Sales Management System (PySide6)")
        self.resize(1280, 780)

        self._init_ui()
        self._restore_state()
        self._apply_matplotlib_style()
        self._apply_qss()
        self._update_texts()
        self._set_tooltips()
        self._update_status()

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.add_car_dialog)
        QShortcut(QKeySequence("Delete"), self, activated=self.delete_selected_car)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_quick_filter)
        QShortcut(QKeySequence("Return"), self, activated=self.edit_selected_car)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.duplicate_selected_car)
        QShortcut(QKeySequence("F5"), self, activated=lambda: (self.model.load_data(), self._update_status()))

    def _set_button_icon(self, button, sp_icon):
        icon = std_icon(sp_icon)
        if icon:
            button.setIcon(icon)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(10)

        self.btn_dashboard = QPushButton(); self._set_button_icon(self.btn_dashboard, QStyle.SP_DesktopIcon)
        self.btn_add = QPushButton(); self._set_button_icon(self.btn_add, QStyle.SP_FileDialogNewFolder)
        self.btn_search = QPushButton(); self._set_button_icon(self.btn_search, QStyle.SP_FileDialogContentsView)
        self.btn_analytics = QPushButton(); self._set_button_icon(self.btn_analytics, QStyle.SP_ComputerIcon)
        self.btn_import = QPushButton(); self._set_button_icon(self.btn_import, QStyle.SP_DialogOpenButton)
        self.btn_export = QPushButton(); self._set_button_icon(self.btn_export, QStyle.SP_DialogSaveButton)
        self.btn_columns = QPushButton(); self._set_button_icon(self.btn_columns, QStyle.SP_FileDialogDetailedView)
        self.btn_backup = QPushButton(); self._set_button_icon(self.btn_backup, QStyle.SP_DriveHDIcon)
        self.btn_restore = QPushButton(); self._set_button_icon(self.btn_restore, QStyle.SP_BrowserReload)
        self.btn_toggle_theme = QPushButton(); self._set_button_icon(self.btn_toggle_theme, QStyle.SP_BrowserStop)
        self.btn_toggle_lang = QPushButton(); self._set_button_icon(self.btn_toggle_lang, QStyle.SP_MessageBoxInformation)
        self.btn_exit = QPushButton(); self._set_button_icon(self.btn_exit, QStyle.SP_DialogCloseButton)

        for b in [
            self.btn_dashboard, self.btn_add, self.btn_search, self.btn_analytics,
            self.btn_import, self.btn_export, self.btn_columns, self.btn_backup,
            self.btn_restore, self.btn_toggle_theme, self.btn_toggle_lang, self.btn_exit
        ]:
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            side_layout.addWidget(b)

        side_layout.addStretch(1)

        # Pages
        self.stack = QStackedWidget()
        self.page_dashboard = self._build_dashboard_page()
        self.page_search = self._build_search_page()
        self.page_analytics = self._build_analytics_page()

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_search)
        self.stack.addWidget(self.page_analytics)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)

        # Status bar
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        self.sb_left = QLabel("")
        self.sb_right = QLabel("")
        sb.addWidget(self.sb_left, 1)
        sb.addPermanentWidget(self.sb_right, 0)

        # Actions
        self.btn_dashboard.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_dashboard))
        self.btn_add.clicked.connect(self.add_car_dialog)
        self.btn_search.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_search))
        self.btn_analytics.clicked.connect(lambda: (self._apply_matplotlib_style(), self._refresh_analytics(), self.stack.setCurrentWidget(self.page_analytics)))
        self.btn_import.clicked.connect(self.import_data)
        self.btn_export.clicked.connect(self.export_to_excel)
        self.btn_columns.clicked.connect(self._open_columns_menu)
        self.btn_backup.clicked.connect(self.backup_data)
        self.btn_restore.clicked.connect(self.restore_data)
        self.btn_toggle_theme.clicked.connect(self.toggle_theme)
        self.btn_toggle_lang.clicked.connect(self.toggle_language)
        self.btn_exit.clicked.connect(self.close)

        if self.current_role != "admin":
            self.btn_backup.setEnabled(False)
            self.btn_restore.setEnabled(False)

        self.setWindowTitle(f"Car Sales Management (PySide6) — {self.current_user} ({self.current_role})")

    def _build_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.lb_dash_title = QLabel()
        self.lb_dash_title.setStyleSheet("font-size:18pt; font-weight:600;")
        layout.addWidget(self.lb_dash_title)

        self.splitter = QSplitter()
        layout.addWidget(self.splitter, 1)

        # Left: table + quick filter
        left = QWidget()
        lv = QVBoxLayout(left)

        top_bar = QHBoxLayout()
        self.ed_quick_filter = QLineEdit()
        self.ed_quick_filter.setPlaceholderText("Search…")
        self.btn_clear_filter = QToolButton()
        self.btn_clear_filter.setIcon(std_icon(QStyle.SP_DialogResetButton))
        self.btn_clear_filter.clicked.connect(lambda: self.ed_quick_filter.clear())
        top_bar.addWidget(self.ed_quick_filter, 1)
        top_bar.addWidget(self.btn_clear_filter, 0)
        lv.addLayout(top_bar)

        self.table = QTableView()
        self.table.setSortingEnabled(True)
        self.model = CarTableModel(self.translator, self.db)
        self.proxy = CarFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.setItemDelegate(InlineDelegate(self.table))
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self._open_header_menu)

        self.ed_quick_filter.textChanged.connect(lambda text: (self.proxy.setQuery(text), self._update_status()))

        self.table.selectionModel().selectionChanged.connect(self._on_table_selection)
        self.table.doubleClicked.connect(self.edit_selected_car)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_table_menu)
        lv.addWidget(self.table)

        # Right: preview (drop-enabled)
        right = QWidget()
        rv = QVBoxLayout(right)

        gb = QGroupBox()
        gb.setTitle(self.translator.t("upload_image"))
        gb_l = QVBoxLayout(gb)

        hint = self.translator.t("drop_image_hint") if "drop_image_hint" in self.translator.translations else "Drop image here to set/update"
        self.lbl_preview_img = ImageDropLabel(on_drop=self._handle_drop_image, tooltip_text=hint)
        self.lbl_preview_img.setAlignment(Qt.AlignCenter)
        self.lbl_preview_img.setMinimumSize(QSize(280, 240))
        self.lbl_preview_img.setStyleSheet("border:1px solid #444;")
        gb_l.addWidget(self.lbl_preview_img)

        self.lbl_preview_title = QLabel()
        self.lbl_preview_title.setStyleSheet("font-weight:600; font-size:12pt;")
        gb_l.addWidget(self.lbl_preview_title, 0, Qt.AlignHCenter)

        self.lbl_preview_meta = QLabel()
        self.lbl_preview_meta.setWordWrap(True)
        gb_l.addWidget(self.lbl_preview_meta, 0, Qt.AlignHCenter)

        btns = QHBoxLayout()
        self.btn_edit = QPushButton(self.translator.t("edit"))
        self.btn_edit.setIcon(std_icon(QStyle.SP_FileDialogDetailedView))
        self.btn_delete = QPushButton(self.translator.t("delete"))
        self.btn_delete.setIcon(std_icon(QStyle.SP_TrashIcon))
        self.btn_dup = QPushButton(self.translator.t("duplicate") if "duplicate" in self.translator.translations else "Duplicate")
        self.btn_dup.setIcon(std_icon(QStyle.SP_FileDialogNewFolder))
        self.btn_gallery = QPushButton(self.translator.t("gallery") if "gallery" in self.translator.translations else "Gallery")
        self.btn_gallery.setIcon(std_icon(QStyle.SP_DirHomeIcon))
        self.btn_pdf = QPushButton(self.translator.t("export_pdf") if "export_pdf" in self.translator.translations else "Export PDF")
        self.btn_pdf.setIcon(std_icon(QStyle.SP_DialogSaveButton))

        self.btn_edit.clicked.connect(self.edit_selected_car)
        self.btn_delete.clicked.connect(self.delete_selected_car)
        self.btn_dup.clicked.connect(self.duplicate_selected_car)
        self.btn_gallery.clicked.connect(self.open_gallery)
        self.btn_pdf.clicked.connect(self.export_selected_pdf)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_delete)
        btns.addWidget(self.btn_dup)
        btns.addWidget(self.btn_gallery)
        btns.addWidget(self.btn_pdf)
        gb_l.addLayout(btns)

        rv.addWidget(gb)
        rv.addStretch(1)

        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        return page

    def _placeholder_pixmap(self, w=280, h=240):
        pm = QPixmap(w, h)
        pm.fill(QColor(240, 240, 240) if not getattr(self, "is_dark", True) else QColor(60, 60, 60))
        painter = QPainter(pm)
        painter.setPen(QColor(120, 120, 120) if not self.is_dark else QColor(200, 200, 200))
        font = QFont(); font.setPointSize(10); font.setBold(True)
        painter.setFont(font)
        text = "No Image" if self.lang == "en" else "لا توجد صورة"
        painter.drawText(pm.rect(), Qt.AlignCenter, text)
        painter.end()
        return pm

    def _selected_source_row(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        idx_proxy = sel[0]
        idx_src = self.proxy.mapToSource(idx_proxy)
        return idx_src.row()

    def _on_table_selection(self):
        row_src = self._selected_source_row()
        if row_src is None:
            self.lbl_preview_img.setPixmap(self._placeholder_pixmap())
            self.lbl_preview_title.setText("")
            self.lbl_preview_meta.setText("")
            return
        car = self.model.get_row(row_src)
        if not car:
            return
        make, model, year = car[1], car[2], car[3]
        price = car[4]
        cond = car[7]
        img_path = car[12] or ""

        self.lbl_preview_title.setText(f"{make} {model} • {year}")
        self.lbl_preview_meta.setText(f"{self.translator.t('condition')}: {cond}  |  {self.translator.t('price')}: {format_price(price, self.translator.lang)}")

        if img_path and os.path.exists(img_path):
            pm = QPixmap(img_path)
            self.lbl_preview_img.setPixmap(pm.scaled(280, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_preview_img.setPixmap(self._placeholder_pixmap())

    def _handle_drop_image(self, path):
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.information(self, self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        car = self.model.get_row(row_src)
        make, model, year = car[1], car[2], car[3]
        stored_img_path = car[12] or ""
        try:
            img_dir = "car_images"
            os.makedirs(img_dir, exist_ok=True)
            ext = os.path.splitext(path)[1] if os.path.splitext(path)[1] else ".png"
            unique_name = f"{make}_{model}_{year}_{int(pd.Timestamp.now().timestamp())}{ext}"
            new_path = os.path.join(img_dir, unique_name)
            with open(path, "rb") as src_f, open(new_path, "wb") as dst_f:
                dst_f.write(src_f.read())
            if stored_img_path and os.path.exists(stored_img_path):
                try: os.remove(stored_img_path)
                except Exception: pass
            self.db.update_car(car[0], {"image_path": new_path})
            self.model.load_data()
            self._on_table_selection()
            Toast(self, self.translator.t("image_updated") if "image_updated" in self.translator.translations else "Image updated.", 2000)
        except Exception as ex:
            QMessageBox.critical(self, self.translator.t("error"), f"{self.translator.t('image_save_fail')}: {ex}")

    def _open_header_menu(self, pos):
        header = self.table.horizontalHeader()
        menu = QMenu(self)
        hidden_cols = set(map(str, self.settings.value("hiddenColumns", [], type=list)))
        for i, key in enumerate(HEADER_KEYS):
            if i == 0:  # ID always visible
                continue
            act = QAction(self.translator.t(key) if key != "ID" else "ID", self, checkable=True)
            act.setChecked(str(i) not in hidden_cols)
            act.triggered.connect(lambda checked, col=i: self._toggle_column(col, checked))
            menu.addAction(act)
        menu.exec(QCursor.pos())

    def _open_columns_menu(self):
        self._open_header_menu(QPoint(0, 0))

    def _toggle_column(self, col, show):
        self.table.setColumnHidden(col, not show)
        hidden_cols = set(map(str, self.settings.value("hiddenColumns", [], type=list)))
        if not show:
            hidden_cols.add(str(col))
        else:
            hidden_cols.discard(str(col))
        self.settings.setValue("hiddenColumns", list(hidden_cols))

    def _open_table_menu(self, pos):
        index = self.table.indexAt(pos)
        if index.isValid():
            self.table.selectRow(index.row())
        menu = QMenu(self)

        act_add = QAction(self.translator.t("add_car"), self)
        act_add.setIcon(std_icon(QStyle.SP_FileDialogNewFolder))
        menu.addAction(act_add)

        sel = self.table.selectionModel().selectedRows()
        act_edit = act_del = act_copy_cell = act_copy_row = act_copy_col = act_export_csv = act_export_xlsx = act_export_pdf = act_dup = None
        if sel:
            menu.addSeparator()
            act_edit = QAction(self.translator.t("edit"), self); act_edit.setIcon(std_icon(QStyle.SP_FileDialogDetailedView)); menu.addAction(act_edit)
            act_dup = QAction(self.translator.t("duplicate") if "duplicate" in self.translator.translations else "Duplicate", self)
            act_dup.setIcon(std_icon(QStyle.SP_FileDialogNewFolder)); menu.addAction(act_dup)
            act_del = QAction(self.translator.t("delete"), self); act_del.setIcon(std_icon(QStyle.SP_TrashIcon)); menu.addAction(act_del)

            menu.addSeparator()
            act_copy_cell = QAction(self.translator.t("copy_cell") if "copy_cell" in self.translator.translations else "Copy Cell", self)
            act_copy_row = QAction(self.translator.t("copy_row") if "copy_row" in self.translator.translations else "Copy Row", self)
            act_copy_col = QAction(self.translator.t("copy_column") if "copy_column" in self.translator.translations else "Copy Column", self)
            menu.addAction(act_copy_cell)
            menu.addAction(act_copy_row)
            menu.addAction(act_copy_col)

            menu.addSeparator()
            act_export_csv = QAction(self.translator.t("export_row_csv") if "export_row_csv" in self.translator.translations else "Export Row (CSV)", self)
            act_export_xlsx = QAction(self.translator.t("export_row_excel") if "export_row_excel" in self.translator.translations else "Export Row (Excel)", self)
            act_export_pdf = QAction(self.translator.t("export_pdf") if "export_pdf" in self.translator.translations else "Export PDF", self)
            act_export_csv.setIcon(std_icon(QStyle.SP_DialogSaveButton))
            act_export_xlsx.setIcon(std_icon(QStyle.SP_DialogSaveButton))
            act_export_pdf.setIcon(std_icon(QStyle.SP_DialogSaveButton))
            menu.addAction(act_export_csv)
            menu.addAction(act_export_xlsx)
            menu.addAction(act_export_pdf)

        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == act_add:
            self.add_car_dialog()
        elif sel and chosen == act_edit:
            self.edit_selected_car()
        elif sel and chosen == act_dup:
            self.duplicate_selected_car()
        elif sel and chosen == act_del:
            self.delete_selected_car()
        elif sel and chosen == act_copy_cell:
            self._copy_selected_cell(index if index.isValid() else None)
        elif sel and chosen == act_copy_row:
            self._copy_selected_row()
        elif sel and chosen == act_copy_col:
            col = index.column() if index.isValid() else 0
            self._copy_column(col)
        elif sel and chosen == act_export_csv:
            self._export_selected_row(csv=True)
        elif sel and chosen == act_export_xlsx:
            self._export_selected_row(csv=False)
        elif sel and chosen == act_export_pdf:
            self.export_selected_pdf()

    def _copy_selected_cell(self, index):
        if not index or not index.isValid():
            return
        val = self.proxy.data(index, Qt.DisplayRole)
        QApplication.clipboard().setText("" if val is None else str(val))
        Toast(self, self.translator.t("copy") + " ✓", 1200)

    def _copy_selected_row(self):
        row_src = self._selected_source_row()
        if row_src is None:
            return
        rec = self.model.get_row(row_src)
        values = []
        for c in range(len(DISPLAY_COLS)):
            v = rec[DISPLAY_COLS[c]]
            if c == 4 and isinstance(v, (int, float)):
                values.append(format_price(v, self.translator.lang))
            else:
                values.append(str(v))
        QApplication.clipboard().setText("\t".join(values))
        Toast(self, self.translator.t("copy") + " ✓", 1200)

    def _copy_column(self, col_proxy):
        out = []
        rows = self.proxy.rowCount()
        for r in range(rows):
            idx = self.proxy.index(r, col_proxy)
            val = self.proxy.data(idx, Qt.DisplayRole)
            out.append("" if val is None else str(val))
        QApplication.clipboard().setText("\n".join(out))
        Toast(self, self.translator.t("copy") + " ✓", 1200)

    def _export_selected_row(self, csv=True):
        row_src = self._selected_source_row()
        if row_src is None:
            return
        car = self.model.get_row(row_src)
        headers = HEADER_KEYS + ["Image Path"]
        data = list(car[:12]) + [car[12]]

        df = pd.DataFrame([data], columns=headers)
        default_name = f"car_{car[0]}.{'csv' if csv else 'xlsx'}"
        caption = self.translator.t("export_row") if "export_row" in self.translator.translations else "Export Row"
        if csv:
            fp, _ = QFileDialog.getSaveFileName(self, caption, default_name, filter="CSV (*.csv)")
        else:
            fp, _ = QFileDialog.getSaveFileName(self, caption, default_name, filter="Excel (*.xlsx)")
        if not fp:
            return
        try:
            if csv:
                if not fp.lower().endswith(".csv"):
                    fp += ".csv"
                df.to_csv(fp, index=False)
            else:
                if not fp.lower().endswith(".xlsx"):
                    fp += ".xlsx"
                df.to_excel(fp, index=False)
            QMessageBox.information(self, self.translator.t("success"), self.translator.t("export_success"))
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), f"{self.translator.t('export_fail')}: {e}")

    def export_selected_pdf(self):
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.warning(self, self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        car = self.model.get_row(row_src)
        fp, _ = QFileDialog.getSaveFileName(self, self.translator.t("export_pdf") if "export_pdf" in self.translator.translations else "Export PDF",
                                            f"car_{car[0]}.pdf", filter="PDF (*.pdf)")
        if not fp:
            return
        img_html = ""
        if car[12] and os.path.exists(car[12]):
            data = bytes_from_image_path(car[12], 400)
            if data:
                b64 = base64.b64encode(data).decode("utf-8")
                img_html = f'<img src="data:image/png;base64,{b64}" style="max-width:400px;"/><br/>'
        html = f"""
        <html><body>
        <h2>{car[1]} {car[2]} ({car[3]})</h2>
        {img_html}
        <p><b>{self.translator.t('price')}:</b> {format_price(car[4], self.translator.lang)}</p>
        <p><b>{self.translator.t('color')}:</b> {car[5]} &nbsp; <b>{self.translator.t('type')}:</b> {car[6]}</p>
        <p><b>{self.translator.t('condition')}:</b> {car[7]} &nbsp; <b>{self.translator.t('drive_trains')}:</b> {car[8]}</p>
        <p><b>{self.translator.t('engine_power')}:</b> {car[9]} &nbsp; <b>{self.translator.t('liter_capacity')}:</b> {car[10]}</p>
        <p><b>{self.translator.t('salesperson')}:</b> {car[11]}</p>
        </body></html>
        """
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            if not fp.lower().endswith(".pdf"):
                fp += ".pdf"
            printer.setOutputFileName(fp)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            Toast(self, "PDF ✓", 1800)
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), str(e))

    def edit_selected_car(self):
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.warning(self, self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        car = self.model.get_row(row_src)
        dlg = CarFormDialog(self.translator, self, car=car)
        if dlg.exec() == QDialog.Accepted:
            try:
                (make, model, year, price, color, car_type, condition, drive, engine, liter, sales, image_path) = dlg.get_data()
            except ValueError as e:
                QMessageBox.critical(self, self.translator.t("error"), str(e))
                return

            stored_img_path = car[12] or ""
            if image_path and image_path != stored_img_path and os.path.exists(image_path):
                try:
                    img_dir = "car_images"
                    os.makedirs(img_dir, exist_ok=True)
                    ext = os.path.splitext(image_path)[1]
                    unique_name = f"{make}_{model}_{year}_{int(pd.Timestamp.now().timestamp())}{ext}"
                    stored_img_path = os.path.join(img_dir, unique_name)
                    with open(image_path, "rb") as src_f, open(stored_img_path, "wb") as dst_f:
                        dst_f.write(src_f.read())
                    if car[12] and os.path.exists(car[12]):
                        os.remove(car[12])
                except Exception as ex:
                    QMessageBox.warning(self, self.translator.t("warning"), f"{self.translator.t('image_save_fail')}: {ex}")

            updates = {
                "make": make, "model": model, "year": year, "price": price, "color": color,
                "type": car_type, "condition": condition, "drive_trains": drive,
                "engine_power": engine, "liter_capacity": liter, "salesperson": sales,
                "image_path": stored_img_path
            }
            self.db.update_car(car[0], updates)
            QMessageBox.information(self, self.translator.t("success"), self.translator.t("car_updated"))
            self.model.load_data()
            self._on_table_selection()
            self._update_status()

    def duplicate_selected_car(self):
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.information(self, self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        car = self.model.get_row(row_src)
        dlg = CarFormDialog(self.translator, self, car=None, prefill=car)
        if dlg.exec() == QDialog.Accepted:
            try:
                (make, model, year, price, color, car_type, condition, drive, engine, liter, sales, image_path) = dlg.get_data()
            except ValueError as e:
                QMessageBox.critical(self, self.translator.t("error"), str(e))
                return

            stored_img_path = ""
            if image_path and os.path.exists(image_path):
                try:
                    img_dir = "car_images"
                    os.makedirs(img_dir, exist_ok=True)
                    ext = os.path.splitext(image_path)[1]
                    unique_name = f"{make}_{model}_{year}_{int(pd.Timestamp.now().timestamp())}{ext}"
                    stored_img_path = os.path.join(img_dir, unique_name)
                    with open(image_path, "rb") as src_f, open(stored_img_path, "wb") as dst_f:
                        dst_f.write(src_f.read())
                except Exception as ex:
                    QMessageBox.warning(self, self.translator.t("warning"), f"{self.translator.t('image_save_fail')}: {ex}")

            self.db.insert_car((make, model, year, price, color, car_type, condition, drive, engine, liter, sales, stored_img_path))
            Toast(self, self.translator.t("car_added"), 1800)
            self.model.load_data()
            self._update_status()

    def add_car_dialog(self):
        dlg = CarFormDialog(self.translator, self, car=None)
        if dlg.exec() == QDialog.Accepted:
            try:
                (make, model, year, price, color, car_type, condition, drive, engine, liter, sales, image_path) = dlg.get_data()
            except ValueError as e:
                QMessageBox.critical(self, self.translator.t("error"), str(e))
                return

            stored_img_path = ""
            if image_path and os.path.exists(image_path):
                try:
                    img_dir = "car_images"
                    os.makedirs(img_dir, exist_ok=True)
                    ext = os.path.splitext(image_path)[1]
                    unique_name = f"{make}_{model}_{year}_{int(pd.Timestamp.now().timestamp())}{ext}"
                    stored_img_path = os.path.join(img_dir, unique_name)
                    with open(image_path, "rb") as src_f, open(stored_img_path, "wb") as dst_f:
                        dst_f.write(src_f.read())
                except Exception as ex:
                    QMessageBox.warning(self, self.translator.t("warning"), f"{self.translator.t('image_save_fail')}: {ex}")

            self.db.insert_car((make, model, year, price, color, car_type, condition, drive, engine, liter, sales, stored_img_path))
            QMessageBox.information(self, self.translator.t("success"), self.translator.t("car_added"))
            self.model.load_data()
            self._update_status()

    def delete_selected_car(self):
        if self.current_role != "admin":
            QMessageBox.warning(self, self.translator.t("warning"), self.translator.t("delete_permission_denied"))
            return
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.warning(self, self.translator.t("warning"), self.translator.t("select_car_delete"))
            return
        if QMessageBox.question(self, self.translator.t("confirm"), self.translator.t("confirm_delete")) != QMessageBox.Yes:
            return
        car = self.model.get_row(row_src)
        car_id = car[0]
        img_path = car[12]
        try:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass
        self.db.delete_car(car_id)
        QMessageBox.information(self, self.translator.t("success"), self.translator.t("car_deleted"))
        self.model.load_data()
        self._on_table_selection()
        self._update_status()

    def open_gallery(self):
        row_src = self._selected_source_row()
        if row_src is None:
            QMessageBox.information(self, self.translator.t("warning"), self.translator.t("select_car_edit"))
            return
        car = self.model.get_row(row_src)
        dlg = GalleryDialog(self.translator, self.db, car_id=car[0], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.model.load_data()
            self._on_table_selection()

    # NEW: focus quick filter method to fix the shortcut
    def _focus_quick_filter(self):
        self.stack.setCurrentWidget(self.page_dashboard)
        self.ed_quick_filter.setFocus()
        self.ed_quick_filter.selectAll()

    # ---------- Search ----------
    def _build_search_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        self.lb_search_title = QLabel()
        self.lb_search_title.setStyleSheet("font-size:18pt; font-weight:600;")
        v.addWidget(self.lb_search_title)

        form = QHBoxLayout()
        v.addLayout(form)

        self.ed_make = QLineEdit()
        self.sb_year_min = QSpinBox(); self.sb_year_min.setRange(0, 9999)
        self.sb_year_max = QSpinBox(); self.sb_year_max.setRange(0, 9999)
        self.ds_price_min = QDoubleSpinBox(); self.ds_price_min.setRange(0, 1e9); self.ds_price_min.setDecimals(2)
        self.ds_price_max = QDoubleSpinBox(); self.ds_price_max.setRange(0, 1e9); self.ds_price_max.setDecimals(2)
        self.cb_condition = QComboBox(); self.cb_condition.addItems(["Any"] + ENUM_CONDITIONS)
        self.cb_drive = QComboBox(); self.cb_drive.addItems(["Any"] + ENUM_DRIVES)
        self.btn_do_search = QPushButton()
        self.btn_do_search.setIcon(std_icon(QStyle.SP_FileDialogContentsView))
        self.btn_do_search.clicked.connect(self.perform_search)

        grid = QFormLayout()
        grid.addRow(self.translator.t("search_make"), self.ed_make)
        grid.addRow(self.translator.t("year_min"), self.sb_year_min)
        grid.addRow(self.translator.t("year_max"), self.sb_year_max)
        grid.addRow(self.translator.t("price_min"), self.ds_price_min)
        grid.addRow(self.translator.t("price_max"), self.ds_price_max)
        grid.addRow(self.translator.t("condition"), self.cb_condition)
        grid.addRow(self.translator.t("drive_trains"), self.cb_drive)

        form.addLayout(grid, 1)
        form.addWidget(self.btn_do_search)

        self.table_search = QTableView()
        self.table_search.setSortingEnabled(True)
        self.model_search = CarTableModel(self.translator, self.db, cars=[])
        self.table_search.setModel(self.model_search)
        self.table_search.setItemDelegate(InlineDelegate(self.table_search))
        self.table_search.verticalHeader().setDefaultSectionSize(28)
        self.table_search.setAlternatingRowColors(True)
        v.addWidget(self.table_search, 1)
        return page

    def perform_search(self):
        make = self.ed_make.text().strip()
        y1 = self.sb_year_min.value() or None
        y2 = self.sb_year_max.value() or None
        p1 = self.ds_price_min.value() or None
        p2 = self.ds_price_max.value() or None
        condition = self.cb_condition.currentText()
        drive = self.cb_drive.currentText()
        cars = self.db.fetch_cars_by_filters(make=make,
                                             year_min=y1 if y1 else None,
                                             year_max=y2 if y2 else None,
                                             price_min=p1 if p1 else None,
                                             price_max=p2 if p2 else None,
                                             condition=condition, drive_trains=drive)
        self.model_search.load_data(cars)
        if not cars:
            QMessageBox.information(self, self.translator.t("search"), self.translator.t("no_cars_found"))

    # ---------- Analytics ----------
    def _build_analytics_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        self.lb_analytics_title = QLabel()
        self.lb_analytics_title.setStyleSheet("font-size:18pt; font-weight:600;")
        v.addWidget(self.lb_analytics_title)

        self.lbl_stats = QLabel()
        v.addWidget(self.lbl_stats)

        self.canvas_holder = QWidget()
        _ = QVBoxLayout(self.canvas_holder)
        self.canvas = None
        v.addWidget(self.canvas_holder, 1)
        return page

    def _apply_matplotlib_style(self):
        if getattr(self, "is_dark", True):
            plt.style.use("dark_background")
        else:
            plt.style.use("default")

    def _refresh_analytics(self):
        cars = self.db.fetch_all_cars()
        total = len(cars)
        avg_price = (sum(c[4] for c in cars) / total) if total else 0.0
        self.lbl_stats.setText(f"{self.translator.t('total_cars')}: {total}   |   {self.translator.t('average_price')}: {format_price(avg_price, self.translator.lang)}")

        layout = self.canvas_holder.layout()
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        if not cars:
            return
        makes = [c[1] for c in cars]
        counts = Counter(makes)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(list(counts.keys()), list(counts.values()), color="#2563eb" if self.is_dark else "#1d4ed8")
        ax.set_title(self.translator.t("cars_by_make"))
        ax.set_xlabel(self.translator.t("make"))
        ax.set_ylabel(self.translator.t("count"))
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)

    # ---------- Export / Import / Backup ----------
    def export_to_excel(self):
        cars = self.db.fetch_all_cars()
        if not cars:
            QMessageBox.warning(self, self.translator.t("warning"), self.translator.t("no_data_export"))
            return
        fp, _ = QFileDialog.getSaveFileName(self, self.translator.t("export"), filter="Excel files (*.xlsx)")
        if not fp:
            return
        cols = HEADER_KEYS + ["Image Path"]
        df = pd.DataFrame(cars, columns=cols)
        try:
            if not fp.lower().endswith(".xlsx"):
                fp += ".xlsx"
            df.to_excel(fp, index=False)
            QMessageBox.information(self, self.translator.t("success"), self.translator.t("export_success"))
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), f"{self.translator.t('export_fail')}: {e}")

    def import_data(self):
        fp, _ = QFileDialog.getOpenFileName(self, self.translator.t("import_data") if "import_data" in self.translator.translations else "Import Data",
                                            filter="Data files (*.csv *.xlsx)")
        if not fp:
            return
        try:
            if fp.lower().endswith(".csv"):
                df = pd.read_csv(fp)
            else:
                df = pd.read_excel(fp)
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), str(e))
            return

        required = ["make", "model", "year", "price", "color", "type", "condition", "drive_trains", "engine_power", "liter_capacity", "salesperson"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            QMessageBox.warning(self, self.translator.t("warning"), f"Missing columns: {', '.join(missing)}")
            return

        ok, failed = 0, 0
        for _, r in df.iterrows():
            try:
                make = str(r["make"]).strip()
                model = str(r["model"]).strip()
                year = int(r["year"])
                price = float(r["price"])
                color = str(r["color"]).strip()
                car_type = str(r["type"]).strip()
                condition = str(r["condition"]).strip()
                drive = str(r["drive_trains"]).strip()
                engine = int(r["engine_power"])
                liter = int(r["liter_capacity"])
                sales = str(r["salesperson"]).strip()
                if not (make and model and color and sales): raise ValueError("Required fields missing")
                if car_type not in ENUM_TYPES or condition not in ENUM_CONDITIONS or drive not in ENUM_DRIVES:
                    raise ValueError("Invalid enum value")
                if not (1886 <= year <= 2050) or price <= 0 or engine <= 0 or liter <= 0:
                    raise ValueError("Invalid numeric value")
                self.db.insert_car((make, model, year, price, color, car_type, condition, drive, engine, liter, sales, ""))
                ok += 1
            except Exception:
                failed += 1

        self.model.load_data()
        self._update_status()
        QMessageBox.information(self, self.translator.t("success"), f"Imported: {ok}, Failed: {failed}")

    def backup_data(self):
        fp, _ = QFileDialog.getSaveFileName(self, self.translator.t("backup"), "backup.zip", filter="Zip (*.zip)")
        if not fp:
            return
        try:
            if not fp.lower().endswith(".zip"):
                fp += ".zip"
            with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.exists(self.db.db_file):
                    z.write(self.db.db_file, arcname=os.path.basename(self.db.db_file))
                if os.path.exists("car_images"):
                    for root, _, files in os.walk("car_images"):
                        for f in files:
                            p = os.path.join(root, f)
                            z.write(p, arcname=os.path.relpath(p, os.getcwd()))
            Toast(self, "Backup ✓", 1800)
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), str(e))

    def restore_data(self):
        fp, _ = QFileDialog.getOpenFileName(self, self.translator.t("restore"), filter="Zip (*.zip)")
        if not fp:
            return
        if QMessageBox.question(self, self.translator.t("confirm"), self.translator.t("confirm_restore") if "confirm_restore" in self.translator.translations else "Restore will overwrite current data. Continue?") != QMessageBox.Yes:
            return
        try:
            self.db.close()
            with zipfile.ZipFile(fp, "r") as z:
                z.extractall(os.getcwd())
            self.db.reopen()
            self.model.load_data()
            self._update_status()
            Toast(self, "Restore ✓", 1800)
        except Exception as e:
            QMessageBox.critical(self, self.translator.t("error"), str(e))

    # ---------- Theme, QSS & Language ----------
    def _apply_qss(self):
        if self.is_dark:
            self.setStyleSheet("""
            QTableView { gridline-color: #444; selection-background-color:#2563eb; selection-color:#fff; }
            QHeaderView::section { background: #2b2b2b; color: #ffffff; padding: 6px; border: none; font-weight:600; }
            QGroupBox::title { subcontrol-origin: margin; padding: 4px 6px; }
            """)
        else:
            self.setStyleSheet("""
            QTableView { gridline-color: #c9d1d9; selection-background-color:#2563eb; selection-color:#fff; }
            QHeaderView::section { background: #f2f4f7; color: #222; padding: 6px; border: 1px solid #e5e7eb; font-weight:600; }
            QGroupBox::title { subcontrol-origin: margin; padding: 4px 6px; }
            """)

    def _apply_theme(self, dark=True):
        self.is_dark = dark
        app = QApplication.instance()
        app.setStyle("Fusion")
        pal = QPalette()
        if dark:
            pal.setColor(QPalette.Window, QColor(32, 33, 36))
            pal.setColor(QPalette.WindowText, Qt.white)
            pal.setColor(QPalette.Base, QColor(26, 27, 30))
            pal.setColor(QPalette.AlternateBase, QColor(39, 40, 43))
            pal.setColor(QPalette.ToolTipBase, Qt.white)
            pal.setColor(QPalette.ToolTipText, Qt.black)
            pal.setColor(QPalette.Text, Qt.white)
            pal.setColor(QPalette.Button, QColor(45, 46, 50))
            pal.setColor(QPalette.ButtonText, Qt.white)
            pal.setColor(QPalette.Highlight, QColor(37, 99, 235))
            pal.setColor(QPalette.HighlightedText, Qt.white)
            pal.setColor(QPalette.Link, QColor(100, 149, 237))
        else:
            pal.setColor(QPalette.Window, QColor(250, 250, 250))
            pal.setColor(QPalette.WindowText, QColor(33, 37, 41))
            pal.setColor(QPalette.Base, Qt.white)
            pal.setColor(QPalette.AlternateBase, QColor(246, 248, 250))
            pal.setColor(QPalette.ToolTipBase, Qt.white)
            pal.setColor(QPalette.ToolTipText, Qt.black)
            pal.setColor(QPalette.Text, QColor(33, 37, 41))
            pal.setColor(QPalette.Button, QColor(245, 245, 245))
            pal.setColor(QPalette.ButtonText, QColor(33, 37, 41))
            pal.setColor(QPalette.Highlight, QColor(37, 99, 235))
            pal.setColor(QPalette.HighlightedText, Qt.white)
            pal.setColor(QPalette.Link, QColor(33, 150, 243))
        app.setPalette(pal)
        self._apply_qss()

    def toggle_theme(self):
        self._apply_theme(not self.is_dark)
        self._apply_matplotlib_style()
        if self.stack.currentWidget() == self.page_analytics:
            self._refresh_analytics()

    def toggle_language(self):
        self.lang = "ar" if self.lang == "en" else "en"
        self.translator = Translator(self.lang)
        QApplication.setLayoutDirection(Qt.RightToLeft if self.lang == "ar" else Qt.LeftToRight)
        self._update_texts()
        self._set_tooltips()
        self.model.update_translator(self.translator)
        self.model_search.update_translator(self.translator)
        self.model.headerDataChanged.emit(Qt.Horizontal, 0, self.model.columnCount() - 1)
        self.model_search.headerDataChanged.emit(Qt.Horizontal, 0, self.model_search.columnCount() - 1)
        self._on_table_selection()
        if self.stack.currentWidget() == self.page_analytics:
            self._refresh_analytics()
        self._update_status()

    def _update_texts(self):
        self.btn_dashboard.setText(self.translator.t("dashboard"))
        self.btn_add.setText(self.translator.t("add_car"))
        self.btn_search.setText(self.translator.t("search"))
        self.btn_analytics.setText(self.translator.t("analytics") if self.lang == "en" else "التحليلات")
        self.btn_import.setText(self.translator.t("import_data") if "import_data" in self.translator.translations else "Import")
        self.btn_export.setText(self.translator.t("export"))
        self.btn_columns.setText(self.translator.t("columns") if "columns" in self.translator.translations else "Columns")
        self.btn_backup.setText(self.translator.t("backup"))
        self.btn_restore.setText(self.translator.t("restore"))
        self.btn_toggle_theme.setText(self.translator.t("toggle_theme"))
        self.btn_toggle_lang.setText(self.translator.t("toggle_language"))
        self.btn_exit.setText(self.translator.t("exit"))

        self.lb_dash_title.setText(self.translator.t("dashboard"))
        self.lb_search_title.setText(self.translator.t("search"))
        self.lb_analytics_title.setText(self.translator.t("analytics") if self.lang == "en" else "التحليلات")

        for w in self.page_dashboard.findChildren(QGroupBox):
            if w.title():
                w.setTitle(self.translator.t("upload_image"))

        self.ed_quick_filter.setPlaceholderText(self.translator.t("search") + "…")
        self.btn_do_search.setText(self.translator.t("search_btn") if "search_btn" in self.translator.translations else self.translator.t("search"))

    def _set_tooltips(self):
        self.btn_dashboard.setToolTip("Dashboard")
        self.btn_add.setToolTip(f"{self.translator.t('add_car')} (Ctrl+N)")
        self.btn_search.setToolTip(self.translator.t("search"))
        self.btn_analytics.setToolTip(self.translator.t("analytics"))
        self.btn_import.setToolTip(self.translator.t("import_data") if "import_data" in self.translator.translations else "Import data")
        self.btn_export.setToolTip(self.translator.t("export"))
        self.btn_columns.setToolTip(self.translator.t("columns") if "columns" in self.translator.translations else "Columns")
        self.btn_backup.setToolTip(self.translator.t("backup"))
        self.btn_restore.setToolTip(self.translator.t("restore"))
        self.btn_toggle_theme.setToolTip(self.translator.t("toggle_theme"))
        self.btn_toggle_lang.setToolTip(self.translator.t("toggle_language"))
        self.btn_exit.setToolTip(self.translator.t("exit"))
        hint = self.translator.t("drop_image_hint") if "drop_image_hint" in self.translator.translations else "Drop image here to set/update"
        self.lbl_preview_img.setToolTip(hint)

    # ---------- Status ----------
    def _update_status(self):
        rows = self.proxy.rowCount()
        total = self.model.rowCount()
        prices = []
        for r in range(rows):
            idx_src = self.proxy.mapToSource(self.proxy.index(r, 0))
            rec = self.model.get_row(idx_src.row())
            if rec and isinstance(rec[4], (int, float)):
                prices.append(float(rec[4]))
        avg = sum(prices)/len(prices) if prices else 0.0
        med = 0.0
        if prices:
            sp = sorted(prices)
            mid = len(sp)//2
            med = (sp[mid] if len(sp)%2==1 else (sp[mid-1]+sp[mid])/2)
        self.sb_left.setText(f"{self.translator.t('visible') if 'visible' in self.translator.translations else 'Visible'}: {rows} | {self.translator.t('total_cars')}: {total}")
        self.sb_right.setText(f"{self.translator.t('average_price')}: {format_price(avg, self.translator.lang)} | {self.translator.t('median_price') if 'median_price' in self.translator.translations else 'Median'}: {format_price(med, self.translator.lang)}")

    # ---------- State (QSettings) ----------
    def _restore_state(self):
        dark = self.settings.value("dark", True, type=bool)
        lang = self.settings.value("lang", self.lang)
        self._apply_theme(bool(dark))
        if lang != self.lang:
            self.lang = lang
            self.translator = Translator(self.lang)
            QApplication.setLayoutDirection(Qt.RightToLeft if self.lang == "ar" else Qt.LeftToRight)

        g = self.settings.value("geometry")
        if g is not None:
            self.restoreGeometry(g)
        ws = self.settings.value("windowState")
        if ws is not None:
            self.restoreState(ws)

        header_state = self.settings.value("tableHeaderState")
        if header_state is not None:
            self.table.horizontalHeader().restoreState(header_state)

        sizes = self.settings.value("splitterSizes")
        if sizes:
            try:
                sizes = [int(x) for x in sizes]
                self.splitter.setSizes(sizes)
            except Exception:
                pass

        hidden_cols = set(map(str, self.settings.value("hiddenColumns", [], type=list)))
        for i in range(len(HEADER_KEYS)):
            if i == 0: continue
            self.table.setColumnHidden(i, str(i) in hidden_cols)

    def closeEvent(self, event):
        if QMessageBox.question(self, self.translator.t("confirm"), self.translator.t("confirm_exit")) == QMessageBox.Yes:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
            self.settings.setValue("lang", self.lang)
            self.settings.setValue("dark", self.is_dark)
            self.settings.setValue("tableHeaderState", self.table.horizontalHeader().saveState())
            self.settings.setValue("splitterSizes", self.splitter.sizes())
            event.accept()
        else:
            event.ignore()


# --------- Bootstrap JSON translations if missing ---------
def ensure_translations():
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
            "cancel": "Cancel",
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
            "upload_image": "Car Image:",
            "browse": "Browse",
            "select_image": "Select Car Image",
            "confirm_delete": "Are you sure you want to delete the selected car?",
            "select_car_edit": "Please select a car to edit.",
            "select_car_delete": "Please select a car to delete.",
            "delete_permission_denied": "You do not have permission to delete cars.",
            "image_save_fail": "Failed to save the image",
            "analytics": "Analytics",
            "total_cars": "Total Cars",
            "average_price": "Average Price",
            "cars_by_make": "Cars by Make",
            "count": "Count",
            "confirm": "Confirm",
            "copy": "Copy",
            "copy_cell": "Copy Cell",
            "copy_row": "Copy Row",
            "copy_column": "Copy Column",
            "export_row": "Export Row",
            "export_row_csv": "Export Row (CSV)",
            "export_row_excel": "Export Row (Excel)",
            "drop_image_hint": "Drop image here to set/update",
            "image_updated": "Image updated.",
            "gallery": "Gallery",
            "add": "Add",
            "set_as_main": "Set as main",
            "import_data": "Import Data",
            "backup": "Backup",
            "restore": "Restore",
            "export_pdf": "Export PDF",
            "login_title": "Login",
            "username": "Username",
            "password": "Password",
            "login_failed": "Invalid username or password.",
            "visible": "Visible",
            "median_price": "Median",
            "columns": "Columns",
            "confirm_restore": "Restore will overwrite current data. Continue?",
            "duplicate": "Duplicate"
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
            "cancel": "إلغاء",
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
            "upload_image": "صورة السيارة:",
            "browse": "تصفح",
            "select_image": "اختر صورة السيارة",
            "confirm_delete": "هل أنت متأكد من حذف السيارة المحددة؟",
            "select_car_edit": "يرجى اختيار سيارة للتعديل.",
            "select_car_delete": "يرجى اختيار سيارة للحذف.",
            "delete_permission_denied": "ليس لديك صلاحية حذف السيارات.",
            "image_save_fail": "فشل حفظ الصورة",
            "analytics": "التحليلات",
            "total_cars": "إجمالي السيارات",
            "average_price": "متوسط السعر",
            "cars_by_make": "السيارات حسب الماركة",
            "count": "العدد",
            "confirm": "تأكيد",
            "copy": "نسخ",
            "copy_cell": "نسخ الخلية",
            "copy_row": "نسخ الصف",
            "copy_column": "نسخ العمود",
            "export_row": "تصدير الصف",
            "export_row_csv": "تصدير الصف (CSV)",
            "export_row_excel": "تصدير الصف (Excel)",
            "drop_image_hint": "اسحب وأفلِت صورة هنا للتعيين/التحديث",
            "image_updated": "تم تحديث الصورة.",
            "gallery": "المعرض",
            "add": "إضافة",
            "set_as_main": "تعيين كرئيسية",
            "import_data": "استيراد بيانات",
            "backup": "نسخ احتياطي",
            "restore": "استرجاع",
            "export_pdf": "تصدير PDF",
            "login_title": "تسجيل الدخول",
            "username": "اسم المستخدم",
            "password": "كلمة المرور",
            "login_failed": "اسم المستخدم أو كلمة المرور غير صحيحة.",
            "visible": "الظاهر",
            "median_price": "الميديان",
            "columns": "الأعمدة",
            "confirm_restore": "الاسترجاع سيستبدل البيانات الحالية. هل تريد المتابعة؟",
            "duplicate": "تكرار"
        }
        with open("ar.json", "w", encoding="utf-8") as f:
            json.dump(ar_content, f, indent=4)


def main():
    ensure_translations()
    app = QApplication(sys.argv)
    # Login
    translator = Translator("en")
    login = LoginDialog(translator)
    if login.exec() != QDialog.Accepted:
        sys.exit(0)
    win = MainWindow(current_user=login.username, current_role=login.role, lang="en")
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()