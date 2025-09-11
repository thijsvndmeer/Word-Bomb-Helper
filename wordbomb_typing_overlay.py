#!/usr/bin/env python3
"""
WordBomb Typing Overlay with Fire, Epic Effects & High Score
"""

import sys, re, os, random, math
from pathlib import Path
from pynput import keyboard
from PyQt5 import QtWidgets, QtCore, QtGui

WORDLIST_CANDIDATES = ["words_alpha.txt", "/usr/share/dict/words"]
SUGGESTION_COUNT = 5
OVERLAY_WIDTH = 480
OVERLAY_HEIGHT = 280
MAX_PARTICLES = 50

# ---------------- Resource path helper ----------------
def get_resource_path(relative_path):
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
    return ["test", "word", "bomb", "play", "game", "overlay"]

# ---------------- Word suggester ----------------
class WordSuggester:
    def __init__(self, words):
        self.words = sorted(set(words))

    def suggest(self, letters, limit=5):
        if not letters:
            return [], True
        results = [w for w in self.words if w.startswith(letters)]
        prefix_mode = True
        if not results:
            results = [w for w in self.words if letters in w]
            prefix_mode = False
        results_sorted = sorted(results, key=lambda x: (len(x), x))
        if results_sorted:
            longest_word = max(results, key=len)
            if longest_word not in results_sorted[:limit]:
                results_sorted = results_sorted[:limit-1] + [longest_word]
            else:
                results_sorted = results_sorted[:limit]
        return results_sorted, prefix_mode

# ---------------- Particle class ----------------
class FireParticle:
    def __init__(self, x, y, size, color, vx, vy, life, phase):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.vx = vx
        self.vy = vy
        self.life = life
        self.phase = phase

