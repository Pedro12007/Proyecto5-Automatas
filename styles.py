"""Tokens de DESIGN.md ("Status" — encrypted vault / dark security console) y hoja de estilos QSS global."""
from __future__ import annotations

# --- Tokens de color (DESIGN.md) -------------------------------------------------
MIDNIGHT_INK = "#09101c"   # canvas principal
SLATE_DEPTH = "#131d2f"    # superficie elevada / tarjetas
STEEL_EDGE = "#1b273d"     # bordes
GRAPHITE_PLATE = "#3a4049"
SLATE_MIST = "#647084"     # texto secundario / helper
ASH_LIGHT = "#a1abbd"      # texto terciario / nav inactivo
PALE_MIST = "#dce0e5"
CLOUD = "#f0f2f5"
PAPER = "#ffffff"
SIGNAL_BLUE = "#2a4af5"    # única acción rellena
STATUS_VIOLET = "#7140fd"  # acento de marca

# --- Colores semánticos (no definidos en DESIGN.md; usados solo para estados) ----
SUCCESS = "#2fbf71"
SUCCESS_TEXT = "#6fe3a3"
DANGER = "#ef4b5b"
DANGER_TEXT = "#ff8f9b"
WARNING = "#f0b429"
WARNING_TEXT = "#f6cd6b"
SELECTION = "#1a2a63"
BLUE_HOVER = "#4562ff"
BLUE_PRESSED = "#2139c4"

# --- Geometría ------------------------------------------------------------------
RADIUS_CARD = 20
RADIUS_CONTROL = 12
RADIUS_PILL = 12  # con altura fija de 24 px produce forma de píldora

FONT_STACK = '"Inter", "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif'


