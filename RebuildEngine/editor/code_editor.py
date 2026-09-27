"""Multi-line code editor with basic syntax highlighting for Rea."""

from __future__ import annotations

import pygame
from typing import List, Optional, Tuple, Callable, Set
from .ui import Fonts, draw_rect, BG_PANEL, BORDER, TEXT, TEXT_DIM, ACCENT, INPUT_BG


# Syntax colors
C_DEFAULT = (210, 210, 220)
C_KEYWORD = (100, 180, 255)
C_STRING = (180, 220, 140)
C_NUMBER = (240, 180, 100)
C_COMMENT = (120, 130, 140)
C_EVENT = (220, 160, 220)
C_BUILTIN = (100, 220, 200)
C_LINE_NUM = (90, 95, 110)
C_CUR_LINE = (40, 45, 60)
C_SEL = (50, 80, 120)

KEYWORDS = {
    "오브젝트", "만약", "아니면", "동안", "반복", "함수", "반환",
    "참", "거짓", "그리고", "또는", "아니다",
    "생성할", "때", "매", "순간", "그릴", "충돌할", "삭제될",
}
BUILTINS = {
    "키를", "눌렀다", "그리기", "출력", "충돌한다", "충돌",
    "키를_눌렀다", "키를눌렀다",
}


class CodeEditor:
    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.lines: List[str] = [""]
        self.cursor_row = 0
        self.cursor_col = 0
        self.sel_anchor: Optional[Tuple[int, int]] = None  # (row, col) or None
        self.scroll_y = 0  # first visible line
        self.scroll_x = 0
        self.line_height = 20
        self.gutter = 44
        self.padding = 6
        self.focused = False
        self.font_size = 14
        self.on_change: Optional[Callable] = None
        self.readonly = False
        self._clipboard = ""
        self._held_keys: Set[int] = set()
        self._repeat_timer = 0.0
        self._blink = 0.0
        self._show_cursor = True
        self._line_render_cache = {}
        self._line_number_cache = {}

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)

    def set_text(self, text: str):
        self.lines = text.split("\n") if text is not None else [""]
        self._line_render_cache.clear()
        self._line_number_cache.clear()
        if not self.lines:
            self.lines = [""]
        # keep trailing empty line behavior consistent with editors
        self.cursor_row = 0
        self.cursor_col = 0
        self.sel_anchor = None
        self.scroll_y = 0
        self.scroll_x = 0

    def get_text(self) -> str:
        return "\n".join(self.lines)

    def _notify(self):
        if self.on_change:
            self.on_change(self.get_text())

    def _font(self):
        return Fonts.get(self.font_size)

    def _visible_rows(self) -> int:
        return max(1, (self.rect.h - 8) // self.line_height)

    def _clamp_cursor(self):
        self.cursor_row = max(0, min(self.cursor_row, len(self.lines) - 1))
        self.cursor_col = max(0, min(self.cursor_col, len(self.lines[self.cursor_row])))

    def _ensure_visible(self):
        vis = self._visible_rows()
        if self.cursor_row < self.scroll_y:
            self.scroll_y = self.cursor_row
        if self.cursor_row >= self.scroll_y + vis:
            self.scroll_y = self.cursor_row - vis + 1

    def _has_selection(self) -> bool:
        if self.sel_anchor is None:
            return False
        return self.sel_anchor != (self.cursor_row, self.cursor_col)

    def _sel_range(self) -> Tuple[int, int, int, int]:
        """Return (r1,c1,r2,c2) ordered."""
        if self.sel_anchor is None:
            return self.cursor_row, self.cursor_col, self.cursor_row, self.cursor_col
        ar, ac = self.sel_anchor
        br, bc = self.cursor_row, self.cursor_col
        if (ar, ac) <= (br, bc):
            return ar, ac, br, bc
        return br, bc, ar, ac

    def _delete_selection(self):
        if not self._has_selection():
            return
        r1, c1, r2, c2 = self._sel_range()
        if r1 == r2:
            line = self.lines[r1]
            self.lines[r1] = line[:c1] + line[c2:]
        else:
            first = self.lines[r1][:c1]
            last = self.lines[r2][c2:]
            self.lines = self.lines[:r1] + [first + last] + self.lines[r2 + 1 :]
        self.cursor_row, self.cursor_col = r1, c1
        self.sel_anchor = None
        if not self.lines:
            self.lines = [""]

    def _selected_text(self) -> str:
        if not self._has_selection():
            return ""
        r1, c1, r2, c2 = self._sel_range()
        if r1 == r2:
            return self.lines[r1][c1:c2]
        parts = [self.lines[r1][c1:]]
        for r in range(r1 + 1, r2):
            parts.append(self.lines[r])
        parts.append(self.lines[r2][:c2])
        return "\n".join(parts)

    def _insert_text(self, text: str):
        if self.readonly:
            return
        self._delete_selection()
        parts = text.split("\n")
        row, col = self.cursor_row, self.cursor_col
        line = self.lines[row]
        if len(parts) == 1:
            self.lines[row] = line[:col] + parts[0] + line[col:]
            self.cursor_col = col + len(parts[0])
        else:
            before = line[:col] + parts[0]
            after = parts[-1] + line[col:]
            mid = parts[1:-1]
            self.lines = self.lines[:row] + [before] + mid + [after] + self.lines[row + 1 :]
            self.cursor_row = row + len(parts) - 1
            self.cursor_col = len(parts[-1])
        self.sel_anchor = None
        self._notify()
        self._ensure_visible()

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.focused = True
                try:
                    pygame.key.start_text_input()
                    pygame.key.set_text_input_rect(self.rect)
                except Exception:
                    pass
                self._click_to_cursor(event.pos)
                mods = pygame.key.get_mods()
                if not (mods & pygame.KMOD_SHIFT):
                    self.sel_anchor = (self.cursor_row, self.cursor_col)
                return True
            else:
                if self.focused:
                    self.focused = False
                return False

        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll_y = max(0, min(len(self.lines) - 1, self.scroll_y - event.y * 3))
            return True

        if not self.focused or self.readonly:
            return False

        # Hangul / IME
        if event.type == pygame.TEXTINPUT:
            self._insert_text(event.text)
            return True
        if event.type == pygame.TEXTEDITING:
            return True

        if event.type == pygame.KEYDOWN:
            self._blink = 0
            self._show_cursor = True
            mods = event.mod
            ctrl = bool(mods & pygame.KMOD_CTRL) or bool(mods & pygame.KMOD_META)
            shift = bool(mods & pygame.KMOD_SHIFT)

            if ctrl and event.key == pygame.K_c:
                t = self._selected_text()
                if t:
                    self._clipboard = t
                    try:
                        pygame.scrap.put(pygame.SCRAP_TEXT, t.encode("utf-8"))
                    except Exception:
                        pass
                return True
            if ctrl and event.key == pygame.K_x:
                t = self._selected_text()
                if t:
                    self._clipboard = t
                    try:
                        pygame.scrap.put(pygame.SCRAP_TEXT, t.encode("utf-8"))
                    except Exception:
                        pass
                    self._delete_selection()
                    self._notify()
                return True
            if ctrl and event.key == pygame.K_v:
                t = self._clipboard
                try:
                    if pygame.scrap.get_init():
                        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if raw:
                            t = raw.decode("utf-8", errors="ignore").replace("\x00", "")
                except Exception:
                    pass
                if t:
                    self._insert_text(t)
                return True
            if ctrl and event.key == pygame.K_a:
                self.sel_anchor = (0, 0)
                self.cursor_row = len(self.lines) - 1
                self.cursor_col = len(self.lines[self.cursor_row])
                return True
            if ctrl and event.key == pygame.K_s:
                return False  # let editor handle save

            if event.key == pygame.K_LEFT:
                self._move_cursor(0, -1, shift)
                return True
            if event.key == pygame.K_RIGHT:
                self._move_cursor(0, 1, shift)
                return True
            if event.key == pygame.K_UP:
                self._move_cursor(-1, 0, shift)
                return True
            if event.key == pygame.K_DOWN:
                self._move_cursor(1, 0, shift)
                return True
            if event.key == pygame.K_HOME:
                if not shift:
                    self.sel_anchor = None
                elif self.sel_anchor is None:
                    self.sel_anchor = (self.cursor_row, self.cursor_col)
                self.cursor_col = 0
                self._ensure_visible()
                return True
            if event.key == pygame.K_END:
                if not shift:
                    self.sel_anchor = None
                elif self.sel_anchor is None:
                    self.sel_anchor = (self.cursor_row, self.cursor_col)
                self.cursor_col = len(self.lines[self.cursor_row])
                self._ensure_visible()
                return True
            if event.key == pygame.K_BACKSPACE:
                if self._has_selection():
                    self._delete_selection()
                elif self.cursor_col > 0:
                    line = self.lines[self.cursor_row]
                    self.lines[self.cursor_row] = line[: self.cursor_col - 1] + line[self.cursor_col :]
                    self.cursor_col -= 1
                elif self.cursor_row > 0:
                    prev = self.lines[self.cursor_row - 1]
                    cur = self.lines[self.cursor_row]
                    self.cursor_col = len(prev)
                    self.lines[self.cursor_row - 1] = prev + cur
                    del self.lines[self.cursor_row]
                    self.cursor_row -= 1
                self.sel_anchor = None
                self._notify()
                self._ensure_visible()
                return True
            if event.key == pygame.K_DELETE:
                if self._has_selection():
                    self._delete_selection()
                else:
                    line = self.lines[self.cursor_row]
                    if self.cursor_col < len(line):
                        self.lines[self.cursor_row] = line[: self.cursor_col] + line[self.cursor_col + 1 :]
                    elif self.cursor_row < len(self.lines) - 1:
                        self.lines[self.cursor_row] = line + self.lines[self.cursor_row + 1]
                        del self.lines[self.cursor_row + 1]
                self.sel_anchor = None
                self._notify()
                return True
            if event.key == pygame.K_RETURN:
                self._insert_text("\n")
                # auto-indent
                prev = self.lines[self.cursor_row - 1] if self.cursor_row > 0 else ""
                indent = len(prev) - len(prev.lstrip(" \t"))
                if prev.rstrip().endswith(":"):
                    indent += 4
                if indent > 0:
                    self._insert_text(" " * indent)
                return True
            if event.key == pygame.K_TAB:
                self._insert_text("    ")
                return True

            # 문자 입력은 TEXTINPUT 만 사용 (영문 두 번 입력 방지)
            return True
        return False

    def _move_cursor(self, drow, dcol, shift):
        if shift:
            if self.sel_anchor is None:
                self.sel_anchor = (self.cursor_row, self.cursor_col)
        else:
            self.sel_anchor = None
        if drow != 0:
            self.cursor_row = max(0, min(len(self.lines) - 1, self.cursor_row + drow))
            self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
        if dcol != 0:
            nc = self.cursor_col + dcol
            if nc < 0:
                if self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = len(self.lines[self.cursor_row])
            elif nc > len(self.lines[self.cursor_row]):
                if self.cursor_row < len(self.lines) - 1:
                    self.cursor_row += 1
                    self.cursor_col = 0
            else:
                self.cursor_col = nc
        self._ensure_visible()

    def _click_to_cursor(self, pos):
        font = self._font()
        local_y = pos[1] - self.rect.y - 4
        row = self.scroll_y + int(local_y // self.line_height)
        row = max(0, min(len(self.lines) - 1, row))
        local_x = pos[0] - self.rect.x - self.gutter - self.padding + self.scroll_x
        line = self.lines[row]
        col = 0
        acc = 0
        for i, ch in enumerate(line):
            w = font.size(ch)[0]
            if acc + w / 2 >= local_x:
                col = i
                break
            acc += w
            col = i + 1
        self.cursor_row = row
        self.cursor_col = col

    def update(self, dt: float):
        self._blink += dt
        if self._blink >= 0.5:
            self._blink = 0
            self._show_cursor = not self._show_cursor

    def _tokenize_line(self, line: str) -> List[Tuple[str, Tuple[int, int, int]]]:
        """Very simple tokenizer for highlighting."""
        tokens = []
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch in " \t":
                j = i
                while j < n and line[j] in " \t":
                    j += 1
                tokens.append((line[i:j], C_DEFAULT))
                i = j
                continue
            if ch == "#":
                tokens.append((line[i:], C_COMMENT))
                break
            if ch in "\"'":
                quote = ch
                j = i + 1
                while j < n and line[j] != quote:
                    if line[j] == "\\":
                        j += 1
                    j += 1
                j = min(n, j + 1)
                tokens.append((line[i:j], C_STRING))
                i = j
                continue
            if ch.isdigit() or (ch == "." and i + 1 < n and line[i + 1].isdigit()):
                j = i
                while j < n and (line[j].isdigit() or line[j] == "."):
                    j += 1
                tokens.append((line[i:j], C_NUMBER))
                i = j
                continue
            if ch.isalpha() or ch == "_" or ("\uac00" <= ch <= "\ud7a3"):
                j = i
                while j < n and (
                    line[j].isalnum()
                    or line[j] == "_"
                    or ("\uac00" <= line[j] <= "\ud7a3")
                ):
                    j += 1
                word = line[i:j]
                if word in KEYWORDS:
                    color = C_KEYWORD
                elif word in BUILTINS:
                    color = C_BUILTIN
                else:
                    color = C_DEFAULT
                tokens.append((word, color))
                i = j
                continue
            tokens.append((ch, C_DEFAULT))
            i += 1
        return tokens

    def _render_line(self, line: str):
        key = (self.font_size, line)
        cached = self._line_render_cache.get(key)
        if cached is not None:
            return cached
        font = self._font()
        tokens = self._tokenize_line(line)
        width = max(1, sum(font.size(text)[0] for text, _ in tokens) + 2)
        img = pygame.Surface((width, self.line_height), pygame.SRCALPHA)
        x = 0
        for text, color in tokens:
            part = font.render(text, True, color)
            img.blit(part, (x, 2))
            x += part.get_width()
        self._line_render_cache[key] = img
        return img

    def draw(self, surf):
        draw_rect(surf, self.rect, INPUT_BG, border=1, border_color=ACCENT if self.focused else BORDER)
        font = self._font()
        clip = surf.get_clip()
        surf.set_clip(self.rect)

        # gutter
        gutter_rect = pygame.Rect(self.rect.x, self.rect.y, self.gutter, self.rect.h)
        draw_rect(surf, gutter_rect, (32, 34, 42))

        vis = self._visible_rows()
        y0 = self.rect.y + 4
        r1, c1, r2, c2 = self._sel_range() if self._has_selection() else (-1, 0, -1, 0)

        for i in range(vis + 1):
            row = self.scroll_y + i
            if row >= len(self.lines):
                break
            y = y0 + i * self.line_height
            # current line bg
            if row == self.cursor_row and self.focused:
                pygame.draw.rect(surf, C_CUR_LINE, (self.rect.x + self.gutter, y, self.rect.w - self.gutter, self.line_height))
            # line number (cached)
            ln_key = (self.font_size, row + 1)
            ln = self._line_number_cache.get(ln_key)
            if ln is None:
                ln = font.render(str(row + 1), True, C_LINE_NUM)
                self._line_number_cache[ln_key] = ln
            surf.blit(ln, (self.rect.x + self.gutter - 6 - ln.get_width(), y + 2))

            # selection background
            if r1 <= row <= r2 and r1 >= 0:
                line = self.lines[row]
                sc = 0 if row > r1 else c1
                ec = len(line) if row < r2 else c2
                x0 = self.rect.x + self.gutter + self.padding + font.size(line[:sc])[0]
                x1 = self.rect.x + self.gutter + self.padding + font.size(line[:ec])[0]
                if x1 <= x0:
                    x1 = x0 + 4
                pygame.draw.rect(surf, C_SEL, (x0, y, x1 - x0, self.line_height))

            # text with highlight -- cached by exact line contents
            x = self.rect.x + self.gutter + self.padding
            line_img = self._render_line(self.lines[row])
            surf.blit(line_img, (x, y))

        # cursor
        if self.focused and self._show_cursor:
            row = self.cursor_row
            if self.scroll_y <= row < self.scroll_y + vis:
                line = self.lines[row]
                cx = self.rect.x + self.gutter + self.padding + font.size(line[: self.cursor_col])[0]
                cy = y0 + (row - self.scroll_y) * self.line_height
                pygame.draw.line(surf, TEXT, (cx, cy + 2), (cx, cy + self.line_height - 2), 2)

        surf.set_clip(clip)

        # status: line/col
        info = f"줄 {self.cursor_row + 1}, 열 {self.cursor_col + 1}"
        img = Fonts.get(11).render(info, True, TEXT_DIM)
        surf.blit(img, (self.rect.right - img.get_width() - 8, self.rect.bottom - 16))