# ---------------- Glow Frame ----------------
class GlowFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.glow_alpha = 0.0
        self.glow_active = False
        self.contains_mode = False
        self.word_length = 0
        self.ready_for_fire = False
        self.particles = []
        self.extra_effects = []
        self.fast_phase = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def set_glow(self, active: bool):
        self.glow_active = active

    def spawn_particles(self):
        if self.ready_for_fire and self.word_length >= 10:
            num_new = min(self.word_length-9, MAX_PARTICLES - len(self.particles))
            for _ in range(num_new):
                x = random.randint(20, OVERLAY_WIDTH-20)
                y = OVERLAY_HEIGHT - random.randint(0,15)
                size = random.randint(6,12)
                t = min(self.word_length, MAX_PARTICLES)/MAX_PARTICLES
                if self.glow_active:
                    color = QtGui.QColor(0,255,200,random.randint(80,150))
                else:
                    r = int(50 + t*205)
                    g = int(50 + t*150)
                    b = int(200 - t*150)
                    color = QtGui.QColor(r,g,b,random.randint(80,150))
                vx = random.uniform(-0.5,0.5)
                vy = random.uniform(-3,-1)
                life = random.randint(40,70)
                phase = random.uniform(0,2*math.pi)
                self.particles.append(FireParticle(x,y,size,color,vx,vy,life,phase))

    def spawn_extra_effects(self):
        if self.ready_for_fire and self.word_length >= 20:
            for _ in range(4):
                side = random.choice(['top','bottom','left','right'])
                if side=='top':
                    x = random.randint(-30, OVERLAY_WIDTH+30)
                    y = -random.randint(5,30)
                elif side=='bottom':
                    x = random.randint(-30, OVERLAY_WIDTH+30)
                    y = OVERLAY_HEIGHT + random.randint(5,30)
                elif side=='left':
                    x = -random.randint(5,30)
                    y = random.randint(-20, OVERLAY_HEIGHT+20)
                else:
                    x = OVERLAY_WIDTH + random.randint(5,30)
                    y = random.randint(-20, OVERLAY_HEIGHT+20)
                size = random.randint(8,16)
                color = QtGui.QColor(random.randint(100,255), random.randint(50,255), random.randint(50,255), random.randint(100,180))
                vx = random.uniform(-1,1)
                vy = random.uniform(-1,0)
                life = random.randint(50,90)
                phase = random.uniform(0, 2*math.pi)
                self.extra_effects.append(FireParticle(x,y,size,color,vx,vy,life,phase))

    def update_frame(self):
        self.fast_phase += 0.05
        if self.fast_phase > 1.0: self.fast_phase = 0.0

        # Fade glow
        if self.glow_active:
            self.glow_alpha = min(1.0, self.glow_alpha+0.05)
        else:
            self.glow_alpha = max(0.0, self.glow_alpha-0.05)

        self.spawn_particles()
        self.spawn_extra_effects()

        # Update main particles
        for p in self.particles:
            p.phase += 0.1
            p.x += math.sin(p.phase)*0.5 + p.vx
            p.y += p.vy
            p.size = max(4,p.size + random.uniform(-0.5,0.5))
            alpha = max(20, min(255, p.color.alpha() + random.randint(-15,15)))
            p.color.setAlpha(alpha)
            p.life -= 1
        self.particles = [p for p in self.particles if p.life>0]

        # Update extra effects
        for p in self.extra_effects:
            p.phase += 0.1
            p.x += math.sin(p.phase)*0.8 + p.vx
            p.y += math.cos(p.phase)*0.5 + p.vy
            p.size = max(4,p.size + random.uniform(-0.7,0.7))
            alpha = max(20, min(255, p.color.alpha() + random.randint(-15,15)))
            p.color.setAlpha(alpha)
            p.life -=1
        self.extra_effects = [p for p in self.extra_effects if p.life>0]

        self.update()

    def paintEvent(self,event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        # Fire particles behind UI
        for p in self.particles:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        # Extra epic effects around UI
        for p in self.extra_effects:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        # Background
        bg_grad = QtGui.QLinearGradient(0,0,0,rect.height())
        bg_grad.setColorAt(0, QtGui.QColor(25,25,40,230))
        bg_grad.setColorAt(1, QtGui.QColor(10,10,20,220))
        painter.setBrush(QtGui.QBrush(bg_grad))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect,14,14)

        # Border
        border_rect = rect.adjusted(2,2,-2,-2)
        slow_grad = QtGui.QConicalGradient(border_rect.center(),self.fast_phase*360)
        slow_grad.setColorAt(0.0,QtGui.QColor(50,150,180,120))
        slow_grad.setColorAt(0.5,QtGui.QColor(80,180,140,120))
        slow_grad.setColorAt(1.0,QtGui.QColor(50,150,180,120))
        pen = QtGui.QPen(QtGui.QBrush(slow_grad),3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(border_rect,14,14)

        # Contains mode
        if not self.glow_active and self.contains_mode:
            pen = QtGui.QPen(QtGui.QColor(255,80,80,150),3)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

        # Glow border fade
        if self.glow_alpha>0:
            fast_grad = QtGui.QConicalGradient(border_rect.center(), self.fast_phase*360)
            fast_grad.setColorAt(0.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            fast_grad.setColorAt(0.5, QtGui.QColor(0,255,128,int(255*self.glow_alpha)))
            fast_grad.setColorAt(1.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            pen = QtGui.QPen(QtGui.QBrush(fast_grad),4)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

# ---------------- Typing Overlay ----------------
class TypingOverlay(QtWidgets.QWidget):
    update_signal = QtCore.pyqtSignal(str)
    def __init__(self,suggester):
        super().__init__()
        self.suggester = suggester
        self.buffer = ""
        self.high_score = 0
        self.hidden_mode = False
        self._build_ui()
        self.update_signal.connect(self.on_update_signal)
        self.show()

    def _build_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.container = GlowFrame(self)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(18,18,18,18)
        layout.setSpacing(4)

        # Header
        self.header_label = QtWidgets.QLabel("Word Bomb Helper by xHondje")
        font_header = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.header_label.setFont(font_header)
        self.header_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)

        # Word length
        self.length_label = QtWidgets.QLabel("")
        font_length = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.length_label.setFont(font_length)
        self.length_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.length_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.length_label)

        # Buffer
        self.buffer_label = QtWidgets.QLabel("typed: (empty)")
        font = QtGui.QFont("Segoe UI",18,QtGui.QFont.Bold)
        self.buffer_label.setFont(font)
        self.buffer_label.setStyleSheet("color:#ffd580; background: transparent;")
        layout.addWidget(self.buffer_label)

        # Suggestions
        self.suggest_label = QtWidgets.QLabel("")
        font2 = QtGui.QFont("Segoe UI",14)
        self.suggest_label.setFont(font2)
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setTextFormat(QtCore.Qt.RichText)
        self.suggest_label.setMinimumHeight(120)
        self.suggest_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.suggest_label)

        # Next letter hint
        self.next_letter_label = QtWidgets.QLabel("")
        font_hint = QtGui.QFont("Segoe UI",14,QtGui.QFont.Bold)
        self.next_letter_label.setFont(font_hint)
        self.next_letter_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.next_letter_label)

        # High score
        self.highscore_label = QtWidgets.QLabel(f"High Score: {self.high_score}")
        font_hs = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.highscore_label.setFont(font_hs)
        self.highscore_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.highscore_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.highscore_label)

        # Status
        self.status_label = QtWidgets.QLabel("F7: hide/show | F8: quit | Enter: submit/reset")
        self.status_label.setStyleSheet("color:#888; font-size:11px; font-family:'Segoe UI'; background: transparent;")
        layout.addWidget(self.status_label)

        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.container.setGeometry(0,0,OVERLAY_WIDTH,OVERLAY_HEIGHT)
        self.move(20,250)
        self.old_pos = None

    # Dragging
    def mousePressEvent(self,event):
        if event.button() == QtCore.Qt.LeftButton:
            self.old_pos = event.globalPos()
    def mouseMoveEvent(self,event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x()+delta.x(), self.y()+delta.y())
            self.old_pos = event.globalPos()
    def mouseReleaseEvent(self,event):
        self.old_pos = None

    def on_update_signal(self,key_char):
        if not self.isVisible(): return
        if key_char=="BACKSPACE":
            self.buffer = self.buffer[:-1]
        elif key_char=="ENTER":
            # Update high score if valid word submitted
            if self.buffer.lower() in self.suggester.words:
                self.high_score = max(self.high_score,len(self.buffer))
                self.highscore_label.setText(f"High Score: {self.high_score}")
            self.buffer = ""
        else:
            self.buffer += key_char.lower()
        self.update_ui()

    def update_ui(self):
        self.buffer_label.setText(f"typed: {self.buffer or '(empty)'}")
        suggestions, prefix_mode = self.suggester.suggest(self.buffer.lower(), SUGGESTION_COUNT)
        self.container.contains_mode = not prefix_mode
        self.container.word_length = len(self.buffer)
        self.container.ready_for_fire = bool(suggestions)
        self.length_label.setText(f"Length: {len(self.buffer)}")

        # Next letter hint
        if not suggestions:
            next_hint = "BACKSPACE" if not prefix_mode else ""
        else:
            longest_word = max(suggestions,key=len)
            if self.buffer.lower() == longest_word.lower():
                next_hint = "Longest word possible typed"
                self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
            elif not prefix_mode:
                next_hint = "BACKSPACE"
                self.next_letter_label.setStyleSheet("color:#3399ff; background: transparent;")
            else:
                next_hint = longest_word[len(self.buffer)]
                self.next_letter_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.next_letter_label.setText(next_hint)

        # Suggestions display
        colored_words = []
        for word in suggestions:
            colored = ""
            for i,c in enumerate(word):
                if prefix_mode and i<len(self.buffer):
                    colored += f"<span style='color:#00ff88; font-weight:700'>{c}</span>"
                elif not prefix_mode and self.buffer.lower() in word.lower() and c.lower() in self.buffer.lower():
                    colored += f"<span style='color:#3399ff; font-weight:700'>{c}</span>"
                else:
                    colored += f"<span style='color:#ff5555'>{c}</span>"
            colored_words.append(colored)
        if not colored_words:
            self.suggest_label.setText("<span style='color:#ffffff'>no matches</span>")
        else:
            self.suggest_label.setText("<br>".join(colored_words))

        # Glow
        self.container.set_glow(bool(self.buffer and self.buffer in suggestions))

    def handle_key(self,key):
        try:
            if hasattr(key,'char') and key.char and re.match(r"[a-zA-Z]",key.char):
                self.update_signal.emit(key.char)
            elif key==keyboard.Key.backspace: self.update_signal.emit("BACKSPACE")
            elif key==keyboard.Key.enter: self.update_signal.emit("ENTER")
            elif key==keyboard.Key.f8: QtWidgets.QApplication.quit()
            elif key==keyboard.Key.f7:
                self.hidden_mode = not self.hidden_mode
                self.setVisible(not self.hidden_mode)
        except Exception as e:
            print("Key handling error:",e)

def main():
    words = load_wordlist()
    suggester = WordSuggester(words)
    app = QtWidgets.QApplication(sys.argv)
    overlay = TypingOverlay(suggester)
    listener = keyboard.Listener(on_press=overlay.handle_key)
    listener.start()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()
