"""Scene viewport: select, drag instances, drop objects from list."""

from __future__ import annotations

import pygame
from typing import Optional, List, Any, Callable, Tuple
from .ui import draw_rect, draw_text, TEXT, TEXT_DIM, ACCENT, SUCCESS


class Viewport:
    def __init__(self, rect: pygame.Rect, sprite_manager=None):
        self.rect = pygame.Rect(rect)
        self.sprite_manager = sprite_manager
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.selected_id: Optional[int] = None
        self.dragging = False
        self.drag_offset = (0.0, 0.0)
        self.panning = False
        self.pan_start = (0, 0)
        self.cam_start = (0.0, 0.0)
        self.show_grid = True
        self.grid_size = 32
        self.on_select: Optional[Callable] = None
        self.on_move: Optional[Callable] = None
        self.on_place: Optional[Callable] = None
        self.scene_w = 800
        self.scene_h = 600
        self.bg_color = (30, 30, 40)
        self.place_object_name: Optional[str] = None
        self.drag_object_name: Optional[str] = None
        self._drag_moved = False
        # Cache scaled sprite frames used by the viewport. Re-scaling images on
        # every editor frame was a major source of slowdown.
        self._scaled_frame_cache = {}

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        sx = (wx - self.camera_x) * self.zoom + self.rect.x
        sy = (wy - self.camera_y) * self.zoom + self.rect.y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        wx = (sx - self.rect.x) / self.zoom + self.camera_x
        wy = (sy - self.rect.y) / self.zoom + self.camera_y
        return wx, wy

    def _cached_frame(self, sprite_name: str, frame, width: int, height: int):
        key = (sprite_name, id(frame), int(width), int(height))
        cached = self._scaled_frame_cache.get(key)
        if cached is not None:
            return cached
        try:
            cached = pygame.transform.scale(frame, (max(1, int(width)), max(1, int(height)))).convert_alpha()
        except Exception:
            cached = pygame.transform.scale(frame, (max(1, int(width)), max(1, int(height))))
        # Keep the cache bounded for editors with lots of zoom/size changes.
        if len(self._scaled_frame_cache) > 256:
            self._scaled_frame_cache.clear()
        self._scaled_frame_cache[key] = cached
        return cached

    def _inst_size(self, inst) -> Tuple[float, float]:
        w = float(getattr(inst, "width", 32) or 32)
        h = float(getattr(inst, "height", 32) or 32)
        return max(24.0, w), max(24.0, h)

    def hit_test(self, instances: List[Any], sx: float, sy: float) -> Optional[Any]:
        # top-most first
        for inst in sorted(instances, key=lambda i: -getattr(i, "depth", 0)):
            if not getattr(inst, "visible", True):
                continue
            w, h = self._inst_size(inst)
            ix, iy = self.world_to_screen(float(inst.x), float(inst.y))
            pad = 6
            r = pygame.Rect(
                int(ix) - pad,
                int(iy) - pad,
                max(1, int(w * self.zoom)) + pad * 2,
                max(1, int(h * self.zoom)) + pad * 2,
            )
            if r.collidepoint(int(sx), int(sy)):
                return inst
        return None

    def handle_event(self, event, instances: List[Any]) -> bool:
        # --- motion: instance drag / pan / ghost ---
        if event.type == pygame.MOUSEMOTION:
            if self.dragging and self.selected_id is not None:
                for inst in instances:
                    if inst.id == self.selected_id:
                        wx, wy = self.screen_to_world(*event.pos)
                        nx = wx + self.drag_offset[0]
                        ny = wy + self.drag_offset[1]
                        gs = float(self.grid_size)
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            inst.x, inst.y = nx, ny
                        else:
                            inst.x = round(nx / gs) * gs
                            inst.y = round(ny / gs) * gs
                        if hasattr(inst, "env"):
                            try:
                                inst.env.set("x", inst.x)
                                inst.env.set("y", inst.y)
                            except Exception:
                                pass
                        self._drag_moved = True
                        if self.on_move:
                            self.on_move(inst)
                        return True
            if self.panning:
                dx = (event.pos[0] - self.pan_start[0]) / self.zoom
                dy = (event.pos[1] - self.pan_start[1]) / self.zoom
                self.camera_x = self.cam_start[0] - dx
                self.camera_y = self.cam_start[1] - dy
                return True
            if self.drag_object_name:
                return True  # keep consuming while dragging from list

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                # drop object from list onto scene
                if self.drag_object_name:
                    name = self.drag_object_name
                    self.drag_object_name = None
                    if self.rect.collidepoint(event.pos) and self.on_place:
                        wx, wy = self.screen_to_world(*event.pos)
                        self.on_place(name, wx, wy)
                    return True
                if self.dragging:
                    self.dragging = False
                    return True
            if event.button in (2, 3) and self.panning:
                self.panning = False
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(event.pos):
                return False

            if event.button == 1:
                # 1) Always try to select/drag existing instance first
                inst = self.hit_test(instances, event.pos[0], event.pos[1])
                if inst is not None:
                    self.selected_id = inst.id
                    self.dragging = True
                    self._drag_moved = False
                    self.place_object_name = None
                    self.drag_object_name = None
                    wx, wy = self.screen_to_world(*event.pos)
                    self.drag_offset = (float(inst.x) - wx, float(inst.y) - wy)
                    if self.on_select:
                        self.on_select(inst)
                    return True

                # 2) Empty space + place mode → place new
                if self.place_object_name and self.on_place:
                    wx, wy = self.screen_to_world(*event.pos)
                    self.on_place(self.place_object_name, wx, wy)
                    return True

                # 3) Empty click → deselect
                self.selected_id = None
                self.dragging = False
                if self.on_select:
                    self.on_select(None)
                return True

            if event.button in (2, 3):
                self.panning = True
                self.pan_start = event.pos
                self.cam_start = (self.camera_x, self.camera_y)
                return True

        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.zoom = max(0.25, min(4.0, self.zoom + event.y * 0.1))
            mx, my = pygame.mouse.get_pos()
            wx, wy = self.screen_to_world(mx, my)
            self.camera_x = wx - (mx - self.rect.x) / self.zoom
            self.camera_y = wy - (my - self.rect.y) / self.zoom
            return True

        return False

    def draw(self, surf, instances: List[Any]):
        draw_rect(surf, self.rect, self.bg_color, border=1)
        clip = surf.get_clip()
        surf.set_clip(self.rect)

        if self.show_grid:
            gs = max(4.0, self.grid_size * self.zoom)
            start_x = self.rect.x - (self.camera_x * self.zoom) % gs
            start_y = self.rect.y - (self.camera_y * self.zoom) % gs
            grid_c = (45, 45, 55)
            x = start_x
            while x < self.rect.right:
                pygame.draw.line(surf, grid_c, (x, self.rect.y), (x, self.rect.bottom))
                x += gs
            y = start_y
            while y < self.rect.bottom:
                pygame.draw.line(surf, grid_c, (self.rect.x, y), (self.rect.right, y))
                y += gs

        sx0, sy0 = self.world_to_screen(0, 0)
        sx1, sy1 = self.world_to_screen(self.scene_w, self.scene_h)
        pygame.draw.rect(surf, (60, 60, 80), pygame.Rect(sx0, sy0, sx1 - sx0, sy1 - sy0), 2)

        for inst in sorted(instances, key=lambda i: getattr(i, "depth", 0)):
            if not getattr(inst, "visible", True):
                continue
            w, h = self._inst_size(inst)
            sx, sy = self.world_to_screen(float(inst.x), float(inst.y))
            dw, dh = w * self.zoom, h * self.zoom
            drawn = False
            if getattr(inst, "sprite", None) and self.sprite_manager:
                try:
                    spr = self.sprite_manager.get(inst.sprite)
                    frame = spr.get_frame(0)
                    if abs(self.zoom - 1.0) > 0.01:
                        frame = self._cached_frame(inst.sprite, frame, int(dw), int(dh))
                    surf.blit(frame, (sx, sy))
                    drawn = True
                    inst.width = spr.width
                    inst.height = spr.height
                    w, h = float(spr.width), float(spr.height)
                    dw, dh = w * self.zoom, h * self.zoom
                except Exception:
                    pass
            if not drawn:
                r = pygame.Rect(int(sx), int(sy), max(8, int(dw)), max(8, int(dh)))
                color = (100 + (inst.id * 40) % 120, 130, 180)
                pygame.draw.rect(surf, color, r, border_radius=3)
                pygame.draw.rect(surf, (220, 220, 230), r, 1, border_radius=3)
                draw_text(surf, str(inst.object_name)[:10], (sx + 3, sy + 3), TEXT, 11)

            if inst.id == self.selected_id:
                r = pygame.Rect(int(sx) - 3, int(sy) - 3, int(dw) + 6, int(dh) + 6)
                pygame.draw.rect(surf, ACCENT, r, 2)
                for hx, hy in ((sx, sy), (sx + dw, sy), (sx, sy + dh), (sx + dw, sy + dh)):
                    pygame.draw.rect(surf, SUCCESS, (hx - 3, hy - 3, 6, 6))

        if self.place_object_name:
            draw_text(
                surf,
                f"배치: {self.place_object_name} (빈 곳 클릭 / Esc 취소)",
                (self.rect.x + 8, self.rect.y + 8),
                ACCENT,
                13,
            )

        if self.drag_object_name:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                pygame.draw.rect(surf, ACCENT, (mx - 16, my - 16, 32, 32), 2, border_radius=4)
                draw_text(surf, self.drag_object_name, (mx + 20, my - 8), ACCENT, 13)

        surf.set_clip(clip)

        mx, my = pygame.mouse.get_pos()
        if self.rect.collidepoint(mx, my):
            wx, wy = self.screen_to_world(mx, my)
            draw_text(
                surf,
                f"({wx:.0f}, {wy:.0f})  x{self.zoom:.2f}",
                (self.rect.x + 8, self.rect.bottom - 20),
                TEXT_DIM,
                11,
            )
