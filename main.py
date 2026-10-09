from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

import styles
from data_manager import DataManager, DataSourceError
from main_window import MainWindow


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(styles.MIDNIGHT_INK))
    p.setColor(QPalette.ColorRole.WindowText, QColor(styles.PAPER))
    p.setColor(QPalette.ColorRole.Base, QColor(styles.MIDNIGHT_INK))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(styles.SLATE_DEPTH))
    p.setColor(QPalette.ColorRole.Text, QColor(styles.PAPER))
    p.setColor(QPalette.ColorRole.Button, QColor(styles.SLATE_DEPTH))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(styles.PAPER))
    p.setColor(QPalette.ColorRole.Highlight, QColor(styles.SIGNAL_BLUE))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(styles.PAPER))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(styles.SLATE_MIST))
    return p


def _load_data(parent: QApplication) -> DataManager:
    base = Path(sys.argv[0]).resolve().parent
    dm = DataManager(base_dir=base)
    labels = {"tesoreria": "Reporte de Tesorería (.xlsx)", "participantes": "Listado oficial de participantes (.xlsx)"}
    for _ in range(2):
        missing = dm.sources_missing()
        if not missing:
            break
        for key in missing:
            QMessageBox.information(None, "Archivo requerido", f"No se encontró el archivo:\n{labels[key]}\n\nSeleccione su ubicación.")
            path, _ = QFileDialog.getOpenFileName(None, labels[key], str(base), "Excel (*.xlsx)")
            if not path:
                sys.exit(1)
            setattr(dm, f"{key}_path", Path(path))
    dm.load_sources()
    return dm


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    font = QFont("Inter")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(styles.build_stylesheet())
    try:
        dm = _load_data(app)
    except (DataSourceError, FileNotFoundError) as exc:
        QMessageBox.critical(None, "Error al iniciar", str(exc))
        return 1
    window = MainWindow(dm)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
