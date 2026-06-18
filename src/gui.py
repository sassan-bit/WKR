import os, sys, threading, time, socket, json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QLineEdit, QTextEdit, QProgressBar, QTableWidget, QTableWidgetItem,
    QComboBox, QStackedWidget, QFileDialog, QMessageBox, QAbstractItemView,
    QHBoxLayout, QVBoxLayout, QHeaderView, QSizePolicy, QScrollArea,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot,
    QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPointF,
)
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush, QFont,
    QTextCharFormat, QCursor, QPixmap, QFontDatabase,
)

try:
    from watchdog.events import FileSystemEventHandler as _WFH
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    class _WFH: pass
    Observer = None

sys.path.insert(0, str(Path(__file__).parent))
from check_file import MalwareDetector

# ── Color palettes ────────────────────────────────────────────────────────────
_DARK_PAL = {
    "BG":"#0A0E1A","CARD":"#111827","RAISED":"#1C2333",
    "ACCENT":"#00D4FF","DANGER":"#FF4757","SUCCESS":"#2ED573",
    "WARN":"#F6C90E","MUTED":"#6B7A99","TEXT":"#E2E8F0","BORDER":"#1E293B",
    "SIDEBAR":"#07090F","HDR_BG":"#111827","TABLE_ALT":"#141F32","HDR_SEC":"#080C18",
}
_LIGHT_PAL = {
    "BG":"#F0F4FF","CARD":"#FFFFFF","RAISED":"#EAF0FB",
    "ACCENT":"#1A6FE8","DANGER":"#DC2626","SUCCESS":"#16A34A",
    "WARN":"#D97706","MUTED":"#8896B3","TEXT":"#0D1B2E","BORDER":"#C8D6EE",
    "SIDEBAR":"#E2EAF8","HDR_BG":"#FFFFFF","TABLE_ALT":"#F5F8FF","HDR_SEC":"#EDF2FB",
}

_DARK = True
_LANG = "en"

# set globals from palette
def _apply_palette(dark: bool):
    global BG, CARD, RAISED, ACCENT, DANGER, SUCCESS, WARN, MUTED, TEXT, BORDER
    global _DARK
    _DARK = dark
    p = _DARK_PAL if dark else _LIGHT_PAL
    BG=p["BG"]; CARD=p["CARD"]; RAISED=p["RAISED"]
    ACCENT=p["ACCENT"]; DANGER=p["DANGER"]; SUCCESS=p["SUCCESS"]
    WARN=p["WARN"]; MUTED=p["MUTED"]; TEXT=p["TEXT"]; BORDER=p["BORDER"]

_apply_palette(True)

PE_EXT     = {".exe", ".dll", ".sys"}
AGENT_PORT = 45000
FILE_PORT  = 45001

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    "en": {
        "nav":          [("◈","Dashboard"),("⊙","Scan Files"),("◎","Monitor"),("≡","Event Log")],
        "engine_on":    "ML Engine Active", "engine_off":  "ML Engine Offline",
        "engine_sub":   "LightGBM  ·  Static PE",
        "protected":    "● PROTECTED",      "at_risk":     "● AT RISK",
        "status_ok":    "SYSTEM PROTECTED",
        "status_ok2":   "Detection engine active  |  Static PE analysis ready",
        "status_bad":   "ATTENTION REQUIRED",
        "status_bad2":  "Model not found — run: python src/train_model.py",
        "quick_scan":   "Quick Scan",
        "sel_file":     "  Select File  ",  "sel_folder":  "  Select Folder  ",
        "run_scan":     "  Run Scan  ",     "start_scan":  "  Start Scan  ",
        "cancel":       "  Cancel  ",       "pause":       "  Pause  ",
        "resume":       "  Resume  ",       "clear":       "  Clear  ",
        "browse":       "  Browse  ",
        "start_mon":    "  Start Monitoring  ", "stop_mon": "  Stop Monitoring  ",
        "scan_dir":     "  Scan Directory  ",   "delete":   "  Delete  ",
        "refresh":      "  Refresh  ",      "open_folder": "  Open Folder  ",
        "del_file":     "  Delete File  ",
        "files_sel":    "Select Files to Scan",
        "scan_prog":    "Scan Progress",    "scan_res":    "Scan Results",
        "sorted_by":    "Sorted by threat level",
        "ready":        "Ready to scan",   "complete":    "Scan complete",
        "cancelled":    "Scan cancelled",  "no_files":    "No files selected",
        "watch_path":   "WATCH PATH",
        "mon_settings": "Monitor Settings",
        "net_agents":   "Network Agents",
        "live_events":  "Live Events",     "realtime":    "Real-time detection feed",
        "no_agents":    "No agents connected",
        "period":       "PERIOD",
        "event_log":    "Event Log",       "det_hist":    "Detection history",
        "threats_lbl":  "Threats",
        "m_total":      "Files Scanned",   "m_threats":   "Threats Found",
        "m_clean":      "Clean Files",     "m_last":      "Last Scan",
        "watching":     "Watching",        "inactive":    "Inactive",
        "th_file":      "File Path",       "th_verdict":  "Verdict",
        "th_prob":      "Probability",     "th_ts":       "Timestamp",
        "th_result":    "Result",          "th_source":   "Source PC",
        "agent_srv":    "Agent listener",  "my_ip":       "My IP",
    },
    "ru": {
        "nav":          [("◈","Главная"),("⊙","Сканер"),("◎","Мониторинг"),("≡","Журнал")],
        "engine_on":    "Движок ML активен", "engine_off":  "Движок ML отключён",
        "engine_sub":   "LightGBM  ·  Статический PE",
        "protected":    "● ЗАЩИЩЁН",          "at_risk":     "● НЕТ ЗАЩИТЫ",
        "status_ok":    "СИСТЕМА ЗАЩИЩЕНА",
        "status_ok2":   "Движок обнаружения активен  |  Статический анализ PE готов",
        "status_bad":   "ТРЕБУЕТСЯ ВНИМАНИЕ",
        "status_bad2":  "Модель не найдена — выполните: python src/train_model.py",
        "quick_scan":   "Быстрый скан",
        "sel_file":     "  Файл  ",          "sel_folder":  "  Папка  ",
        "run_scan":     "  Сканировать  ",   "start_scan":  "  Начать скан  ",
        "cancel":       "  Отмена  ",        "pause":       "  Пауза  ",
        "resume":       "  Продолжить  ",    "clear":       "  Очистить  ",
        "browse":       "  Обзор  ",
        "start_mon":    "  Начать мониторинг  ", "stop_mon": "  Остановить  ",
        "scan_dir":     "  Сканировать папку  ",  "delete":  "  Удалить  ",
        "refresh":      "  Обновить  ",       "open_folder": "  Открыть папку  ",
        "del_file":     "  Удалить файл  ",
        "files_sel":    "Выбор файлов для сканирования",
        "scan_prog":    "Прогресс сканирования", "scan_res": "Результаты",
        "sorted_by":    "Сортировка по уровню угрозы",
        "ready":        "Готов к сканированию", "complete": "Сканирование завершено",
        "cancelled":    "Отменено",             "no_files": "Файлы не выбраны",
        "watch_path":   "ПУТЬ НАБЛЮДЕНИЯ",
        "mon_settings": "Настройки мониторинга",
        "net_agents":   "Сетевые агенты",
        "live_events":  "Живые события",    "realtime":    "Лента событий",
        "no_agents":    "Нет подключённых агентов",
        "period":       "ПЕРИОД",
        "event_log":    "Журнал событий",   "det_hist":    "История обнаружений",
        "threats_lbl":  "Угрозы",
        "m_total":      "Проверено файлов", "m_threats":   "Найдено угроз",
        "m_clean":      "Чистых файлов",    "m_last":      "Последний скан",
        "watching":     "Наблюдение",       "inactive":    "Неактивен",
        "th_file":      "Путь к файлу",     "th_verdict":  "Вердикт",
        "th_prob":      "Вероятность",      "th_ts":       "Время",
        "th_result":    "Результат",        "th_source":   "Источник",
        "agent_srv":    "Сервер агентов",   "my_ip":       "Мой IP",
    },
}

def _tr(key: str) -> str:
    return T[_LANG].get(key, T["en"].get(key, key))

