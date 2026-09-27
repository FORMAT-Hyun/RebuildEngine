"""Sprite, sprite-sheet animation, and resource management."""
import os, json
from typing import Dict, Optional, List, Tuple
import pygame


class Sprite:
    def __init__(self, name: str, frames: List[pygame.Surface], frame_speed: float = 0.0, fps: float = 0.0, loop: bool = True):
        self.name = name
        self.frames = frames
        self.frame_count = len(frames)
        self.fps = float(fps)
        self.loop = bool(loop)
        self.frame_speed = float(frame_speed) if frame_speed else (self.fps / 60.0 if self.fps else 0.0)
        self.width = frames[0].get_width() if frames else 32
        self.height = frames[0].get_height() if frames else 32

    @property
    def animated(self):
        return self.frame_count > 1

    def get_frame(self, index: float) -> pygame.Surface:
        if not self.frames:
            surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.rect(surf, (200, 80, 80), (0, 0, 32, 32))
            return surf
        if self.loop:
            return self.frames[int(index) % self.frame_count]
        return self.frames[min(self.frame_count - 1, max(0, int(index)))]


class SpriteManager:
    def __init__(self, assets_path: str = "assets"):
        self.assets_path = os.path.abspath(assets_path)
        self.sprites: Dict[str, Sprite] = {}
        self._placeholders: Dict[str, pygame.Surface] = {}
        self._path_cache: Dict[str, str] = {}

    def _load_image(self, path: str):
        image = pygame.image.load(path)
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            try:
                return image.convert_alpha()
            except Exception:
                return image
        return image

    def _resolve(self, name: str, path: Optional[str]):
        if path:
            return os.path.abspath(path), name
        if os.path.isabs(name):
            return name, os.path.basename(name)
        return os.path.join(self.assets_path, name), name

    def load(self, name: str, path: Optional[str] = None, frame_width: int = 0, frame_height: int = 0) -> Sprite:
        if name in self.sprites:
            return self.sprites[name]
        resolved, resource_name = self._resolve(name, path)
        self._path_cache[name] = resolved

        # Generated animation resource.
        if resolved.lower().endswith(".anim.json"):
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    data = json.load(f)
                source = data["source"]
                if not os.path.isabs(source):
                    source = os.path.join(self.assets_path, source)
                image = self._load_image(source)
                fw = int(data.get("frame_width", image.get_width()))
                fh = int(data.get("frame_height", image.get_height()))
                fps = float(data.get("fps", 10))
                frames = []
                w, h = image.get_size()
                for y in range(0, h - fh + 1, fh):
                    for x in range(0, w - fw + 1, fw):
                        frames.append(image.subsurface((x, y, fw, fh)).copy())
                if not frames:
                    frames = [image.copy()]
                spr = Sprite(resource_name, frames, fps=fps, loop=bool(data.get("loop", True)))
                self.sprites[name] = spr
                return spr
            except Exception:
                pass

        if not os.path.exists(resolved):
            surf = self._placeholders.get(name)
            if surf is None:
                h = hash(name)
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                pygame.draw.rect(surf, (100 + h % 155, 80 + (h >> 8) % 155, 120), (0,0,32,32))
                pygame.draw.rect(surf, (255,255,255), (0,0,32,32), 2)
                self._placeholders[name] = surf
            spr = Sprite(name, [surf])
            self.sprites[name] = spr
            return spr

        try:
            image = self._load_image(resolved)
        except Exception:
            image = pygame.image.load(resolved)

        if frame_width > 0 and frame_height > 0:
            frames = []
            w, h = image.get_size()
            for y in range(0, h - frame_height + 1, frame_height):
                for x in range(0, w - frame_width + 1, frame_width):
                    frames.append(image.subsurface((x, y, frame_width, frame_height)).copy())
            spr = Sprite(name, frames or [image])
        else:
            spr = Sprite(name, [image])
        self.sprites[name] = spr
        return spr

    def get(self, name: str) -> Sprite:
        return self.sprites[name] if name in self.sprites else self.load(name)

    def create_placeholder(self, name: str, color: Tuple[int,int,int] = (200,100,100), size: int = 32) -> Sprite:
        surf = pygame.Surface((size,size), pygame.SRCALPHA)
        pygame.draw.rect(surf, color, (0,0,size,size))
        pygame.draw.rect(surf, (255,255,255), (0,0,size,size), 2)
        pygame.draw.circle(surf, (50,50,50), (size//3,size//3), 3)
        pygame.draw.circle(surf, (50,50,50), (2*size//3,size//3), 3)
        spr = Sprite(name,[surf])
        self.sprites[name] = spr
        return spr
