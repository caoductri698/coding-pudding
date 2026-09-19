import sys
import os
import re
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit,
                             QMenuBar, QMenu, QFileDialog, QMessageBox,
                             QStatusBar, QLabel, QFontDialog, QColorDialog,
                             QDialog, QVBoxLayout, QLineEdit, QPushButton,
                             QCheckBox, QGroupBox, QHBoxLayout, QRadioButton,
                             QButtonGroup, QWidget, QListWidget,
                             QListWidgetItem, QAbstractItemView, QTabWidget,
                             QSpinBox, QComboBox, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QSettings
from PyQt6.QtGui import (QFont, QColor, QTextCursor, QKeySequence, QIcon,
                         QTextDocument, QPainter, QTextFormat, QCursor,
                         QTextCharFormat, QFontDatabase, QAction)


def resource_path(relative_path):
    """Get absolute path to resource"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False


# ============================================================
# CONTEXT MENU REGISTRATION
# ============================================================

def is_registered(exe_path):
    if not HAS_WINREG:
        return False
    try:
        key_path = r"Software\Classes\*\shell\coding-pudding\command"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "")
            return exe_path.lower() in value.lower()
    except FileNotFoundError:
        return False
    except Exception:
        return False


def register_context_menu(exe_path):
    if not HAS_WINREG:
        return False

    registry_entries = [
        (r"*\shell\coding-pudding", "Open with coding-pudding", exe_path, f'"{exe_path}" "%1"'),
        (r"Directory\shell\coding-pudding", "Open with coding-pudding", exe_path, f'"{exe_path}" "%1"'),
        (r"Directory\Background\shell\coding-pudding", "Open with coding-pudding", exe_path, f'"{exe_path}" "%V"'),
    ]

    base_key = winreg.HKEY_CURRENT_USER
    success = True

    for key_path, menu_text, icon_path, command in registry_entries:
        try:
            full_key_path = r"Software\Classes\\" + key_path
            with winreg.CreateKeyEx(base_key, full_key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_text)
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            command_key_path = full_key_path + r"\command"
            with winreg.CreateKeyEx(base_key, command_key_path, 0, winreg.KEY_WRITE) as cmd_key:
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
        except Exception:
            success = False

    return success


def unregister_context_menu():
    if not HAS_WINREG:
        return False

    registry_entries = [
        r"*\shell\coding-pudding",
        r"Directory\shell\coding-pudding",
        r"Directory\Background\shell\coding-pudding",
    ]

    base_key = winreg.HKEY_CURRENT_USER

    for key_path in registry_entries:
        try:
            full_key_path = r"Software\Classes\\" + key_path
            try:
                winreg.DeleteKey(base_key, full_key_path + r"\command")
            except FileNotFoundError:
                pass
            winreg.DeleteKey(base_key, full_key_path)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to unregister {key_path}: {e}")

    return True


def auto_register_context_menu():
    if not getattr(sys, 'frozen', False):
        return
    if not HAS_WINREG:
        return
    exe_path = sys.executable
    if not is_registered(exe_path):
        print(f"Registering context menu for: {exe_path}")
        register_context_menu(exe_path)


# ============================================================
# LINE NUMBER AREA
# ============================================================

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(50)

    def sizeHint(self):
        return self.size()

    def paintEvent(self, event):
        self.editor.line_number_area_paint(event)


# ============================================================
# AUTO SCROLL ANCHOR
# ============================================================

class AutoScrollAnchor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(40, 40)
        self.hide()
        self.anchor_color = QColor(80, 80, 80, 200)
        self.arrow_color = QColor(255, 255, 255)
        self.direction = 0
        self.speed = 0.0

    def set_direction(self, direction, speed):
        self.direction = direction
        self.speed = speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.anchor_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        painter.setBrush(self.arrow_color)
        center_x = 20
        center_y = 20
        if self.direction == -1:
            points = [QPoint(center_x, center_y - 10),
                     QPoint(center_x - 6, center_y - 2),
                     QPoint(center_x + 6, center_y - 2)]
            painter.drawPolygon(*points)
        elif self.direction == 1:
            points = [QPoint(center_x, center_y + 10),
                     QPoint(center_x - 6, center_y + 2),
                     QPoint(center_x + 6, center_y + 2)]
            painter.drawPolygon(*points)
        else:
            painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)


# ============================================================
# CODE EDITOR (QPlainTextEdit)
# ============================================================

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None, dark_mode=False, indent_size=4):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.font_family = "Consolas"
        self.font_size = 14

        # v5.0 settings
        self.indent_size = indent_size

        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.document().setDefaultFont(font)

        self.dark_mode = dark_mode
        self.setViewportMargins(50, 0, 0, 0)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Prevent Tab from changing focus - we handle it manually
        self.setTabChangesFocus(False)

        self.auto_scroll_active = False
        self.auto_scroll_anchor = None
        self.auto_scroll_timer = QTimer()
        self.auto_scroll_timer.timeout.connect(self._auto_scroll_step)
        self.auto_scroll_anchor_widget = AutoScrollAnchor(self)
        self.setMouseTracking(True)

        self.update_colors()

        # Update line numbers when text changes or scroll
        self.textChanged.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area_request)

        self.update_line_number_area_width()
        self.update_line_number_area()

    def update_line_number_area_width(self):
        """Adjust line number area width based on number of digits"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1

        width = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        width = max(width, 50)
        self.setViewportMargins(width, 0, 0, 0)
        self.line_number_area.setFixedWidth(width)

    def update_line_number_area_request(self, rect, dy):
        """Called when the viewport needs to be updated"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(),
                                          self.line_number_area.width(),
                                          rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def get_indent_str(self):
        if self.indent_size == 0:
            return '\t'
        return ' ' * self.indent_size

    def get_indent_width(self):
        if self.indent_size == 0:
            return 4
        return self.indent_size

    # ============ DRAG & DROP ============
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.ignore()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.ignore()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            main_window = self.window()
            if hasattr(main_window, 'dropEvent'):
                main_window.dropEvent(event)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def apply_font(self):
        """Apply font to all text (including existing)"""
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.document().setDefaultFont(font)

        # Apply font to all existing text
        self.blockSignals(True)

        cursor = self.textCursor()
        pos = cursor.position()
        had_selection = cursor.hasSelection()
        sel_start = cursor.selectionStart()
        sel_end = cursor.selectionEnd()

        select_all = QTextCursor(self.document())
        select_all.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        char_format.setFontFamily(self.font_family)
        char_format.setFontPointSize(self.font_size)
        select_all.mergeCharFormat(char_format)

        # Restore cursor
        new_cursor = self.textCursor()
        if had_selection:
            new_cursor.setPosition(sel_start)
            new_cursor.setPosition(sel_end, QTextCursor.MoveMode.KeepAnchor)
        else:
            doc_len = self.document().characterCount() - 1
            new_cursor.setPosition(min(pos, max(0, doc_len)))
        self.setTextCursor(new_cursor)

        self.blockSignals(False)
        self.update_line_number_area_width()
        self.viewport().update()

    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            self.insertPlainText(text)
            self.apply_font()
        else:
            super().insertFromMimeData(source)

    def update_colors(self):
        if self.dark_mode:
            self.text_color = QColor(220, 220, 220)
            self.bg_color = QColor(30, 30, 30)
            self.line_number_bg = QColor(40, 40, 40)
            self.line_number_fg = QColor(100, 100, 100)
        else:
            self.text_color = QColor(0, 0, 0)
            self.bg_color = QColor(255, 255, 255)
            self.line_number_bg = QColor(240, 240, 240)
            self.line_number_fg = QColor(128, 128, 128)

        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, self.bg_color)
        palette.setColor(palette.ColorRole.Text, self.text_color)
        self.setPalette(palette)

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.bg_color.name()};
                color: {self.text_color.name()};
                border: none;
            }}
        """)

        self.viewport().update()
        self.line_number_area.update()

    def toggle_dark_mode(self, dark_mode):
        self.dark_mode = dark_mode
        self.update_colors()

    # ============ EXPAND BRACKET PAIR ============
    def expand_bracket_pair(self, open_char, close_char):
        cursor = self.textCursor()

        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        current_line = cursor.selectedText()

        base_indent = 0
        for char in current_line:
            if char == ' ':
                base_indent += 1
            elif char == '\t':
                base_indent += self.get_indent_width()
            else:
                break

        cursor = self.textCursor()
        pos = cursor.position()
        open_pos = pos - 1
        indent_str = ' ' * base_indent
        inner_indent_width = self.get_indent_width()
        inner_indent = ' ' * (base_indent + inner_indent_width)

        cursor.setPosition(open_pos)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 2)
        cursor.removeSelectedText()

        new_text = f"{open_char}\n{inner_indent}\n{indent_str}{close_char}"
        cursor.insertText(new_text)

        cursor.setPosition(open_pos + 1 + len(inner_indent))
        self.setTextCursor(cursor)

    # ============ DELETE BRACKET PAIR ============
    def delete_bracket_pair(self):
        cursor = self.textCursor()
        pos = cursor.position()
        block = cursor.block()
        block_text = block.text()
        pos_in_block = cursor.positionInBlock()

        brackets = {'(': ')', '[': ']', '{': '}', '<': '>', '"': '"', "'": "'"}

        if pos_in_block > 0 and pos_in_block < len(block_text):
            char_left = block_text[pos_in_block - 1]
            char_right = block_text[pos_in_block]

            if char_left in brackets:
                expected_close = brackets[char_left]
                if char_right == expected_close:
                    cursor.setPosition(pos - 1)
                    cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 2)
                    cursor.removeSelectedText()
                    return True

        return False

    # ============ TRIM TRAILING SPACES ============
    def trim_trailing_spaces(self):
        cursor = self.textCursor()
        original_pos = cursor.position()
        scroll_pos = self.verticalScrollBar().value()

        text = self.toPlainText()
        lines = text.split('\n')
        new_lines = [line.rstrip() for line in lines]
        new_text = '\n'.join(new_lines)

        if new_text != text:
            self.blockSignals(True)
            self.setPlainText(new_text)
            self.blockSignals(False)

            doc_length = self.document().characterCount() - 1
            new_pos = min(original_pos, doc_length)
            cursor.setPosition(new_pos)
            self.setTextCursor(cursor)

            self.verticalScrollBar().setValue(scroll_pos)
            return True
        return False

    # ============ WORD COUNT ============
    def get_word_count(self):
        text = self.toPlainText()

        char_count = len(text)
        char_count_no_space = len(text.replace(' ', '').replace('\t', '').replace('\n', ''))

        words = text.split()
        word_count = len(words)

        line_count = text.count('\n') + 1 if text else 0

        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)

        return {
            'chars': char_count,
            'chars_no_space': char_count_no_space,
            'words': word_count,
            'lines': line_count,
            'paragraphs': paragraph_count
        }

    # ============ AUTO-SCROLL ============
    def start_auto_scroll(self, pos):
        self.auto_scroll_active = True
        self.auto_scroll_anchor = pos
        self.auto_scroll_anchor_widget.move(pos.x() - 20, pos.y() - 20)
        self.auto_scroll_anchor_widget.set_direction(0, 0)
        self.auto_scroll_anchor_widget.show()
        self.auto_scroll_anchor_widget.raise_()
        self.auto_scroll_timer.start(16)

    def stop_auto_scroll(self):
        self.auto_scroll_active = False
        self.auto_scroll_anchor = None
        self.auto_scroll_timer.stop()
        self.auto_scroll_anchor_widget.hide()

    def _auto_scroll_step(self):
        if not self.auto_scroll_active or self.auto_scroll_anchor is None:
            return

        global_pos = QCursor.pos()
        local_pos = self.viewport().mapFromGlobal(global_pos)
        dy = local_pos.y() - self.auto_scroll_anchor.y()
        DEAD_ZONE = 5

        if abs(dy) < DEAD_ZONE:
            self.auto_scroll_anchor_widget.set_direction(0, 0)
            return

        MAX_DISTANCE = 100
        MAX_SPEED = 40

        distance = abs(dy) - DEAD_ZONE
        speed_ratio = min(distance / MAX_DISTANCE, 3.0)
        speed = int(speed_ratio * MAX_SPEED) + 2

        if dy < 0:
            direction = -1
            self.auto_scroll_anchor_widget.set_direction(-1, speed_ratio)
        else:
            direction = 1
            self.auto_scroll_anchor_widget.set_direction(1, speed_ratio)

        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + direction * speed)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.auto_scroll_active:
                self.stop_auto_scroll()
            else:
                viewport_pos = self.viewport().mapFrom(self, event.pos())
                self.start_auto_scroll(viewport_pos)
            event.accept()
            return
        elif event.button() == Qt.MouseButton.LeftButton and self.auto_scroll_active:
            self.stop_auto_scroll()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self.auto_scroll_active:
            self.stop_auto_scroll()

        # Handle Tab manually (QPlainTextEdit would use it to change focus by default)
        if event.key() == Qt.Key.Key_Tab and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            cursor = self.textCursor()
            if cursor.hasSelection():
                self.indent_selection()
            else:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                line_text = cursor.selectedText()
                current_cursor = self.textCursor()
                pos_in_line = current_cursor.position() - current_cursor.block().position()

                leading_spaces = 0
                for char in line_text:
                    if char == ' ':
                        leading_spaces += 1
                    elif char == '\t':
                        leading_spaces += self.get_indent_width()
                    else:
                        break

                # Only indent whole line if it has content AND cursor is in leading whitespace
                # Otherwise insert indent string at cursor position
                has_content = bool(line_text.strip())

                if has_content and pos_in_line <= leading_spaces:
                    self.indent_selection()
                else:
                    current_cursor.insertText(self.get_indent_str())
                    self.setTextCursor(current_cursor)
            event.accept()
            return

        # Handle Backtab (Shift+Tab)
        if event.key() == Qt.Key.Key_Backtab:
            self.unindent_selection()
            event.accept()
            return

        # Handle Enter
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.handle_enter_key()
            event.accept()
            return

        # Handle Backspace/Delete for bracket pair
        if event.key() == Qt.Key.Key_Backspace or event.key() == Qt.Key.Key_Delete:
            if self.delete_bracket_pair():
                event.accept()
                return

        # Handle bracket smart typing
        if self.handle_bracket_smart(event):
            event.accept()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self.auto_scroll_active:
            self.stop_auto_scroll()

        # Ctrl + wheel -> zoom font
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(self.font_size + 1, 72)
            else:
                self.font_size = max(self.font_size - 1, 6)
            self.apply_font()
            event.accept()
            return

        # Shift + wheel -> horizontal scroll
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.angleDelta().x()

            num_degrees = delta / 8.0
            num_steps = num_degrees / 15.0

            scroll_lines = QApplication.wheelScrollLines()
            if scroll_lines == -1:
                scroll_lines = self.viewport().height() // self.fontMetrics().height()

            char_width = self.fontMetrics().horizontalAdvance(' ')
            scroll_amount = int(num_steps * scroll_lines * char_width)

            h_scrollbar = self.horizontalScrollBar()
            h_scrollbar.setValue(h_scrollbar.value() - scroll_amount)
            event.accept()
            return

        super().wheelEvent(event)

    # ============ INDENT / UNINDENT ============
    def indent_selection(self):
        cursor = self.textCursor()
        original_pos = cursor.position()
        has_selection = cursor.hasSelection()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        start_line_pos = cursor.position()

        cursor.setPosition(end)
        if cursor.atBlockStart() and end != start:
            cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        end_line_pos = cursor.position()

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        selected_text = cursor.selectedText()

        indent_str = self.get_indent_str()
        lines = selected_text.split('\u2029')
        new_lines = [indent_str + line if line.strip() else line for line in lines]
        new_text = '\u2029'.join(new_lines)

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new_text)

        doc_length = self.document().characterCount() - 1
        indent_len = len(indent_str)

        if has_selection:
            new_end = start_line_pos + len(new_text)
            new_end = min(new_end, doc_length)
            cursor.setPosition(min(start_line_pos, doc_length))
            cursor.setPosition(new_end, QTextCursor.MoveMode.KeepAnchor)
        else:
            new_pos = original_pos + indent_len
            new_pos = min(new_pos, doc_length)
            cursor.setPosition(new_pos)

        self.setTextCursor(cursor)

    def unindent_selection(self):
        cursor = self.textCursor()
        original_pos = cursor.position()
        has_selection = cursor.hasSelection()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        start_line_pos = cursor.position()

        cursor.setPosition(end)
        if cursor.atBlockStart() and end != start:
            cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        end_line_pos = cursor.position()

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        selected_text = cursor.selectedText()

        lines = selected_text.split('\u2029')
        new_lines = []
        total_removed = 0
        indent_width = self.get_indent_width()
        for line in lines:
            removed = 0
            new_line = line
            while removed < indent_width and new_line.startswith(' '):
                new_line = new_line[1:]
                removed += 1
            if removed == 0 and new_line.startswith('\t'):
                new_line = new_line[1:]
                removed = indent_width
            total_removed += removed
            new_lines.append(new_line)

        new_text = '\u2029'.join(new_lines)

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new_text)

        doc_length = self.document().characterCount() - 1

        if has_selection:
            new_end = start_line_pos + len(new_text)
            new_end = min(new_end, doc_length)
            cursor.setPosition(min(start_line_pos, doc_length))
            cursor.setPosition(new_end, QTextCursor.MoveMode.KeepAnchor)
        else:
            new_pos = original_pos - total_removed
            new_pos = max(start_line_pos, new_pos)
            new_pos = min(new_pos, doc_length)
            cursor.setPosition(new_pos)

        self.setTextCursor(cursor)

    # ============ COMMENT/UNCOMMENT ============
    def toggle_comment(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        start_line_pos = cursor.position()

        cursor.setPosition(end)
        if cursor.atBlockStart() and end != start:
            cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        end_line_pos = cursor.position()

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        selected_text = cursor.selectedText()
        lines = selected_text.split('\u2029')

        all_commented = True
        has_content = False
        for line in lines:
            stripped = line.lstrip()
            if not stripped:
                continue
            has_content = True
            if not stripped.startswith('#'):
                all_commented = False
                break

        if not has_content:
            return

        new_lines = []
        for line in lines:
            if all_commented:
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                if stripped.startswith('# '):
                    new_line = line[:indent] + stripped[2:]
                elif stripped.startswith('#'):
                    new_line = line[:indent] + stripped[1:]
                else:
                    new_line = line
            else:
                if line.strip():
                    stripped = line.lstrip()
                    indent = len(line) - len(stripped)
                    new_line = line[:indent] + '# ' + stripped
                else:
                    new_line = line
            new_lines.append(new_line)

        new_text = '\u2029'.join(new_lines)

        cursor.setPosition(start_line_pos)
        cursor.setPosition(end_line_pos, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(new_text)

        cursor.setPosition(start_line_pos)
        cursor.setPosition(start_line_pos + len(new_text), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    # ============ BRACKET SMART TYPING ============
    def handle_bracket_smart(self, event):
        open_brackets = {
            Qt.Key.Key_ParenLeft: ('(', ')'),
            Qt.Key.Key_BraceLeft: ('{', '}'),
            Qt.Key.Key_BracketLeft: ('[', ']'),
            Qt.Key.Key_Less: ('<', '>'),
        }
        smart_quotes = {
            Qt.Key.Key_QuoteDbl: '"',
            Qt.Key.Key_Apostrophe: "'",
        }
        close_brackets = {
            Qt.Key.Key_ParenRight: ')',
            Qt.Key.Key_BraceRight: '}',
            Qt.Key.Key_BracketRight: ']',
            Qt.Key.Key_Greater: '>',
        }

        cursor = self.textCursor()
        pos_in_block = cursor.positionInBlock()
        block = cursor.block()
        block_text = block.text()

        if event.key() in close_brackets:
            close_char = close_brackets[event.key()]
            if pos_in_block < len(block_text) and block_text[pos_in_block] == close_char:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True

        if event.key() in smart_quotes:
            quote_char = smart_quotes[event.key()]
            if pos_in_block < len(block_text) and block_text[pos_in_block] == quote_char:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True

            line_text = block_text
            quote_count = line_text.count(quote_char)

            if quote_count % 2 == 1:
                cursor = self.textCursor()
                cursor.insertText(quote_char)
                self.setTextCursor(cursor)
                return True
            else:
                cursor = self.textCursor()
                cursor.insertText(quote_char + quote_char)
                cursor.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(cursor)
                return True

        if event.key() in open_brackets:
            open_char, close_char = open_brackets[event.key()]
            cursor = self.textCursor()
            cursor.insertText(open_char + close_char)
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return True
        return False

    def handle_enter_key(self):
        cursor = self.textCursor()
        block = cursor.block()
        block_text = block.text()
        pos_in_block = cursor.positionInBlock()

        brackets = {'(': ')', '[': ']', '{': '}', '<': '>'}

        if pos_in_block > 0 and pos_in_block < len(block_text):
            char_left = block_text[pos_in_block - 1]
            char_right = block_text[pos_in_block]

            if char_left in brackets:
                expected_close = brackets[char_left]
                if char_right == expected_close:
                    self.expand_bracket_pair(char_left, char_right)
                    return

        current_line = block_text

        indent_spaces = 0
        for char in current_line:
            if char == ' ':
                indent_spaces += 1
            elif char == '\t':
                indent_spaces += self.get_indent_width()
            else:
                break

        needs_extra_indent = current_line.rstrip().endswith(':')

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        self.setTextCursor(cursor)
        cursor.insertText('\n')

        if indent_spaces > 0:
            cursor.insertText(' ' * indent_spaces)
        if needs_extra_indent:
            cursor.insertText(self.get_indent_str())

        self.setTextCursor(cursor)

    def line_number_area_paint(self, event):
        """Optimized line number painting using QPlainTextEdit API"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), self.line_number_bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        font_metrics = painter.fontMetrics()
        painter.setPen(self.line_number_fg)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                text_y = int(top + (self.fontMetrics().height() - font_metrics.height()) / 2 + font_metrics.ascent())
                painter.drawText(5, text_y, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def update_line_number_area(self):
        self.line_number_area.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                  self.line_number_area.width(),
                                                  cr.height()))


# ============================================================
# EDITOR TAB
# ============================================================

class EditorTab:
    def __init__(self, editor, file_path=None, is_modified=False):
        self.editor = editor
        self.file_path = file_path
        self.is_modified = is_modified
        self.original_content = ""

    def get_display_name(self):
        if self.file_path:
            name = os.path.basename(self.file_path)
        else:
            name = "Untitled"
        if self.is_modified:
            name += " *"
        return name

    def get_tooltip(self):
        if self.file_path:
            return self.file_path
        return "Unsaved file"


# ============================================================
# TAB WIDGET
# ============================================================

class CustomTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_notepad = parent
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.on_tab_close_requested)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_tab_context_menu)

    def on_tab_close_requested(self, index):
        if self.parent_notepad:
            self.parent_notepad.close_tab(index)

    def on_tab_context_menu(self, pos):
        tab_bar = self.tabBar()
        index = tab_bar.tabAt(pos)
        if index < 0:
            return

        if self.parent_notepad:
            self.parent_notepad.show_tab_context_menu(index, tab_bar.mapToGlobal(pos))


# ============================================================
# SETTINGS DIALOG
# ============================================================

class SettingsDialog(QDialog):
    def __init__(self, parent_notepad):
        super().__init__(parent_notepad)
        self.parent_notepad = parent_notepad
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 520)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # ============ EDITOR SECTION ============
        editor_group = QGroupBox("Editor")
        editor_layout = QVBoxLayout()

        # Font family
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()

        CODE_FONTS = [
            "Consolas", "JetBrains Mono", "Fira Code", "Cascadia Code",
            "Source Code Pro", "IBM Plex Mono", "Hack", "Roboto Mono",
            "Inconsolata", "Menlo", "SF Mono", "Ubuntu Mono",
            "Anonymous Pro", "Input Mono", "Iosevka", "Monoid",
            "Cascadia Mono", "Courier New",
        ]

        available = QFontDatabase.families()
        current_family = parent_notepad.font_family
        added = set()

        for font_name in CODE_FONTS:
            if font_name in available:
                self.font_combo.addItem(font_name)
                added.add(font_name)

        if current_family not in added:
            self.font_combo.addItem(current_family)

        idx = self.font_combo.findText(current_family)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)

        self.font_combo.currentTextChanged.connect(self.update_preview)
        font_row.addWidget(self.font_combo, 1)
        editor_layout.addLayout(font_row)

        hint_label = QLabel("Tip: install JetBrains Mono or Fira Code for a better experience")
        hint_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic;")
        editor_layout.addWidget(hint_label)

        # Font size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Font size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 72)
        self.size_spin.setValue(parent_notepad.font_size)
        self.size_spin.setSuffix(" pt")
        self.size_spin.valueChanged.connect(self.update_preview)
        size_row.addWidget(self.size_spin)
        size_row.addStretch()
        editor_layout.addLayout(size_row)

        # Tab size (Indentation size)
        tab_row = QHBoxLayout()
        tab_row.addWidget(QLabel("Indentation size:"))
        self.tab_size_combo = QComboBox()
        self.tab_size_combo.addItem("2 spaces", 2)
        self.tab_size_combo.addItem("4 spaces", 4)
        self.tab_size_combo.addItem("8 spaces", 8)
        self.tab_size_combo.addItem("Tab character", 0)

        for i in range(self.tab_size_combo.count()):
            if self.tab_size_combo.itemData(i) == parent_notepad.indent_size:
                self.tab_size_combo.setCurrentIndex(i)
                break

        tab_row.addWidget(self.tab_size_combo)
        tab_row.addStretch()
        editor_layout.addLayout(tab_row)

        # Preview
        editor_layout.addWidget(QLabel("Preview:"))
        self.preview = QLabel("def hello():\n    print(\"Hello, world!\")")
        self.preview.setMinimumHeight(60)
        editor_layout.addWidget(self.preview)

        editor_group.setLayout(editor_layout)
        layout.addWidget(editor_group)

        # ============ APPEARANCE SECTION ============
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout()

        self.light_radio = QRadioButton("Light mode")
        self.dark_radio = QRadioButton("Dark mode")

        if parent_notepad.dark_mode:
            self.dark_radio.setChecked(True)
        else:
            self.light_radio.setChecked(True)

        self.light_radio.toggled.connect(self.update_preview)
        self.dark_radio.toggled.connect(self.update_preview)

        appearance_layout.addWidget(self.light_radio)
        appearance_layout.addWidget(self.dark_radio)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # ============ EDITOR BEHAVIOR ============
        behavior_group = QGroupBox("Editor behavior")
        behavior_layout = QVBoxLayout()

        self.wrap_check = QCheckBox("Word wrap")
        self.wrap_check.setChecked(parent_notepad.word_wrap)

        self.linenum_check = QCheckBox("Show line numbers")
        self.linenum_check.setChecked(parent_notepad.show_line_numbers)

        self.trim_check = QCheckBox("Trim trailing spaces on save")
        self.trim_check.setChecked(parent_notepad.trim_on_save)

        self.restore_tabs_check = QCheckBox("Restore tabs on startup")
        self.restore_tabs_check.setChecked(parent_notepad.restore_tabs)

        behavior_layout.addWidget(self.wrap_check)
        behavior_layout.addWidget(self.linenum_check)
        behavior_layout.addWidget(self.trim_check)
        behavior_layout.addWidget(self.restore_tabs_check)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        layout.addStretch()

        # ============ BUTTONS ============
        button_row = QHBoxLayout()

        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.reset_defaults)
        button_row.addWidget(reset_btn)

        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.apply_settings)
        button_row.addWidget(ok_btn)

        layout.addLayout(button_row)

        self.setLayout(layout)

        # ============ DIRTY TRACKING ============
        self._dirty = False
        self._suppress_dirty = False

        self.font_combo.currentTextChanged.connect(self._mark_dirty)
        self.size_spin.valueChanged.connect(self._mark_dirty)
        self.tab_size_combo.currentIndexChanged.connect(self._mark_dirty)
        self.light_radio.toggled.connect(self._mark_dirty)
        self.dark_radio.toggled.connect(self._mark_dirty)
        self.wrap_check.toggled.connect(self._mark_dirty)
        self.linenum_check.toggled.connect(self._mark_dirty)
        self.trim_check.toggled.connect(self._mark_dirty)
        self.restore_tabs_check.toggled.connect(self._mark_dirty)

        self.update_preview()

    def _mark_dirty(self):
        if not self._suppress_dirty:
            self._dirty = True

    def update_preview(self):
        font = QFont(self.font_combo.currentText())
        font.setPointSize(self.size_spin.value())
        self.preview.setFont(font)

        if self.dark_radio.isChecked():
            self.preview.setStyleSheet(
                "background-color: #1e1e1e; color: #d4d4d4; "
                "border: 1px solid #3d3d3d; padding: 8px;"
            )
        else:
            self.preview.setStyleSheet(
                "background-color: white; color: black; "
                "border: 1px solid #ccc; padding: 8px;"
            )

    def reset_defaults(self):
        self._suppress_dirty = True

        idx = self.font_combo.findText("Consolas")
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        self.size_spin.setValue(14)

        for i in range(self.tab_size_combo.count()):
            if self.tab_size_combo.itemData(i) == 4:
                self.tab_size_combo.setCurrentIndex(i)
                break

        self.light_radio.setChecked(True)
        self.wrap_check.setChecked(False)
        self.linenum_check.setChecked(True)
        self.trim_check.setChecked(False)
        self.restore_tabs_check.setChecked(True)
        self.update_preview()

        self._suppress_dirty = False
        self._dirty = True

    def apply_settings(self):
        self.parent_notepad.font_family = self.font_combo.currentText()
        self.parent_notepad.font_size = self.size_spin.value()
        self.parent_notepad.apply_font()

        new_dark = self.dark_radio.isChecked()
        if new_dark != self.parent_notepad.dark_mode:
            self.parent_notepad.toggle_dark_mode(new_dark)

        self.parent_notepad.word_wrap = self.wrap_check.isChecked()
        self.parent_notepad.show_line_numbers = self.linenum_check.isChecked()
        self.parent_notepad.trim_on_save = self.trim_check.isChecked()
        self.parent_notepad.restore_tabs = self.restore_tabs_check.isChecked()

        self.parent_notepad.indent_size = self.tab_size_combo.currentData()

        self.parent_notepad.toggle_word_wrap(self.parent_notepad.word_wrap)

        show_numbers = self.parent_notepad.show_line_numbers
        for tab in self.parent_notepad.tabs:
            if isinstance(tab.editor, CodeEditor):
                tab.editor.line_number_area.setVisible(show_numbers)
                if show_numbers:
                    tab.editor.update_line_number_area_width()
                else:
                    tab.editor.setViewportMargins(0, 0, 0, 0)

                tab.editor.indent_size = self.parent_notepad.indent_size

        self.parent_notepad.save_settings()
        self._dirty = False
        self.accept()

    def reject(self):
        if self._dirty:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Changes")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("You have unsaved changes in Settings.")
            msg_box.setInformativeText("Do you want to apply them before closing?")
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Save
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Save)

            msg_box.button(QMessageBox.StandardButton.Save).setText("Apply && Close")
            msg_box.button(QMessageBox.StandardButton.Discard).setText("Discard Changes")
            msg_box.button(QMessageBox.StandardButton.Cancel).setText("Keep Editing")

            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.Save:
                self.apply_settings()
                return
            elif reply == QMessageBox.StandardButton.Discard:
                self._dirty = False
                super().reject()
                return
            else:
                return

        super().reject()


# ============================================================
# MAIN NOTEPAD
# ============================================================

class MyNotepad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("coding-pudding.exe")
        self.setGeometry(100, 100, 1000, 800)

        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setAcceptDrops(True)

        self.dark_mode = False
        self.font_family = "Consolas"
        self.font_size = 14
        self.word_wrap = False
        self.show_line_numbers = True
        self.trim_on_save = False

        # v5.0
        self.indent_size = 4
        self.restore_tabs = True

        self.tabs = []

        self.dragging_tab = False
        self.drag_start_pos = None
        self.drag_tab_index = -1

        self.tab_widget = CustomTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.tabBar().installEventFilter(self)
        self.tab_widget.tabBar().setMouseTracking(True)

        self.create_status_bar()
        self.create_menu_bar()

        self.find_dialog = None
        self.replace_dialog = None

        self.apply_theme()
        self.load_settings()

        if not self.restore_session():
            self.add_new_tab()

        self.update_title()

    def eventFilter(self, obj, event):
        if obj != self.tab_widget.tabBar():
            return super().eventFilter(obj, event)

        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_pos = event.pos()
                self.drag_tab_index = self.tab_widget.tabBar().tabAt(event.pos())
                self.dragging_tab = False
        elif event.type() == event.Type.MouseMove:
            if self.drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
                if self.drag_tab_index >= 0:
                    if not self.tab_widget.tabBar().rect().contains(event.pos()):
                        if not self.dragging_tab:
                            self.dragging_tab = True
                            self.tab_widget.tabBar().setCursor(Qt.CursorShape.DragMoveCursor)
        elif event.type() == event.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                if self.dragging_tab and self.drag_tab_index >= 0:
                    self.detach_tab(self.drag_tab_index)
                self.dragging_tab = False
                self.drag_start_pos = None
                self.drag_tab_index = -1
                self.tab_widget.tabBar().setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(obj, event)

    def detach_tab(self, index):
        if index < 0 or index >= len(self.tabs):
            return
        if len(self.tabs) <= 1:
            return

        tab = self.tabs[index]
        content = tab.editor.toPlainText()
        file_path = tab.file_path
        is_modified = tab.is_modified
        original_content = tab.original_content

        self.tab_widget.removeTab(index)
        self.tabs.pop(index)
        self.update_title()

        new_window = MyNotepad()
        if len(new_window.tabs) > 0:
            new_window.tab_widget.removeTab(0)
            new_window.tabs.pop(0)

        new_tab = new_window.add_new_tab(file_path, content)
        if is_modified:
            new_tab.is_modified = True
            new_tab.original_content = original_content
            new_window.update_tab_title(0)
            new_window.update_title()
        else:
            new_tab.original_content = original_content

        new_window.dark_mode = self.dark_mode
        for t in new_window.tabs:
            t.editor.toggle_dark_mode(self.dark_mode)
        new_window.apply_theme()
        new_window.apply_font()
        new_window.show()

    # ============ SESSION RESTORE ============
    def restore_session(self):
        if not self.restore_tabs:
            return False

        settings = QSettings("coding-pudding", "coding-pudding")
        session_files = settings.value("session_files", [])
        session_positions = settings.value("session_positions", [])
        session_active = settings.value("session_active", 0, type=int)

        if not session_files:
            return False

        if isinstance(session_files, str):
            session_files = [session_files]
        if isinstance(session_positions, str):
            session_positions = [session_positions]
        if not isinstance(session_positions, list):
            session_positions = []

        opened = 0
        for i, file_path in enumerate(session_files):
            if not file_path or not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tab = self.add_new_tab(file_path, content)

                if i < len(session_positions):
                    try:
                        pos = int(session_positions[i])
                        cursor = tab.editor.textCursor()
                        doc_len = tab.editor.document().characterCount() - 1
                        pos = min(pos, max(0, doc_len))
                        cursor.setPosition(pos)
                        tab.editor.setTextCursor(cursor)
                    except (ValueError, TypeError):
                        pass

                opened += 1
            except Exception:
                continue

        if opened == 0:
            return False

        for i, tab in enumerate(self.tabs):
            if tab.file_path is None and not tab.is_modified and not tab.editor.toPlainText():
                self.tab_widget.removeTab(i)
                self.tabs.pop(i)
                break

        if 0 <= session_active < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(session_active)

        self.apply_font()
        return True

    def save_session(self):
        if not self.restore_tabs:
            settings = QSettings("coding-pudding", "coding-pudding")
            settings.remove("session_files")
            settings.remove("session_positions")
            settings.remove("session_active")
            return

        files = []
        positions = []

        for tab in self.tabs:
            if tab.file_path and os.path.isfile(tab.file_path):
                files.append(tab.file_path)
                cursor = tab.editor.textCursor()
                positions.append(cursor.position())

        settings = QSettings("coding-pudding", "coding-pudding")
        settings.setValue("session_files", files)
        settings.setValue("session_positions", positions)
        settings.setValue("session_active", self.tab_widget.currentIndex())

    def load_settings(self):
        settings = QSettings("coding-pudding", "coding-pudding")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)

        dark_mode = settings.value("dark_mode", False, type=bool)
        if dark_mode:
            self.dark_mode = True
            self.apply_theme()

        font_family = settings.value("font_family", "Consolas", type=str)
        font_size = settings.value("font_size", 14, type=int)
        if font_family:
            self.font_family = font_family
        if font_size:
            self.font_size = int(font_size)

        self.word_wrap = settings.value("word_wrap", False, type=bool)
        self.show_line_numbers = settings.value("show_line_numbers", True, type=bool)
        self.trim_on_save = settings.value("trim_on_save", False, type=bool)

        # v5.0
        self.indent_size = settings.value("indent_size", 4, type=int)
        self.restore_tabs = settings.value("restore_tabs", True, type=bool)

    def save_settings(self):
        settings = QSettings("coding-pudding", "coding-pudding")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("dark_mode", self.dark_mode)
        settings.setValue("font_family", self.font_family)
        settings.setValue("font_size", self.font_size)
        settings.setValue("word_wrap", self.word_wrap)
        settings.setValue("show_line_numbers", self.show_line_numbers)
        settings.setValue("trim_on_save", self.trim_on_save)
        settings.setValue("indent_size", self.indent_size)
        settings.setValue("restore_tabs", self.restore_tabs)

    def current_editor(self):
        return self.tab_widget.currentWidget()

    def current_tab(self):
        index = self.tab_widget.currentIndex()
        if 0 <= index < len(self.tabs):
            return self.tabs[index]
        return None

    def add_new_tab(self, file_path=None, content=None):
        editor = CodeEditor(
            self,
            self.dark_mode,
            indent_size=self.indent_size
        )
        editor.font_family = self.font_family
        editor.font_size = self.font_size
        editor.apply_font()

        editor.line_number_area.setVisible(self.show_line_numbers)
        if self.show_line_numbers:
            editor.update_line_number_area_width()
        else:
            editor.setViewportMargins(0, 0, 0, 0)

        if self.word_wrap:
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        editor.cursorPositionChanged.connect(self.update_cursor_position)
        editor.textChanged.connect(self.on_text_changed)

        tab = EditorTab(editor, file_path, False)

        if content is not None:
            editor.blockSignals(True)
            editor.setPlainText(content)
            editor.blockSignals(False)
            editor.apply_font()
            tab.original_content = content
        else:
            tab.original_content = ""

        self.tabs.append(tab)
        index = self.tab_widget.addTab(editor, tab.get_display_name())
        self.tab_widget.setTabToolTip(index, tab.get_tooltip())
        self.tab_widget.setCurrentIndex(index)

        return tab

    def on_tab_changed(self, index):
        if 0 <= index < len(self.tabs):
            self.update_cursor_position()
            self.update_title()

    def update_tab_title(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            self.tab_widget.setTabText(index, tab.get_display_name())
            self.tab_widget.setTabToolTip(index, tab.get_tooltip())

    def close_tab(self, index):
        if index < 0 or index >= len(self.tabs):
            return
        tab = self.tabs[index]
        if tab.is_modified:
            self.tab_widget.setCurrentIndex(index)
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"Do you want to save changes to {tab.get_display_name().rstrip(' *')}?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_tab(index):
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tab_widget.removeTab(index)
        self.tabs.pop(index)
        if len(self.tabs) == 0:
            self.add_new_tab()
        self.update_title()

    # ============ CLOSE ALL / CLOSE OTHERS ============
    def close_all_tabs(self):
        if not self.tabs:
            return

        modified_tabs = [t for t in self.tabs if t.is_modified]

        if modified_tabs:
            file_list = "\n".join(f"  - {t.get_display_name().rstrip(' *')}" for t in modified_tabs[:5])
            if len(modified_tabs) > 5:
                file_list += f"\n  ... and {len(modified_tabs) - 5} more"

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Save changes before closing?")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(f"You have {len(modified_tabs)} file(s) with unsaved changes:")
            msg_box.setInformativeText(file_list)
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Save
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Save)

            msg_box.button(QMessageBox.StandardButton.Save).setText("Save All && Close")
            msg_box.button(QMessageBox.StandardButton.Discard).setText("Discard All")
            msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel")

            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.Save:
                for i in range(len(self.tabs)):
                    if self.tabs[i].is_modified:
                        if not self.save_tab(i):
                            return
            elif reply == QMessageBox.StandardButton.Discard:
                pass
            else:
                return

        self.tab_widget.blockSignals(True)
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        self.tabs.clear()
        self.tab_widget.blockSignals(False)

        self.add_new_tab()
        self.update_title()

    def close_other_tabs(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0 or len(self.tabs) <= 1:
            return

        current_tab = self.tabs[current_index]

        others_modified = [
            self.tabs[i] for i in range(len(self.tabs))
            if i != current_index and self.tabs[i].is_modified
        ]

        if others_modified:
            file_list = "\n".join(f"  - {t.get_display_name().rstrip(' *')}" for t in others_modified[:5])
            if len(others_modified) > 5:
                file_list += f"\n  ... and {len(others_modified) - 5} more"

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Save changes before closing?")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(f"You have {len(others_modified)} other file(s) with unsaved changes:")
            msg_box.setInformativeText(file_list)
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Save
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Save)

            msg_box.button(QMessageBox.StandardButton.Save).setText("Save All && Close")
            msg_box.button(QMessageBox.StandardButton.Discard).setText("Discard All")
            msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel")

            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.Save:
                for i in range(len(self.tabs) - 1, -1, -1):
                    if i != current_index and self.tabs[i].is_modified:
                        self.tab_widget.setCurrentIndex(i)
                        if not self.save_tab(i):
                            self.tab_widget.setCurrentIndex(current_index)
                            return
                self.tab_widget.setCurrentIndex(current_index)
            elif reply == QMessageBox.StandardButton.Discard:
                pass
            else:
                return

        self.tab_widget.blockSignals(True)
        self.tab_widget.removeTab(current_index)
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)
        self.tab_widget.addTab(current_tab.editor, current_tab.get_display_name())
        self.tabs = [current_tab]
        self.tab_widget.blockSignals(False)
        self.tab_widget.setCurrentIndex(0)
        self.update_title()

    # ============ TAB CONTEXT MENU ============
    def show_tab_context_menu(self, index, global_pos):
        if index < 0 or index >= len(self.tabs):
            return

        tab = self.tabs[index]
        has_file = tab.file_path is not None

        menu = QMenu(self)

        close_action = menu.addAction("Close")
        close_action.triggered.connect(lambda: self.close_tab(index))

        close_others_action = menu.addAction("Close Others")
        close_others_action.setEnabled(len(self.tabs) > 1)
        close_others_action.triggered.connect(lambda: self._close_others_for(index))

        close_all_action = menu.addAction("Close All")
        close_all_action.triggered.connect(self.close_all_tabs)

        close_right_action = menu.addAction("Close Tabs to the Right")
        close_right_action.setEnabled(index < len(self.tabs) - 1)
        close_right_action.triggered.connect(lambda: self._close_tabs_to_right(index))

        close_left_action = menu.addAction("Close Tabs to the Left")
        close_left_action.setEnabled(index > 0)
        close_left_action.triggered.connect(lambda: self._close_tabs_to_left(index))

        menu.addSeparator()

        copy_path_action = menu.addAction("Copy Full Path")
        copy_path_action.setEnabled(has_file)
        copy_path_action.triggered.connect(lambda: self._copy_tab_path(index))

        copy_name_action = menu.addAction("Copy File Name")
        copy_name_action.triggered.connect(lambda: self._copy_tab_name(index))

        open_folder_action = menu.addAction("Open Containing Folder")
        open_folder_action.setEnabled(has_file)
        open_folder_action.triggered.connect(lambda: self._open_containing_folder(index))

        menu.addSeparator()

        rename_action = menu.addAction("Rename File...")
        rename_action.setEnabled(has_file)
        rename_action.triggered.connect(lambda: self._rename_tab_file(index))

        reload_action = menu.addAction("Reload from Disk")
        reload_action.setEnabled(has_file)
        reload_action.triggered.connect(lambda: self._reload_tab_from_disk(index))

        menu.exec(global_pos)

    def _close_others_for(self, index):
        self.tab_widget.setCurrentIndex(index)
        self.close_other_tabs()

    def _close_tabs_to_right(self, index):
        if index >= len(self.tabs) - 1:
            return

        to_close = list(range(index + 1, len(self.tabs)))
        modified = [self.tabs[i] for i in to_close if self.tabs[i].is_modified]
        if modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"{len(modified)} tab(s) have unsaved changes. Close them anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.tab_widget.blockSignals(True)
        for i in range(len(self.tabs) - 1, index, -1):
            self.tab_widget.removeTab(i)
            self.tabs.pop(i)
        self.tab_widget.blockSignals(False)
        self.update_title()

    def _close_tabs_to_left(self, index):
        if index <= 0:
            return

        to_close = list(range(0, index))
        modified = [self.tabs[i] for i in to_close if self.tabs[i].is_modified]
        if modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"{len(modified)} tab(s) have unsaved changes. Close them anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        current = self.tab_widget.currentIndex()
        self.tab_widget.blockSignals(True)
        for i in range(index - 1, -1, -1):
            self.tab_widget.removeTab(i)
            self.tabs.pop(i)
        self.tab_widget.blockSignals(False)

        new_current = current - index
        if new_current < 0:
            new_current = 0
        self.tab_widget.setCurrentIndex(new_current)
        self.update_title()

    def _copy_tab_path(self, index):
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            if tab.file_path:
                QApplication.clipboard().setText(tab.file_path)

    def _copy_tab_name(self, index):
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            if tab.file_path:
                QApplication.clipboard().setText(os.path.basename(tab.file_path))
            else:
                QApplication.clipboard().setText("Untitled")

    def _open_containing_folder(self, index):
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            if tab.file_path:
                folder = os.path.dirname(tab.file_path)
                try:
                    os.startfile(folder)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Cannot open folder:\n{e}")

    def _rename_tab_file(self, index):
        if not (0 <= index < len(self.tabs)):
            return
        tab = self.tabs[index]
        if not tab.file_path:
            return

        old_path = tab.file_path
        old_name = os.path.basename(old_path)

        new_name, ok = QInputDialog.getText(
            self, "Rename File",
            f"Rename '{old_name}' to:",
            QLineEdit.EchoMode.Normal, old_name
        )

        if not ok or not new_name or new_name == old_name:
            return

        new_path = os.path.join(os.path.dirname(old_path), new_name)

        try:
            os.rename(old_path, new_path)
            tab.file_path = new_path
            self.update_tab_title(index)
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, "Rename Error", f"Cannot rename file:\n{e}")

    def _reload_tab_from_disk(self, index):
        if not (0 <= index < len(self.tabs)):
            return
        tab = self.tabs[index]
        if not tab.file_path:
            return

        if tab.is_modified:
            reply = QMessageBox.question(
                self, "Reload File",
                "The file has unsaved changes. Reload and lose them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            with open(tab.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tab.editor.blockSignals(True)
            tab.editor.setPlainText(content)
            tab.editor.blockSignals(False)
            tab.editor.apply_font()
            tab.original_content = content
            tab.is_modified = False
            self.update_tab_title(index)
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, "Reload Error", f"Cannot reload file:\n{e}")

    def next_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            index = (self.tab_widget.currentIndex() + 1) % count
            self.tab_widget.setCurrentIndex(index)

    def prev_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            index = (self.tab_widget.currentIndex() - 1) % count
            self.tab_widget.setCurrentIndex(index)

    def save_tab(self, index):
        if index < 0 or index >= len(self.tabs):
            return False
        tab = self.tabs[index]

        if self.trim_on_save:
            tab.editor.trim_trailing_spaces()

        if tab.file_path:
            try:
                content = tab.editor.toPlainText()
                with open(tab.file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                tab.is_modified = False
                tab.original_content = content
                self.update_tab_title(index)
                self.update_title()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
                return False
        else:
            return self.save_tab_as(index)

    def save_tab_as(self, index):
        if index < 0 or index >= len(self.tabs):
            return False
        tab = self.tabs[index]

        if self.trim_on_save:
            tab.editor.trim_trailing_spaces()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                content = tab.editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                tab.file_path = file_path
                tab.is_modified = False
                tab.original_content = content
                self.update_tab_title(index)
                self.update_title()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
                return False
        return False

    def on_text_changed(self):
        tab = self.current_tab()
        if not tab:
            return

        editor = tab.editor

        # Fast check: compare length first
        current_len = editor.document().characterCount() - 1
        original_len = len(tab.original_content)

        if current_len != original_len:
            is_modified = True
        else:
            current_content = editor.toPlainText()
            is_modified = (current_content != tab.original_content)

        if is_modified != tab.is_modified:
            tab.is_modified = is_modified
            self.update_tab_title()
            self.update_title()

    def update_title(self):
        base_title = "coding-pudding.exe"
        tab = self.current_tab()
        if tab:
            if tab.file_path:
                filename = os.path.basename(tab.file_path)
                if tab.is_modified:
                    self.setWindowTitle(f"{base_title} - {filename} *")
                else:
                    self.setWindowTitle(f"{base_title} - {filename}")
            else:
                if tab.is_modified:
                    self.setWindowTitle(f"{base_title} *")
                else:
                    self.setWindowTitle(base_title)
        else:
            self.setWindowTitle(base_title)

    def update_cursor_position(self):
        """Optimized - uses block position instead of full text copy"""
        editor = self.current_editor()
        if not editor:
            return

        cursor = editor.textCursor()
        block = cursor.block()

        line_number = block.blockNumber() + 1
        column_number = cursor.positionInBlock() + 1

        self.position_label.setText(f"Ln {line_number}, Col {column_number}")

        # Cheap line ending detection - only checks last 2 chars
        doc = editor.document()
        if doc.characterCount() <= 1:
            self.line_ending_label.setText("None")
            return

        last_cursor = QTextCursor(doc)
        last_cursor.movePosition(QTextCursor.MoveOperation.End)
        last_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 2)
        last_chars = last_cursor.selectedText()

        if last_chars.endswith('\r\n'):
            self.line_ending_label.setText("Windows (CRLF)")
        elif last_chars.endswith('\n'):
            self.line_ending_label.setText("Unix (LF)")
        elif last_chars.endswith('\r'):
            self.line_ending_label.setText("Macintosh (CR)")
        else:
            self.line_ending_label.setText("None")

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #1e1e1e; }
                QMenuBar { background-color: #2d2d2d; color: #d4d4d4; }
                QMenuBar::item { background-color: #2d2d2d; color: #d4d4d4; }
                QMenuBar::item:selected { background-color: #3d3d3d; color: white; }
                QMenu { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3d3d3d; }
                QMenu::item:selected { background-color: #3d3d3d; color: white; }
                QStatusBar { background-color: #2d2d2d; color: #d4d4d4; }
                QLabel { color: #d4d4d4; }
                QDialog { background-color: #2d2d2d; color: #d4d4d4; }
                QLineEdit { background-color: #3d3d3d; color: #d4d4d4; border: 1px solid #4d4d4d; padding: 3px; }
                QPushButton { background-color: #3d3d3d; color: #d4d4d4; border: 1px solid #4d4d4d; padding: 5px 10px; }
                QPushButton:hover { background-color: #4d4d4d; }
                QCheckBox { color: #d4d4d4; }
                QGroupBox { color: #d4d4d4; border: 1px solid #4d4d4d; margin-top: 8px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QRadioButton { color: #d4d4d4; }
                QTabWidget::pane { border: none; background-color: #1e1e1e; }
                QTabBar::tab { background-color: #2d2d2d; color: #d4d4d4; padding: 8px 20px; border: 1px solid #3d3d3d; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 3px; }
                QTabBar::tab:selected { background-color: #1e1e1e; color: white; }
                QTabBar::tab:hover { background-color: #3d3d3d; }
                QComboBox { background-color: #3d3d3d; color: #d4d4d4; border: 1px solid #4d4d4d; padding: 3px; }
                QComboBox QAbstractItemView { background-color: #2d2d2d; color: #d4d4d4; selection-background-color: #3d3d3d; }
                QSpinBox { background-color: #3d3d3d; color: #d4d4d4; border: 1px solid #4d4d4d; padding: 3px; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #f0f0f0; }
                QMenuBar { background-color: #f0f0f0; color: black; }
                QMenuBar::item:selected { background-color: #e0e0e0; }
                QMenu { background-color: white; color: black; }
                QMenu::item:selected { background-color: #e0e0e0; }
                QStatusBar { background-color: #f0f0f0; color: black; }
                QLabel { color: black; }
                QDialog { background-color: white; color: black; }
                QLineEdit { background-color: white; color: black; border: 1px solid #ccc; padding: 3px; }
                QPushButton { background-color: #f0f0f0; color: black; border: 1px solid #ccc; padding: 5px 10px; }
                QPushButton:hover { background-color: #e0e0e0; }
                QCheckBox { color: black; }
                QGroupBox { color: black; border: 1px solid #ccc; margin-top: 8px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QRadioButton { color: black; }
                QTabWidget::pane { border: none; background-color: white; }
                QTabBar::tab { background-color: #e0e0e0; color: black; padding: 6px 12px; border: 1px solid #ccc; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 3px; }
                QTabBar::tab:selected { background-color: white; color: black; }
                QTabBar::tab:hover { background-color: #f0f0f0; }
                QComboBox { background-color: white; color: black; border: 1px solid #ccc; padding: 3px; }
                QComboBox QAbstractItemView { background-color: white; color: black; selection-background-color: #e0e0e0; }
                QSpinBox { background-color: white; color: black; border: 1px solid #ccc; padding: 3px; }
            """)
        self.update_status_bar_style()

    def update_status_bar_style(self):
        if self.dark_mode:
            self.status_bar.setStyleSheet("""
                QStatusBar { padding: 6px 0px; font-size: 11pt; background-color: #2d2d2d; color: #d4d4d4; }
                QLabel { color: #d4d4d4; }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar { padding: 6px 0px; font-size: 11pt; background-color: #f0f0f0; color: black; }
                QLabel { color: black; }
            """)

    def apply_font(self):
        for tab in self.tabs:
            tab.editor.font_family = self.font_family
            tab.editor.font_size = self.font_size
            tab.editor.apply_font()

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.position_label = QLabel("Ln 1, Col 1")
        self.position_label.setStyleSheet("padding: 0px 15px;")
        self.status_bar.addPermanentWidget(self.position_label)

        self.encoding_label = QLabel("UTF-8")
        self.encoding_label.setStyleSheet("padding: 0px 15px;")
        self.status_bar.addPermanentWidget(self.encoding_label)

        self.line_ending_label = QLabel("Windows (CRLF)")
        self.line_ending_label.setStyleSheet("padding: 0px 15px;")
        self.status_bar.addPermanentWidget(self.line_ending_label)

        self.update_status_bar_style()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # FILE
        file_menu = menu_bar.addMenu("File")

        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.new_file)
        file_menu.addAction(new_tab_action)

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        file_menu.addAction(close_tab_action)

        close_others_action = QAction("Close Other Tabs", self)
        close_others_action.triggered.connect(self.close_other_tabs)
        file_menu.addAction(close_others_action)

        close_all_action = QAction("Close All Tabs", self)
        close_all_action.setShortcut("Ctrl+Alt+W")
        close_all_action.triggered.connect(self.close_all_tabs)
        file_menu.addAction(close_all_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # EDIT
        edit_menu = menu_bar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.current_editor().undo() if self.current_editor() else None)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.current_editor().redo() if self.current_editor() else None)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.current_editor().cut() if self.current_editor() else None)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.current_editor().copy() if self.current_editor() else None)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.current_editor().paste() if self.current_editor() else None)
        edit_menu.addAction(paste_action)

        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_text)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        find_action = QAction("Find...", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)

        replace_action = QAction("Replace...", self)
        replace_action.setShortcut("Ctrl+H")
        replace_action.triggered.connect(self.show_replace_dialog)
        edit_menu.addAction(replace_action)

        goto_action = QAction("Go To...", self)
        goto_action.setShortcut("Ctrl+G")
        goto_action.triggered.connect(self.show_goto_dialog)
        edit_menu.addAction(goto_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(lambda: self.current_editor().selectAll() if self.current_editor() else None)
        edit_menu.addAction(select_all_action)

        time_date_action = QAction("Time/Date", self)
        time_date_action.setShortcut("F5")
        time_date_action.triggered.connect(self.insert_time_date)
        edit_menu.addAction(time_date_action)

        comment_action = QAction("Toggle Comment", self)
        comment_action.setShortcut("Ctrl+/")
        comment_action.triggered.connect(lambda: self.current_editor().toggle_comment() if self.current_editor() else None)
        edit_menu.addAction(comment_action)

        trim_action = QAction("Trim Trailing Spaces", self)
        trim_action.triggered.connect(lambda: self.current_editor().trim_trailing_spaces() if self.current_editor() else None)
        edit_menu.addAction(trim_action)

        # TAB
        tab_menu = menu_bar.addMenu("Tab")

        next_tab_action = QAction("Next Tab", self)
        next_tab_action.setShortcut("Ctrl+Tab")
        next_tab_action.triggered.connect(self.next_tab)
        tab_menu.addAction(next_tab_action)

        prev_tab_action = QAction("Previous Tab", self)
        prev_tab_action.setShortcut("Ctrl+Shift+Tab")
        prev_tab_action.triggered.connect(self.prev_tab)
        tab_menu.addAction(prev_tab_action)

        # FORMAT
        format_menu = menu_bar.addMenu("Format")

        word_wrap_action = QAction("Word Wrap", self)
        word_wrap_action.setCheckable(True)
        word_wrap_action.setChecked(self.word_wrap)
        word_wrap_action.triggered.connect(self.toggle_word_wrap)
        format_menu.addAction(word_wrap_action)

        # VIEW
        view_menu = menu_bar.addMenu("View")

        status_bar_action = QAction("Status Bar", self)
        status_bar_action.setCheckable(True)
        status_bar_action.setChecked(True)
        status_bar_action.triggered.connect(self.toggle_status_bar)
        view_menu.addAction(status_bar_action)

        word_count_action = QAction("Word Count", self)
        word_count_action.setShortcut("Ctrl+Shift+W")
        word_count_action.triggered.connect(self.show_word_count)
        view_menu.addAction(word_count_action)

        # SETTINGS
        settings_action = QAction("Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        menu_bar.addAction(settings_action)

        # HELP
        help_menu = menu_bar.addMenu("Help")

        register_action = QAction("Register 'Open with' Menu", self)
        register_action.triggered.connect(self.manual_register)
        help_menu.addAction(register_action)

        unregister_action = QAction("Unregister 'Open with' Menu", self)
        unregister_action.triggered.connect(self.manual_unregister)
        help_menu.addAction(unregister_action)

        help_menu.addSeparator()

        about_action = QAction("About coding-pudding", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def manual_register(self):
        if not getattr(sys, 'frozen', False):
            QMessageBox.information(self, "Info",
                "This feature only works when running as .exe\n(not when running as .py)")
            return
        exe_path = sys.executable
        if register_context_menu(exe_path):
            QMessageBox.information(self, "Success",
                f"Registered 'Open with coding-pudding' for:\n{exe_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to register context menu.")

    def manual_unregister(self):
        if unregister_context_menu():
            QMessageBox.information(self, "Success",
                "Unregistered 'Open with coding-pudding' menu.")
        else:
            QMessageBox.critical(self, "Error", "Failed to unregister context menu.")

    def show_about(self):
        QMessageBox.about(self, "About coding-pudding",
            "<h2>coding-pudding.exe</h2>"
            "<p>Lightweight Python editor for weak PCs</p>"
            "<p><b>Version:</b> 5.0</p>"
            "<p><b>RAM:</b> ~30MB</p>"
            "<p><b>License:</b> GPL v3</p>")

    def toggle_dark_mode(self, checked):
        self.dark_mode = checked
        for tab in self.tabs:
            tab.editor.dark_mode = checked
            tab.editor.update_colors()
        self.apply_theme()

    def delete_text(self):
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()

    def insert_time_date(self):
        editor = self.current_editor()
        if editor:
            now = datetime.now()
            cursor = editor.textCursor()
            cursor.insertText(now.strftime("%I:%M %p %m/%d/%Y"))

    def toggle_word_wrap(self, checked):
        self.word_wrap = checked
        for tab in self.tabs:
            if checked:
                tab.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
                tab.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            else:
                tab.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
                tab.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def show_word_count(self):
        editor = self.current_editor()
        if not editor:
            return

        stats = editor.get_word_count()

        QMessageBox.information(
            self,
            "Word Count",
            f"<h3>Statistics</h3>"
            f"<table>"
            f"<tr><td><b>Characters:</b></td><td>{stats['chars']:,}</td></tr>"
            f"<tr><td><b>Characters (no space):</b></td><td>{stats['chars_no_space']:,}</td></tr>"
            f"<tr><td><b>Words:</b></td><td>{stats['words']:,}</td></tr>"
            f"<tr><td><b>Lines:</b></td><td>{stats['lines']:,}</td></tr>"
            f"<tr><td><b>Paragraphs:</b></td><td>{stats['paragraphs']:,}</td></tr>"
            f"</table>"
        )

    def toggle_status_bar(self, checked):
        self.status_bar.setVisible(checked)

    def show_find_dialog(self):
        editor = self.current_editor()
        if editor:
            self.find_dialog = FindDialog(editor)
            self.find_dialog.show()

    def show_replace_dialog(self):
        editor = self.current_editor()
        if editor:
            self.replace_dialog = ReplaceDialog(editor)
            self.replace_dialog.show()

    def show_goto_dialog(self):
        editor = self.current_editor()
        if editor:
            dialog = GotoDialog(editor)
            dialog.exec()

    def new_file(self):
        self.add_new_tab()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.add_new_tab(file_path, content)
                self.apply_font()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")

    def save_file(self):
        index = self.tab_widget.currentIndex()
        self.save_tab(index)

    def save_as_file(self):
        index = self.tab_widget.currentIndex()
        self.save_tab_as(index)

    def closeEvent(self, event):
        self.save_settings()
        self.save_session()

        for i in range(len(self.tabs) - 1, -1, -1):
            tab = self.tabs[i]
            if tab.is_modified:
                self.tab_widget.setCurrentIndex(i)
                reply = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"Do you want to save changes to {tab.get_display_name().rstrip(' *')}?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Save:
                    if not self.save_tab(i):
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
        event.accept()

    # ============ DRAG & DROP ============
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        event.acceptProposedAction()

        errors = []

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue

            file_path = url.toLocalFile()

            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.add_new_tab(file_path, content)
                self.apply_font()
            except UnicodeDecodeError:
                errors.append(f"{os.path.basename(file_path)}: binary or non-UTF-8 file")
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        if errors:
            QMessageBox.warning(
                self, "Cannot Open Files",
                "coding-pudding is a text editor and can only open text files (UTF-8).\n\n"
                "The following files are not supported:\n\n" + "\n".join(errors)
            )


# ============================================================
# DIALOGS
# ============================================================

class FindDialog(QDialog):
    def __init__(self, text_area):
        super().__init__()
        self.text_area = text_area
        self.setWindowTitle("Find")
        self.setFixedSize(400, 180)

        layout = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Find what:"))
        self.find_input = QLineEdit()
        hbox.addWidget(self.find_input)
        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.case_check = QCheckBox("Match case")
        hbox2.addWidget(self.case_check)
        self.word_check = QCheckBox("Whole word")
        hbox2.addWidget(self.word_check)
        layout.addLayout(hbox2)

        direction_group = QGroupBox("Direction")
        direction_layout = QHBoxLayout()

        self.direction_down = QRadioButton("Down")
        self.direction_down.setChecked(True)
        direction_layout.addWidget(self.direction_down)

        self.direction_up = QRadioButton("Up")
        direction_layout.addWidget(self.direction_up)

        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)

        hbox3 = QHBoxLayout()
        find_next = QPushButton("Find Next")
        find_next.clicked.connect(self.on_find_next_clicked)
        find_next.setDefault(True)
        hbox3.addWidget(find_next)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        hbox3.addWidget(close_btn)
        layout.addLayout(hbox3)

        self.setLayout(layout)

    def on_find_next_clicked(self):
        self.show_not_found = True
        self.find_next()

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return

        cursor = self.text_area.textCursor()
        flags = QTextDocument.FindFlag(0)
        if self.case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords

        if self.direction_up.isChecked():
            flags |= QTextDocument.FindFlag.FindBackward

        new_cursor = self.text_area.document().find(text, cursor, flags)
        if not new_cursor.isNull():
            self.text_area.setTextCursor(new_cursor)
        else:
            if self.direction_up.isChecked():
                cursor.movePosition(QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.Start)

            new_cursor = self.text_area.document().find(text, cursor, flags)
            if not new_cursor.isNull():
                self.text_area.setTextCursor(new_cursor)
            else:
                if getattr(self, 'show_not_found', True):
                    QMessageBox.information(
                        self, "Find",
                        f'Cannot find "{text}"'
                    )
                self.show_not_found = False


class ReplaceDialog(QDialog):
    def __init__(self, text_area):
        super().__init__()
        self.text_area = text_area
        self.setWindowTitle("Replace")
        self.setFixedSize(400, 240)

        layout = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Find what:"))
        self.find_input = QLineEdit()
        hbox.addWidget(self.find_input)
        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(QLabel("Replace with:"))
        self.replace_input = QLineEdit()
        hbox2.addWidget(self.replace_input)
        layout.addLayout(hbox2)

        hbox3 = QHBoxLayout()
        self.case_check = QCheckBox("Match case")
        hbox3.addWidget(self.case_check)
        self.word_check = QCheckBox("Whole word")
        hbox3.addWidget(self.word_check)
        layout.addLayout(hbox3)

        direction_group = QGroupBox("Direction")
        direction_layout = QHBoxLayout()

        self.direction_down = QRadioButton("Down")
        self.direction_down.setChecked(True)
        direction_layout.addWidget(self.direction_down)

        self.direction_up = QRadioButton("Up")
        direction_layout.addWidget(self.direction_up)

        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)

        hbox4 = QHBoxLayout()
        find_btn = QPushButton("Find Next")
        find_btn.clicked.connect(self.on_find_next_clicked)
        find_btn.setDefault(True)
        hbox4.addWidget(find_btn)
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(self.replace)
        hbox4.addWidget(replace_btn)
        replace_all_btn = QPushButton("Replace All")
        replace_all_btn.clicked.connect(self.replace_all)
        hbox4.addWidget(replace_all_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        hbox4.addWidget(close_btn)
        layout.addLayout(hbox4)

        self.setLayout(layout)

    def on_find_next_clicked(self):
        self.show_not_found = True
        self.find_next()

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return

        cursor = self.text_area.textCursor()
        flags = QTextDocument.FindFlag(0)
        if self.case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords

        if self.direction_up.isChecked():
            flags |= QTextDocument.FindFlag.FindBackward

        new_cursor = self.text_area.document().find(text, cursor, flags)
        if not new_cursor.isNull():
            self.text_area.setTextCursor(new_cursor)
        else:
            if self.direction_up.isChecked():
                cursor.movePosition(QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.Start)

            new_cursor = self.text_area.document().find(text, cursor, flags)
            if not new_cursor.isNull():
                self.text_area.setTextCursor(new_cursor)
            else:
                if getattr(self, 'show_not_found', True):
                    QMessageBox.information(
                        self, "Replace",
                        f'Cannot find "{text}"'
                    )
                self.show_not_found = False

    def replace(self):
        text = self.find_input.text()
        if not text:
            return

        cursor = self.text_area.textCursor()

        if not cursor.hasSelection():
            self.find_next()
            return

        if cursor.selectedText() != text:
            self.find_next()
            return

        cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not text:
            return

        count = 0
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_area.setTextCursor(cursor)

        flags = QTextDocument.FindFlag(0)
        if self.case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_check.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords

        while True:
            new_cursor = self.text_area.document().find(text, cursor, flags)
            if new_cursor.isNull():
                break
            self.text_area.setTextCursor(new_cursor)
            cursor = self.text_area.textCursor()
            cursor.insertText(replace_text)
            count += 1

        if count > 0:
            QMessageBox.information(
                self, "Replace All",
                f"Replaced {count} occurrence(s)"
            )
        else:
            QMessageBox.information(
                self, "Replace All",
                f'Cannot find "{text}"'
            )


class GotoDialog(QDialog):
    def __init__(self, text_area):
        super().__init__()
        self.text_area = text_area
        self.setWindowTitle("Go To")
        self.setFixedSize(300, 120)

        layout = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Line number:"))
        self.line_input = QLineEdit()
        self.line_input.returnPressed.connect(self.go_to_line)
        hbox.addWidget(self.line_input)
        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        go_btn = QPushButton("Go To")
        go_btn.clicked.connect(self.line_input.setFocus)
        hbox2.addWidget(go_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        hbox2.addWidget(close_btn)
        layout.addLayout(hbox2)

        self.setLayout(layout)

    def go_to_line(self):
        try:
            line_num = int(self.line_input.text())
            if line_num < 1:
                QMessageBox.warning(self, "Go To", "Line number must be >= 1")
                return

            total_lines = self.text_area.document().blockCount()

            if line_num > total_lines:
                QMessageBox.warning(
                    self, "Go To",
                    f"Line number too large\nTotal lines: {total_lines}"
                )
                return

            cursor = self.text_area.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)

            for i in range(line_num - 1):
                cursor.movePosition(QTextCursor.MoveOperation.Down)

            self.text_area.setTextCursor(cursor)
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Go To", "Please enter a valid number")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "coding.pudding.app.1"
        )

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    window = MyNotepad()
    auto_register_context_menu()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            window.add_new_tab(file_path, content)
            window.apply_font()
        except Exception as e:
            print(f"Error opening file: {e}")

    window.show()
    sys.exit(app.exec())