# ── QSS builder ───────────────────────────────────────────────────────────────
def _build_qss() -> str:
    _p = _DARK_PAL if _DARK else _LIGHT_PAL
    sb  = _p["SIDEBAR"]; hb = _p["HDR_BG"]
    ta  = _p["TABLE_ALT"]; hs = _p["HDR_SEC"]
    return f"""
QMainWindow {{ background: {BG}; }}
QWidget {{ font-family: "Inter"; font-size: 10pt; color: {TEXT}; }}
QFrame#sidebar  {{ background: {sb}; border-right: 1px solid {BORDER}; }}
QFrame#hdr_frame {{ background: {hb}; border-bottom: 1px solid {BORDER}; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
QFrame#vsep {{ background: {BORDER}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}
QProgressBar {{
    background: {RAISED}; border: none; border-radius: 4px;
    max-height: 6px; color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 #0055EE);
    border-radius: 4px;
}}
QTableWidget {{
    background: {CARD}; border: none; outline: none;
    gridline-color: {BORDER}; font-size: 9pt;
    alternate-background-color: {ta};
}}
QTableWidget::item {{ padding: 6px 10px; border: none; }}
QTableWidget::item:selected {{ background: {ACCENT}; color: {BG}; }}
QHeaderView::section {{
    background: {hs}; color: {MUTED}; padding: 8px 10px;
    border: none; border-bottom: 1px solid {BORDER};
    font-weight: 600; font-size: 9pt;
}}
QHeaderView {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: {RAISED}; border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 6px; }}
QScrollBar::handle:horizontal {{ background: {RAISED}; border-radius: 3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit {{
    background: {RAISED}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 8px 12px; color: {TEXT}; font-size: 10pt;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox {{
    background: {RAISED}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 6px 12px; color: {TEXT}; min-width: 110px; font-size: 10pt;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER};
    selection-background-color: {RAISED}; color: {TEXT}; outline: none;
}}
QTextEdit {{
    background: {RAISED}; border: none; border-radius: 6px;
    padding: 6px; color: {TEXT};
    font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace; font-size: 9pt;
}}
"""

QSS = _build_qss()

# ── Button factory ────────────────────────────────────────────────────────────
def _dk(c: str, n: int = 22) -> str:
    c = c.lstrip("#")
    r = max(0, int(c[0:2], 16) - n)
    g = max(0, int(c[2:4], 16) - n)
    b = max(0, int(c[4:6], 16) - n)
    return f"#{r:02x}{g:02x}{b:02x}"


def Btn(text: str, bg: str = ACCENT, fg: str = BG, small: bool = False) -> QPushButton:
    b   = QPushButton(text)
    pad = "5px 13px" if small else "9px 20px"
    fs  = "9pt"      if small else "10pt"
    hov = _dk(bg, 22); pre = _dk(bg, 38)
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg}; color: {fg};
            border: none; border-radius: 6px; padding: {pad};
            font-weight: 600; font-size: {fs}; font-family: "Inter"; min-width: 80px;
        }}
        QPushButton:hover   {{ background-color: {hov}; }}
        QPushButton:pressed {{ background-color: {pre}; }}
        QPushButton:disabled {{ background-color: {RAISED}; color: {MUTED}; }}
    """)
    return b


def GhostBtn(text: str, small: bool = False) -> QPushButton:
    b   = QPushButton(text)
    pad = "4px 12px" if small else "8px 16px"
    fs  = "9pt"      if small else "10pt"
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent; color: {MUTED};
            border: 1px solid {BORDER}; border-radius: 6px;
            padding: {pad}; font-weight: 600; font-size: {fs}; font-family: "Inter";
        }}
        QPushButton:hover   {{ background-color: {RAISED}; color: {TEXT}; border-color: {MUTED}; }}
        QPushButton:disabled {{ color: {MUTED}; }}
    """)
    return b


def IconBtn(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFixedSize(34, 34)
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: {RAISED}; color: {TEXT};
            border: 1px solid {BORDER}; border-radius: 17px;
            font-size: 13pt; font-family: "Inter";
            padding: 0px;
        }}
        QPushButton:hover   {{ background-color: {BORDER}; border-color: {ACCENT}; color: {ACCENT}; }}
        QPushButton:pressed {{ background-color: {ACCENT}; color: {BG}; }}
    """)
    return b


# ── Card helper ───────────────────────────────────────────────────────────────
def _card(parent, title: str = None, subtitle: str = None):
    outer = QFrame(parent); outer.setObjectName("card")
    vl = QVBoxLayout(outer); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
    if title:
        hdr = QWidget(outer); hdr.setStyleSheet(f"background: {CARD};")
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(20,14,20,0)
        t = QLabel(title, hdr)
        t.setStyleSheet(f"font-size:11pt; font-weight:600; color:{TEXT}; background:transparent;")
        hl.addWidget(t)
        if subtitle:
            s = QLabel(subtitle, hdr)
            s.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
            hl.addStretch(); hl.addWidget(s)
        vl.addWidget(hdr)
        sep = QFrame(outer); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};"); vl.addWidget(sep)
    body = QWidget(outer); body.setStyleSheet(f"background: {CARD};")
    vl.addWidget(body)
    return outer, body


# ─────────────────────────────────────────────────────────────────────────────
# Custom widgets
# ─────────────────────────────────────────────────────────────────────────────

class ShieldWidget(QWidget):
    def _get(self):    return self._glow
    def _set(self, v): self._glow = max(0.0, min(1.0, float(v))); self.update()
    glow = pyqtProperty(float, _get, _set)

    def __init__(self, ok: bool = True, parent=None):
        super().__init__(parent)
        self._ok = ok; self._glow = 0.0
        self.setFixedSize(170, 126)
        a = QPropertyAnimation(self, b"glow", self)
        a.setDuration(800); a.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim = a

    def set_active(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy, sz, g = W//2, H//2+2, 36.0, self._glow
        p.fillRect(0, 0, W, H, QColor(CARD))
        if g > 0.02:
            for r, am in [(60,32),(48,52),(38,78)]:
                c = QColor(0,212,255,int(am*g))
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(c))
                p.drawEllipse(QPointF(cx,cy), r, r)
        path = QPainterPath()
        path.moveTo(cx, cy-sz); path.lineTo(cx+sz*.78, cy-sz)
        path.lineTo(cx+sz*.78, cy+sz*.20); path.lineTo(cx, cy+sz*1.05)
        path.lineTo(cx-sz*.78, cy+sz*.20); path.lineTo(cx-sz*.78, cy-sz)
        path.closeSubpath()
        sc = QColor(int(0x2A+(0x00-0x2A)*g), int(0x3A+(0xD4-0x3A)*g), int(0x4A+(0xFF-0x4A)*g))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(sc)); p.drawPath(path)
        pen = QPen(QColor(255,255,255)); pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        if self._ok:
            ck = QPainterPath()
            ck.moveTo(cx-sz*.34, cy+sz*.06); ck.lineTo(cx-sz*.09, cy+sz*.33)
            ck.lineTo(cx+sz*.44, cy-sz*.37)
            p.drawPath(ck)
        else:
            p.setFont(QFont("Segoe UI", int(sz*.55), QFont.Weight.Bold))
            p.drawText(int(cx-10), int(cy-18), 20, 36, int(Qt.AlignmentFlag.AlignCenter), "!")
        p.end()


class DropZone(QWidget):
    files_dropped = pyqtSignal(list)
    open_dialog   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._hover = False
        self._text  = "Drop .exe / .dll / .sys  or  click to browse"
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_text(self, t):
        self._text = t or "Drop .exe / .dll / .sys  or  click to browse"; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(0, 0, W, H, QColor(CARD))
        pen = QPen(QColor(ACCENT if self._hover else BORDER)); pen.setWidth(1)
        if not self._hover: pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(3, 3, W-6, H-6, 7, 7)
        ic = QColor(ACCENT if self._hover else MUTED)
        p.setPen(ic); p.setFont(QFont("Segoe UI", 17))
        p.drawText(QRectF(0, 8, W, 30), Qt.AlignmentFlag.AlignHCenter, "+")
        p.setPen(QColor(TEXT if self._hover else MUTED))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(0, 44, W, 22), Qt.AlignmentFlag.AlignHCenter, self._text)
        p.end()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction(); self._hover = True; self.update()
    def dragMoveEvent(self, e): e.acceptProposedAction()
    def dragLeaveEvent(self, _): self._hover = False; self.update()
    def dropEvent(self, e):
        self._hover = False
        files = [Path(u.toLocalFile()) for u in e.mimeData().urls()
                 if Path(u.toLocalFile()).exists()
                 and Path(u.toLocalFile()).suffix.lower() in PE_EXT]
        if files: self.files_dropped.emit(files)
        self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.open_dialog.emit()


class MetricCard(QFrame):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._color = color; self._cur = 0; self._target = 0
        self._from  = 0;    self._step = 0
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)
        bar = QFrame(self); bar.setFixedHeight(2)
        bar.setStyleSheet(f"background:{color}; border:none;"); vl.addWidget(bar)
        inner = QWidget(self); inner.setStyleSheet(f"background:{CARD};")
        il = QVBoxLayout(inner); il.setContentsMargins(16,12,16,14); il.setSpacing(4)
        self._lbl = QLabel(label, inner)
        self._lbl.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        self._val = QLabel("0", inner)
        self._val.setStyleSheet(f"color:{color}; font-size:24pt; font-weight:700; background:transparent;")
        il.addWidget(self._lbl); il.addWidget(self._val); vl.addWidget(inner)

    def animate_to(self, target):
        if isinstance(target, str): self._val.setText(target); return
        self._from = self._cur; self._target = int(target)
        self._step = 0; self._timer.start(25)

    def _tick(self):
        self._step += 1
        if self._step >= 18: self._cur = self._target; self._timer.stop()
        else:
            t = self._step / 18
            self._cur = int(self._from + (self._target - self._from) * (1-(1-t)**3))
        self._val.setText(str(self._cur))


class NavButton(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, icon, label, key, parent=None):
        super().__init__(parent)
        self._key = key; self._active = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(46)
        hl = QHBoxLayout(self); hl.setContentsMargins(16,0,16,0); hl.setSpacing(10)
        self._ic = QLabel(icon, self); self._ic.setFont(QFont("Segoe UI",14))
        self._ic.setFixedWidth(26); self._ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tx = QLabel(label, self); self._tx.setFont(QFont("Segoe UI",11))
        hl.addWidget(self._ic); hl.addWidget(self._tx); hl.addStretch()
        self._refresh()

    def set_active(self, on):
        self._active = on; self._refresh(); self.update()

    def _refresh(self):
        c = ACCENT if self._active else MUTED
        w = "600" if self._active else "400"
        self._ic.setStyleSheet(f"color:{c}; background:transparent;")
        self._tx.setStyleSheet(f"color:{c}; font-weight:{w}; background:transparent;")

    def paintEvent(self, _):
        p = QPainter(self); W, H = self.width(), self.height()
        if self._active:
            p.fillRect(0,0,W,H,QColor(RAISED)); p.fillRect(0,0,3,H,QColor(ACCENT))
        elif self.underMouse():
            p.fillRect(0,0,W,H,QColor(RAISED))
        p.end()

    def enterEvent(self, _): self.update()
    def leaveEvent(self, _): self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.clicked.emit(self._key)


class ThemeOverlay(QLabel):
    """Full-window screenshot overlay for smooth theme crossfade."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setScaledContents(True)
        self._fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fx)
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.hide)
        self.hide()

    def crossfade(self, pixmap: QPixmap, duration_ms: int = 460):
        self.setGeometry(self.parent().rect())
        self.setPixmap(pixmap)
        self._fx.setOpacity(1.0)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self.show(); self.raise_()
        self._anim.start()