def build_stylesheet() -> str:
    qss = """
QMainWindow, QDialog, QMessageBox, QFileDialog { background: @MIDNIGHT_INK@; }
QWidget { color: @PAPER@; font-family: @FONT@; font-size: 14px; }
QWidget#Root { background: @MIDNIGHT_INK@; }
QLabel { background: transparent; }
QToolTip { background: @SLATE_DEPTH@; color: @PALE_MIST@; border: 1px solid @STEEL_EDGE@; padding: 6px 8px; }

/* ---------- Tipografía ---------- */
QLabel#PageTitle { font-size: 26px; font-weight: 600; color: @PAPER@; }
QLabel#PageSubtitle { font-size: 14px; color: @SLATE_MIST@; }
QLabel#CardTitle { font-size: 17px; font-weight: 600; color: @PAPER@; }
QLabel#CardSubtitle { font-size: 13px; color: @SLATE_MIST@; }
QLabel#FieldLabel { font-size: 12px; color: @SLATE_MIST@; font-weight: 500; }
QLabel#FieldValue { font-size: 15px; color: @PAPER@; font-weight: 500; }
QLabel#FieldValueMuted { font-size: 15px; color: @SLATE_MIST@; }
QLabel#Helper { font-size: 13px; color: @SLATE_MIST@; }
QLabel#Brand { font-size: 17px; font-weight: 700; color: @PAPER@; }
QLabel#BrandSub { font-size: 12px; color: @SLATE_MIST@; }
QLabel#TrackTitle { font-size: 11px; font-weight: 600; color: @SLATE_MIST@; }
QLabel#StatValue { font-size: 30px; font-weight: 600; color: @PAPER@; }
QLabel#StatLabel { font-size: 12px; color: @SLATE_MIST@; }
QLabel#Accent { color: @STATUS_VIOLET@; font-weight: 500; }

/* ---------- Sidebar ---------- */
QFrame#Sidebar { background: @MIDNIGHT_INK@; border: none; border-right: 1px solid @STEEL_EDGE@; }
QFrame#TopBar { background: @MIDNIGHT_INK@; border: none; border-bottom: 1px solid @STEEL_EDGE@; }
QPushButton#NavButton {
    background: transparent; color: @ASH_LIGHT@; border: 1px solid transparent;
    border-radius: @R_CTRL@px; padding: 11px 14px; text-align: left; font-size: 14px; font-weight: 500;
}
QPushButton#NavButton:hover { background: @SLATE_DEPTH@; color: @PAPER@; }
QPushButton#NavButton:checked { background: @SLATE_DEPTH@; color: @PAPER@; border: 1px solid @STEEL_EDGE@; }
QPushButton#NavButton:disabled { color: @GRAPHITE_PLATE@; }

/* ---------- Tarjetas ---------- */
QFrame#Card { background: @SLATE_DEPTH@; border: 1px solid @STEEL_EDGE@; border-radius: @R_CARD@px; }
QFrame#Card[accent="success"] { border: 1px solid @SUCCESS@; }
QFrame#Card[accent="danger"] { border: 1px solid @DANGER@; }
QFrame#Divider { background: @STEEL_EDGE@; border: none; max-height: 1px; min-height: 1px; }

/* ---------- Banners ---------- */
QFrame#Banner { border-radius: @R_CTRL@px; border: 1px solid @STEEL_EDGE@; background: @SLATE_DEPTH@; }
QFrame#Banner[tone="info"] { background: #101c3f; border: 1px solid @SIGNAL_BLUE@; }
QFrame#Banner[tone="success"] { background: #0f2a22; border: 1px solid @SUCCESS@; }
QFrame#Banner[tone="danger"] { background: #2d1219; border: 1px solid @DANGER@; }
QFrame#Banner[tone="warn"] { background: #2b2210; border: 1px solid @WARNING@; }
QLabel#BannerTitle { font-size: 15px; font-weight: 600; }
QLabel#BannerText { font-size: 13px; color: @PALE_MIST@; }

/* ---------- Botones ---------- */
QPushButton { font-family: @FONT@; font-size: 15px; font-weight: 500; border-radius: @R_CTRL@px; padding: 11px 22px; }
QPushButton[variant="primary"] { background: @SIGNAL_BLUE@; color: @PAPER@; border: 1px solid @SIGNAL_BLUE@; }
QPushButton[variant="primary"]:hover { background: @BLUE_HOVER@; border-color: @BLUE_HOVER@; }
QPushButton[variant="primary"]:pressed { background: @BLUE_PRESSED@; border-color: @BLUE_PRESSED@; }
QPushButton[variant="primary"]:disabled { background: @SLATE_DEPTH@; color: @SLATE_MIST@; border: 1px solid @STEEL_EDGE@; }
QPushButton[variant="ghost"] { background: transparent; color: @PALE_MIST@; border: 1px solid @STEEL_EDGE@; }
QPushButton[variant="ghost"]:hover { background: @MIDNIGHT_INK@; border-color: @SLATE_MIST@; color: @PAPER@; }
QPushButton[variant="ghost"]:pressed { background: @STEEL_EDGE@; }
QPushButton[variant="ghost"]:disabled { color: @GRAPHITE_PLATE@; border-color: @STEEL_EDGE@; }

/* ---------- Entradas ---------- */
QLineEdit, QComboBox {
    background: @MIDNIGHT_INK@; color: @PAPER@; border: 1px solid @STEEL_EDGE@;
    border-radius: @R_CTRL@px; padding: 11px 14px; font-size: 15px; selection-background-color: @SIGNAL_BLUE@;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid @SIGNAL_BLUE@; }
QLineEdit::placeholder { color: @SLATE_MIST@; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background: @SLATE_DEPTH@; color: @PAPER@; border: 1px solid @STEEL_EDGE@;
    selection-background-color: @SELECTION@; outline: none; padding: 4px;
}

/* ---------- Pills / badges de estado ---------- */
QLabel#Pill {
    border-radius: @R_PILL@px; padding: 0px 12px; font-size: 12px; font-weight: 600;
    border: 1px solid @STEEL_EDGE@; color: @SLATE_MIST@; background: transparent;
}
QLabel#Pill[tone="active"] { background: @SIGNAL_BLUE@; border: 1px solid @SIGNAL_BLUE@; color: @PAPER@; }
QLabel#Pill[tone="violet"] { background: #26185a; border: 1px solid @STATUS_VIOLET@; color: #c3b0ff; }
QLabel#Pill[tone="success"] { background: #0f2a22; border: 1px solid @SUCCESS@; color: @SUCCESS_TEXT@; }
QLabel#Pill[tone="danger"] { background: #2d1219; border: 1px solid @DANGER@; color: @DANGER_TEXT@; }
QLabel#Pill[tone="warn"] { background: #2b2210; border: 1px solid @WARNING@; color: @WARNING_TEXT@; }
QLabel#Tag { border-radius: 9px; padding: 2px 10px; font-size: 12px; font-weight: 500; border: 1px solid @STEEL_EDGE@; color: @ASH_LIGHT@; }

/* ---------- Tablas ---------- */
QTableWidget {
    background: transparent; alternate-background-color: #0f1828; border: 1px solid @STEEL_EDGE@;
    border-radius: @R_CTRL@px; gridline-color: transparent; color: @PALE_MIST@; outline: none;
    selection-background-color: @SELECTION@; selection-color: @PAPER@;
}
QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid @STEEL_EDGE@; }
QTableWidget::item:selected { background: @SELECTION@; color: @PAPER@; }
QHeaderView { background: transparent; }
QHeaderView::section {
    background: @MIDNIGHT_INK@; color: @SLATE_MIST@; border: none; border-bottom: 1px solid @STEEL_EDGE@;
    padding: 10px; font-size: 12px; font-weight: 600;
}
QTableCornerButton::section { background: @MIDNIGHT_INK@; border: none; }

/* ---------- Scrollbars ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: @STEEL_EDGE@; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: @SLATE_MIST@; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: @STEEL_EDGE@; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: @SLATE_MIST@; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollArea { background: transparent; border: none; }

/* ---------- Diálogos ---------- */
QMessageBox QLabel { color: @PALE_MIST@; }
QMessageBox QPushButton { background: transparent; color: @PALE_MIST@; border: 1px solid @STEEL_EDGE@; min-width: 80px; padding: 8px 16px; }
QMessageBox QPushButton:hover { border-color: @SLATE_MIST@; }
QMessageBox QPushButton:default { background: @SIGNAL_BLUE@; border-color: @SIGNAL_BLUE@; color: @PAPER@; }
"""
    tokens = {
        "MIDNIGHT_INK": MIDNIGHT_INK, "SLATE_DEPTH": SLATE_DEPTH, "STEEL_EDGE": STEEL_EDGE,
        "GRAPHITE_PLATE": GRAPHITE_PLATE, "SLATE_MIST": SLATE_MIST, "ASH_LIGHT": ASH_LIGHT,
        "PALE_MIST": PALE_MIST, "PAPER": PAPER, "SIGNAL_BLUE": SIGNAL_BLUE, "STATUS_VIOLET": STATUS_VIOLET,
        "SUCCESS": SUCCESS, "SUCCESS_TEXT": SUCCESS_TEXT, "DANGER": DANGER, "DANGER_TEXT": DANGER_TEXT,
        "WARNING": WARNING, "WARNING_TEXT": WARNING_TEXT, "SELECTION": SELECTION,
        "BLUE_HOVER": BLUE_HOVER, "BLUE_PRESSED": BLUE_PRESSED, "FONT": FONT_STACK,
        "R_CARD": str(RADIUS_CARD), "R_CTRL": str(RADIUS_CONTROL), "R_PILL": str(RADIUS_PILL),
    }
    for key in sorted(tokens, key=len, reverse=True):
        qss = qss.replace(f"@{key}@", tokens[key])
    return qss
