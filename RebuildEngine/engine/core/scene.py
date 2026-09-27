"""Scene management."""

from typing import List, Dict, Optional, Any
import json
import os
from .object import Instance, GameObject


class Scene:
    def __init__(self, name: str = "main"):
        self.name = name
        self.instances: List[Instance] = []
        self.width = 800
        self.height = 600
        self.background_color = (30, 30, 40)
        self.tilemap_data: Optional[Dict] = None
        self.camera_x = 0.0
        self.camera_y = 0.0
        # Path this scene was loaded from (optional)
        self.path: Optional[str] = None

    def add_instance(self, inst: Instance):
        self.instances.append(inst)

    def remove_instance(self, inst: Instance):
        if inst in self.instances:
            self.instances.remove(inst)

    def get_instances_by_object(self, object_name: str) -> List[Instance]:
        return [i for i in self.instances if i.object_name == object_name]

    def clear(self):
        self.instances.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "background_color": list(self.background_color),
            "camera_x": float(self.camera_x),
            "camera_y": float(self.camera_y),
            "instances": [
                {
                    "object": inst.object_name,
                    "x": float(inst.x),
                    "y": float(inst.y),
                    "sprite": inst.sprite or "",
                    "depth": float(inst.depth),
                    "visible": bool(inst.visible),
                    "width": getattr(inst, "width", 32),
                    "height": getattr(inst, "height", 32),
                }
                for inst in self.instances
            ],
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        self.path = path

    @classmethod
    def load(cls, path: str, engine) -> "Scene":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scene = cls(data.get("name", "main"))
        scene.path = path
        scene.width = data.get("width", 800)
        scene.height = data.get("height", 600)
        bg = data.get("background_color", [30, 30, 40])
        scene.background_color = tuple(bg)
        scene.camera_x = float(data.get("camera_x", 0.0))
        scene.camera_y = float(data.get("camera_y", 0.0))
        for idata in data.get("instances", []):
            obj_name = idata.get("object") or idata.get("name", "Unknown")
            obj = engine.get_object(obj_name) if engine else None
            if obj is None and engine is not None:
                # Create a placeholder GameObject so editor/runtime can still place it
                from .object import GameObject
                obj = GameObject(obj_name)
                engine.objects[obj_name] = obj
            if obj is None:
                from .object import GameObject
                obj = GameObject(obj_name)
            inst = Instance(obj, idata.get("x", 0), idata.get("y", 0), engine)
            if idata.get("sprite"):
                inst.sprite = idata["sprite"]
            inst.depth = idata.get("depth", 0)
            inst.visible = idata.get("visible", True)
            if "width" in idata:
                inst.width = idata["width"]
            if "height" in idata:
                inst.height = idata["height"]
            scene.add_instance(inst)
        return scene

    @classmethod
    def from_dict(cls, data: Dict[str, Any], engine=None) -> "Scene":
        scene = cls(data.get("name", "main"))
        scene.width = data.get("width", 800)
        scene.height = data.get("height", 600)
        bg = data.get("background_color", [30, 30, 40])
        scene.background_color = tuple(bg)
        scene.camera_x = float(data.get("camera_x", 0.0))
        scene.camera_y = float(data.get("camera_y", 0.0))
        for idata in data.get("instances", []):
            obj_name = idata.get("object") or idata.get("name", "Unknown")
            obj = None
            if engine:
                obj = engine.get_object(obj_name)
            if obj is None:
                from .object import GameObject
                obj = GameObject(obj_name)
                if engine:
                    engine.objects[obj_name] = obj
            inst = Instance(obj, idata.get("x", 0), idata.get("y", 0), engine)
            if idata.get("sprite"):
                inst.sprite = idata["sprite"]
            inst.depth = idata.get("depth", 0)
            inst.visible = idata.get("visible", True)
            scene.add_instance(inst)
        return scene
