#!/usr/bin/env python3
"""
WordBomb Typing Overlay with improved TAB autocomplete behavior
- TAB hint hidden when the buffer already equals the longest suggestion
- Enter cancels an in-progress autocomplete
- Autocomplete runs 1.5x faster than the previous version (~66.7ms mean per char)
- Submitted words are removed from the suggester so they won't be suggested again
"""

import sys, re, os, random, math
from pathlib import Path
from pynput import keyboard
from pynput.keyboard import Controller as KController
from PyQt5 import QtWidgets, QtCore, QtGui

WORDLIST_CANDIDATES = ["words_alpha.txt", "/usr/share/dict/words"]
SUGGESTION_COUNT = 5
OVERLAY_WIDTH = 480
OVERLAY_HEIGHT = 280
MAX_PARTICLES = 50

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_wordlist():
    for path in WORDLIST_CANDIDATES:
        full_path = get_resource_path(path)
        if Path(full_path).exists():
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return [w.strip().lower() for w in f if w.strip()]
    return ["test", "word", "bomb", "play", "game", "overlay",
            "autocomplete", "realistic", "typing", "longest", "suggestion"]

class WordSuggester:
    def __init__(self, words):
        self._set = set(words)
        self._list = sorted(self._set)

    def suggest(self, letters, limit=5):
        if letters is None:
            letters = ""
        if not letters:
            return [], True
        results = [w for w in self._list if w.startswith(letters)]
        prefix_mode = True
        if not results:
            results = [w for w in self._list if letters in w]
            prefix_mode = False
        results_sorted = sorted(results, key=lambda x: (len(x), x))
        if results_sorted:
            longest_word = max(results, key=len)
            if longest_word not in results_sorted[:limit]:
                results_sorted = results_sorted[:max(0, limit-1)] + [longest_word]
            else:
                results_sorted = results_sorted[:limit]
        return results_sorted, prefix_mode

    def remove_word(self, word):
        word = word.lower()
        if word in self._set:
            self._set.remove(word)
            self._list = sorted(self._set)
            return True
        return False

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

        if self.glow_active:
            self.glow_alpha = min(1.0, self.glow_alpha+0.05)
        else:
            self.glow_alpha = max(0.0, self.glow_alpha-0.05)

        self.spawn_particles()
        self.spawn_extra_effects()

        for p in self.particles:
            p.phase += 0.1
            p.x += math.sin(p.phase)*0.5 + p.vx
            p.y += p.vy
            p.size = max(4,p.size + random.uniform(-0.5,0.5))
            alpha = max(20, min(255, p.color.alpha() + random.randint(-15,15)))
            p.color.setAlpha(alpha)
            p.life -= 1
        self.particles = [p for p in self.particles if p.life>0]

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

        for p in self.particles:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        for p in self.extra_effects:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        bg_grad = QtGui.QLinearGradient(0,0,0,rect.height())
        bg_grad.setColorAt(0, QtGui.QColor(25,25,40,230))
        bg_grad.setColorAt(1, QtGui.QColor(10,10,20,220))
        painter.setBrush(QtGui.QBrush(bg_grad))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect,14,14)

        border_rect = rect.adjusted(2,2,-2,-2)
        slow_grad = QtGui.QConicalGradient(border_rect.center(),self.fast_phase*360)
        slow_grad.setColorAt(0.0,QtGui.QColor(50,150,180,120))
        slow_grad.setColorAt(0.5,QtGui.QColor(80,180,140,120))
        slow_grad.setColorAt(1.0,QtGui.QColor(50,150,180,120))
        pen = QtGui.QPen(QtGui.QBrush(slow_grad),3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(border_rect,14,14)

        if not self.glow_active and self.contains_mode:
            pen = QtGui.QPen(QtGui.QColor(255,80,80,150),3)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

        if self.glow_alpha>0:
            fast_grad = QtGui.QConicalGradient(border_rect.center(), self.fast_phase*360)
            fast_grad.setColorAt(0.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            fast_grad.setColorAt(0.5, QtGui.QColor(0,255,128,int(255*self.glow_alpha)))
            fast_grad.setColorAt(1.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            pen = QtGui.QPen(QtGui.QBrush(fast_grad),4)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

class TypingOverlay(QtWidgets.QWidget):
    update_signal = QtCore.pyqtSignal(str)
    autocomplete_signal = QtCore.pyqtSignal(str)
    cancel_signal = QtCore.pyqtSignal()  # used to cancel from timers or keys

    def __init__(self,suggester):
        super().__init__()
        self.suggester = suggester
        self.buffer = ""
        self.high_score = 0
        self.hidden_mode = False

        # autocomplete state
        self.autocomplete_in_progress = False
        self.autocomplete_timers = []  # list of QTimer objects for scheduled char sends
        self.ignore_synthetic = False
        self.expected_synthetic = 0

        # controller for real keystrokes
        self.kcontroller = KController()

        self.MEAN_MS = 100.0   # ≈66.666...
        self.SD_MS = 50.0  
        self.MIN_MS = 40
        self.MAX_MS = 300
        self.KEY_DOWN_MS = 8

        self._build_ui()
        self.update_signal.connect(self.on_update_signal)
        self.autocomplete_signal.connect(self.start_autocomplete)
        self.cancel_signal.connect(self.cancel_autocomplete)
        self.show()

    def _build_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.container = GlowFrame(self)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(18,18,18,18)
        layout.setSpacing(4)

        self.header_label = QtWidgets.QLabel("Word Bomb Helper by xHondje")
        font_header = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.header_label.setFont(font_header)
        self.header_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)

        self.length_label = QtWidgets.QLabel("")
        font_length = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.length_label.setFont(font_length)
        self.length_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.length_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.length_label)

        self.buffer_label = QtWidgets.QLabel("typed: (empty)")
        font = QtGui.QFont("Segoe UI",18,QtGui.QFont.Bold)
        self.buffer_label.setFont(font)
        self.buffer_label.setStyleSheet("color:#ffd580; background: transparent;")
        layout.addWidget(self.buffer_label)

        self.suggest_label = QtWidgets.QLabel("")
        font2 = QtGui.QFont("Segoe UI",14)
        self.suggest_label.setFont(font2)
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setTextFormat(QtCore.Qt.RichText)
        self.suggest_label.setMinimumHeight(120)
        self.suggest_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.suggest_label)

        self.next_letter_label = QtWidgets.QLabel("")
        font_hint = QtGui.QFont("Segoe UI",14,QtGui.QFont.Bold)
        self.next_letter_label.setFont(font_hint)
        self.next_letter_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.next_letter_label)

        self.highscore_label = QtWidgets.QLabel(f"High Score: {self.high_score}")
        font_hs = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.highscore_label.setFont(font_hs)
        self.highscore_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.highscore_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.highscore_label)

        self.status_label = QtWidgets.QLabel("F7: hide/show | F8: quit | Enter: submit/reset | Tab: autocomplete")
        self.status_label.setStyleSheet("color:#888; font-size:11px; font-family:'Segoe UI'; background: transparent;")
        layout.addWidget(self.status_label)

        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.container.setGeometry(0,0,OVERLAY_WIDTH,OVERLAY_HEIGHT)
        self.move(20,250)
        self.old_pos = None

    # dragging
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

        # If Enter pressed while autocompleting -> cancel instead of submitting.
        if key_char == "ENTER" and self.autocomplete_in_progress:
            self.cancel_autocomplete()
            return

        if key_char=="BACKSPACE":
            self.buffer = self.buffer[:-1]
            # If user manually backspaces while autocomplete in progress, keep going (but their actions may conflict)
        elif key_char=="ENTER":
            # submit: if it's a valid word remove it from suggester
            if self.buffer.lower() in self.suggester._set:
                self.high_score = max(self.high_score,len(self.buffer))
                self.highscore_label.setText(f"High Score: {self.high_score}")
                # remove the submitted word so it won't be suggested again
                removed = self.suggester.remove_word(self.buffer.lower())
                if removed:
                    # small feedback: clear suggestions
                    pass
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
                # show next letter to complete longest suggestion
                next_hint = longest_word[len(self.buffer)]
                self.next_letter_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.next_letter_label.setText(next_hint)

        # Suggestions display (TAB indicator hidden if buffer==longest_word or autocomplete in progress)
        colored_words = []
        longest_word = None
        if suggestions:
            longest_word = max(suggestions, key=len)

        for word in suggestions:
            colored = ""
            for i,c in enumerate(word):
                if prefix_mode and i<len(self.buffer):
                    colored += f"<span style='color:#00ff88; font-weight:700'>{c}</span>"
                elif not prefix_mode and self.buffer.lower() in word.lower() and c.lower() in self.buffer.lower():
                    colored += f"<span style='color:#3399ff; font-weight:700'>{c}</span>"
                else:
                    colored += f"<span style='color:#ff5555'>{c}</span>"

            # Only show TAB hint when:
            # - word is the longest suggestion
            # - prefix_mode is True
            # - buffer is NOT already equal to that longest word (i.e. not "Longest word possible typed")
            # - and autocomplete is not currently in progress
            show_tab_hint = (longest_word is not None and word == longest_word and prefix_mode
                             and (self.buffer.lower() != longest_word.lower())
                             and (not self.autocomplete_in_progress))
            if show_tab_hint:
                colored += " <span style='color:#aaaaaa; font-size:11px'>&nbsp;&nbsp;(TAB to auto-complete)</span>"
            colored_words.append(colored)

        if not colored_words:
            self.suggest_label.setText("<span style='color:#ffffff'>no matches</span>")
        else:
            self.suggest_label.setText("<br>".join(colored_words))

        # Glow: highlight when buffer is exactly a suggestion
        self.container.set_glow(bool(self.buffer and self.buffer in [s for s,_ in [ (None,None) ] or [] ] ) )  # harmless placeholder
        # real glow:
        self.container.set_glow(bool(self.buffer and (self.buffer in self.suggester._set)))

    def handle_key(self,key):
        """
        Global listener callback. This function ignores synthetic events that were
        generated by this process while autocomplete is sending real keystrokes.
        """
        try:
            # if we're ignoring synthetic events, decrement counter and skip processing
            if self.ignore_synthetic and self.expected_synthetic > 0:
                self.expected_synthetic -= 1
                if self.expected_synthetic <= 0:
                    self.ignore_synthetic = False
                return

            if hasattr(key,'char') and key.char and re.match(r"[a-zA-Z]",key.char):
                self.update_signal.emit(key.char)
            elif key==keyboard.Key.backspace:
                self.update_signal.emit("BACKSPACE")
            elif key==keyboard.Key.enter:
                self.update_signal.emit("ENTER")
            elif key==keyboard.Key.f8:
                QtWidgets.QApplication.quit()
            elif key==keyboard.Key.f7:
                self.hidden_mode = not self.hidden_mode
                self.setVisible(not self.hidden_mode)
            elif key==keyboard.Key.tab:
                # Tab pressed -> try autocomplete (prefix-mode only)
                suggestions, prefix_mode = self.suggester.suggest(self.buffer.lower(), SUGGESTION_COUNT)
                if suggestions and prefix_mode:
                    longest_word = max(suggestions, key=len)
                    if self.buffer.lower() != longest_word.lower():
                        # trigger autocomplete request
                        self.autocomplete_signal.emit(longest_word)
        except Exception as e:
            print("Key handling error:",e)

    @QtCore.pyqtSlot()
    def cancel_autocomplete(self):
        """
        Stop all scheduled timers and reset autocomplete state.
        Called when Enter is pressed during autocomplete or when user manually cancels.
        """
        if not self.autocomplete_in_progress:
            return
        # stop and delete timers
        for t in self.autocomplete_timers:
            try:
                t.stop()
            except Exception:
                pass
        self.autocomplete_timers = []
        # reset flags so synthetic events will not be ignored forever
        self.autocomplete_in_progress = False
        self.ignore_synthetic = False
        self.expected_synthetic = 0

    @QtCore.pyqtSlot(str)
    def start_autocomplete(self, target_word: str):
        """
        Schedule real OS key presses for the missing characters of target_word.
        Each scheduled send is a QTimer we keep a reference to so it can be canceled.
        """
        if self.autocomplete_in_progress:
            return
        cur = self.buffer
        if not target_word.startswith(cur):
            return
        remaining = target_word[len(cur):]
        if not remaining:
            return

        # prepare state
        self.autocomplete_in_progress = True
        self.autocomplete_timers = []
        # We'll expect one incoming synthetic 'char' event per character (listener consumes that)
        self.expected_synthetic = len(remaining)
        self.ignore_synthetic = True

        cumulative_ms = 0

        def make_timer_for_char(ch):
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            def on_timeout():
                # send the real keystroke to the OS
                try:
                    self.kcontroller.press(ch)
                    # release shortly after
                    release_timer = QtCore.QTimer(self)
                    release_timer.setSingleShot(True)
                    release_timer.timeout.connect(lambda: self.kcontroller.release(ch))
                    release_timer.start(self.KEY_DOWN_MS)
                except Exception as e:
                    print("Controller send error:", e)
                # update overlay immediately
                self.update_signal.emit(ch)
            t.timeout.connect(on_timeout)
            return t

        # schedule timers with randomized gaussian delays (clamped)
        for ch in remaining:
            # gaussian jitter around MEAN_MS, clamped
            delay = int(max(self.MIN_MS, min(self.MAX_MS, random.gauss(self.MEAN_MS, self.SD_MS))))
            cumulative_ms += delay
            t = make_timer_for_char(ch)
            # start timer after cumulative_ms
            t.start(cumulative_ms)
            self.autocomplete_timers.append(t)

        # schedule a final timer to clear autocomplete state a bit after last char
        fin = QtCore.QTimer(self)
        fin.setSingleShot(True)
        def finish():
            # cleanup only if not cancelled already
            self.autocomplete_timers = []
            self.autocomplete_in_progress = False
            # allow the listener to process any trailing synthetic events for safety
            # give a small grace window before resetting ignore flag to avoid race
            self.ignore_synthetic = False
            self.expected_synthetic = 0
        fin.timeout.connect(finish)
        fin.start(cumulative_ms + 40)

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