# ── Thread worker ─────────────────────────────────────────────────────────────
class ScanWorker(QObject):
    progress = pyqtSignal(int, int, float, float, str)
    finished = pyqtSignal(list)

    def __init__(self, paths, detector, pause_event):
        super().__init__()
        self.paths = paths; self.detector = detector
        self.pause_event = pause_event; self.cancel_flag = False

    @pyqtSlot()
    def run(self):
        results, total, t0 = [], len(self.paths), time.time()
        for idx, path in enumerate(self.paths):
            if self.cancel_flag: break
            self.pause_event.wait()
            if self.cancel_flag: break
            try:
                r = self.detector.check_file(str(path))
                if "error" in r:
                    results.append({"file":str(path),"verdict":"Error","prob":"N/A","is_malware":False,"err":True})
                else:
                    is_m = bool(r.get("is_malware",False))
                    results.append({"file":str(path),"verdict":"THREAT" if is_m else "Clean",
                                    "prob":f"{r.get('probability',0):.1%}","is_malware":is_m,"err":False})
            except Exception:
                results.append({"file":str(path),"verdict":"Error","prob":"N/A","is_malware":False,"err":True})
            elapsed = time.time()-t0; avg = elapsed/(idx+1)
            self.progress.emit(idx, total, elapsed, avg*(total-idx-1), path.name)
        self.finished.emit(results)


class WatchdogBridge(QObject):
    new_file = pyqtSignal(str)

class AgentBridge(QObject):
    agent_event = pyqtSignal(dict)

class FileBridge(QObject):
    file_ready = pyqtSignal(str, str, str)  # tmp_path, source, original_path

class MonitorEventHandler(_WFH):
    def __init__(self, bridge):
        super().__init__(); self._b = bridge
    def on_created(self, event):
        if not event.is_directory: self._b.new_file.emit(event.src_path)


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent); self.mw = mw
        self.setStyleSheet(f"background:{BG};"); self._build()

    def _build(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background:{BG}; border:none;")
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        vl = QVBoxLayout(w); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)

        f, b = _card(w)
        hl = QHBoxLayout(b); hl.setContentsMargins(22,18,22,18); hl.setSpacing(22)
        self.shield = ShieldWidget(self.mw.model_loaded, b)
        hl.addWidget(self.shield, 0, Qt.AlignmentFlag.AlignVCenter)
        ok = self.mw.model_loaded
        txt = QWidget(b); txt.setStyleSheet(f"background:{CARD};")
        tvl = QVBoxLayout(txt); tvl.setContentsMargins(0,0,0,0); tvl.setSpacing(6)
        t1  = QLabel(_tr("status_ok") if ok else _tr("status_bad"), txt)
        t1.setStyleSheet(f"font-size:15pt; font-weight:700; color:{TEXT}; background:transparent;")
        t2  = QLabel(_tr("status_ok2") if ok else _tr("status_bad2"), txt)
        t2.setStyleSheet(f"color:{MUTED}; font-size:10pt; background:transparent;")
        tvl.addWidget(t1); tvl.addWidget(t2)
        tags = QWidget(txt); tags.setStyleSheet(f"background:{CARD};")
        thl = QHBoxLayout(tags); thl.setContentsMargins(0,4,0,0); thl.setSpacing(6)
        for tag in ("LightGBM","Static Analysis","PE Headers"):
            l = QLabel(tag, tags)
            l.setStyleSheet(f"background:#071630; color:{ACCENT}; font-size:8pt; padding:2px 7px; border-radius:3px;")
            thl.addWidget(l)
        thl.addStretch()
        tvl.addWidget(tags); tvl.addStretch()
        hl.addWidget(txt, 1); vl.addWidget(f)

        mw2 = QWidget(w); mw2.setStyleSheet(f"background:{BG};")
        mhl = QHBoxLayout(mw2); mhl.setContentsMargins(0,0,0,0); mhl.setSpacing(10)
        self.mc_total   = MetricCard(_tr("m_total"),   ACCENT,   mw2)
        self.mc_threats = MetricCard(_tr("m_threats"),  DANGER,  mw2)
        self.mc_clean   = MetricCard(_tr("m_clean"),    SUCCESS, mw2)
        self.mc_last    = MetricCard(_tr("m_last"),     MUTED,   mw2)
        self.mc_last._val.setStyleSheet(f"color:{MUTED}; font-size:22pt; font-weight:700; background:transparent;")
        for mc in (self.mc_total, self.mc_threats, self.mc_clean, self.mc_last):
            mhl.addWidget(mc)
        vl.addWidget(mw2)

        f2, b2 = _card(w, _tr("quick_scan"))
        b2vl = QVBoxLayout(b2); b2vl.setContentsMargins(20,14,20,14); b2vl.setSpacing(12)
        br = QWidget(b2); br.setStyleSheet(f"background:{CARD};")
        brl = QHBoxLayout(br); brl.setContentsMargins(0,0,0,0); brl.setSpacing(8)
        self.btn_file   = Btn(_tr("sel_file"))
        self.btn_folder = Btn(_tr("sel_folder"))
        self.btn_scan   = Btn(_tr("run_scan"), bg=SUCCESS)
        self.btn_scan.setEnabled(False)
        brl.addWidget(self.btn_file); brl.addWidget(self.btn_folder)
        brl.addWidget(self.btn_scan); brl.addStretch()
        b2vl.addWidget(br)
        self.drop = DropZone(b2); b2vl.addWidget(self.drop)
        vl.addWidget(f2); vl.addStretch()

        self.btn_file.clicked.connect(self.mw.select_file)
        self.btn_folder.clicked.connect(self.mw.select_folder)
        self.btn_scan.clicked.connect(self.mw.start_scan)
        self.drop.files_dropped.connect(self.mw.on_files_dropped)
        self.drop.open_dialog.connect(self.mw.select_file)

        scroll.setWidget(w)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0); ol.addWidget(scroll)

    def update_scan_btn(self):
        self.btn_scan.setEnabled(bool(self.mw.scan_paths) and self.mw.model_loaded)

    def update_metrics(self, total, threats, clean, last=""):
        self.mc_total.animate_to(total); self.mc_threats.animate_to(threats)
        self.mc_clean.animate_to(clean)
        if last: self.mc_last.animate_to(last)


