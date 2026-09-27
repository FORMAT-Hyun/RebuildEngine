"""Project Manager — Godot-style recent projects UI."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Tuple

import pygame

from editor.ui import (
    draw_rect, draw_text, Button, TextInput,
    TEXT, TEXT_DIM, ACCENT, BORDER, SUCCESS, DANGER, INPUT_BG,
)
from editor.project import Project, load_recent, add_recent, remove_recent
from editor.file_dialog import FileDialog


GODOT_BG = (30, 32, 38)
GODOT_PANEL = (36, 38, 46)
GODOT_CARD = (42, 45, 54)
GODOT_CARD_HOVER = (50, 54, 66)
GODOT_CARD_SEL = (45, 70, 110)
GODOT_TOP = (28, 30, 36)
GODOT_GREEN = (80, 180, 120)
GODOT_BORDER = (55, 58, 70)


def _fmt_mtime(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


def _project_display(path: str) -> Tuple[str, str, str]:
    path = os.path.abspath(path)
    name = os.path.basename(path.rstrip(os.sep)) or path
    meta = os.path.join(path, "project.json")
    if os.path.isfile(meta):
        try:
            import json
            with open(meta, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", name) or name
        except Exception:
            pass
        edited = _fmt_mtime(meta)
    else:
        edited = _fmt_mtime(path)
    return name, path, edited


class ProjectManager:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.clock = pygame.time.Clock()
        self.running = True
        self.result_path: Optional[str] = None
        self.recent: List[str] = load_recent()
        self.filtered: List[str] = list(self.recent)
        self.selected_idx = 0 if self.filtered else -1
        self.scroll = 0
        self.mode = "list"  # list | create
        self.error = ""
        self.status = ""
        self.file_dialog = FileDialog()
        self.search = TextInput((0, 0, 220, 30), "")
        self.name_input = TextInput((0, 0, 320, 32), "MyGame")
        self.path_input = TextInput((0, 0, 400, 32), os.path.expanduser("~"))
        self._hover_idx = -1
        self._hover_remove = -1
        self._last_click = (None, 0)
        self._build_buttons()
        self._layout()
        self._apply_search()

    def _build_buttons(self):
        self.btn_scan = Button((0, 0, 80, 30), "Scan", self._scan_recent)
        self.btn_create = Button((0, 0, 90, 30), "Create", self._start_create, accent=True)
        self.btn_import = Button((0, 0, 90, 30), "Import", self._browse_open)
        self.btn_open = Button((0, 0, 110, 34), "Edit", self._open_selected, accent=True)
        self.btn_remove = Button((0, 0, 110, 34), "목록에서 제거", self._remove_selected, danger=True)
        self.btn_do_create = Button((0, 0, 120, 36), "생성", self._do_create, accent=True)
        self.btn_browse_path = Button((0, 0, 100, 32), "폴더 찾기", self._browse_parent)
        self.btn_cancel = Button((0, 0, 90, 36), "취소", self._cancel_create)
        self.btn_quit = Button((0, 0, 70, 30), "종료", self._quit, danger=True)

    def _layout(self):
        self.w, self.h = self.screen.get_size()
        self.top_rect = pygame.Rect(0, 0, self.w, 52)
        margin = 40
        self.list_rect = pygame.Rect(margin, 70, self.w - margin * 2, self.h - 140)
        self.search.rect = pygame.Rect(self.w - 520, 11, 200, 30)
        self.btn_scan.rect = pygame.Rect(self.w - 310, 11, 70, 30)
        self.btn_create.rect = pygame.Rect(self.w - 230, 11, 80, 30)
        self.btn_import.rect = pygame.Rect(self.w - 140, 11, 80, 30)
        self.btn_quit.rect = pygame.Rect(self.w - 50, 11, 40, 30)

        self.btn_open.rect = pygame.Rect(self.list_rect.x + 16, self.h - 55, 100, 34)
        self.btn_remove.rect = pygame.Rect(self.list_rect.x + 130, self.h - 55, 120, 34)

        # create form
        self.name_input.rect = pygame.Rect(self.list_rect.x + 40, self.list_rect.y + 100, 360, 34)
        self.path_input.rect = pygame.Rect(self.list_rect.x + 40, self.list_rect.y + 180, 400, 34)
        self.btn_browse_path.rect = pygame.Rect(self.list_rect.x + 450, self.list_rect.y + 180, 100, 34)
        self.btn_do_create.rect = pygame.Rect(self.list_rect.x + 40, self.list_rect.y + 250, 120, 36)
        self.btn_cancel.rect = pygame.Rect(self.list_rect.x + 175, self.list_rect.y + 250, 90, 36)

    def _apply_search(self):
        q = (self.search.value or "").strip().lower()
        if not q:
            self.filtered = list(self.recent)
        else:
            self.filtered = []
            for p in self.recent:
                name, path, _ = _project_display(p)
                if q in name.lower() or q in path.lower():
                    self.filtered.append(p)
        if self.selected_idx >= len(self.filtered):
            self.selected_idx = len(self.filtered) - 1 if self.filtered else -1

    def _scan_recent(self):
        valid = []
        for p in load_recent():
            if os.path.isdir(p):
                valid.append(p)
            else:
                remove_recent(p)
        self.recent = valid
        from editor.project import RECENT_FILE
        import json
        try:
            with open(RECENT_FILE, "w", encoding="utf-8") as f:
                json.dump(valid, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._apply_search()
        self.status = f"스캔 완료 — {len(valid)}개 프로젝트"

    def _start_create(self):
        self.mode = "create"
        self.error = ""
        self.status = "이름과 저장 폴더를 정한 뒤 [생성]을 누르세요"
        self.name_input.set_value("MyGame")
        self.name_input.active = True
        # default parent = home or last recent parent
        if self.recent and os.path.isdir(self.recent[0]):
            parent = os.path.dirname(self.recent[0])
        else:
            parent = os.path.expanduser("~")
        self.path_input.set_value(parent)
        self.path_input.active = False

    def _cancel_create(self):
        self.mode = "list"
        self.error = ""
        self.status = ""
        self.name_input.active = False
        self.path_input.active = False

    def _browse_parent(self):
        """Pick parent folder via file dialog — any file click uses its folder."""
        start = self.path_input.value.strip() or os.path.expanduser("~")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        self.file_dialog.open(
            title="상위 폴더 선택 (폴더 안으로 들어간 뒤 확인, 또는 파일 선택 시 그 폴더 사용)",
            start_dir=start,
            extensions=None,
            on_result=self._on_parent_picked,
            mode="open_folder",
        )

    def _on_parent_picked(self, path):
        if not path:
            return
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if os.path.isdir(path):
            self.path_input.set_value(path)
            self.status = f"경로 설정: {path}"
            self.error = ""
        else:
            self.error = "유효한 폴더가 아닙니다"

    def _do_create(self):
        """Create project using name + path fields — no extra dialog required."""
        name = (self.name_input.value or "").strip()
        parent = (self.path_input.value or "").strip()
        self.error = ""
        if not name:
            self.error = "프로젝트 이름을 입력하세요"
            return
        if not parent:
            self.error = "저장 경로를 입력하세요"
            return
        parent = os.path.expanduser(parent)
        if not os.path.isdir(parent):
            # try create parent
            try:
                os.makedirs(parent, exist_ok=True)
            except Exception as e:
                self.error = f"경로를 만들 수 없음: {e}"
                return
        target = os.path.join(parent, name)
        if os.path.exists(target) and os.listdir(target):
            if Project.is_project(target):
                self.error = f"이미 프로젝트가 있습니다: {target}"
                return
            self.error = f"빈 폴더가 아닙니다: {target}"
            return
        try:
            proj = Project.create_new(parent, name)
            self.status = f"생성됨: {proj.root}"
            self.result_path = proj.root
            self.running = False
        except Exception as e:
            self.error = f"생성 실패: {e}"
            print("[ProjectManager]", e)

    def _browse_open(self):
        start = self.recent[0] if self.recent else os.path.expanduser("~")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        self.file_dialog.open(
            title="프로젝트 폴더 열기",
            start_dir=start,
            extensions=None,
            on_result=self._on_browse_open,
            mode="open_folder",
        )

    def _on_browse_open(self, path):
        if not path:
            return
        if os.path.isfile(path):
            if os.path.basename(path) == "project.json":
                path = os.path.dirname(path)
            else:
                path = os.path.dirname(path)
        if not os.path.isdir(path):
            self.error = "폴더가 아닙니다"
            return
        if not Project.is_project(path):
            try:
                p = Project(path)
                p.ensure_dirs()
                p.save_meta()
            except Exception as e:
                self.error = str(e)
                return
        add_recent(path)
        self.result_path = path
        self.running = False

    def _open_selected(self):
        if 0 <= self.selected_idx < len(self.filtered):
            path = self.filtered[self.selected_idx]
            if os.path.isdir(path):
                add_recent(path)
                self.result_path = path
                self.running = False
            else:
                self.error = "경로가 없습니다. Scan 으로 정리하세요."
                remove_recent(path)
                self.recent = load_recent()
                self._apply_search()
        else:
            self.error = "프로젝트를 선택하세요"

    def _remove_selected(self):
        if 0 <= self.selected_idx < len(self.filtered):
            path = self.filtered[self.selected_idx]
            remove_recent(path)
            self.recent = load_recent()
            self._apply_search()
            self.status = f"목록에서만 제거됨: {os.path.basename(path)}"
            self.error = ""
        else:
            self.error = "제거할 항목을 선택하세요"

    def _remove_at(self, idx: int):
        if 0 <= idx < len(self.filtered):
            path = self.filtered[idx]
            remove_recent(path)
            self.recent = load_recent()
            self._apply_search()
            self.status = f"목록에서만 제거됨: {os.path.basename(path)}"

    def _quit(self):
        self.result_path = None
        self.running = False

    def _item_rect(self, i: int) -> pygame.Rect:
        y = self.list_rect.y + 48 + i * 72 - self.scroll
        return pygame.Rect(self.list_rect.x + 12, y, self.list_rect.w - 24, 64)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(
                    (max(900, event.w), max(600, event.h)), pygame.RESIZABLE
                )
                self._layout()
                continue

            if self.file_dialog.active:
                self.file_dialog.handle_event(event)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode == "create":
                        self._cancel_create()
                    else:
                        self._quit()
                    continue
                if event.key == pygame.K_RETURN:
                    if self.mode == "create":
                        # if typing path/name, don't create on enter from field deactivation only
                        if not self.name_input.active and not self.path_input.active:
                            self._do_create()
                        else:
                            self.name_input.active = False
                            self.path_input.active = False
                    else:
                        self._open_selected()
                    continue
                if self.mode == "list":
                    if event.key == pygame.K_UP:
                        self.selected_idx = max(0, self.selected_idx - 1)
                    if event.key == pygame.K_DOWN:
                        self.selected_idx = min(len(self.filtered) - 1, self.selected_idx + 1)
                    if event.key == pygame.K_DELETE:
                        self._remove_selected()

            if self.mode == "create":
                # inputs first
                self.name_input.handle_event(event)
                self.path_input.handle_event(event)
                # buttons — always process clicks
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in (self.btn_do_create, self.btn_browse_path, self.btn_cancel, self.btn_quit):
                        if btn.rect.collidepoint(event.pos):
                            if btn.on_click:
                                btn.on_click()
                            return
                self.btn_do_create.handle_event(event)
                self.btn_browse_path.handle_event(event)
                self.btn_cancel.handle_event(event)
                self.btn_quit.handle_event(event)
            else:
                prev = self.search.value
                self.search.handle_event(event)
                if self.search.value != prev:
                    self._apply_search()
                for btn in (self.btn_scan, self.btn_create, self.btn_import, self.btn_open, self.btn_remove, self.btn_quit):
                    btn.handle_event(event)

                if event.type == pygame.MOUSEWHEEL:
                    if self.list_rect.collidepoint(pygame.mouse.get_pos()):
                        self.scroll = max(0, self.scroll - event.y * 36)

                if event.type == pygame.MOUSEMOTION:
                    self._hover_idx = -1
                    self._hover_remove = -1
                    for i in range(len(self.filtered)):
                        r = self._item_rect(i)
                        if r.collidepoint(event.pos) and r.bottom > self.list_rect.y + 40 and r.top < self.list_rect.bottom:
                            self._hover_idx = i
                            xr = pygame.Rect(r.right - 40, r.y + 16, 28, 28)
                            if xr.collidepoint(event.pos):
                                self._hover_remove = i
                            break

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(len(self.filtered)):
                        r = self._item_rect(i)
                        if not (r.collidepoint(event.pos) and r.bottom > self.list_rect.y + 40 and r.top < self.list_rect.bottom):
                            continue
                        xr = pygame.Rect(r.right - 40, r.y + 18, 26, 26)
                        if xr.collidepoint(event.pos):
                            self._remove_at(i)
                            return
                        self.selected_idx = i
                        now = pygame.time.get_ticks()
                        if self._last_click[0] == i and now - self._last_click[1] < 400:
                            self._open_selected()
                        self._last_click = (i, now)
                        break

    def draw(self):
        self.screen.fill(GODOT_BG)
        draw_rect(self.screen, self.top_rect, GODOT_TOP)
        pygame.draw.line(self.screen, GODOT_BORDER, (0, self.top_rect.bottom), (self.w, self.top_rect.bottom))
        draw_text(self.screen, "Rebuild Engine", (16, 14), TEXT, 18, bold=True)

        if self.mode == "list":
            draw_text(self.screen, "검색", (self.search.rect.x - 36, 16), TEXT_DIM, 12)
            self.search.draw(self.screen)
            self.btn_scan.draw(self.screen)
            self.btn_create.draw(self.screen)
            self.btn_import.draw(self.screen)
            self.btn_quit.draw(self.screen)

            draw_rect(self.screen, self.list_rect, GODOT_PANEL, border=1, border_color=GODOT_BORDER, radius=8)
            draw_text(self.screen, "Recent Projects", (self.list_rect.x + 16, self.list_rect.y + 14), TEXT, 15, bold=True)
            draw_text(self.screen, f"{len(self.filtered)} projects", (self.list_rect.right - 120, self.list_rect.y + 16), TEXT_DIM, 12)

            clip = self.screen.get_clip()
            inner = pygame.Rect(self.list_rect.x, self.list_rect.y + 44, self.list_rect.w, self.list_rect.h - 52)
            self.screen.set_clip(inner)
            if not self.filtered:
                draw_text(
                    self.screen,
                    "프로젝트가 없습니다. Create 또는 Import 를 사용하세요.",
                    (self.list_rect.centerx, self.list_rect.centery),
                    TEXT_DIM,
                    14,
                    center=True,
                )
            else:
                for i, path in enumerate(self.filtered):
                    r = self._item_rect(i)
                    if r.bottom < inner.top or r.top > inner.bottom:
                        continue
                    name, full, edited = _project_display(path)
                    if i == self.selected_idx:
                        bg = GODOT_CARD_SEL
                    elif i == self._hover_idx:
                        bg = GODOT_CARD_HOVER
                    else:
                        bg = GODOT_CARD
                    draw_rect(self.screen, r, bg, border=1, border_color=GODOT_BORDER, radius=6)
                    icon = pygame.Rect(r.x + 12, r.y + 12, 40, 40)
                    draw_rect(self.screen, icon, (55, 90, 140), radius=6)
                    draw_text(self.screen, name[:1].upper() or "P", icon.center, TEXT, 18, bold=True, center=True)
                    draw_text(self.screen, name, (r.x + 66, r.y + 10), TEXT, 15, bold=True)
                    draw_text(self.screen, full, (r.x + 66, r.y + 32), TEXT_DIM, 11)
                    draw_text(self.screen, f"Last edited: {edited}", (r.x + 66, r.y + 48), TEXT_DIM, 11)
                    xr = pygame.Rect(r.right - 40, r.y + 18, 26, 26)
                    xc = DANGER if i == self._hover_remove else (70, 70, 85)
                    draw_rect(self.screen, xr, xc, radius=4)
                    draw_text(self.screen, "×", xr.center, TEXT, 16, center=True)
            self.screen.set_clip(clip)
            self.btn_open.draw(self.screen)
            self.btn_remove.draw(self.screen)
            draw_text(
                self.screen,
                "삭제 = 최근 목록에서만 제거 (파일 유지)",
                (self.btn_remove.rect.right + 16, self.h - 48),
                TEXT_DIM,
                11,
            )
        else:
            # CREATE form
            draw_rect(self.screen, self.list_rect, GODOT_PANEL, border=1, border_color=GODOT_BORDER, radius=8)
            draw_text(self.screen, "새 프로젝트 만들기", (self.list_rect.x + 24, self.list_rect.y + 24), TEXT, 18, bold=True)

            draw_text(self.screen, "프로젝트 이름", (self.list_rect.x + 40, self.list_rect.y + 74), TEXT_DIM, 13)
            self.name_input.draw(self.screen)

            draw_text(self.screen, "저장 위치 (상위 폴더)", (self.list_rect.x + 40, self.list_rect.y + 154), TEXT_DIM, 13)
            self.path_input.draw(self.screen)
            self.btn_browse_path.draw(self.screen)

            # preview path
            name = (self.name_input.value or "").strip() or "MyGame"
            parent = (self.path_input.value or "").strip()
            preview = os.path.join(parent, name) if parent else name
            draw_text(self.screen, f"생성될 경로: {preview}", (self.list_rect.x + 40, self.list_rect.y + 220), TEXT_DIM, 12)

            self.btn_do_create.draw(self.screen)
            self.btn_cancel.draw(self.screen)

            draw_text(
                self.screen,
                "경로를 직접 입력하거나 [폴더 찾기] 후 [생성]을 누르세요",
                (self.list_rect.x + 40, self.list_rect.y + 300),
                TEXT_DIM,
                12,
            )

        if self.error:
            draw_text(self.screen, self.error, (40, self.h - 88), DANGER, 13)
        if self.status:
            draw_text(self.screen, self.status, (40, self.h - 88), GODOT_GREEN, 12)

        self.file_dialog.draw(self.screen)
        pygame.display.flip()

    def run(self) -> Optional[str]:
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(60)
        return self.result_path
