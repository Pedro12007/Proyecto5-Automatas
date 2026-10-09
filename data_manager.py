from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

REGISTRO_FILENAME = "REGISTRO_Y_ASISTENCIA_SIMPOSIO.xlsx"
REGISTRO_SHEET = "Control_Asistencia"
REGISTRO_COLUMNS: list[str] = [
    "Carnet", "Nombre_Oficial", "Correo", "No_Recibo", "Monto_Pago", "Fecha_Pago",
    "Estado_AFD", "Asistencia_Validada", "Ticket_Entregado", "Fecha_Hora_Registro",
]

TESORERIA_PATTERNS = ["REPORTE*TESORERIA*SIMPOSIO*2025*.xlsx", "*TESORERIA*.xlsx"]
PARTICIPANTES_PATTERNS = ["Participantes_Simposio*.xlsx", "*Participantes*.xlsx"]

_FUZZY_TOKEN_RATIO = 0.78
_MIN_LINK_COVERAGE = 0.99


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_text(text: object) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = strip_accents(str(text)).upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def digits_only(text: object) -> str:
    return re.sub(r"\D", "", "" if text is None else str(text))


def _clean_str(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _format_receipt(value: object) -> str:
    s = _clean_str(value)
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    return s


def _format_date(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()[:10]


@dataclass(frozen=True)
class Participant:
    carnet: str
    nombre: str
    correo: str

    @property
    def nombre_norm(self) -> str:
        return normalize_text(self.nombre)

    @property
    def carnet_digits(self) -> str:
        return digits_only(self.carnet)


@dataclass(frozen=True)
class Payment:
    id: int
    fecha: str
    recibo: str
    nombre: str
    monto: float
    concepto: str

    @property
    def nombre_norm(self) -> str:
        return normalize_text(self.nombre)


@dataclass
class Candidate:
    participant: Optional[Participant]
    payment: Optional[Payment]
    registered: bool = False

    @property
    def key(self) -> str:
        if self.participant:
            return f"C:{self.participant.carnet}"
        return f"P:{self.payment.id if self.payment else '-'}"

    @property
    def display_name(self) -> str:
        if self.participant:
            return self.participant.nombre
        return self.payment.nombre if self.payment else ""

    @property
    def status_label(self) -> str:
        if self.registered:
            return "Ya registrado"
        if self.participant and self.payment:
            return "Pago encontrado"
        if self.participant:
            return "Sin pago asociado"
        return "Solo en Tesorería"


class DataSourceError(Exception):
    pass


class DataManager:
    def __init__(self, base_dir: Path | str | None = None,
                 tesoreria_path: Path | str | None = None,
                 participantes_path: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.tesoreria_path: Optional[Path] = Path(tesoreria_path) if tesoreria_path else None
        self.participantes_path: Optional[Path] = Path(participantes_path) if participantes_path else None
        self.registro_path: Path = self.base_dir / REGISTRO_FILENAME

        self.participants: list[Participant] = []
        self.payments: list[Payment] = []
        self._payment_of: dict[str, Payment] = {}
        self._owner_of: dict[int, Participant] = {}
        self._by_carnet: dict[str, Participant] = {}
        self._by_receipt: dict[str, Payment] = {}

    def _find(self, patterns: list[str]) -> Optional[Path]:
        for folder in (self.base_dir, Path.cwd()):
            for pat in patterns:
                found = sorted(folder.glob(pat))
                found = [f for f in found if not f.name.startswith("~$") and f.name != REGISTRO_FILENAME]
                if found:
                    return found[0]
        return None

    def sources_missing(self) -> list[str]:
        missing: list[str] = []
        if not (self.tesoreria_path and self.tesoreria_path.exists()):
            self.tesoreria_path = self._find(TESORERIA_PATTERNS)
            if self.tesoreria_path is None:
                missing.append("tesoreria")
        if not (self.participantes_path and self.participantes_path.exists()):
            self.participantes_path = self._find(PARTICIPANTES_PATTERNS)
            if self.participantes_path is None:
                missing.append("participantes")
        return missing

    def load_sources(self) -> None:
        if self.sources_missing():
            raise FileNotFoundError("No se encontraron los archivos de origen.")
        assert self.tesoreria_path and self.participantes_path
        try:
            self.participants = self._read_participants(self.participantes_path)
            self.payments = self._read_payments(self.tesoreria_path)
        except PermissionError as exc:
            raise DataSourceError(f"No se puede leer el archivo (¿está abierto en Excel?): {exc}") from exc
        except Exception as exc:
            raise DataSourceError(f"Error leyendo archivos de origen: {exc}") from exc
        self._by_carnet = {p.carnet: p for p in self.participants}
        self._by_receipt = {pay.recibo: pay for pay in self.payments if pay.recibo}
        self._link_sources()
        self.ensure_registry()

    @staticmethod
    def _read_participants(path: Path) -> list[Participant]:
        df = pd.read_excel(path, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        out: list[Participant] = []
        seen: set[str] = set()
        for _, row in df.iterrows():
            carnet = _clean_str(row.get("Carnet"))
            nombre = _clean_str(row.get("Nombre"))
            if not carnet or not nombre or carnet in seen:
                continue
            seen.add(carnet)
            out.append(Participant(carnet, nombre, _clean_str(row.get("Correo"))))
        return out

    @staticmethod
    def _read_payments(path: Path) -> list[Payment]:
        raw = pd.read_excel(path, header=None)
        header_idx: Optional[int] = None
        for i in range(min(len(raw), 60)):
            cells = {normalize_text(v) for v in raw.iloc[i].tolist()}
            if "NOMBRE" in cells and "MONTO" in cells:
                header_idx = i
                break
        if header_idx is None:
            raise DataSourceError("No se encontró la fila de encabezados en el reporte de Tesorería.")
        headers = [normalize_text(v) for v in raw.iloc[header_idx].tolist()]
        body = raw.iloc[header_idx + 1:].copy()
        body.columns = headers

        def col(*names: str) -> str:
            for n in names:
                for h in headers:
                    if h.startswith(n):
                        return h
            raise DataSourceError(f"Falta la columna {names[0]} en Tesorería.")

        c_n, c_fecha, c_rec = col("N"), col("FECHA"), col("NUMERO DE RECIBO", "NUMERO")
        c_nom, c_monto, c_conc = col("NOMBRE"), col("MONTO"), col("CONCEPTO")
        out: list[Payment] = []
        for _, row in body.iterrows():
            nombre = _clean_str(row[c_nom])
            n_val = pd.to_numeric(row[c_n], errors="coerce")
            monto = pd.to_numeric(row[c_monto], errors="coerce")
            if not nombre or pd.isna(n_val) or pd.isna(monto):
                continue
            out.append(Payment(int(n_val), _format_date(row[c_fecha]), _format_receipt(row[c_rec]),
                               nombre, float(monto), _clean_str(row[c_conc])))
        return out

    @staticmethod
    def _token_match(a: list[str], b: list[str]) -> int:
        pool = list(b)
        matched = 0
        for tok in a:
            if tok in pool:
                pool.remove(tok)
                matched += 1
                continue
            if len(tok) < 4:
                continue
            best_i, best_r = -1, 0.0
            for i, cand in enumerate(pool):
                if len(cand) < 4:
                    continue
                if len(cand) == len(tok) and cand[0] == tok[0] and sorted(cand) == sorted(tok):
                    best_i, best_r = i, 1.0
                    break
                r = difflib.SequenceMatcher(None, tok, cand).ratio()
                if r > best_r:
                    best_i, best_r = i, r
            if best_r >= _FUZZY_TOKEN_RATIO:
                pool.pop(best_i)
                matched += 1
        return matched

    def _link_sources(self) -> None:
        pay_tokens = [(pay, pay.nombre_norm.split()) for pay in self.payments]
        pairs: list[tuple[float, float, Participant, Payment]] = []
        for part in self.participants:
            p_tokens = part.nombre_norm.split()
            if len(p_tokens) < 2:
                continue
            first = p_tokens[0]
            for pay, t_tokens in pay_tokens:
                if len(t_tokens) < 2:
                    continue
                if not any(t == first or (len(t) > 3 and len(first) > 3 and t[:3] == first[:3]) for t in t_tokens) \
                        and not set(p_tokens) & set(t_tokens):
                    continue
                short, long_ = (p_tokens, t_tokens) if len(p_tokens) <= len(t_tokens) else (t_tokens, p_tokens)
                m = self._token_match(short, long_)
                coverage = m / len(short)
                if coverage >= _MIN_LINK_COVERAGE and m >= 2:
                    pairs.append((coverage, m / len(long_), part, pay))
        pairs.sort(key=lambda x: (x[0], x[1]), reverse=True)
        used_pay: set[int] = set()
        self._payment_of.clear()
        self._owner_of.clear()
        for _, _, part, pay in pairs:
            if part.carnet in self._payment_of or pay.id in used_pay:
                continue
            self._payment_of[part.carnet] = pay
            self._owner_of[pay.id] = part
            used_pay.add(pay.id)

    def payment_for(self, participant: Participant) -> Optional[Payment]:
        return self._payment_of.get(participant.carnet)

    def stats(self) -> dict[str, int]:
        return {"participantes": len(self.participants), "pagos": len(self.payments),
                "vinculados": len(self._payment_of)}

    def search(self, query: str) -> list[Candidate]:
        q = normalize_text(query)
        if not q:
            return []
        registered = self.registered_carnets()
        digits = digits_only(query)
        numeric = bool(digits) and not re.search(r"[A-Za-z]", strip_accents(query))

        if numeric:
            by_carnet = [p for p in self.participants if p.carnet_digits == digits]
            if not by_carnet and len(digits) >= 3:
                by_carnet = [p for p in self.participants if digits in p.carnet_digits]
            by_receipt = [pay for pay in self.payments if pay.recibo == digits]
            if not by_receipt and len(digits) >= 5:
                by_receipt = [pay for pay in self.payments if digits in pay.recibo]
            part_hits, pay_hits = by_carnet, by_receipt
        else:
            tokens = q.split()
            part_hits = [p for p in self.participants if p.nombre_norm == q] or \
                        [p for p in self.participants if all(t in p.nombre_norm for t in tokens)]
            pay_hits = [pay for pay in self.payments if pay.nombre_norm == q] or \
                       [pay for pay in self.payments if all(t in pay.nombre_norm for t in tokens)]

        found: dict[str, Candidate] = {}
        for part in part_hits:
            cand = Candidate(part, self._payment_of.get(part.carnet), part.carnet in registered)
            found[cand.key] = cand
        for pay in pay_hits:
            owner = self._owner_of.get(pay.id)
            cand = Candidate(owner, pay, bool(owner and owner.carnet in registered)) if owner \
                else Candidate(None, pay, False)
            found.setdefault(cand.key, cand)
        return sorted(found.values(), key=lambda c: normalize_text(c.display_name))

    def lookup_carnet(self, carnet: str) -> Optional[Participant]:
        c = _clean_str(carnet)
        if c in self._by_carnet:
            return self._by_carnet[c]
        d = digits_only(c)
        if len(d) >= 4:
            for p in self.participants:
                if p.carnet_digits == d:
                    return p
        return None

    def lookup_receipt(self, recibo: str) -> Optional[Payment]:
        return self._by_receipt.get(digits_only(recibo)) or self._by_receipt.get(_clean_str(recibo))

    def ensure_registry(self) -> None:
        if self.registro_path.exists():
            return
        self._write_registry(pd.DataFrame(columns=REGISTRO_COLUMNS))

    def load_registry(self) -> pd.DataFrame:
        self.ensure_registry()
        try:
            df = pd.read_excel(self.registro_path, sheet_name=REGISTRO_SHEET,
                               dtype={"Carnet": str, "No_Recibo": str})
        except PermissionError as exc:
            raise DataSourceError("El archivo de registro está bloqueado (¿abierto en Excel?).") from exc
        for c in REGISTRO_COLUMNS:
            if c not in df.columns:
                df[c] = None
        df = df[REGISTRO_COLUMNS].copy()
        for c in ("Asistencia_Validada", "Ticket_Entregado"):
            df[c] = df[c].map(lambda v: str(v).strip().upper() in ("TRUE", "1", "VERDADERO")).astype(bool)
        return df

    def registry_mtime(self) -> float:
        try:
            return self.registro_path.stat().st_mtime
        except OSError:
            return 0.0

    def registered_carnets(self) -> set[str]:
        try:
            df = self.load_registry()
        except DataSourceError:
            return set()
        return set(df.loc[df["Asistencia_Validada"], "Carnet"].astype(str))

    def registry_conflict(self, participant: Participant, payment: Payment) -> Optional[str]:
        df = self.load_registry()
        done = df[df["Asistencia_Validada"]]
        same = done[done["Carnet"].astype(str) == participant.carnet]
        if not same.empty:
            when = _clean_str(same.iloc[0]["Fecha_Hora_Registro"]) or "fecha desconocida"
            return f"La asistencia y el ticket ya fueron marcados previamente ({when})."
        other = done[(done["No_Recibo"].astype(str) == payment.recibo) & (done["Carnet"].astype(str) != participant.carnet)]
        if not other.empty:
            return (f"El recibo {payment.recibo} ya fue utilizado por el carné "
                    f"{other.iloc[0]['Carnet']}. Posible duplicidad de pago.")
        return None

    def register_attendance(self, participant: Participant, payment: Payment, estado_afd: int = 2) -> str:
        df = self.load_registry()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "Carnet": participant.carnet, "Nombre_Oficial": participant.nombre, "Correo": participant.correo,
            "No_Recibo": payment.recibo, "Monto_Pago": payment.monto, "Fecha_Pago": payment.fecha,
            "Estado_AFD": estado_afd, "Asistencia_Validada": True, "Ticket_Entregado": True,
            "Fecha_Hora_Registro": stamp,
        }
        mask = df["Carnet"].astype(str) == participant.carnet
        if mask.any():
            for k, v in row.items():
                df.loc[mask, k] = v
        else:
            df = pd.concat([df, pd.DataFrame([row], columns=REGISTRO_COLUMNS)], ignore_index=True) \
                if not df.empty else pd.DataFrame([row], columns=REGISTRO_COLUMNS)
        self._write_registry(df)
        return stamp

    def _write_registry(self, df: pd.DataFrame) -> None:
        df = df.copy()
        for c in ("Asistencia_Validada", "Ticket_Entregado"):
            df[c] = df[c].astype(bool)
        tmp = self.registro_path.with_suffix(".tmp.xlsx")
        try:
            with pd.ExcelWriter(tmp, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=REGISTRO_SHEET, index=False)
                ws = writer.sheets[REGISTRO_SHEET]
                widths = [13, 36, 40, 13, 12, 13, 11, 20, 18, 21]
                for i, w in enumerate(widths):
                    ws.column_dimensions[chr(ord("A") + i)].width = w
                ws.freeze_panes = "A2"
            tmp.replace(self.registro_path)
        except PermissionError as exc:
            tmp.unlink(missing_ok=True)
            raise DataSourceError("No se pudo escribir el registro: cierre el archivo si está abierto en Excel.") from exc
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise DataSourceError(f"No se pudo escribir el registro: {exc}") from exc

    def export_registry(self, destination: Path | str) -> None:
        df = self.load_registry()
        dest = Path(destination)
        if dest.suffix.lower() == ".csv":
            df.to_csv(dest, index=False, encoding="utf-8-sig")
        else:
            df.to_excel(dest, sheet_name=REGISTRO_SHEET, index=False)