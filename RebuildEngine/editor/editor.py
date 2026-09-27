"""Rebuild Engine IDE - GameMaker-style editor."""

from __future__ import annotations

import os
import sys
import json
import shutil
import pygame
from typing import Optional, List, Any

from editor.ui import (
    Button, TextInput, draw_rect, draw_text, Fonts,
    BG_DARK, BG_PANEL, BG_PANEL2, BG_HOVER, BG_ACTIVE, TEXT, TEXT_DIM,
    ACCENT, SUCCESS, DANGER, BORDER, INPUT_BG, TOOLBAR, text_width,
)
from editor.viewport import Viewport
from editor.inspector import Inspector
from editor.asset_browser import AssetBrowser
from editor.resource_panel import ResourcePanel
from editor.code_editor import CodeEditor
from editor.project import Project, ProjectObject, EVENT_TYPES, EVENT_KEY_TO_LABEL
from editor.file_dialog import FileDialog
from editor.animation_dialog import AnimationDialog

from engine.core.object import GameObject, Instance
from engine.core.scene import Scene
from engine.graphics.sprite import SpriteManager


class Editor:
    def __init__(self, root_path: str):
        self.root = root_path
        pygame.init()
        try:
            pygame.scrap.init()
        except Exception:
            pass

        self.w, self.h = 1400, 900
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
        pygame.display.set_caption("Rebuild Engine IDE")
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.clock = pygame.time.Clock()
        self.running = True

        self.project = Project(root_path)
        self.project.scan()
        # 빈 프로젝트로 시작 — 기본 Object/스프라이트 자동 생성 없음

        self.sprite_manager = SpriteManager(assets_path=self.project.assets_dir)
        self.scene = Scene("main")
        self.scene_path: Optional[str] = os.path.join(self.project.scenes_dir, "main.json")
        self.dirty = False
        self.status = "준비"
        self._scene_files_cache: List[str] = []
        self._music_files_cache: List[str] = []
        self._sprite_files_cache: List[str] = []
        self._last_scene_mtime = 0.0
        self.animation_dialog = AnimationDialog()

        # selection state
        self.selected_object_name: Optional[str] = None  # project object
        self.selected_event_key: Optional[str] = None
        self.selected_instance_id: Optional[int] = None

        # layout sizes — target mockup: Resources / Events | Scene / Code | Inspector
        self.toolbar_h = 40
        self.status_h = 22
        self.left_w = 250
        self.right_w = 300
        self.code_h = 300

        # panels
        self.viewport = Viewport(pygame.Rect(0, 0, 100, 100), self.sprite_manager)
        self.inspector = Inspector(pygame.Rect(0, 0, 100, 100))
        self.inspector.sprite_manager = self.sprite_manager
        self.resources = ResourcePanel(pygame.Rect(0, 0, 100, 100))
        self.resources.sprite_manager = self.sprite_manager
        self.resources.project = self.project
        self.assets = AssetBrowser(pygame.Rect(0, 0, 100, 100), self.project.assets_dir, self.sprite_manager)
        self.code_editor = CodeEditor(pygame.Rect(0, 0, 100, 100))

        self.viewport.on_select = self._on_viewport_select
        self.viewport.on_move = self._on_instance_moved
        self.viewport.on_place = self._on_viewport_place
        self.inspector.on_change = self._on_inspector_change
        self.inspector.on_object_change = self._on_object_inspector_change
        self.inspector.on_sprite_assign = self._on_inspector_sprite
        self.inspector.on_sprite_asset_change = self._on_inspector_sprite_asset_change
        self.inspector.on_music_change = self._on_inspector_music_change
        self.inspector.on_music_action = self._on_inspector_music_action
        self.inspector.on_scene_change = self._on_inspector_scene_change
        self.inspector.on_scene_action = self._on_inspector_scene_action
        self.resources.on_select_object = self._select_object
        self.resources.on_select_sprite = self._on_resource_sprite
        self.resources.on_select_music = self._on_resource_music
        self.resources.on_select_scene = self.switch_scene
        self.code_editor.on_change = self._on_code_change

        # dialogs
        self.dialog_active = False
        self.dialog_mode = ""  # "new_object"
        self.dialog_input = TextInput((0, 0, 200, 28), "")
        self.dialog_error = ""
        self.file_dialog = FileDialog()

        # clipboard for instances
        self.instance_clipboard = None

        self.buttons: List[Button] = []
        self.add_menu_open = False
        self.add_menu_items = [
            ("오브젝트", self._start_new_object),
            ("스프라이트 가져오기", self.import_image),
            ("스프라이트 애니메이션", self.import_animation),
            ("음악 가져오기", self.import_music),
            ("씬 만들기", self.new_scene_dialog),
            ("Rea 스크립트", self.import_rea),
            ("파일 가져오기", self.import_any_file),
        ]
        self._build_toolbar()
        self._relayout()

        # load scene if exists, else create with player
        if os.path.isfile(self.scene_path):
            self._load_scene_file(self.scene_path)
        else:
            self._new_scene_default()

        self._refresh_resources()
        # select first object
        names = self.project.list_object_names()
        if names:
            self._select_object(names[0])

    # ── layout ──────────────────────────────────────────
    def _build_toolbar(self):
        """Keep the top bar compact: one + menu, save and play."""
        self.buttons = []
        plus = Button((8, 6, 34, 28), "+", self.toggle_add_menu, accent=True)
        self.buttons.append(plus)
        self.add_button = plus
        self.buttons.append(Button((48, 6, 58, 28), "저장", self.save_all))
        self.buttons.append(Button((112, 6, 72, 28), "▶ Play", self.play_scene, accent=True))

    def toggle_add_menu(self):
        self.add_menu_open = not self.add_menu_open

    def _add_menu_rect(self):
        w = 220
        h = 7 * 34 + 12
        x = self.add_button.rect.x
        y = self.toolbar_h + 3
        return pygame.Rect(x, y, w, h)

    def _handle_add_menu_event(self, event):
        if not self.add_menu_open:
            return False
        menu = self._add_menu_rect()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.add_menu_open = False
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if menu.collidepoint(event.pos):
                rel_y = event.pos[1] - menu.y - 6
                idx = rel_y // 34
                if 0 <= idx < len(self.add_menu_items):
                    self.add_menu_open = False
                    self.add_menu_items[idx][1]()
                    return True
                return True
            if self.add_button.rect.collidepoint(event.pos):
                self.add_menu_open = False
                return True
            self.add_menu_open = False
            return False
        return True

    def _draw_add_menu(self):
        if not self.add_menu_open:
            return
        r = self._add_menu_rect()
        draw_rect(self.screen, r, BG_PANEL2, border=1, border_color=ACCENT, radius=6)
        for i, (label, _cb) in enumerate(self.add_menu_items):
            item = pygame.Rect(r.x + 6, r.y + 6 + i * 34, r.w - 12, 30)
            if item.collidepoint(pygame.mouse.get_pos()):
                draw_rect(self.screen, item, BG_HOVER, radius=4)
            draw_text(self.screen, "+  " + label, (item.x + 10, item.y + 7), TEXT, 12)


    def _relayout(self):
        self.w, self.h = self.screen.get_size()
        top = self.toolbar_h
        left = self.left_w
        right = self.right_w
        status_h = self.status_h

        center_w = max(320, self.w - left - right)
        body_bottom = self.h - status_h
        body_h = max(300, body_bottom - top)
        code_h = min(self.code_h, max(220, body_h // 2))
        scene_h = max(120, body_h - code_h)

        # Left side: Resource panel on top, Events panel at bottom.
        self.left_objects_rect = pygame.Rect(0, top, left, scene_h)
        self.left_events_rect = pygame.Rect(0, top + scene_h, left, code_h)
        self.resources.set_rect(self.left_objects_rect)

        # Center: Scene view on top, code/output on bottom.
        self.scene_header_rect = pygame.Rect(left, top, center_w, 30)
        self.viewport.set_rect(pygame.Rect(left, top + 30, center_w, max(80, scene_h - 30)))
        self.code_header_rect = pygame.Rect(left, top + scene_h, center_w, 28)
        self.code_rect = pygame.Rect(left, top + scene_h + 28, center_w, max(80, code_h - 28))
        self.code_editor.set_rect(self.code_rect)

        # Right side: Inspector spans both halves like the mockup.
        self.inspector.set_rect(pygame.Rect(self.w - right, top, right, body_h))
        self.assets.set_rect(pygame.Rect(0, 0, 1, 1))

        self.status_rect = pygame.Rect(0, body_bottom, self.w, status_h)
        self.viewport.scene_w = self.scene.width
        self.viewport.scene_h = self.scene.height
        self.viewport.bg_color = self.scene.background_color
        self.dialog_input.rect = pygame.Rect(self.w // 2 - 120, self.h // 2 - 10, 240, 28)


    def _select_object(self, name: Optional[str]):
        # Flush code and switch the inspector from instance -> object cleanly.
        self._flush_code_to_object()
        self.selected_object_name = name
        self.selected_event_key = None
        self.selected_instance_id = None
        self.viewport.selected_id = None
        self.viewport.place_object_name = None
        if name and name in self.project.objects:
            obj = self.project.objects[name]
            self.selected_event_key = "create"
            self.code_editor.set_text(obj.events.get("create", ""))
            self.status = f"Object: {name} — [배치] 버튼 또는 더블클릭으로 Scene에 배치"
            self.inspector.set_object(obj)
            self.resources.selected_object = name
            self.resources.selected_music = None
            self.resources.selected_scene = os.path.basename(self.scene_path) if self.scene_path else None
            self.resources.active_category = "objects"
            self._refresh_resources()
        else:
            self.code_editor.set_text("")
            self.viewport.place_object_name = None

    def _select_event(self, key: str):
        self._flush_code_to_object()
        self.selected_event_key = key
        if self.selected_object_name and self.selected_object_name in self.project.objects:
            obj = self.project.objects[self.selected_object_name]
            self.code_editor.set_text(obj.events.get(key, ""))
            label = EVENT_KEY_TO_LABEL.get(key, key)
            self.status = f"{self.selected_object_name} / {label}"

    def _flush_code_to_object(self):
        if not self.selected_object_name or not self.selected_event_key:
            return
        obj = self.project.objects.get(self.selected_object_name)
        if not obj:
            return
        code = self.code_editor.get_text()
        if obj.events.get(self.selected_event_key, "") != code:
            obj.events[self.selected_event_key] = code
            self.dirty = True

    def _on_code_change(self, text: str):
        self.dirty = True
        if self.selected_object_name and self.selected_event_key:
            obj = self.project.objects.get(self.selected_object_name)
            if obj:
                obj.events[self.selected_event_key] = text

    # ── scene helpers ───────────────────────────────────
    def _new_scene_default(self):
        self.scene = Scene("main")
        self.scene.width = 800
        self.scene.height = 600
        # 빈 씬 — 기본 인스턴스 없음
        self.scene_path = os.path.join(self.project.scenes_dir, "main.json")
        self.dirty = True
        self.selected_instance_id = None
        self.inspector.set_instance(None)
        self.inspector.set_scene(self.scene, self.scene_path)
        self.status = "새 Scene"

    def _apply_sprite_defaults(self, inst, sprite_name: str):
        if not sprite_name:
            inst.sprite = None
            return
        inst.sprite = sprite_name
        try:
            spr = self.sprite_manager.get(sprite_name)
            inst.width = spr.width
            inst.height = spr.height
            if spr.animated and inst.image_speed == 0:
                inst.image_speed = spr.frame_speed
                if hasattr(inst, "env"):
                    inst.env.set("image_speed", inst.image_speed)
        except Exception:
            pass

    def _add_instance(self, object_name: str, x: float, y: float) -> Instance:
        po = self.project.objects.get(object_name)
        go = GameObject(object_name)
        if po:
            go.default_sprite = po.sprite or None
            go.default_width = po.width or 32
            go.default_height = po.height or 32
        inst = Instance(go, x, y, engine=None)
        if po and po.sprite:
            self._apply_sprite_defaults(inst, po.sprite)
            if inst.width == 32 and inst.height == 32 and (po.width or po.height):
                inst.width = po.width or 32
                inst.height = po.height or 32
        elif po:
            inst.width = po.width or 32
            inst.height = po.height or 32
        else:
            inst.width = 32
            inst.height = 32
        if inst.sprite:
            try:
                inst.env.set("sprite", inst.sprite)
            except Exception:
                pass
        self.scene.add_instance(inst)
        self.dirty = True
        return inst

    def place_selected_object(self):
        name = self.selected_object_name
        if not name:
            names = self.project.list_object_names()
            if not names:
                self.status = "먼저 Object를 만드세요 (+ Object)"
                return
            name = names[0]
            self._select_object(name)
        # Toggle place mode: next click on viewport places object
        if self.viewport.place_object_name == name:
            self.viewport.place_object_name = None
            self.status = "배치 모드 해제"
        else:
            self.viewport.place_object_name = name
            self.status = f"배치 모드: {name} — Scene을 클릭하세요 (Esc 취소)"


    def _on_viewport_select(self, inst):
        self.selected_instance_id = inst.id if inst else None
        self.viewport.selected_id = inst.id if inst else None
        if inst:
            self.resources.selected_music = None
            self.resources.selected_scene = os.path.basename(self.scene_path) if self.scene_path else None
            self.inspector.set_instance(inst)
            # highlight object type without wiping inspector (skip full _select_object)
            if inst.object_name in self.project.objects:
                if self.selected_object_name != inst.object_name:
                    self._flush_code_to_object()
                    self.selected_object_name = inst.object_name
                    self.selected_event_key = "create"
                    obj = self.project.objects[inst.object_name]
                    self.code_editor.set_text(obj.events.get("create", ""))
            self.viewport.place_object_name = None  # cancel place when selecting
            self.status = f"선택: {inst.object_name} #{inst.id}"
        else:
            # keep object inspector if object selected
            if self.selected_object_name and self.selected_object_name in self.project.objects:
                self.inspector.set_object(self.project.objects[self.selected_object_name])
            else:
                self.inspector.clear()

    def _on_instance_moved(self, inst):
        self.dirty = True
        self.inspector.refresh_from_instance()

    def _on_inspector_change(self, inst):
        self.dirty = True

    def _on_object_inspector_change(self, obj):
        self.dirty = True
        if obj and obj.sprite:
            # propagate sprite/size to instances of this type
            try:
                spr = self.sprite_manager.get(obj.sprite)
                obj.width = spr.width
                obj.height = spr.height
            except Exception:
                pass
            for inst in self.scene.instances:
                if inst.object_name == obj.name:
                    inst.sprite = obj.sprite
                    inst.width = obj.width
                    inst.height = obj.height


    def _on_inspector_sprite(self, filename: str):
        """Sprite assigned from Inspector only — propagate to object + instances."""
        self.dirty = True
        filename = filename or ""
        name = self.selected_object_name
        if not name and self.inspector.instance:
            name = getattr(self.inspector.instance, "object_name", None)
        if name and name in self.project.objects:
            obj = self.project.objects[name]
            obj.sprite = filename
            if filename:
                try:
                    spr = self.sprite_manager.get(filename)
                    obj.width = spr.width
                    obj.height = spr.height
                except Exception:
                    pass
            for inst in self.scene.instances:
                if inst.object_name == name:
                    if filename:
                        self._apply_sprite_defaults(inst, filename)
                    else:
                        inst.sprite = None
                    if filename:
                        try:
                            spr = self.sprite_manager.get(filename)
                            inst.width = spr.width
                            inst.height = spr.height
                        except Exception:
                            pass
            self.status = f"Sprite → {name}: {filename or '(없음)'}"
        self._refresh_resources()

    def _on_inspector_sprite_asset_change(self, filename: str, info: dict):
        """Persist GameMaker-style animation metadata from the Sprite inspector."""
        if not filename or not filename.endswith('.anim.json'):
            return
        path = os.path.join(self.project.assets_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['type'] = 'sprite_animation'
            data['fps'] = float(info.get('fps', data.get('fps', 10)))
            data['loop'] = bool(info.get('loop', data.get('loop', True)))
            data['frame_width'] = max(1, int(info.get('frame_width', data.get('frame_width', 32))))
            data['frame_height'] = max(1, int(info.get('frame_height', data.get('frame_height', 32))))
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.sprite_manager.sprites.pop(filename, None)
            self.inspector.set_sprite_resource(filename, path)
            self.dirty = True
            self.status = f"스프라이트 저장: {os.path.basename(filename)}"
        except Exception as e:
            self.status = f"스프라이트 저장 실패: {e}"

    def _on_inspector_music_change(self, filename: str, volume: float, loop: bool):
        if not filename:
            return
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
        except Exception:
            pass

    def _on_inspector_music_action(self, action: str, filename: str, volume: float, loop: bool):
        if not filename:
            return
        full = os.path.join(self.project.assets_dir, filename)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            if action == "stop":
                pygame.mixer.music.stop()
                self.status = f"음악 정지: {os.path.basename(filename)}"
                return
            pygame.mixer.music.load(full)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
            pygame.mixer.music.play(-1 if loop else 0)
            self.status = f"음악 재생: {os.path.basename(filename)}" + (" (반복)" if loop else "")
        except Exception as e:
            self.status = f"음악 재생 실패: {e}"

    def _on_inspector_scene_change(self, scene):
        if scene is not self.scene:
            return
        try:
            self.scene.width = max(1, int(self.scene.width))
            self.scene.height = max(1, int(self.scene.height))
            bg = tuple(int(max(0, min(255, c))) for c in self.scene.background_color[:3])
            self.scene.background_color = bg
            self.viewport.scene_w = self.scene.width
            self.viewport.scene_h = self.scene.height
            self.viewport.bg_color = self.scene.background_color
            self.dirty = True
            self.status = f"씬 설정 변경: {self.scene.name}"
        except Exception:
            pass

    def _on_inspector_scene_action(self, action: str, scene):
        if scene is not self.scene:
            return
        if action == "save":
            self.save_all()
        elif action == "reload":
            if self.scene_path and os.path.isfile(self.scene_path):
                self._load_scene_file(self.scene_path)
                self.resources.active_category = "scenes"
                self.resources.selected_scene = os.path.basename(self.scene_path)
                self.inspector.set_scene(self.scene, self.scene_path)
                self.status = f"씬 다시 불러오기: {self.scene.name}"

    def _refresh_resources(self):
        # Filesystem is scanned only when a project operation changes resources, not every frame.
        self._sprite_files_cache = self.project.list_assets()
        self._music_files_cache = self.project.list_music()
        self._scene_files_cache = self.project.list_scenes()
        names = self.project.list_object_names()
        self.resources.set_data(names, self._sprite_files_cache, self._music_files_cache, self._scene_files_cache)
        self.resources.selected_object = self.selected_object_name
        self.resources.selected_scene = os.path.basename(self.scene_path) if self.scene_path else None
        self.resources.project = self.project
        self.resources.sprite_manager = self.sprite_manager
        self.inspector.set_sprite_list(self._sprite_files_cache)
        self.inspector.sprite_manager = self.sprite_manager

    def _on_viewport_place(self, object_name: str, wx: float, wy: float):
        if object_name not in self.project.objects:
            self.status = f"Object 없음: {object_name}"
            return
        gs = float(self.viewport.grid_size)
        wx = round(wx / gs) * gs
        wy = round(wy / gs) * gs
        inst = self._add_instance(object_name, wx, wy)
        self.selected_instance_id = inst.id
        self.viewport.selected_id = inst.id
        self.viewport.place_object_name = None
        self.inspector.set_instance(inst)
        self.status = f"배치됨: {object_name} @ ({wx:.0f}, {wy:.0f})"

    def _on_resource_sprite(self, filename: str):
        """Selecting a sprite opens its GameMaker-style resource inspector."""
        if not filename:
            return
        full = os.path.join(self.project.assets_dir, filename)
        self.resources.selected_sprite = filename
        self.resources.selected_music = None
        self.resources.selected_scene = None
        self.inspector.sprite_manager = self.sprite_manager
        self.inspector.set_sprite_resource(filename, full)
        self.status = f"스프라이트 선택: {os.path.basename(filename)} — Inspector에서 속성 편집"

    def _assign_sprite(self, filename: str):
        """Attach image to selected Instance and/or Object definition."""
        if not filename:
            return
        filename = str(filename)
        # ensure sprite is loadable
        try:
            spr = self.sprite_manager.get(filename)
            sw, sh = spr.width, spr.height
        except Exception as e:
            self.status = f"이미지 로드 실패: {e}"
            return

        assigned = False

        # 1) selected instance
        if self.selected_instance_id is not None:
            for inst in self.scene.instances:
                if inst.id == self.selected_instance_id:
                    self._apply_sprite_defaults(inst, filename)
                    inst.width = sw
                    inst.height = sh
                    if hasattr(inst, "env"):
                        inst.env.set("sprite", filename)
                    self.inspector.set_instance(inst)
                    assigned = True
                    break

        # 2) selected object definition — always update when object selected
        if self.selected_object_name:
            obj = self.project.objects.get(self.selected_object_name)
            if obj:
                obj.sprite = filename
                obj.width = sw
                obj.height = sh
                # propagate to all instances of this type without explicit sprite override
                for inst in self.scene.instances:
                    if inst.object_name == self.selected_object_name:
                        inst.sprite = filename
                        inst.width = sw
                        inst.height = sh
                        if hasattr(inst, "env"):
                            inst.env.set("sprite", filename)
                assigned = True
                self.dirty = True

        if assigned:
            self.dirty = True
            self.status = f"이미지 연결: {filename}"
            # refresh inspector if needed
            if self.selected_instance_id is not None:
                for inst in self.scene.instances:
                    if inst.id == self.selected_instance_id:
                        self.inspector.set_instance(inst)
                        break
        else:
            self.status = "이미지를 붙이려면 Object 또는 Scene의 인스턴스를 선택하세요"

    def delete_selected(self):
        if self.selected_instance_id is not None:
            for inst in list(self.scene.instances):
                if inst.id == self.selected_instance_id:
                    self.scene.remove_instance(inst)
                    self.selected_instance_id = None
                    self.viewport.selected_id = None
                    self.inspector.set_instance(None)
                    self.dirty = True
                    self.status = "Instance 삭제"
                    return

        # No instance selected: delete the selected Object definition and its scene instances.
        name = self.selected_object_name
        if name and name in self.project.objects:
            removed = len([i for i in self.scene.instances if i.object_name == name])
            self.scene.instances[:] = [i for i in self.scene.instances if i.object_name != name]
            self.project.delete_object(name)
            self.selected_object_name = None
            self.selected_event_key = None
            self.selected_instance_id = None
            self.viewport.selected_id = None
            self.viewport.place_object_name = None
            self.inspector.clear()
            self.code_editor.set_text("")
            self._refresh_resources()
            self.dirty = True
            self.status = f"Object 삭제: {name}" + (f" (Instance {removed}개도 삭제)" if removed else "")

    # ── new object dialog ───────────────────────────────
    def _start_new_object(self):
        self.dialog_active = True
        self.dialog_mode = "new_object"
        self.dialog_input.set_value("")
        self.dialog_input.active = True
        self.dialog_error = ""

    def _confirm_dialog(self):
        if self.dialog_mode == "new_object":
            name = self.dialog_input.value.strip()
            if not name:
                self.dialog_error = "이름을 입력하세요"
                return
            try:
                obj = self.project.create_object(name)
                obj.events["create"] = ""
                obj.events["step"] = ""
                obj.events["draw"] = ""
                obj.save()
                self.dialog_active = False
                self._select_object(name)
                self.dirty = True
                self._refresh_resources()
                self.status = f"Object 생성: {name}"
            except ValueError as e:
                self.dialog_error = str(e)
        elif self.dialog_mode == "new_scene":
            name = self.dialog_input.value.strip()
            if not name:
                self.dialog_error = "씬 이름을 입력하세요"
                return
            try:
                path = self.project.create_scene(name)
                self.dialog_active = False
                self._refresh_resources()
                self.resources.active_category = "scenes"
                self.switch_scene(os.path.basename(path))
                self.status = f"씬 생성: {name}"
            except ValueError as e:
                self.dialog_error = str(e)

    def _cancel_dialog(self):
        self.dialog_active = False
        self.dialog_input.active = False

    # ── save / load ─────────────────────────────────────

    # ── external file import ────────────────────────────
    def import_music(self):
        self.file_dialog.open(
            title="음악 가져오기",
            start_dir=os.path.expanduser("~"),
            extensions=[".ogg", ".wav", ".mp3", ".flac", ".mod", ".xm", ".mid", ".midi"],
            on_result=self._on_import_music,
        )

    def _on_import_music(self, path):
        if not path:
            return
        try:
            audio_dir = os.path.join(self.project.assets_dir, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            base = os.path.basename(path)
            dest = os.path.join(audio_dir, base)
            stem, ext = os.path.splitext(base)
            n = 2
            while os.path.exists(dest):
                dest = os.path.join(audio_dir, f"{stem}_{n}{ext}")
                n += 1
            shutil.copy2(path, dest)
            self._refresh_resources()
            self.resources.active_category = "music"
            self.status = f"음악 가져오기 완료: {os.path.basename(dest)}"
        except Exception as e:
            self.status = f"음악 가져오기 실패: {e}"

    def _on_resource_music(self, filename: str):
        if not filename:
            return
        self._flush_code_to_object()
        self.selected_instance_id = None
        self.viewport.selected_id = None
        self.viewport.place_object_name = None
        self.resources.selected_music = filename
        self.resources.selected_object = None
        self.inspector.set_music(filename, os.path.join(self.project.assets_dir, filename))
        self.status = f"음악 선택: {os.path.basename(filename)} — Inspector에서 재생/설정"


    def import_animation(self):
        self.file_dialog.open(
            title="스프라이트 시트 선택",
            start_dir=os.path.expanduser("~"),
            extensions=[".png", ".jpg", ".jpeg", ".bmp", ".gif"],
            on_result=self._on_animation_source,
        )

    def _on_animation_source(self, path):
        if not path:
            return
        try:
            image = pygame.image.load(path)
            w, h = image.get_size()
            default = h if h > 0 else 32
            self.animation_dialog.open(path, default, default, self._create_animation)
        except Exception as e:
            self.status = f"스프라이트 시트 열기 실패: {e}"

    def _create_animation(self, name: str, frame_w: int, frame_h: int, fps: float):
        try:
            # Keep the source inside the project so the animation is portable.
            source_base = os.path.basename(self.animation_dialog.source_path or "sheet.png")
            dest_source = os.path.join(self.project.assets_dir, source_base)
            stem, ext = os.path.splitext(source_base)
            n = 2
            while os.path.abspath(dest_source) != os.path.abspath(self.animation_dialog.source_path or "") and os.path.exists(dest_source):
                dest_source = os.path.join(self.project.assets_dir, f"{stem}_{n}{ext}")
                n += 1
            if os.path.abspath(dest_source) != os.path.abspath(self.animation_dialog.source_path or ""):
                shutil.copy2(self.animation_dialog.source_path, dest_source)
            source_rel = os.path.relpath(dest_source, self.project.assets_dir).replace(os.sep, "/")
            anim_dir = os.path.join(self.project.assets_dir, "animations")
            os.makedirs(anim_dir, exist_ok=True)
            safe = name.strip()
            if not safe:
                raise ValueError("애니메이션 이름이 비어 있습니다")
            safe = "".join(c if (c.isalnum() or c in "_-가-힣") else "_" for c in safe)
            path = os.path.join(anim_dir, safe + ".anim.json")
            if os.path.exists(path):
                raise ValueError(f"이미 있는 애니메이션: {safe}")
            data = {
                "name": safe,
                "type": "sprite_animation",
                "source": source_rel,
                "frame_width": int(frame_w),
                "frame_height": int(frame_h),
                "fps": float(fps),
                "loop": True,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.sprite_manager.sprites.pop(os.path.relpath(path, self.project.assets_dir).replace(os.sep, "/"), None)
            self._refresh_resources()
            self.resources.active_category = "sprites"
            self.resources.selected_sprite = os.path.relpath(path, self.project.assets_dir).replace(os.sep, "/")
            self.status = f"애니메이션 생성: {safe} ({frame_w}×{frame_h}, {fps:g} FPS)"
        except Exception as e:
            self.status = f"애니메이션 생성 실패: {e}"

    def import_image(self):
        start = self.project.assets_dir
        home = os.path.expanduser("~")
        self.file_dialog.open(
            title="이미지 가져오기 (png/jpg/bmp/gif)",
            start_dir=home if os.path.isdir(home) else self.root,
            extensions=[".png", ".jpg", ".jpeg", ".bmp", ".gif"],
            on_result=self._on_import_image,
        )

    def _on_import_image(self, path):
        if not path:
            self.status = "이미지 가져오기 취소"
            return
        import shutil
        try:
            name = os.path.basename(path)
            dest = os.path.join(self.project.assets_dir, name)
            # avoid overwrite: add suffix
            base, ext = os.path.splitext(name)
            n = 1
            while os.path.exists(dest):
                dest = os.path.join(self.project.assets_dir, f"{base}_{n}{ext}")
                n += 1
                name = os.path.basename(dest)
            shutil.copy2(path, dest)
            # clear sprite cache for this name
            if name in self.sprite_manager.sprites:
                del self.sprite_manager.sprites[name]
            self.assets.refresh()
            self._refresh_resources()
            self.resources.active_category = "sprites"
            self.status = f"이미지 추가: {name} — Inspector에서 Sprite 선택"
        except Exception as e:
            self.status = f"가져오기 실패: {e}"
            print(e)

    def import_rea(self):
        home = os.path.expanduser("~")
        self.file_dialog.open(
            title="Rea 스크립트 가져오기 (.rea)",
            start_dir=home if os.path.isdir(home) else self.root,
            extensions=[".rea", ".txt"],
            on_result=self._on_import_rea,
        )

    def _on_import_rea(self, path):
        if not path:
            self.status = "Rea 가져오기 취소"
            return
        try:
            self.project._import_rea_file(path)
            self.project.scan()
            names = self.project.list_object_names()
            self.status = f"Rea 가져옴 → Objects: {', '.join(names)}"
            if names and not self.selected_object_name:
                self._select_object(names[0])
            elif self.selected_object_name:
                self._select_object(self.selected_object_name)
            self.dirty = True
        except Exception as e:
            self.status = f"Rea 가져오기 실패: {e}"
            print(e)

    def import_any_file(self):
        """Generic: copy any file into assets/."""
        home = os.path.expanduser("~")
        self.file_dialog.open(
            title="파일 가져오기 → assets/",
            start_dir=home if os.path.isdir(home) else self.root,
            extensions=None,
            on_result=self._on_import_any,
        )

    def _on_import_any(self, path):
        if not path:
            return
        import shutil
        try:
            name = os.path.basename(path)
            dest = os.path.join(self.project.assets_dir, name)
            shutil.copy2(path, dest)
            self.assets.refresh()
            self.status = f"파일 추가: {name}"
        except Exception as e:
            self.status = f"실패: {e}"

    def save_all(self):
        self._flush_code_to_object()
        try:
            self.project.save_all_objects()
            path = self.scene_path or os.path.join(self.project.scenes_dir, "main.json")
            self.scene.name = os.path.splitext(os.path.basename(path))[0]
            self.scene.save(path)
            self.scene_path = path
            self.project.current_scene_path = path
            self.project.save_meta()
            self.dirty = False
            self.status = f"저장 완료 (Objects + Scene: {os.path.basename(path)})"
        except Exception as e:
            self.status = f"저장 실패: {e}"
            print(e)

    def new_scene(self):
        self._flush_code_to_object()
        self._new_scene_default()
        self.status = "새 Scene"

    def open_scene(self):
        self._flush_code_to_object()
        path = os.path.join(self.project.scenes_dir, "main.json")
        if not os.path.isfile(path):
            # any json
            for fn in sorted(os.listdir(self.project.scenes_dir)):
                if fn.endswith(".json"):
                    path = os.path.join(self.project.scenes_dir, fn)
                    break
            else:
                self.status = "열 Scene 없음"
                return
        self._load_scene_file(path)

    def _load_scene_file(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.scene = Scene.from_dict(data, engine=None)
            for inst in self.scene.instances:
                po = self.project.objects.get(inst.object_name)
                if po and not inst.sprite and po.sprite:
                    inst.sprite = po.sprite
                if inst.sprite:
                    self._apply_sprite_defaults(inst, inst.sprite)
            self.scene_path = path
            self.dirty = False
            self.viewport.scene_w = self.scene.width
            self.viewport.scene_h = self.scene.height
            self.selected_instance_id = None
            self.viewport.selected_id = None
            self.inspector.set_instance(None)
            self.resources.selected_scene = os.path.basename(path)
            self.inspector.set_scene(self.scene, path)
            self.status = f"Scene 로드: {os.path.basename(path)}"
        except Exception as e:
            self.status = f"로드 실패: {e}"
            print(e)

    # ── Play ────────────────────────────────────────────

    def list_scene_files(self):
        return self._scene_files_cache if self._scene_files_cache else self.project.list_scenes()

    def switch_scene(self, filename: str):
        self._flush_code_to_object()
        if self.scene_path:
            try:
                self.scene.save(self.scene_path)
            except Exception:
                pass
        path = self.project.scene_path(filename)
        if os.path.isfile(path):
            self._load_scene_file(path)
            self.project.current_scene_path = path
            self._scene_files_cache = self.project.list_scenes()
            self.resources.set_data(self.project.list_object_names(), self._sprite_files_cache, self._music_files_cache, self._scene_files_cache)
            self.resources.active_category = "scenes"
            self.resources.selected_scene = filename
            self.resources.selected_object = None
            self.resources.selected_music = None
            self.inspector.set_scene(self.scene, self.scene_path)
            self.status = f"씬 전환: {filename}"
        else:
            self.status = f"씬 없음: {filename}"

    def new_scene_dialog(self):
        self.dialog_active = True
        self.dialog_mode = "new_scene"
        self.dialog_input.set_value("scene2")
        self.dialog_input.active = True
        self.dialog_error = ""

    def play_scene(self):
        self._flush_code_to_object()
        self.save_all()

        play_path = self.scene_path or os.path.join(self.project.scenes_dir, "_play.json")
        self.scene.save(play_path)

        rea_source = self.project.build_combined_rea()
        temp_rea = os.path.join(self.root, "_play_objects.rea")
        with open(temp_rea, "w", encoding="utf-8") as f:
            f.write(rea_source)

        self.status = "Play 실행 중... (창을 닫거나 Esc)"
        try:
            self._run_game(play_path, temp_rea)
        except Exception as e:
            print(f"[Play 오류] {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore editor window without pygame.display.quit() (causes freeze on some OS)
            try:
                pygame.event.clear()
            except Exception:
                pass
            try:
                if not pygame.get_init():
                    pygame.init()
                if not pygame.display.get_init():
                    pygame.display.init()
                if not pygame.font.get_init():
                    pygame.font.init()
            except Exception:
                try:
                    pygame.init()
                except Exception:
                    pass
            Fonts._cache.clear()
            Fonts._resolved = False
            try:
                self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
            except Exception:
                self.screen = pygame.display.set_mode((1400, 900), pygame.RESIZABLE)
                self.w, self.h = self.screen.get_size()
            pygame.display.set_caption("Rebuild Engine IDE")
            try:
                pygame.key.start_text_input()
            except Exception:
                pass
            try:
                pygame.scrap.init()
            except Exception:
                pass
            # drop leftover events so editor doesn't freeze
            for _ in range(5):
                pygame.event.clear()
            self.status = "에디터로 복귀"
            self._relayout()
            self._refresh_resources()


    def _run_game(self, scene_path: str, rea_path: str):
        from engine.core.engine import RebuildEngine
        from engine.graphics.sprite import SpriteManager

        eng = RebuildEngine(
            width=int(self.scene.width),
            height=int(self.scene.height),
            title="Rebuild Engine - Play",
            fps=60,
        )
        # Use PROJECT assets folder (not engine default) so sprites load
        assets_dir = os.path.abspath(self.project.assets_dir)
        eng.sprite_manager = SpriteManager(assets_path=assets_dir)
        # Preload all project sprites while display is active
        for fname in self.project.list_assets():
            try:
                eng.sprite_manager.load(fname)
            except Exception as e:
                print(f"[Play] sprite load fail {fname}: {e}")

        eng.load_script(rea_path)

        for name in self.project.list_object_names():
            if name not in eng.objects:
                eng.objects[name] = GameObject(name)

        loaded = Scene.load(scene_path, eng)
        eng.scene = loaded
        for inst in list(eng.scene.instances):
            inst.engine = eng
            po = self.project.objects.get(inst.object_name)
            if po:
                if not inst.sprite and po.sprite:
                    inst.sprite = po.sprite
                if inst.sprite:
                    try:
                        spr = eng.sprite_manager.get(inst.sprite)
                        inst.width = spr.width
                        inst.height = spr.height
                    except Exception:
                        pass
            eng._run_event(inst, "create")

        eng.run()
        # engine finished — ensure window can be reused
        try:
            pygame.event.clear()
        except Exception:
            pass


    # ── input ───────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._flush_code_to_object()
                if self.dirty:
                    self.save_all()
                self.running = False
                return

            if event.type == pygame.VIDEORESIZE:
                self.w, self.h = max(1000, event.w), max(700, event.h)
                self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
                self._relayout()
                continue

            # file dialog modal
            if self.file_dialog.active:
                self.file_dialog.handle_event(event)
                continue

            # animation creation modal
            if self.animation_dialog.active:
                self.animation_dialog.handle_event(event)
                continue

            # dialog modal
            if self.dialog_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self._confirm_dialog()
                        continue
                    if event.key == pygame.K_ESCAPE:
                        self._cancel_dialog()
                        continue
                self.dialog_input.handle_event(event)
                continue

            if self._handle_add_menu_event(event):
                continue

            if event.type == pygame.KEYDOWN:
                ctrl = bool(event.mod & pygame.KMOD_CTRL) or bool(event.mod & pygame.KMOD_META)
                if ctrl and event.key == pygame.K_s:
                    self.save_all()
                    continue
                if ctrl and event.key == pygame.K_n:
                    self._start_new_object()
                    continue
                if ctrl and event.key == pygame.K_p:
                    self.play_scene()
                    continue
                if ctrl and event.key == pygame.K_c and not self.code_editor.focused:
                    # copy instance
                    if self.selected_instance_id is not None:
                        for inst in self.scene.instances:
                            if inst.id == self.selected_instance_id:
                                self.instance_clipboard = {
                                    "object": inst.object_name,
                                    "x": inst.x,
                                    "y": inst.y,
                                    "sprite": inst.sprite,
                                    "depth": inst.depth,
                                    "visible": inst.visible,
                                }
                                self.status = "Instance 복사"
                                break
                    continue
                if ctrl and event.key == pygame.K_v and not self.code_editor.focused:
                    if self.instance_clipboard:
                        d = self.instance_clipboard
                        inst = self._add_instance(d["object"], d["x"] + 20, d["y"] + 20)
                        inst.sprite = d.get("sprite")
                        inst.depth = d.get("depth", 0)
                        inst.visible = d.get("visible", True)
                        self.selected_instance_id = inst.id
                        self.viewport.selected_id = inst.id
                        self.inspector.set_instance(inst)
                        self.status = "Instance 붙여넣기"
                    continue
                if event.key == pygame.K_DELETE and not self.code_editor.focused:
                    self.delete_selected()
                    continue

            # toolbar
            handled = False
            for btn in self.buttons:
                if btn.handle_event(event):
                    handled = True
                    break
            if handled:
                continue

            # ESC cancels place mode
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.viewport.place_object_name:
                    self.viewport.place_object_name = None
                    self.status = "배치 모드 취소"
                    continue

            # Pending object-list drag: move enough → start drag_object_name
            if event.type == pygame.MOUSEMOTION and getattr(self, "_pending_drag_object", None):
                px, py = getattr(self, "_pending_drag_pos", event.pos)
                if abs(event.pos[0] - px) + abs(event.pos[1] - py) > 8:
                    self.viewport.drag_object_name = self._pending_drag_object
                    self._pending_drag_object = None
                    self.status = f"배치: {self.viewport.drag_object_name} — Scene에 놓으세요"

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._pending_drag_object = None

            # Viewport priority: drag/pan OR click inside viewport
            vp_needs = (
                self.viewport.dragging
                or self.viewport.panning
                or self.viewport.drag_object_name
                or (
                    event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)
                    and hasattr(event, "pos")
                    and self.viewport.rect.collidepoint(event.pos)
                )
                or (
                    event.type == pygame.MOUSEMOTION
                    and (self.viewport.dragging or self.viewport.panning or self.viewport.drag_object_name)
                )
            )
            if vp_needs:
                if self.viewport.handle_event(event, self.scene.instances):
                    continue
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.viewport.drag_object_name = None

            # Inspector
            if self.inspector.handle_event(event):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.code_editor.focused = False
                continue

            # Code editor
            if self.code_editor.handle_event(event):
                continue

            # resources (objects + sprites)
            if self.resources.handle_event(event):
                # Start drag-to-scene only when an Object item itself was clicked.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and getattr(self.resources, "_last_action", "") == "item"
                    and self.resources.active_category == "objects"
                    and self.resources.selected_object
                ):
                    self._pending_drag_object = self.resources.selected_object
                    self._pending_drag_pos = event.pos
                continue

            # events panel still
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_left_panel_click(event.pos):
                    continue
            # fallback viewport (e.g. motion)
            if self.viewport.handle_event(event, self.scene.instances):
                continue

    def _handle_left_panel_click(self, pos) -> bool:
        r = self.left_events_rect
        if r.collidepoint(pos):
            y = pos[1] - r.y - 32
            if y >= 0 and self.selected_object_name:
                idx = int(y // 26)
                if 0 <= idx < len(EVENT_TYPES):
                    key = EVENT_TYPES[idx][0]
                    self._select_event(key)
                    return True
            return True
        return False


    # ── draw ────────────────────────────────────────────
    def draw(self):
        self.screen.fill(BG_DARK)

        # Compact command bar. Main editor area follows the target mockup.
        draw_rect(self.screen, pygame.Rect(0, 0, self.w, self.toolbar_h), TOOLBAR)
        pygame.draw.line(self.screen, BORDER, (0, self.toolbar_h - 1), (self.w, self.toolbar_h - 1))
        for btn in self.buttons:
            btn.draw(self.screen)
        dirty = " *" if self.dirty else ""
        draw_text(self.screen, f"Rebuild IDE{dirty}", (self.w - 145, 12), TEXT_DIM, 12)

        # Resource / Events | Scene / Code | Inspector.
        self.resources.draw(self.screen)
        self._draw_event_panel()
        self._draw_scene_panel_header()
        self.viewport.draw(self.screen, self.scene.instances)
        self.inspector.draw(self.screen)
        self._draw_code_panel_header()
        self._draw_add_menu()

        # Thin status bar.
        sr = self.status_rect
        draw_rect(self.screen, sr, (26, 28, 34))
        pygame.draw.line(self.screen, BORDER, (0, sr.y), (self.w, sr.y))
        inst_n = len(self.scene.instances)
        obj_n = len(self.project.objects)
        right_info = f"Objects {obj_n} | Instances {inst_n} | Ctrl+S 저장"
        draw_text(self.screen, self.status, (8, sr.y + 4), TEXT, 11)
        draw_text(self.screen, right_info, (self.w - text_width(right_info, 11) - 12, sr.y + 4), TEXT_DIM, 11)

        if self.dialog_active:
            self._draw_dialog()
        self.file_dialog.draw(self.screen)
        self.animation_dialog.draw(self.screen)
        pygame.display.flip()

    def _draw_scene_panel_header(self):
        r = self.scene_header_rect
        draw_rect(self.screen, r, BG_PANEL2, border=1)
        scene_name = os.path.splitext(os.path.basename(self.scene_path or self.scene.name))[0]
        draw_text(self.screen, "씬 보는곳", (r.x + 10, r.y + 7), TEXT, 13, bold=True)
        draw_text(self.screen, scene_name, (r.right - text_width(scene_name, 11) - 12, r.y + 8), TEXT_DIM, 11)

    def _draw_code_panel_header(self):
        r = self.code_header_rect
        draw_rect(self.screen, r, BG_PANEL2, border=1)
        label = "코드 / 출력"
        if self.selected_object_name and self.selected_event_key:
            label = f"코드 / 출력 · {self.selected_object_name} / {EVENT_KEY_TO_LABEL.get(self.selected_event_key, self.selected_event_key)}"
        draw_text(self.screen, label, (r.x + 10, r.y + 7), TEXT, 12, bold=True)
        self.code_editor.draw(self.screen)

    def _draw_event_panel(self):
        r = self.left_events_rect
        draw_rect(self.screen, r, BG_PANEL, border=1)
        draw_rect(self.screen, pygame.Rect(r.x, r.y, r.w, 28), (45, 45, 58))
        draw_text(self.screen, "이벤트", (r.x + 10, r.y + 7), TEXT, 13, bold=True)
        if not self.selected_object_name:
            draw_text(self.screen, "Object 선택 필요", (r.x + 10, r.y + 40), TEXT_DIM, 12)
            return
        obj = self.project.objects.get(self.selected_object_name)
        y = r.y + 32
        for key, label in EVENT_TYPES:
            item = pygame.Rect(r.x + 4, y, r.w - 8, 24)
            if key == self.selected_event_key:
                draw_rect(self.screen, item, BG_ACTIVE, radius=3)
            elif item.collidepoint(pygame.mouse.get_pos()):
                draw_rect(self.screen, item, BG_HOVER, radius=3)
            has_code = bool(obj and (obj.events.get(key) or "").strip())
            mark = "●" if has_code else "○"
            draw_text(self.screen, f"{mark} {label}", (item.x + 8, item.y + 4), TEXT if has_code else TEXT_DIM, 12)
            y += 26

    def _draw_dialog(self):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(self.w // 2 - 160, self.h // 2 - 70, 320, 140)
        draw_rect(self.screen, box, BG_PANEL2, border=1, border_color=ACCENT, radius=8)
        title = "새 씬 이름" if self.dialog_mode == "new_scene" else "새 Object 이름"
        draw_text(self.screen, title, (box.x + 20, box.y + 16), TEXT, 15, bold=True)
        self.dialog_input.draw(self.screen)
        if self.dialog_error:
            draw_text(self.screen, self.dialog_error, (box.x + 20, box.y + 70), DANGER, 12)
        draw_text(self.screen, "Enter=생성  Esc=취소", (box.x + 20, box.y + 105), TEXT_DIM, 12)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.code_editor.update(dt)
            self.draw()
        pygame.quit()


def run_editor(root: Optional[str] = None):
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    Editor(root).run()
