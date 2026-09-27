"""Simple tilemap support."""

from typing import List, Optional, Tuple
import pygame


class Tilemap:
    def __init__(self, tile_size: int = 32, width: int = 25, height: int = 19):
        self.tile_size = tile_size
        self.width = width
        self.height = height
        self.data: List[List[int]] = [[0 for _ in range(width)] for _ in range(height)]
        self.tileset: Optional[pygame.Surface] = None
        self.tile_images: dict = {}  # id -> Surface

    def set_tile(self, tx: int, ty: int, tile_id: int):
        if 0 <= tx < self.width and 0 <= ty < self.height:
            self.data[ty][tx] = tile_id

    def get_tile(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.data[ty][tx]
        return 0

    def load_from_list(self, rows: List[List[int]]):
        self.height = len(rows)
        self.width = len(rows[0]) if rows else 0
        self.data = [list(r) for r in rows]

    def draw(self, surface: pygame.Surface, camera_x: float = 0, camera_y: float = 0):
        if not self.tile_images and not self.tileset:
            return
        start_tx = max(0, int(camera_x // self.tile_size))
        start_ty = max(0, int(camera_y // self.tile_size))
        end_tx = min(self.width, start_tx + surface.get_width() // self.tile_size + 2)
        end_ty = min(self.height, start_ty + surface.get_height() // self.tile_size + 2)
        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                tid = self.data[ty][tx]
                if tid == 0:
                    continue
                img = self.tile_images.get(tid)
                if img:
                    sx = tx * self.tile_size - camera_x
                    sy = ty * self.tile_size - camera_y
                    surface.blit(img, (sx, sy))

    def set_tile_image(self, tile_id: int, surface: pygame.Surface):
        self.tile_images[tile_id] = surface