class ScanPage(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent); self.mw = mw
        self.setStyleSheet(f"background:{BG};"); self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)

        f0, b0 = _card(self, _tr("files_sel"))
        b0vl = QVBoxLayout(b0); b0vl.setContentsMargins(20,12,20,14); b0vl.setSpacing(8)
        row0 = QWidget(b0); row0.setStyleSheet(f"background:{CARD};")
        r0hl = QHBoxLayout(row0); r0hl.setContentsMargins(0,0,0,0); r0hl.setSpacing(8)
        self.btn_file2   = Btn(_tr("sel_file"))
        self.btn_folder2 = Btn(_tr("sel_folder"))
        self.btn_start   = Btn(_tr("start_scan"), bg=SUCCESS); self.btn_start.setEnabled(False)
        r0hl.addWidget(self.btn_file2); r0hl.addWidget(self.btn_folder2)
        r0hl.addWidget(self.btn_start); r0hl.addStretch()
        b0vl.addWidget(row0)
        self._sel_label = QLabel(_tr("no_files"), b0)
        self._sel_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        b0vl.addWidget(self._sel_label); vl.addWidget(f0)

        f, b = _card(self, _tr("scan_prog"))
        pvl = QVBoxLayout(b); pvl.setContentsMargins(20,14,20,14); pvl.setSpacing(6)
        row1 = QWidget(b); row1.setStyleSheet(f"background:{CARD};")
        r1hl = QHBoxLayout(row1); r1hl.setContentsMargins(0,0,0,0)
        self._prog_lbl = QLabel(_tr("ready"), row1)
        self._prog_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        self._prog_pct = QLabel("", row1)
        self._prog_pct.setStyleSheet(f"color:{ACCENT}; font-size:20pt; font-weight:700; background:transparent;")
        r1hl.addWidget(self._prog_lbl); r1hl.addStretch(); r1hl.addWidget(self._prog_pct)
        pvl.addWidget(row1)
        self._prog_file = QLabel("", b)
        self._prog_file.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent; font-family: 'JetBrains Mono';")
        pvl.addWidget(self._prog_file)
        self._pbar = QProgressBar(b); self._pbar.setRange(0,100); self._pbar.setValue(0)
        self._pbar.setTextVisible(False)
        self._pbar_anim = QPropertyAnimation(self._pbar, b"value", self)
        self._pbar_anim.setDuration(250); self._pbar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        pvl.addWidget(self._pbar)
        self._time_lbl = QLabel("", b)
        self._time_lbl.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        pvl.addWidget(self._time_lbl)
        ctrl = QWidget(b); ctrl.setStyleSheet(f"background:{CARD};")
        chl = QHBoxLayout(ctrl); chl.setContentsMargins(0,8,0,0); chl.setSpacing(8)
        self.btn_cancel = Btn(_tr("cancel"), bg=DANGER, fg="#fff", small=True)
        self.btn_pause  = Btn(_tr("pause"), small=True)
        self.btn_clear  = GhostBtn(_tr("clear"), small=True)
        self.btn_cancel.setEnabled(False); self.btn_pause.setEnabled(False)
        chl.addWidget(self.btn_cancel); chl.addWidget(self.btn_pause)
        chl.addStretch(); chl.addWidget(self.btn_clear)
        pvl.addWidget(ctrl); vl.addWidget(f)

        rf, rb = _card(self, _tr("scan_res"), _tr("sorted_by"))
        rvl = QVBoxLayout(rb); rvl.setContentsMargins(20,10,20,10)
        self._table = QTableWidget(0, 3, rb)
        self._table.setHorizontalHeaderLabels([_tr("th_file"), _tr("th_verdict"), _tr("th_prob")])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1,110); self._table.setColumnWidth(2,105)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False); self._table.setAlternatingRowColors(True)
        rvl.addWidget(self._table); vl.addWidget(rf, 1)
        self._stats = QLabel("", self)
        self._stats.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        vl.addWidget(self._stats)

        self.btn_file2.clicked.connect(self.mw.select_file)
        self.btn_folder2.clicked.connect(self.mw.select_folder)
        self.btn_start.clicked.connect(self.mw.start_scan)
        self.btn_cancel.clicked.connect(self.mw.cancel_scanning)
        self.btn_pause.clicked.connect(self.mw.toggle_pause)
        self.btn_clear.clicked.connect(self.mw.clear_results)

    def update_sel_label(self, text: str):
        self._sel_label.setText(text)
        ok = bool(self.mw.scan_paths) and self.mw.model_loaded
        self.btn_start.setEnabled(ok)

    def reset(self):
        self._table.setRowCount(0); self._pbar.setValue(0)
        self._prog_lbl.setText(_tr("ready"))
        self._prog_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        self._prog_pct.setText(""); self._prog_file.setText("")
        self._time_lbl.setText(""); self._stats.setText("")

    def update_progress(self, idx, total, elapsed, remaining, fname):
        pct = int((idx+1)/total*100)
        self._pbar_anim.stop()
        self._pbar_anim.setStartValue(self._pbar.value())
        self._pbar_anim.setEndValue(pct); self._pbar_anim.start()
        self._prog_lbl.setText(f"Scanning  {idx+1} of {total}")
        self._prog_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self._prog_pct.setText(f"{pct}%")
        self._prog_file.setText(fname)
        self._time_lbl.setText(f"Elapsed: {elapsed:.1f}s   |   ETA: {remaining:.1f}s")

    def add_result(self, r: dict, delay_ms: int = 0):
        def _do():
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setRowHeight(row, 32)
            is_m, is_e = r.get("is_malware",False), r.get("err",False)
            bg = QColor(255,71,87,50) if is_m else (QColor(246,201,14,40) if is_e else QColor(46,213,115,30))
            fg = QColor(DANGER) if is_m else (QColor(WARN) if is_e else QColor(SUCCESS))
            for col, txt in enumerate([r["file"], r["verdict"], r["prob"]]):
                item = QTableWidgetItem(txt)
                item.setBackground(bg)
                item.setForeground(fg if col==1 else QColor(TEXT))
                self._table.setItem(row, col, item)
            self._table.scrollToBottom()
        QTimer.singleShot(delay_ms, _do)

    def finalize(self, stats: str):
        self._pbar_anim.stop(); self._pbar.setValue(100)
        self._prog_lbl.setText(_tr("complete"))
        self._prog_lbl.setStyleSheet(f"color:{SUCCESS}; background:transparent;")
        self._prog_pct.setText("100%"); self._prog_file.setText("")
        self._stats.setText(stats)

    def set_cancelled(self):
        self._prog_lbl.setText(_tr("cancelled"))
        self._prog_lbl.setStyleSheet(f"color:{WARN}; background:transparent;")
        self._prog_file.setText("")


