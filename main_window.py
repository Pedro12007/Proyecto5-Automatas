"""Ventana principal: conecta AFND (búsqueda), AFD (pago/asistencia), DataManager y las vistas."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
                             QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import styles
from afd import AFD
from afnd import AFND
from data_manager import (Candidate, DataManager, DataSourceError, Participant, Payment,
                          REGISTRO_COLUMNS, normalize_text)
from widgets import (Banner, Card, DataPanel, StatCard, afd_track, afnd_track, make_button, make_tag,
                     repolish)

# Índices de las vistas
PAGE_SEARCH, PAGE_CONFIRM, PAGE_RECORDS = 0, 1, 2
# Subvistas del módulo de búsqueda
SUB_INTRO, SUB_CANDIDATES, SUB_MANUAL = 0, 1, 2


def _page_header(title: str, subtitle: str) -> QVBoxLayout:
    lay = QVBoxLayout()
    lay.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSubtitle")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return lay


def _money(value: float) -> str:
    return f"Q {value:,.2f}"


class MainWindow(QMainWindow):
    def __init__(self, data: DataManager) -> None:
        super().__init__()
        self.dm = data
        self.afnd = AFND()
        self.afd = AFD()
        self.candidates: list[Candidate] = []
        self.current_participant: Optional[Participant] = None
        self.current_payment: Optional[Payment] = None
        self._registry_mtime = self.dm.registry_mtime()

        self.setWindowTitle("Simposio de Ingeniería · Control de Asistencia y Tickets")
        self.resize(1320, 840)
        self.setMinimumSize(1120, 720)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setSpacing(0)
        right.addWidget(self._build_topbar())
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_search_page())
        self.pages.addWidget(self._build_confirm_page())
        self.pages.addWidget(self._build_records_page())
        right.addWidget(self.pages, 1)
        outer.addLayout(right, 1)

        self._reset_automata()
        self._go(PAGE_SEARCH)
        self.refresh_records()

        self._watch = QTimer(self)
        self._watch.setInterval(4000)
        self._watch.timeout.connect(self._poll_registry)
        self._watch.start()

    # ================================================================== #
    # Construcción de UI
    # ================================================================== #
    def _build_sidebar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(250)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(18, 24, 18, 20)
        lay.setSpacing(6)


        sub = QLabel("Validación de pagos y asistencia")
        sub.setObjectName("BrandSub")
  
        lay.addWidget(sub)
        lay.addSpacing(22)

        self.nav_buttons: list[QPushButton] = []
        for idx, text in enumerate(["⌕   Búsqueda", "✓   Confirmación", "▤   Registros"]):
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=idx: self._go(i))
            lay.addWidget(b)
            self.nav_buttons.append(b)
        lay.addStretch(1)

        st = self.dm.stats()
        info = QLabel(f"{st['participantes']} participantes oficiales\n{st['pagos']} pagos en Tesorería\n"
                      f"{st['vinculados']} cruces automáticos")
        info.setObjectName("Helper")
        lay.addWidget(info)
        return bar

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(32, 14, 32, 14)
        lay.setSpacing(40)
        self.afnd_view = afnd_track()
        self.afd_view = afd_track()
        lay.addWidget(self.afnd_view)
        lay.addWidget(self.afd_view)
        lay.addStretch(1)
        return bar

    # ---------------------------- Módulo 1 ---------------------------- #
    def _build_search_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)
        lay.addLayout(_page_header(
            "Búsqueda e identificación",
            "Ingrese el nombre, el carné o el número de recibo. El AFND resuelve coincidencias únicas, múltiples o inexistentes."))

        card = Card()
        row = QHBoxLayout()
        row.setSpacing(12)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre del estudiante, carné (2026-0001) o No. de recibo…")
        self.search_input.returnPressed.connect(self.on_search)
        self.search_input.setClearButtonEnabled(True)
        btn = make_button("Buscar", "primary", pill=True)
        btn.clicked.connect(self.on_search)
        row.addWidget(self.search_input, 1)
        row.addWidget(btn)
        card.body.addLayout(row)
        self.search_helper = QLabel("El texto se normaliza automáticamente: mayúsculas, sin tildes y sin espacios sobrantes.")
        self.search_helper.setObjectName("Helper")
        card.body.addWidget(self.search_helper)
        lay.addWidget(card)

        self.sub = QStackedWidget()
        self.sub.addWidget(self._build_intro())
        self.sub.addWidget(self._build_candidates())
        self.sub.addWidget(self._build_manual())
        lay.addWidget(self.sub, 1)
        return page

    def _build_intro(self) -> QWidget:
        card = Card("Cómo funciona", "Resultados posibles de la búsqueda")
        grid = QGridLayout()
        grid.setSpacing(12)
        items = [("E", "qM", "Coincidencia exacta: pasa directo a la confirmación."),
                 ("P", "qC", "Varios candidatos: elija al estudiante correcto en la tabla."),
                 ("X", "qR", "Sin coincidencias: vincule carné y recibo manualmente.")]
        for i, (sym, state, desc) in enumerate(items):
            grid.addWidget(make_tag(f"{sym} → {state}", styles.STATUS_VIOLET), i, 0)
            d = QLabel(desc)
            d.setObjectName("Helper")
            grid.addWidget(d, i, 1)
        grid.setColumnStretch(1, 1)
        card.body.addLayout(grid)
        card.body.addStretch(1)
        return card

    def _build_candidates(self) -> QWidget:
        card = Card("Candidatos posibles", "Se encontró más de una coincidencia. Seleccione al estudiante (doble clic o botón).")
        self.cand_table = QTableWidget(0, 6)
        self.cand_table.setHorizontalHeaderLabels(["CARNÉ", "NOMBRE OFICIAL", "NOMBRE EN RECIBO", "RECIBO", "MONTO", "ESTADO"])
        self._style_table(self.cand_table)
        hh = self.cand_table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cand_table.doubleClicked.connect(lambda _idx: self.on_select_candidate())
        card.body.addWidget(self.cand_table, 1)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.cand_count = QLabel("")
        self.cand_count.setObjectName("Helper")
        row.addWidget(self.cand_count, 1)
        none = make_button("Ninguno coincide", "ghost")
        none.clicked.connect(self.on_none_matches)
        pick = make_button("Seleccionar candidato", "primary")
        pick.clicked.connect(self.on_select_candidate)
        row.addWidget(none)
        row.addWidget(pick)
        card.body.addLayout(row)
        return card

    def _build_manual(self) -> QWidget:
        card = Card("Vinculación manual (qR)",
                    "No hay un match automático. Ingrese el carné del estudiante y el número de recibo de Tesorería para vincularlos.")
        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        l1, l2 = QLabel("CARNÉ"), QLabel("NO. DE RECIBO")
        l1.setObjectName("FieldLabel")
        l2.setObjectName("FieldLabel")
        self.manual_carnet = QLineEdit()
        self.manual_carnet.setPlaceholderText("2026-0001")
        self.manual_receipt = QLineEdit()
        self.manual_receipt.setPlaceholderText("25041654")
        self.manual_carnet_info = QLabel("")
        self.manual_receipt_info = QLabel("")
        for lab in (self.manual_carnet_info, self.manual_receipt_info):
            lab.setObjectName("Helper")
            lab.setWordWrap(True)
        form.addWidget(l1, 0, 0)
        form.addWidget(l2, 0, 1)
        form.addWidget(self.manual_carnet, 1, 0)
        form.addWidget(self.manual_receipt, 1, 1)
        form.addWidget(self.manual_carnet_info, 2, 0)
        form.addWidget(self.manual_receipt_info, 2, 1)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        card.body.addLayout(form)
        self.manual_banner = Banner()
        card.body.addWidget(self.manual_banner)
        card.body.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addStretch(1)
        cancel = make_button("Cancelar", "ghost")
        cancel.clicked.connect(self.on_cancel_manual)
        link = make_button("Vincular y continuar", "primary")
        link.clicked.connect(self.on_manual_link)
        row.addWidget(cancel)
        row.addWidget(link)
        card.body.addLayout(row)
        self.manual_carnet.textChanged.connect(self._refresh_manual_preview)
        self.manual_receipt.textChanged.connect(self._refresh_manual_preview)
        self.manual_carnet.returnPressed.connect(self.on_manual_link)
        self.manual_receipt.returnPressed.connect(self.on_manual_link)
        return card

    # ---------------------------- Módulo 2 ---------------------------- #
    def _build_confirm_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)
        lay.addLayout(_page_header("Confirmación detallada",
                                   "Compare los datos oficiales con el comprobante de Tesorería antes de registrar la asistencia."))
        panels = QHBoxLayout()
        panels.setSpacing(18)
        self.panel_official = DataPanel("Datos oficiales del estudiante", "Listado oficial de participantes",
                                        ["Carné", "Nombre oficial", "Correo"])
        self.panel_payment = DataPanel("Datos de pago · Tesorería", "Reporte de Tesorería",
                                       ["No. de recibo", "Nombre en recibo", "Monto", "Fecha de pago", "Concepto"])
        panels.addWidget(self.panel_official, 1)
        panels.addWidget(self.panel_payment, 1)
        lay.addLayout(panels)
        self.confirm_banner = Banner()
        lay.addWidget(self.confirm_banner)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.btn_new = make_button("Nueva búsqueda", "ghost")
        self.btn_new.clicked.connect(self.on_new_search)
        self.btn_relink = make_button("Vincular pago manualmente", "ghost")
        self.btn_relink.clicked.connect(self.on_relink)
        self.btn_confirm = make_button("Confirmar Asistencia y Entregar Ticket", "primary", pill=True)
        self.btn_confirm.clicked.connect(self.on_confirm)
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_relink)
        row.addStretch(1)
        row.addWidget(self.btn_confirm)
        lay.addLayout(row)
        return page

    # ---------------------------- Módulo 3 ---------------------------- #
    def _build_records_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)
        lay.addLayout(_page_header("Registros y reporte",
                                   "Contenido en vivo de REGISTRO_Y_ASISTENCIA_SIMPOSIO.xlsx (se actualiza automáticamente)."))
        stats = QHBoxLayout()
        stats.setSpacing(16)
        self.stat_total = StatCard("Registros")
        self.stat_att = StatCard("Asistencias confirmadas")
        self.stat_tix = StatCard("Tickets entregados")
        self.stat_pending = StatCard("Pendientes (oficiales)")
        for s in (self.stat_total, self.stat_att, self.stat_tix, self.stat_pending):
            stats.addWidget(s)
        lay.addLayout(stats)

        card = Card()
        tools = QHBoxLayout()
        tools.setSpacing(12)
        self.rec_search = QLineEdit()
        self.rec_search.setPlaceholderText("Filtrar por carné, nombre, correo o recibo…")
        self.rec_search.setClearButtonEnabled(True)
        self.rec_search.textChanged.connect(self._apply_records_filter)
        self.rec_filter = QComboBox()
        self.rec_filter.addItems(["Todos los registros", "Asistencia confirmada", "Sin confirmar"])
        self.rec_filter.currentIndexChanged.connect(self._apply_records_filter)
        self.rec_filter.setMinimumWidth(210)
        refresh = make_button("Actualizar", "ghost")
        refresh.clicked.connect(self.refresh_records)
        export = make_button("Exportar", "primary")
        export.clicked.connect(self.on_export)
        tools.addWidget(self.rec_search, 1)
        tools.addWidget(self.rec_filter)
        tools.addWidget(refresh)
        tools.addWidget(export)
        card.body.addLayout(tools)

        self.rec_table = QTableWidget(0, len(REGISTRO_COLUMNS))
        self.rec_table.setHorizontalHeaderLabels([c.upper() for c in REGISTRO_COLUMNS])
        self._style_table(self.rec_table)
        self.rec_table.setSortingEnabled(True)
        hh = self.rec_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        card.body.addWidget(self.rec_table, 1)
        self.rec_footer = QLabel("")
        self.rec_footer.setObjectName("Helper")
        card.body.addWidget(self.rec_footer)
        lay.addWidget(card, 1)
        self._registry_df = pd.DataFrame(columns=REGISTRO_COLUMNS)
        return page

    @staticmethod
    def _style_table(table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ================================================================== #
    # Navegación y autómatas
    # ================================================================== #
    def _go(self, index: int) -> None:
        if index == PAGE_CONFIRM and self.current_participant is None and self.current_payment is None:
            index = PAGE_SEARCH
        self.pages.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)
        self.nav_buttons[PAGE_CONFIRM].setEnabled(self.current_participant is not None)
        if index == PAGE_RECORDS:
            self.refresh_records()
        elif index == PAGE_SEARCH:
            self.search_input.setFocus()

    def _sync_tracks(self) -> None:
        self.afnd_view.set_state(self.afnd.obtener_estado())
        self.afd_view.set_state(self.afd.obtener_estado())

    def _reset_automata(self) -> None:
        self.afnd.reiniciar()
        self.afd.reiniciar()
        self._sync_tracks()

    def _afnd_event(self, symbol: str) -> bool:
        result = self.afnd.procesar_evento(symbol)
        self._sync_tracks()
        return result is not None

    # ================================================================== #
    # Módulo 1: búsqueda
    # ================================================================== #
    def on_search(self) -> None:
        raw = self.search_input.text()
        norm = normalize_text(raw)
        if not norm:
            self.search_helper.setText("Escriba un nombre, carné o número de recibo para buscar.")
            return
        self.search_helper.setText(f"Búsqueda normalizada: “{norm}”")
        self.current_participant = None
        self.current_payment = None
        self._reset_automata()
        try:
            self.candidates = self.dm.search(raw)
        except DataSourceError as exc:
            QMessageBox.critical(self, "Error de datos", str(exc))
            return

        if len(self.candidates) == 1:
            cand = self.candidates[0]
            if cand.participant is not None:
                self._afnd_event("E")                     # q0 -E-> qM
                self._open_confirmation(cand.participant, cand.payment)
            else:
                # Pago sin carné oficial: no es un match completo → revisión manual
                self._afnd_event("X")                     # q0 -X-> qR
                self._open_manual(prefill_receipt=cand.payment.recibo if cand.payment else "",
                                  note="Se encontró el pago en Tesorería pero no un estudiante oficial asociado. "
                                       "Ingrese el carné para vincularlos.")
        elif len(self.candidates) > 1:
            self._afnd_event("P")                         # q0 -P-> qC
            self._fill_candidates()
            self.sub.setCurrentIndex(SUB_CANDIDATES)
            self._go(PAGE_SEARCH)
        else:
            self._afnd_event("X")                         # q0 -X-> qR
            self._open_manual(note="Sin coincidencias para esta búsqueda. Verifique el carné y el recibo del estudiante.")

    def _fill_candidates(self) -> None:
        t = self.cand_table
        t.setRowCount(len(self.candidates))
        for r, c in enumerate(self.candidates):
            p, pay = c.participant, c.payment
            cells = [p.carnet if p else "—", p.nombre if p else "—", pay.nombre if pay else "—",
                     pay.recibo if pay else "—", _money(pay.monto) if pay else "—", c.status_label]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 5:
                    color = {"Ya registrado": styles.WARNING_TEXT, "Pago encontrado": styles.SUCCESS_TEXT,
                             "Sin pago asociado": styles.DANGER_TEXT}.get(text, styles.ASH_LIGHT)
                    item.setForeground(Qt.GlobalColor.white)
                    from PyQt6.QtGui import QColor
                    item.setForeground(QColor(color))
                t.setItem(r, col, item)
        t.resizeColumnToContents(0)
        t.resizeColumnToContents(3)
        t.resizeColumnToContents(4)
        t.resizeColumnToContents(5)
        t.selectRow(0)
        self.cand_count.setText(f"{len(self.candidates)} coincidencias · AFND en qC (no determinismo)")

    def on_select_candidate(self) -> None:
        row = self.cand_table.currentRow()
        if row < 0 or row >= len(self.candidates):
            QMessageBox.information(self, "Seleccione un candidato", "Elija una fila de la tabla para continuar.")
            return
        cand = self.candidates[row]
        if cand.participant is not None and self._afnd_event("S"):    # qC -S-> qM
            self._open_confirmation(cand.participant, cand.payment)
        else:
            self._afnd_event("X")                                      # qC -X-> qR
            self._open_manual(prefill_receipt=cand.payment.recibo if cand.payment else "",
                              note="El candidato elegido no tiene estudiante oficial asociado. Ingrese su carné.")

    def on_none_matches(self) -> None:
        self._afnd_event("X")                                          # qC -X-> qR
        self._open_manual(note="Ningún candidato fue aceptado. Vincule manualmente con carné y recibo.")

    # ---- qR: formulario manual ---- #
    def _open_manual(self, prefill_carnet: str = "", prefill_receipt: str = "", note: str = "") -> None:
        self.manual_carnet.setText(prefill_carnet)
        self.manual_receipt.setText(prefill_receipt)
        self.manual_banner.hide()
        if note:
            self.manual_banner.show_message("warn", "Revisión manual requerida", note)
        self._refresh_manual_preview()
        self.sub.setCurrentIndex(SUB_MANUAL)
        self._go(PAGE_SEARCH)
        (self.manual_receipt if prefill_carnet else self.manual_carnet).setFocus()

    def _refresh_manual_preview(self) -> None:
        c_txt, r_txt = self.manual_carnet.text().strip(), self.manual_receipt.text().strip()
        part = self.dm.lookup_carnet(c_txt) if c_txt else None
        pay = self.dm.lookup_receipt(r_txt) if r_txt else None
        self.manual_carnet_info.setText("" if not c_txt else (f"✓ {part.nombre}" if part else "✗ Carné no encontrado en el listado oficial"))
        self.manual_receipt_info.setText("" if not r_txt else (f"✓ {pay.nombre} · {_money(pay.monto)}" if pay else "✗ Recibo no encontrado en Tesorería"))
        self.manual_carnet_info.setStyleSheet(f"color: {styles.SUCCESS_TEXT if part else styles.DANGER_TEXT};")
        self.manual_receipt_info.setStyleSheet(f"color: {styles.SUCCESS_TEXT if pay else styles.DANGER_TEXT};")

    def on_manual_link(self) -> None:
        part = self.dm.lookup_carnet(self.manual_carnet.text())
        pay = self.dm.lookup_receipt(self.manual_receipt.text())
        if part is None:
            self.manual_banner.show_message("danger", "Carné inválido", "El carné no existe en el listado oficial de participantes.")
            return
        if pay is None:
            self.manual_banner.show_message("danger", "Recibo inválido", "El número de recibo no existe en el reporte de Tesorería.")
            return
        if not self._afnd_event("S"):                                  # qR -S-> qM
            self.manual_banner.show_message("danger", "Transición no permitida", "El AFND no admite esta operación en el estado actual.")
            return
        self._open_confirmation(part, pay)

    def on_cancel_manual(self) -> None:
        self.sub.setCurrentIndex(SUB_INTRO)
        self._reset_automata()
        self.search_input.setFocus()

    # ================================================================== #
    # Módulo 2: confirmación
    # ================================================================== #
    def _open_confirmation(self, participant: Participant, payment: Optional[Payment]) -> None:
        self.current_participant, self.current_payment = participant, payment
        self.afd.reiniciar()                                           # q0: identidad confirmada
        self.panel_official.set_data({"Carné": participant.carnet, "Nombre oficial": participant.nombre,
                                      "Correo": participant.correo})
        self.panel_official.set_accent("")
        self.panel_payment.set_accent("")
        if payment is not None:
            self.panel_payment.set_data({"No. de recibo": payment.recibo, "Nombre en recibo": payment.nombre,
                                         "Monto": _money(payment.monto), "Fecha de pago": payment.fecha,
                                         "Concepto": payment.concepto})
        else:
            self.panel_payment.set_data(None, "No se encontró un pago asociado a este estudiante en Tesorería.")

        self.btn_relink.setVisible(False)
        self.btn_confirm.setVisible(True)
        alert: Optional[str] = None
        try:
            conflict = self.dm.registry_conflict(participant, payment) if payment else None
        except DataSourceError as exc:
            conflict, alert = None, str(exc)

        if alert:
            self.afd.transicion("e")
            self.confirm_banner.show_message("danger", "No se pudo consultar el registro", alert)
        elif payment is None:
            self.afd.transicion("e")                                   # inconsistencia: sin pago
            self.panel_payment.set_accent("danger")
            self.btn_relink.setVisible(True)
            self.confirm_banner.show_message("danger", "Pago no encontrado",
                                             "El estudiante no tiene un recibo vinculado. Use la vinculación manual si cuenta con el número de recibo.")
        elif conflict:
            self.afd.transicion("e")                                   # duplicidad
            self.panel_official.set_accent("danger")
            self.panel_payment.set_accent("danger")
            self.confirm_banner.show_message("danger", "Estudiante ya registrado" if "ya fueron" in conflict else "Recibo duplicado", conflict)
            QMessageBox.warning(self, "Registro duplicado", conflict)
        else:
            self.afd.transicion("v")                                   # q0 -v-> q1: pago validado
            self.panel_payment.set_accent("success")
            hint = ""
            if participant.nombre_norm != payment.nombre_norm:
                hint = " Los nombres difieren en forma (p. ej. nombre completo o abreviado): verifique visualmente."
            self.confirm_banner.show_message("info", "Pago validado en Tesorería",
                                             "Todo listo para registrar la asistencia y entregar el ticket." + hint)
        self.btn_confirm.setEnabled(self.afd.obtener_estado() == 1)
        self._sync_tracks()
        self._go(PAGE_CONFIRM)

    def on_confirm(self) -> None:
        part, pay = self.current_participant, self.current_payment
        if part is None or pay is None or self.afd.obtener_estado() != 1:
            return
        self.afd.transicion("a")                                       # q1 -a-> q2
        self._sync_tracks()
        if not self.afd.es_aceptado():
            self.confirm_banner.show_message("danger", "Operación rechazada", "El AFD cayó en el estado trampa qE.")
            self.btn_confirm.setEnabled(False)
            return
        try:
            stamp = self.dm.register_attendance(part, pay, estado_afd=self.afd.obtener_estado())
        except DataSourceError as exc:
            self.afd.estado_actual = 1                                 # no se registró: volver a q1
            self._sync_tracks()
            self.confirm_banner.show_message("danger", "No se pudo guardar el registro", str(exc))
            return
        self.btn_confirm.setEnabled(False)
        self.panel_official.set_accent("success")
        self.confirm_banner.show_message("success", "Asistencia Confirmada y Ticket Entregado",
                                         f"{part.nombre} · Registrado el {stamp}.")
        self.refresh_records()

    def on_new_search(self) -> None:
        self.current_participant = self.current_payment = None
        self.search_input.clear()
        self.sub.setCurrentIndex(SUB_INTRO)
        self.search_helper.setText("El texto se normaliza automáticamente: mayúsculas, sin tildes y sin espacios sobrantes.")
        self._reset_automata()
        self._go(PAGE_SEARCH)

    def on_relink(self) -> None:
        if self.current_participant is None:
            return
        carnet = self.current_participant.carnet
        self.afnd.reiniciar()
        self._afnd_event("X")                                          # q0 -X-> qR
        self.afd.reiniciar()
        self._sync_tracks()
        self._open_manual(prefill_carnet=carnet, note="Ingrese el número de recibo de Tesorería para este estudiante.")

    # ================================================================== #
    # Módulo 3: registros
    # ================================================================== #
    def _poll_registry(self) -> None:
        mtime = self.dm.registry_mtime()
        if mtime != self._registry_mtime:
            self.refresh_records()

    def refresh_records(self) -> None:
        try:
            self._registry_df = self.dm.load_registry()
        except DataSourceError as exc:
            self.rec_footer.setText(f"⚠ {exc}")
            return
        self._registry_mtime = self.dm.registry_mtime()
        df = self._registry_df
        att = int(df["Asistencia_Validada"].sum())
        tix = int(df["Ticket_Entregado"].sum())
        self.stat_total.set_value(str(len(df)))
        self.stat_att.set_value(str(att))
        self.stat_tix.set_value(str(tix))
        self.stat_pending.set_value(str(max(len(self.dm.participants) - att, 0)))
        self._apply_records_filter()

    def _apply_records_filter(self) -> None:
        df = self._registry_df
        mode = self.rec_filter.currentIndex()
        if mode == 1:
            df = df[df["Asistencia_Validada"]]
        elif mode == 2:
            df = df[~df["Asistencia_Validada"]]
        q = normalize_text(self.rec_search.text())
        if q:
            hay = (df["Carnet"].astype(str) + " " + df["Nombre_Oficial"].astype(str) + " " +
                   df["Correo"].astype(str) + " " + df["No_Recibo"].astype(str)).map(normalize_text)
            df = df[hay.map(lambda s: all(tok in s for tok in q.split()))]
        t = self.rec_table
        t.setSortingEnabled(False)
        t.setRowCount(len(df))
        for r, (_, row) in enumerate(df.iterrows()):
            for c, name in enumerate(REGISTRO_COLUMNS):
                val = row[name]
                if name in ("Asistencia_Validada", "Ticket_Entregado"):
                    text = "Sí" if bool(val) else "No"
                elif name == "Monto_Pago":
                    text = _money(float(val)) if pd.notna(val) else ""
                elif name == "Estado_AFD":
                    text = f"q{int(val)}" if pd.notna(val) and str(val) != "" else ""
                else:
                    text = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(text)
                if name in ("Asistencia_Validada", "Ticket_Entregado"):
                    from PyQt6.QtGui import QColor
                    item.setForeground(QColor(styles.SUCCESS_TEXT if bool(val) else styles.SLATE_MIST))
                t.setItem(r, c, item)
        t.setSortingEnabled(True)
        self.rec_footer.setText(f"Mostrando {len(df)} de {len(self._registry_df)} registros · {self.dm.registro_path.name}")

    def on_export(self) -> None:
        default = str(self.dm.base_dir / "reporte_asistencia.xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "Exportar registro", default, "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        try:
            self.dm.export_registry(Path(path))
        except (DataSourceError, OSError) as exc:
            QMessageBox.critical(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportación completa", f"Archivo guardado en:\n{path}")
