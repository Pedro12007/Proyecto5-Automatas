from __future__ import annotations

from typing import Mapping, Optional, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                             QSizePolicy, QVBoxLayout, QWidget)


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def make_button(text: str, variant: str = "ghost", pill: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("variant", variant)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if pill:
        btn.setStyleSheet("border-radius: 21px; padding: 11px 28px;")
    return btn


class Card(QFrame):

    def __init__(self, title: str = "", subtitle: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("accent", "")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(24, 22, 24, 24)
        self.body.setSpacing(14)
        if title:
            t = QLabel(title)
            t.setObjectName("CardTitle")
            self.body.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("CardSubtitle")
            s.setWordWrap(True)
            self.body.addWidget(s)

    def set_accent(self, accent: str) -> None:
        self.setProperty("accent", accent)
        repolish(self)


class DataPanel(Card):

    def __init__(self, title: str, subtitle: str, fields: Sequence[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(title, subtitle, parent)
        self._fields = list(fields)
        divider = QFrame()
        divider.setObjectName("Divider")
        self.body.addWidget(divider)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        self._values: dict[str, QLabel] = {}
        for row, name in enumerate(self._fields):
            lab = QLabel(name.upper())
            lab.setObjectName("FieldLabel")
            val = QLabel("—")
            val.setObjectName("FieldValueMuted")
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lab, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(val, row, 1)
            self._values[name] = val
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 130)
        self.body.addLayout(grid)
        self.empty_note = QLabel("")
        self.empty_note.setObjectName("Helper")
        self.empty_note.setWordWrap(True)
        self.empty_note.hide()
        self.body.addWidget(self.empty_note)
        self.body.addStretch(1)

    def set_data(self, data: Optional[Mapping[str, str]], empty_message: str = "") -> None:
        for name, label in self._values.items():
            value = (data or {}).get(name, "")
            label.setText(value if value else "—")
            label.setObjectName("FieldValue" if value else "FieldValueMuted")
            repolish(label)
        self.empty_note.setVisible(bool(empty_message))
        self.empty_note.setText(empty_message)


class Banner(QFrame):

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        self.setProperty("tone", "info")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(3)
        self.title = QLabel("")
        self.title.setObjectName("BannerTitle")
        self.text = QLabel("")
        self.text.setObjectName("BannerText")
        self.text.setWordWrap(True)
        lay.addWidget(self.title)
        lay.addWidget(self.text)
        self.hide()

    def show_message(self, tone: str, title: str, text: str = "") -> None:
        colors = {"info": "#8fa5ff", "success": "#6fe3a3", "danger": "#ff8f9b", "warn": "#f6cd6b"}
        self.setProperty("tone", tone)
        self.title.setText(title)
        self.title.setStyleSheet(f"color: {colors.get(tone, '#ffffff')};")
        self.text.setText(text)
        self.text.setVisible(bool(text))
        repolish(self)
        self.show()


class StatePill(QLabel):
    def __init__(self, text: str, tooltip: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Pill")
        self.setProperty("tone", "idle")
        self.setFixedHeight(24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip(tooltip)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)


class AutomatonTrack(QWidget):

    def __init__(self, title: str, states: Sequence[tuple[int, str, str, str]],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tones = {sid: tone for sid, _, _, tone in states}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        head = QLabel(title.upper())
        head.setObjectName("TrackTitle")
        lay.addWidget(head)
        row = QHBoxLayout()
        row.setSpacing(6)
        self._pills: dict[int, StatePill] = {}
        for sid, label, desc, _ in states:
            pill = StatePill(label, f"{label} — {desc}")
            pill.setMinimumWidth(46)
            self._pills[sid] = pill
            row.addWidget(pill)
        row.addStretch(1)
        lay.addLayout(row)

    def set_state(self, state: Optional[int]) -> None:
        for sid, pill in self._pills.items():
            pill.set_tone(self._tones[sid] if sid == state else "idle")


def afnd_track() -> AutomatonTrack:
    return AutomatonTrack("AFND · Búsqueda", [
        (0, "q0", "Inicio / en espera", "active"),
        (1, "qC", "Candidatos múltiples", "violet"),
        (2, "qR", "Rechazo — revisión manual", "warn"),
        (3, "qM", "Match confirmado", "success"),
    ])


def afd_track() -> AutomatonTrack:
    return AutomatonTrack("AFD · Pago y asistencia", [
        (0, "q0", "Identidad confirmada", "active"),
        (1, "q1", "Pago validado", "active"),
        (2, "q2", "Asistencia + ticket entregado", "success"),
        (3, "qE", "Estado trampa / error", "danger"),
    ])


class StatCard(Card):
    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.body.setContentsMargins(20, 16, 20, 16)
        self.body.setSpacing(2)
        self.value = QLabel("0")
        self.value.setObjectName("StatValue")
        cap = QLabel(label.upper())
        cap.setObjectName("StatLabel")
        self.body.addWidget(self.value)
        self.body.addWidget(cap)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


def make_tag(text: str, color: str = "") -> QLabel:
    tag = QLabel(text)
    tag.setObjectName("Tag")
    if color:
        tag.setStyleSheet(f"color: {color}; border-color: {color};")
    return tag
