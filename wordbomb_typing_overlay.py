#!/usr/bin/env python3
"""
WordBomb Typing Overlay (Stable Rounded UI + Embedded Wordlist)
"""

import sys, re, os
from pathlib import Path
from pynput import keyboard
from PyQt5 import QtWidgets, QtCore, QtGui

WORDLIST_CANDIDATES = ["words_alpha.txt", "/usr/share/dict/words"]
SUGGESTION_COUNT = 5
OVERLAY_WIDTH = 480
OVERLAY_HEIGHT = 280

# ---------------- Resource path helper ----------------
def get_resource_path(relative_path):
    """Krijg het correcte pad voor resources, ook in exe via PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------- Wordlist loader ----------------
def load_wordlist():
    for path in WORDLIST_CANDIDATES:
        full_path = get_resource_path(path)
        if Path(full_path).exists():
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return [w.strip().lower() for w in f if w.strip()]
    # fallback
    return ["test", "word", "bomb", "play", "game", "overlay"]

# ---------------- Word suggester ----------------
class WordSuggester:
    def __init__(self, words):
        self.words = sorted(set(words))
    def suggest(self, letters, limit=5):
        if not letters: return []
        results = [w for w in self.words if w.startswith(letters)]
        if not results: return []
        results_sorted = sorted(results, key=lambda x: (len(x), x))
        longest_word = max(results, key=len)
        if longest_word not in results_sorted[:limit]:
            results_sorted = results_sorted[:limit-1] + [longest_word]
        else:
            results_sorted = results_sorted[:limit]
        return results_sorted

# ---------------- Glow Frame ----------------
class GlowFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.glow_active = False
        self.slow_phase = 0.0
        self.fast_phase = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_glow)
        self.timer.start(30)

    def set_glow(self, active: bool):
        self.glow_active = active
        self.update()

    def update_glow(self):
        self.slow_phase += 0.005
        if self.slow_phase > 1.0:
            self.slow_phase = 0.0
        if self.glow_active:
            self.fast_phase += 0.05
            if self.fast_phase > 1.0:
                self.fast_phase = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        # Achtergrond gradient
        bg_grad = QtGui.QLinearGradient(0, 0, 0, rect.height())
        bg_grad.setColorAt(0, QtGui.QColor(25,25,40,230))
        bg_grad.setColorAt(1, QtGui.QColor(10,10,20,220))
        painter.setBrush(QtGui.QBrush(bg_grad))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 14, 14)

        # Rustige animatie (altijd aanwezig)
        border_rect = rect.adjusted(2,2,-2,-2)
        slow_grad = QtGui.QConicalGradient(border_rect.center(), self.slow_phase*360)
        slow_grad.setColorAt(0.0, QtGui.QColor(50,150,180,120))
        slow_grad.setColorAt(0.5, QtGui.QColor(80,180,140,120))
        slow_grad.setColorAt(1.0, QtGui.QColor(50,150,180,120))
        pen = QtGui.QPen(QtGui.QBrush(slow_grad), 3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(border_rect, 14, 14)

        # Actieve glow als woord compleet
        if self.glow_active:
            fast_grad = QtGui.QConicalGradient(border_rect.center(), self.fast_phase*360)
            fast_grad.setColorAt(0.0, QtGui.QColor(0,255,255))
            fast_grad.setColorAt(0.5, QtGui.QColor(0,255,128))
            fast_grad.setColorAt(1.0, QtGui.QColor(0,255,255))
            pen = QtGui.QPen(QtGui.QBrush(fast_grad), 4)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect, 14, 14)

# ---------------- Typing Overlay ----------------
class TypingOverlay(QtWidgets.QWidget):
    update_signal = QtCore.pyqtSignal(str)
    def __init__(self, suggester):
        super().__init__()
        self.suggester = suggester
        self.buffer = ""
        self.hidden_mode = False
        self._build_ui()
        self.update_signal.connect(self.on_update_signal)
        self.show()

    def _build_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.container = GlowFrame(self)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        # Header
        self.header_label = QtWidgets.QLabel("Word Bomb Helper by xHondje")
        font_header = QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold)
        self.header_label.setFont(font_header)
        self.header_label.setStyleSheet("color: #00ff88; background: transparent;")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)

        # Buffer
        self.buffer_label = QtWidgets.QLabel("typed: (empty)")
        font = QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold)
        self.buffer_label.setFont(font)
        self.buffer_label.setStyleSheet("color: #ffd580; background: transparent;")
        layout.addWidget(self.buffer_label)

        # Suggestions
        self.suggest_label = QtWidgets.QLabel("")
        font2 = QtGui.QFont("Segoe UI", 14)
        self.suggest_label.setFont(font2)
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setTextFormat(QtCore.Qt.RichText)
        self.suggest_label.setMinimumHeight(120)
        self.suggest_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.suggest_label)

        # Status
        self.status_label = QtWidgets.QLabel("F7: hide/show | F8: quit | Enter: reset")
        self.status_label.setStyleSheet("color:#888; font-size:11px; font-family: 'Segoe UI'; background: transparent;")
        layout.addWidget(self.status_label)

        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.container.setGeometry(0,0,OVERLAY_WIDTH,OVERLAY_HEIGHT)
        self.move(20,250)
        self.old_pos = None

    # Dragging
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton: self.old_pos = event.globalPos()
    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()
    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def on_update_signal(self, key_char):
        if not self.isVisible(): return
        if key_char == "BACKSPACE": self.buffer = self.buffer[:-1]
        elif key_char == "ENTER": self.buffer = ""
        else: self.buffer += key_char.lower()
        self.update_ui()

    def update_ui(self):
        self.buffer_label.setText(f"typed: {self.buffer or '(empty)'}")
        suggestions = self.suggester.suggest(self.buffer.lower(), SUGGESTION_COUNT)

        colored_words = []
        for word in suggestions:
            colored = ""
            for i, c in enumerate(word):
                if i < len(self.buffer):
                    colored += f"<span style='color:#00ff88; font-weight:700'>{c}</span>"
                else:
                    colored += f"<span style='color:#ff5555'>{c}</span>"
            colored_words.append(colored)

        if not colored_words:
            self.suggest_label.setText("<span style='color:#ffffff'>no matches</span>")
        else:
            self.suggest_label.setText("<br>".join(colored_words))

        self.container.set_glow(bool(self.buffer and self.buffer in suggestions))

    def handle_key(self, key):
        try:
            if hasattr(key, 'char') and key.char and re.match(r"[a-zA-Z]", key.char):
                self.update_signal.emit(key.char)
            elif key == keyboard.Key.backspace: self.update_signal.emit("BACKSPACE")
            elif key == keyboard.Key.enter: self.update_signal.emit("ENTER")
            elif key == keyboard.Key.f8: QtWidgets.QApplication.quit()
            elif key == keyboard.Key.f7:
                self.hidden_mode = not self.hidden_mode
                self.setVisible(not self.hidden_mode)
        except Exception as e:
            print("Key handling error:", e)

def main():
    words = load_wordlist()
    suggester = WordSuggester(words)
    app = QtWidgets.QApplication(sys.argv)
    overlay = TypingOverlay(suggester)
    listener = keyboard.Listener(on_press=overlay.handle_key)
    listener.start()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