class MonitorPage(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw; self.setStyleSheet(f"background:{BG};")
        self._pulse_on = False
        self._ptimer = QTimer(self); self._ptimer.timeout.connect(self._blink)
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)

        sf, sb = _card(self, _tr("mon_settings"))
        svl = QVBoxLayout(sb); svl.setContentsMargins(20,14,20,14); svl.setSpacing(10)
        lbl = QLabel(_tr("watch_path"), sb)
        lbl.setStyleSheet(f"color:{MUTED}; font-size:8pt; font-weight:600; background:transparent;")
        svl.addWidget(lbl)
        pr = QWidget(sb); pr.setStyleSheet(f"background:{CARD};")
        prl = QHBoxLayout(pr); prl.setContentsMargins(0,0,0,0); prl.setSpacing(8)
        self.path_edit  = QLineEdit(self.mw.monitor_pref_path or "C:\\", pr)
        self.btn_browse = Btn(_tr("browse"), small=True)
        prl.addWidget(self.path_edit, 1); prl.addWidget(self.btn_browse)
        svl.addWidget(pr)
        cr = QWidget(sb); cr.setStyleSheet(f"background:{CARD};")
        crl = QHBoxLayout(cr); crl.setContentsMargins(0,0,0,0); crl.setSpacing(8)
        self.btn_monitor  = Btn(_tr("start_mon"), bg=SUCCESS)
        self.btn_scan_dir = Btn(_tr("scan_dir"))
        self.btn_del      = Btn(_tr("delete"), bg=DANGER, fg="#fff", small=True)
        crl.addWidget(self.btn_monitor); crl.addWidget(self.btn_scan_dir)
        crl.addWidget(self.btn_del); crl.addStretch()
        sw = QWidget(cr); sw.setStyleSheet(f"background:{CARD};")
        sl = QHBoxLayout(sw); sl.setContentsMargins(0,0,0,0); sl.setSpacing(5)
        self._dot  = QLabel("●", sw)
        self._dot.setStyleSheet(f"color:{MUTED}; font-size:13pt; background:transparent;")
        self._slbl = QLabel(_tr("inactive"), sw)
        self._slbl.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        sl.addWidget(self._dot); sl.addWidget(self._slbl)
        crl.addWidget(sw); svl.addWidget(cr); vl.addWidget(sf)

        af, ab = _card(self, _tr("net_agents"))
        avl = QVBoxLayout(ab); avl.setContentsMargins(20,12,20,12); avl.setSpacing(6)
        ar = QWidget(ab); ar.setStyleSheet(f"background:{CARD};")
        arl = QHBoxLayout(ar); arl.setContentsMargins(0,0,0,0); arl.setSpacing(8)
        self._agent_dot     = QLabel("●", ar)
        self._agent_dot.setStyleSheet(f"color:{SUCCESS}; font-size:11pt; background:transparent;")
        self._agent_srv_lbl = QLabel(f"{_tr('agent_srv')}: UDP port {AGENT_PORT}  ●  active", ar)
        self._agent_srv_lbl.setStyleSheet(f"color:{TEXT}; font-size:9pt; background:transparent;")
        self._agent_my_ip   = QLabel("", ar)
        self._agent_my_ip.setStyleSheet(f"color:{ACCENT}; font-size:9pt; background:transparent;")
        arl.addWidget(self._agent_dot); arl.addWidget(self._agent_srv_lbl)
        arl.addStretch(); arl.addWidget(self._agent_my_ip)
        avl.addWidget(ar)
        self._agents_list = QLabel(_tr("no_agents"), ab)
        self._agents_list.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        avl.addWidget(self._agents_list); vl.addWidget(af)

        lf, lb = _card(self, _tr("live_events"), _tr("realtime"))
        lvl = QVBoxLayout(lb); lvl.setContentsMargins(20,10,20,14)
        self._log = QTextEdit(lb); self._log.setReadOnly(True)
        lvl.addWidget(self._log); vl.addWidget(lf, 1)

        self.btn_browse.clicked.connect(self.mw.browse_monitor_path)
        self.btn_monitor.clicked.connect(self.mw.toggle_monitoring)
        self.btn_scan_dir.clicked.connect(self.mw.scan_selected_directory)
        self.btn_del.clicked.connect(self.mw.delete_selected)

    @property
    def path(self): return self.path_edit.text().strip()

    def set_monitoring(self, on: bool, path_name: str = ""):
        if on:
            self.btn_monitor.setStyleSheet(self.btn_monitor.styleSheet()
                .replace(SUCCESS, DANGER).replace(_dk(SUCCESS), _dk(DANGER))
                .replace(_dk(SUCCESS,38), _dk(DANGER,38)))
            self.btn_monitor.setText(_tr("stop_mon"))
            self._slbl.setText(f"{_tr('watching')}: {path_name}")
            self._slbl.setStyleSheet(f"color:{SUCCESS}; font-size:9pt; background:transparent;")
            self._dot.setStyleSheet(f"color:{SUCCESS}; font-size:13pt; background:transparent;")
            self._ptimer.start(650)
        else:
            self.btn_monitor.setStyleSheet(self.btn_monitor.styleSheet()
                .replace(DANGER, SUCCESS).replace(_dk(DANGER), _dk(SUCCESS))
                .replace(_dk(DANGER,38), _dk(SUCCESS,38)))
            self.btn_monitor.setText(_tr("start_mon"))
            self._slbl.setText(_tr("inactive"))
            self._slbl.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
            self._dot.setStyleSheet(f"color:{MUTED}; font-size:13pt; background:transparent;")
            self._ptimer.stop()

    def update_agent_server_ip(self, ip: str):
        self._agent_my_ip.setText(f"{_tr('my_ip')}: {ip}  (--server {ip})")

    def update_agents(self, agents: dict):
        if not agents:
            self._agents_list.setText(_tr("no_agents")); return
        parts = [f"● {info['hostname']}  ({ip})" for ip, info in agents.items()]
        self._agents_list.setText("   |   ".join(parts))

    def _blink(self):
        self._pulse_on = not self._pulse_on
        c = SUCCESS if self._pulse_on else MUTED
        self._dot.setStyleSheet(f"color:{c}; font-size:13pt; background:transparent;")

    def append_log(self, msg: str, tag: str = "clean"):
        ts = datetime.now().strftime("%H:%M:%S")
        cur = self._log.textCursor(); cur.movePosition(cur.MoveOperation.End)
        fmt_ts = QTextCharFormat(); fmt_ts.setForeground(QColor(MUTED))
        cur.setCharFormat(fmt_ts); cur.insertText(f"[{ts}]  ")
        fmt = QTextCharFormat()
        if   tag == "malware": fmt.setForeground(QColor(DANGER)); fmt.setFontWeight(QFont.Weight.Bold)
        elif tag == "clean":   fmt.setForeground(QColor(SUCCESS))
        elif tag == "info":    fmt.setForeground(QColor(ACCENT))
        else:                  fmt.setForeground(QColor(TEXT))
        cur.setCharFormat(fmt); cur.insertText(msg + "\n")
        self._log.setTextCursor(cur); self._log.ensureCursorVisible()


