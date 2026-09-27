"""Object definition and Instance management."""

from typing import Any, Dict, Optional, TYPE_CHECKING
from rea.interpreter import Environment

if TYPE_CHECKING:
    from engine.core.engine import RebuildEngine


class GameObject:
    """Object definition (like GameMaker Object)."""

    def __init__(self, name: str, script_source: str = ""):
        self.name = name
        self.script_source = script_source
        self.events: Dict[str, list] = {}  # filled by interpreter
        self.default_sprite: Optional[str] = None
        self.default_width = 32
        self.default_height = 32


class Instance:
    """Runtime instance of a GameObject."""

    _next_id = 1

    def __init__(self, obj: GameObject, x: float = 0, y: float = 0, engine: Optional["RebuildEngine"] = None):
        self.id = Instance._next_id
        Instance._next_id += 1
        self.object = obj
        self.object_name = obj.name
        self.x = float(x)
        self.y = float(y)
        self.sprite: Optional[str] = obj.default_sprite
        self.width = obj.default_width
        self.height = obj.default_height
        self.visible = True
        self.active = True
        self.depth = 0
        self.image_index = 0.0
        self.image_speed = 0.0
        self.direction = 0.0
        self.speed = 0.0
        self.hspeed = 0.0
        self.vspeed = 0.0
        self.engine = engine

        # Per-instance environment for Rea variables
        self.env = Environment()
        self.env.define("x", self.x)
        self.env.define("y", self.y)
        self.env.define("id", self.id)
        self.env.define("sprite", self.sprite or "")
        self.env.define("visible", self.visible)
        self.env.define("depth", self.depth)
        self.env.define("image_index", self.image_index)
        self.env.define("image_speed", self.image_speed)

        # Custom variables live in env

    def sync_from_env(self):
        """Pull common variables from env back to instance."""
        try:
            self.x = float(self.env.get("x"))
            self.y = float(self.env.get("y"))
        except Exception:
            pass
        try:
            self.visible = bool(self.env.get("visible"))
        except Exception:
            pass
        try:
            self.depth = float(self.env.get("depth"))
        except Exception:
            pass
        try:
            self.image_index = float(self.env.get("image_index"))
        except Exception:
            pass
        try:
            self.image_speed = float(self.env.get("image_speed"))
        except Exception:
            pass
        try:
            s = self.env.get("sprite")
            if isinstance(s, str):
                self.sprite = s
        except Exception:
            pass

    def sync_to_env(self):
        """Push instance properties into env before running events."""
        self.env.set("x", self.x)
        self.env.set("y", self.y)
        self.env.set("id", self.id)
        self.env.set("sprite", self.sprite or "")
        self.env.set("visible", self.visible)
        self.env.set("depth", self.depth)
        self.env.set("image_index", self.image_index)
        self.env.set("image_speed", self.image_speed)

    def get_bbox(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)