class LogPage(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent); self.mw = mw
        self.setStyleSheet(f"background:{BG};"); self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)
        ff, fb = _card(self)
        fhl = QHBoxLayout(fb); fhl.setContentsMargins(20,12,20,12); fhl.setSpacing(10)
        lbl = QLabel(_tr("period"), fb)
        lbl.setStyleSheet(f"color:{MUTED}; font-size:8pt; font-weight:600; background:transparent;")
        fhl.addWidget(lbl)
        self._period = QComboBox(fb); self._period.addItems(["today","24h","7d","30d","all"])
        fhl.addWidget(self._period)
        self.btn_ref = Btn(_tr("refresh"), small=True); fhl.addWidget(self.btn_ref)
        fhl.addStretch()
        self._summary = QLabel(f"{_tr('threats_lbl')}: 0", fb)
        self._summary.setStyleSheet(f"color:{DANGER}; font-size:11pt; font-weight:600; background:transparent;")
        fhl.addWidget(self._summary); vl.addWidget(ff)

        tf, tb = _card(self, _tr("event_log"), _tr("det_hist"))
        tvl = QVBoxLayout(tb); tvl.setContentsMargins(20,10,20,10)
        self._table = QTableWidget(0, 4, tb)
        self._table.setHorizontalHeaderLabels([_tr("th_ts"), _tr("th_file"), _tr("th_result"), _tr("th_source")])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0,175); self._table.setColumnWidth(2,120)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False); self._table.setAlternatingRowColors(True)
        tvl.addWidget(self._table); vl.addWidget(tf, 1)

        act = QWidget(self); act.setStyleSheet(f"background:{BG};")
        ahl = QHBoxLayout(act); ahl.setContentsMargins(0,0,0,0); ahl.setSpacing(8)
        ahl.addStretch()
        self.btn_open = GhostBtn(_tr("open_folder"), small=True)
        self.btn_del  = Btn(_tr("del_file"), bg=DANGER, fg="#fff", small=True)
        ahl.addWidget(self.btn_open); ahl.addWidget(self.btn_del); vl.addWidget(act)

        self.btn_ref.clicked.connect(self.mw.refresh_log)
        self._period.currentTextChanged.connect(lambda _: self.mw.refresh_log())
        self.btn_open.clicked.connect(self.mw.open_selected_folder)
        self.btn_del.clicked.connect(self.mw.delete_selected)

    @property
    def period(self): return self._period.currentText()

    @property
    def selected_record(self):
        sel = self._table.selectedItems()
        if not sel: return None
        r = sel[0].row()
        return (self._table.item(r,0).text(), self._table.item(r,1).text(),
                self._table.item(r,2).text(), self._table.item(r,3).text())

    def populate(self, records):
        self._table.setRowCount(0); vc = 0
        for rec in records:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setRowHeight(row, 32)
            mal = rec.get("malware", False)
            if mal: vc += 1
            bg  = QColor(255,71,87,50) if mal else QColor(0,0,0,0)
            fcr = QColor(DANGER) if mal else QColor(SUCCESS)
            source = rec.get("source", "Local")
            for col, txt in enumerate([rec["time"], rec["path"], rec["status"], source]):
                item = QTableWidgetItem(txt)
                item.setBackground(bg)
                item.setForeground(fcr if col==2 else (QColor(ACCENT) if col==3 and source!="Local" else QColor(TEXT)))
                self._table.setItem(row, col, item)
        self._summary.setText(f"{_tr('threats_lbl')}: {vc}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Malware Detector")
        self._dark = True
        self._lang = "en"
        self.detector = None; self.model_loaded = False
        self.scan_paths: list = []; self.scanning = False; self.paused = False
        self.pause_event = threading.Event(); self.pause_event.set()
        self.monitoring = False; self.observer = None
        self.log_file_path = Path(__file__).parent.parent / "logs" / "antivirus.log"
        self.monitor_pref_path = self._load_monitor_pref()
        self.total_scanned = 0; self.total_threats = 0
        self._bridge = WatchdogBridge(); self._bridge.new_file.connect(self._handle_new_file)
        self._agent_bridge = AgentBridge(); self._agent_bridge.agent_event.connect(self._handle_agent_event)
        self._file_bridge  = FileBridge();  self._file_bridge.file_ready.connect(self._handle_received_file)
        self._seen_agents: dict[str, dict] = {}
        self._pending_sources: dict[str, str] = {}
        self._qthread: QThread | None = None; self._worker: ScanWorker | None = None
        self._load_model_silent()
        self._build_ui()
        self._overlay = ThemeOverlay(self)
        screen = QApplication.primaryScreen().availableGeometry()
        w = max(1140, int(screen.width()*.72)); h = max(720, int(screen.height()*.78))
        self.resize(w,h); self.move((screen.width()-w)//2, (screen.height()-h)//2)
        threading.Thread(target=self._run_agent_server, daemon=True).start()
        threading.Thread(target=self._run_file_server,  daemon=True).start()
        self._update_my_ip()
        if not self.model_loaded:
            QTimer.singleShot(400, lambda: QMessageBox.warning(
                self, "Model Not Found",
                "Model file not found.\n\nTrain it:\n  python src/train_model.py"))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, '_overlay'): self._overlay.setGeometry(self.rect())

    # ── UI build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        root.setStyleSheet(f"background:{BG};"); self.setCentralWidget(root)
        mvl = QVBoxLayout(root); mvl.setContentsMargins(0,0,0,0); mvl.setSpacing(0)

        hdr = QFrame(root); hdr.setObjectName("hdr_frame"); hdr.setFixedHeight(56)
        hhl = QHBoxLayout(hdr); hhl.setContentsMargins(24,0,16,0); hhl.setSpacing(8)
        icon = QLabel("◈", hdr)
        icon.setStyleSheet(f"color:{ACCENT}; font-size:16pt; background:transparent;")
        app  = QLabel("  MALWARE DETECTOR", hdr)
        app.setStyleSheet(f"font-size:13pt; font-weight:700; color:#C8D8FF; background:transparent;")
        ver_bg = "#071630" if _DARK else "#DCF0FF"
        ver  = QLabel(" v1.0 ", hdr)
        ver.setStyleSheet(f"background:{ver_bg}; color:{ACCENT}; font-size:8pt; padding:2px 6px; border-radius:3px; border: none; font-family: 'JetBrains Mono';")
        hhl.addWidget(icon); hhl.addWidget(app); hhl.addWidget(ver); hhl.addStretch()

        ok_c = SUCCESS if self.model_loaded else DANGER
        if _DARK:
            ok_b = "#071810" if self.model_loaded else "#1E0808"
        else:
            ok_b = "#D4F7E5" if self.model_loaded else "#FFE4E4"
            ok_c = "#15803D" if self.model_loaded else "#B91C1C"
        ok_t = _tr("protected") if self.model_loaded else _tr("at_risk")
        pill = QLabel(ok_t, hdr)
        pill.setStyleSheet(f"background:{ok_b}; color:{ok_c}; font-weight:600;"
                           f" font-size:9pt; padding:4px 10px; border-radius:4px; border: none;")
        hhl.addSpacing(12)
        hhl.addWidget(pill)
        hhl.addSpacing(10)

        # language toggle
        cur_lang = "RU" if self._lang == "en" else "EN"
        self._lang_btn = IconBtn(cur_lang)
        self._lang_btn.setToolTip("Switch language / Сменить язык")
        self._lang_btn.clicked.connect(self.toggle_language)
        hhl.addWidget(self._lang_btn)

        # theme toggle
        self._theme_btn = IconBtn("☀" if self._dark else "☾")
        self._theme_btn.setToolTip("Toggle light/dark theme")
        self._theme_btn.clicked.connect(self.toggle_theme)
        hhl.addWidget(self._theme_btn)
        hhl.addSpacing(8)

        mvl.addWidget(hdr)

        body = QWidget(root); body.setStyleSheet(f"background:{BG};")
        bhl  = QHBoxLayout(body); bhl.setContentsMargins(0,0,0,0); bhl.setSpacing(0)

        sb = QFrame(body); sb.setObjectName("sidebar"); sb.setFixedWidth(220)
        svl = QVBoxLayout(sb); svl.setContentsMargins(0,18,0,18); svl.setSpacing(0)
        nav_lbl = QLabel("NAVIGATION", sb)
        nav_lbl.setStyleSheet(f"color:{MUTED}; font-size:8pt; font-weight:600;")
        nav_lbl.setContentsMargins(20,0,0,8); svl.addWidget(nav_lbl)
        self._nav: dict[str, NavButton] = {}
        for (ic, lbl), key in zip(_tr("nav"), ["dashboard","scan","monitor","log"]):
            nb = NavButton(ic, lbl, key, sb); nb.clicked.connect(self._switch_tab)
            svl.addWidget(nb); self._nav[key] = nb
        svl.addStretch()
        sep = QFrame(sb); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; margin:0 16px;"); svl.addWidget(sep)
        ec = SUCCESS if self.model_loaded else DANGER
        et = _tr("engine_on") if self.model_loaded else _tr("engine_off")
        el = QLabel(f"● {et}", sb); el.setContentsMargins(20,12,0,2)
        el.setStyleSheet(f"color:{ec}; font-size:9pt; background:transparent;")
        sl2 = QLabel(_tr("engine_sub"), sb); sl2.setContentsMargins(20,0,0,0)
        sl2.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        svl.addWidget(el); svl.addWidget(sl2)
        bhl.addWidget(sb)

        vs = QFrame(body); vs.setObjectName("vsep"); vs.setFixedWidth(1)
        vs.setStyleSheet(f"background:{BORDER};"); bhl.addWidget(vs)

        self._stack = QStackedWidget(body)
        self._stack.setStyleSheet(f"background:{BG};"); bhl.addWidget(self._stack,1)
        mvl.addWidget(body, 1)

        self.dashboard    = DashboardPage(self)
        self.scan_page    = ScanPage(self)
        self.monitor_page = MonitorPage(self)
        self.log_page     = LogPage(self)
        for p in (self.dashboard, self.scan_page, self.monitor_page, self.log_page):
            self._stack.addWidget(p)
        self._switch_tab("dashboard")

    def _switch_tab(self, key: str):
        idx = {"dashboard":0,"scan":1,"monitor":2,"log":3}
        self._stack.setCurrentIndex(idx[key])
        for k, nb in self._nav.items(): nb.set_active(k==key)
        if key == "log": self.refresh_log()

    # ── Theme & language ──────────────────────────────────────────────────────
    def toggle_theme(self):
        pixmap = self.grab()
        self._dark = not self._dark
        global _DARK
        _DARK = self._dark
        _apply_palette(self._dark)
        QApplication.instance().setStyleSheet(_build_qss())
        self._rebuild_ui()
        self._overlay.crossfade(pixmap, duration_ms=460)

    def toggle_language(self):
        pixmap = self.grab()
        global _LANG
        _LANG = "ru" if self._lang == "en" else "en"
        self._lang = _LANG
        self._rebuild_ui()
        self._overlay.crossfade(pixmap, duration_ms=220)

    def _rebuild_ui(self):
        tab = ["dashboard","scan","monitor","log"][self._stack.currentIndex()]
        mon = self.monitoring; mon_path = self.monitor_pref_path
        ts = self.total_scanned; tt = self.total_threats
        self._build_ui()
        self._overlay = ThemeOverlay(self)
        self._switch_tab(tab)
        self.dashboard.update_metrics(ts, tt, ts - tt)
        if mon:
            self.monitor_page.set_monitoring(True, Path(mon_path).name if mon_path else "")
        self._update_my_ip()
        if self._seen_agents:
            self.monitor_page.update_agents(self._seen_agents)

    # ── File selection ────────────────────────────────────────────────────────
    def _update_scan_paths(self, paths, label):
        self.scan_paths = paths
        self.dashboard.update_scan_btn()
        self.scan_page.update_sel_label(label)
        self.dashboard.drop.set_text(label)

    def select_file(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Select file to scan", "",
            "PE Files (*.exe *.dll *.sys);;All files (*.*)")
        if fp: self._update_scan_paths([Path(fp)], f"Selected: {Path(fp).name}")

    def select_folder(self):
        fd = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if fd:
            files = []
            for ext in ("*.exe","*.dll","*.sys","*.EXE","*.DLL","*.SYS"):
                files.extend(Path(fd).rglob(ext))
            if files:
                self._update_scan_paths(files, f"{Path(fd).name} — {len(files)} files found")
            else:
                QMessageBox.information(self, "No PE Files",
                    "No .exe / .dll / .sys files found in the selected folder.")

    def on_files_dropped(self, files):
        self._update_scan_paths(files, f"Dropped: {len(files)} file(s)")

    def browse_monitor_path(self):
        fd = QFileDialog.getExistingDirectory(self, "Select folder to monitor")
        if fd: self.monitor_page.path_edit.setText(fd)

    # ── Scan ──────────────────────────────────────────────────────────────────
    def start_scan(self):
        if not self.model_loaded:
            QMessageBox.critical(self,"Error","Model not loaded!"); return
        if not self.scan_paths:
            QMessageBox.warning(self,"Warning","No files selected!"); return
        self._switch_tab("scan"); self.scan_page.reset()
        self.scanning = True; self.paused = False; self.pause_event.set()
        self.scan_page.btn_cancel.setEnabled(True)
        self.scan_page.btn_pause.setEnabled(True)
        self.scan_page.btn_start.setEnabled(False)
        self.dashboard.btn_scan.setEnabled(False)
        self.dashboard.shield.set_active(True)
        self._qthread = QThread()
        self._worker  = ScanWorker(self.scan_paths, self.detector, self.pause_event)
        self._worker.moveToThread(self._qthread)
        self._qthread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._qthread.quit)
        self._qthread.start()

    @pyqtSlot(int,int,float,float,str)
    def _on_progress(self, idx, total, elapsed, remaining, fname):
        self.scan_page.update_progress(idx, total, elapsed, remaining, fname)

    @pyqtSlot(list)
    def _on_finished(self, results):
        self.scanning = False
        self.scan_page.btn_cancel.setEnabled(False)
        self.scan_page.btn_pause.setEnabled(False)
        self.scan_page.btn_pause.setText(_tr("pause"))
        ok = bool(self.scan_paths) and self.model_loaded
        self.scan_page.btn_start.setEnabled(ok)
        self.dashboard.btn_scan.setEnabled(ok)
        self.dashboard.shield.set_active(self.monitoring)
        results.sort(key=lambda x: (not x.get("is_malware"), x.get("file","")))
        for i, r in enumerate(results):
            self.scan_page.add_result(r, delay_ms=min(i*15, 450))
        m = sum(1 for r in results if r.get("is_malware"))
        c = sum(1 for r in results if not r.get("is_malware") and not r.get("err"))
        e = sum(1 for r in results if r.get("err"))
        self.total_scanned += len(results); self.total_threats += m
        self.dashboard.update_metrics(
            self.total_scanned, self.total_threats,
            self.total_scanned-self.total_threats, datetime.now().strftime("%H:%M"))
        self.scan_page.finalize(
            f"Total: {len(results)}   |   Threats: {m}   |   Clean: {c}   |   Errors: {e}")
        if m > 0:
            QMessageBox.warning(self,"Threats Detected",
                f"{m} threat{'s' if m>1 else ''} detected!\nReview results below.")

    def cancel_scanning(self):
        if self._worker: self._worker.cancel_flag = True
        self.scanning = False; self.paused = False; self.pause_event.set()
        self.scan_page.btn_cancel.setEnabled(False)
        self.scan_page.btn_pause.setEnabled(False)
        self.scan_page.set_cancelled()
        ok = bool(self.scan_paths) and self.model_loaded
        self.scan_page.btn_start.setEnabled(ok)
        self.dashboard.btn_scan.setEnabled(ok)
        self.dashboard.shield.set_active(self.monitoring)

    def toggle_pause(self):
        if not self.scanning: return
        if self.paused:
            self.paused = False; self.pause_event.set()
            self.scan_page.btn_pause.setText(_tr("pause"))
        else:
            self.paused = True; self.pause_event.clear()
            self.scan_page.btn_pause.setText(_tr("resume"))

    def clear_results(self):
        if self.scanning:
            QMessageBox.information(self,"Info","Cancel the current scan first."); return
        self.scan_paths = []; self.scan_page.reset()
        self.scan_page.btn_start.setEnabled(False)
        self.scan_page.update_sel_label(_tr("no_files"))
        self.dashboard.update_scan_btn(); self.dashboard.drop.set_text(None)

    # ── Monitor ───────────────────────────────────────────────────────────────
    def toggle_monitoring(self):
        if self.monitoring: self.stop_monitoring()
        else: self.start_monitoring()

    def start_monitoring(self):
        if not self.model_loaded:
            QMessageBox.critical(self,"Error","Model not loaded!"); return
        if not WATCHDOG_AVAILABLE:
            QMessageBox.critical(self,"Error","watchdog not installed.\npip install watchdog"); return
        rp = Path(self.monitor_page.path or "C:\\")
        if not rp.exists():
            QMessageBox.critical(self,"Error",f"Path not found:\n{rp}"); return
        try:
            self.monitoring = True
            self._save_monitor_pref(str(rp))
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_file_path.touch(exist_ok=True)
            self.observer = Observer()
            self.observer.schedule(MonitorEventHandler(self._bridge), str(rp), recursive=True)
            self.observer.daemon = True; self.observer.start()
            self.monitor_page.set_monitoring(True, rp.name)
            self.dashboard.shield.set_active(True)
            self.refresh_log()
            self.monitor_page.append_log(f"Monitoring started: {rp}", "info")
        except Exception as ex:
            self.monitoring = False
            self.observer = None
            QMessageBox.critical(self, "Error", f"Failed to start monitoring:\n{ex}")

    def stop_monitoring(self):
        self.monitoring = False
        if self.observer:
            try: self.observer.stop(); self.observer.join(timeout=2)
            except Exception: pass
            self.observer = None
        self.monitor_page.set_monitoring(False)
        self.dashboard.shield.set_active(self.scanning)
        self.monitor_page.append_log("Monitoring stopped", "info")

    @pyqtSlot(str)
    def _handle_new_file(self, fp: str):
        p = Path(fp)
        if p.suffix.lower() not in PE_EXT: return
        source = self._pending_sources.pop(p.name, "Local")
        threading.Thread(target=self._scan_new_file, args=(p, source), daemon=True).start()

    def _scan_new_file(self, fp: Path, source_pc: str = "Local", display_path: str = ""):
        try:
            r = self.detector.check_file(str(fp))
            if "error" in r: return
            malware  = bool(r.get("is_malware",False))
            ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status   = "VIRUS FOUND" if malware else "CLEAN"
            log_path = display_path or str(fp)
            try:
                with open(self.log_file_path,"a",encoding="utf-8") as f:
                    f.write(f"[{ts}] SCANNED | {log_path} | {status} | {source_pc}\n")
            except Exception: pass
            tag     = "malware" if malware else "clean"
            src_tag = f"  [{source_pc}]" if source_pc != "Local" else ""
            verdict = "THREAT DETECTED" if malware else "Clean"
            fname   = Path(log_path).name
            QTimer.singleShot(0, lambda: self.monitor_page.append_log(
                f"{fname}{src_tag}  —  {verdict}", tag))
            QTimer.singleShot(0, self.refresh_log)
        except Exception: pass

    def scan_selected_directory(self):
        fd = QFileDialog.getExistingDirectory(self, "Select directory to scan")
        if not fd: return
        files = []
        for ext in ("*.exe","*.dll","*.sys","*.EXE","*.DLL","*.SYS"):
            files.extend(Path(fd).rglob(ext))
        if not files:
            QMessageBox.information(self,"Info","No PE files found."); return
        self._update_scan_paths(files, f"{Path(fd).name} — {len(files)} files")
        self._switch_tab("scan"); self.start_scan()

    # ── Agent server ──────────────────────────────────────────────────────────
    def _update_my_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        except Exception: ip = "unavailable"
        QTimer.singleShot(0, lambda: self.monitor_page.update_agent_server_ip(ip))

    def _run_agent_server(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", AGENT_PORT))
            while True:
                try:
                    data, _ = sock.recvfrom(8192)
                    event = json.loads(data.decode("utf-8"))
                    self._agent_bridge.agent_event.emit(event)
                except Exception: pass
        except Exception as ex:
            QTimer.singleShot(0, lambda: self.monitor_page.append_log(
                f"Agent server error: {ex}", "info"))

    def _run_file_server(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", FILE_PORT)); srv.listen(10)
            while True:
                try:
                    conn, _ = srv.accept()
                    threading.Thread(target=self._receive_file, args=(conn,), daemon=True).start()
                except Exception: pass
        except Exception as ex:
            QTimer.singleShot(0, lambda: self.monitor_page.append_log(
                f"File server error: {ex}", "info"))

    def _receive_file(self, conn):
        import tempfile
        try:
            raw = self._recvall(conn, 4)
            if not raw: return
            hlen   = int.from_bytes(raw, "big")
            header = json.loads(self._recvall(conn, hlen).decode("utf-8"))
            hostname      = header.get("hostname", "unknown")
            ip            = header.get("ip", "?")
            filename      = header.get("filename", "file.exe")
            filesize      = header.get("filesize", 0)
            source        = f"{ip} · {hostname}"
            original_path = header.get("filepath", filename)
            data = self._recvall(conn, filesize)
            tmpdir   = Path(tempfile.mkdtemp())
            tmp_path = tmpdir / filename
            tmp_path.write_bytes(data)
            self._file_bridge.file_ready.emit(str(tmp_path), source, original_path)
        except Exception: pass
        finally: conn.close()

    def _recvall(self, conn, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = conn.recv(min(n - len(data), 65536))
            if not chunk: break
            data += chunk
        return data

    @pyqtSlot(dict)
    def _handle_agent_event(self, event: dict):
        hostname = event.get("hostname", "unknown")
        ip       = event.get("ip", "?")
        mac      = event.get("mac", "?")
        filename = event.get("filename", "?")
        source   = f"{ip} · {hostname}"
        self._seen_agents[ip] = {"hostname": hostname, "mac": mac}
        self.monitor_page.update_agents(self._seen_agents)
        self._pending_sources[filename] = source
        self.monitor_page.append_log(f"{filename}  [{source}]  — agent report", "info")

    @pyqtSlot(str, str, str)
    def _handle_received_file(self, tmp_path: str, source_pc: str, original_path: str):
        p = Path(tmp_path)
        threading.Thread(
            target=self._scan_and_cleanup, args=(p, source_pc, original_path), daemon=True).start()

    def _scan_and_cleanup(self, tmp_path: Path, source_pc: str, original_path: str = ""):
        try:
            self._scan_new_file(tmp_path, source_pc, display_path=original_path)
        finally:
            try: tmp_path.unlink(); tmp_path.parent.rmdir()
            except Exception: pass

    # ── Log ───────────────────────────────────────────────────────────────────
    def refresh_log(self):
        records = []
        if self.log_file_path.exists():
            for line in self.log_file_path.read_text(encoding="utf-8",errors="ignore").splitlines():
                if "SCANNED |" not in line: continue
                try:
                    ts = line[1:20]; rest = line.split("SCANNED |",1)[1].strip()
                    parts  = [x.strip() for x in rest.split("|")]
                    path   = parts[0]
                    status = parts[1] if len(parts) > 1 else "UNKNOWN"
                    source = parts[2] if len(parts) > 2 else "Local"
                    records.append({"time":ts,"path":path,"status":status,
                                    "source":source,"malware":status=="VIRUS FOUND"})
                except Exception: continue
        delta = {"24h":86400,"7d":604800,"30d":2592000}.get(self.log_page.period)
        if self.log_page.period == "today":
            n = datetime.now(); delta=(n-datetime(n.year,n.month,n.day)).total_seconds()
        if delta is not None:
            now = datetime.now().timestamp()
            records = [r for r in records if self._in_delta(r,now,delta)]
        self.log_page.populate(records)

    def _in_delta(self, rec, now, delta):
        try: return datetime.strptime(rec["time"],"%Y-%m-%d %H:%M:%S").timestamp() >= now-delta
        except Exception: return True

    def open_selected_folder(self):
        rec = self.log_page.selected_record
        if not rec: QMessageBox.warning(self,"Warning","Select a log entry first."); return
        try: os.startfile(str(Path(rec[1]).parent))
        except Exception as ex: QMessageBox.critical(self,"Error",f"Cannot open folder:\n{ex}")

    def delete_selected(self):
        fp = None
        rec = self.log_page.selected_record
        if rec: fp = rec[1]
        else:
            sel = self.scan_page._table.selectedItems()
            if sel: fp = self.scan_page._table.item(sel[0].row(),0).text()
        if not fp: QMessageBox.warning(self,"Warning","Select a file entry first."); return
        ans = QMessageBox.question(self,"Delete File",f"Permanently delete:\n\n{fp}",
              QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes: return
        try: Path(fp).unlink(); QMessageBox.information(self,"Done","File deleted."); self.refresh_log()
        except Exception as ex: QMessageBox.critical(self,"Error",f"Cannot delete:\n{ex}")

    # ── Model ─────────────────────────────────────────────────────────────────
    def _load_model_silent(self):
        try:
            mp = Path(__file__).parent.parent/"model"/"malware_detector.model"
            fp = Path(__file__).parent.parent/"model"/"feature_names.json"
            if mp.exists() and fp.exists():
                self.detector = MalwareDetector(str(mp),str(fp)); self.model_loaded = True
        except Exception: self.model_loaded = False

    def _load_monitor_pref(self):
        try:
            cfg = Path(__file__).parent.parent/"config"/"monitor_path.txt"
            if cfg.exists(): return cfg.read_text(encoding="utf-8").strip()
        except Exception: pass
        return ""

    def _save_monitor_pref(self, path):
        try:
            d = Path(__file__).parent.parent/"config"; d.mkdir(exist_ok=True)
            (d/"monitor_path.txt").write_text(path, encoding="utf-8")
        except Exception: pass

    def closeEvent(self, e):
        self.stop_monitoring()
        if self._qthread and self._qthread.isRunning():
            if self._worker: self._worker.cancel_flag = True
            self.pause_event.set(); self._qthread.quit(); self._qthread.wait(2000)
        e.accept()


# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)

    fonts_dir = Path(__file__).parent.parent / "fonts"
    for ttf in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(ttf))

    app.setFont(QFont("Inter", 10))
    app.setStyleSheet(_build_qss())
    win = MainWindow(); win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
