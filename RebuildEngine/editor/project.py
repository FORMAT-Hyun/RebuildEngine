"""Project model: external folder with objects/, scenes/, assets/, project.json."""

from __future__ import annotations

import os
import json
import shutil
import re
from typing import Dict, List, Optional, Any
from datetime import datetime


EVENT_TYPES = [
    ("create", "생성할 때"),
    ("step", "매 순간"),
    ("draw", "그릴 때"),
    ("collision", "충돌할 때"),
    ("destroy", "삭제될 때"),
]

EVENT_LABEL_TO_KEY = {label: key for key, label in EVENT_TYPES}
EVENT_KEY_TO_LABEL = {key: label for key, label in EVENT_TYPES}

RECENT_FILE = os.path.join(os.path.expanduser("~"), ".rebuild_engine_recent.json")


class ProjectObject:
    def __init__(self, name: str, folder: str):
        self.name = name
        self.folder = folder
        self.sprite: str = ""
        self.width: int = 32
        self.height: int = 32
        self.events: Dict[str, str] = {k: "" for k, _ in EVENT_TYPES}

    @property
    def object_json_path(self) -> str:
        return os.path.join(self.folder, "object.json")

    def event_path(self, event_key: str) -> str:
        return os.path.join(self.folder, "events", f"{event_key}.rea")

    def load(self):
        if os.path.isfile(self.object_json_path):
            with open(self.object_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.name = data.get("name", self.name)
            self.sprite = data.get("sprite", "") or ""
            self.width = int(data.get("width", 32))
            self.height = int(data.get("height", 32))
        events_dir = os.path.join(self.folder, "events")
        os.makedirs(events_dir, exist_ok=True)
        for key, _ in EVENT_TYPES:
            path = self.event_path(key)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.events[key] = f.read()
            else:
                self.events[key] = self.events.get(key, "")

    def save(self):
        os.makedirs(os.path.join(self.folder, "events"), exist_ok=True)
        data = {
            "name": self.name,
            "sprite": self.sprite,
            "width": self.width,
            "height": self.height,
        }
        with open(self.object_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        for key, code in self.events.items():
            with open(self.event_path(key), "w", encoding="utf-8") as f:
                f.write(code if code is not None else "")

    def to_rea_source(self) -> str:
        lines = [f"오브젝트 {self.name}:", ""]
        for key, label in EVENT_TYPES:
            code = (self.events.get(key) or "").rstrip()
            if not code.strip():
                continue
            lines.append(f"    {label}:")
            for line in code.splitlines():
                if line.strip() == "":
                    lines.append("")
                else:
                    lines.append("        " + line)
            lines.append("")
        return "\n".join(lines) + "\n"


class Project:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.objects_dir = os.path.join(self.root, "objects")
        self.scenes_dir = os.path.join(self.root, "scenes")
        self.assets_dir = os.path.join(self.root, "assets")
        self.project_json = os.path.join(self.root, "project.json")
        self.name = os.path.basename(self.root)
        self.objects: Dict[str, ProjectObject] = {}
        self.current_scene_path: Optional[str] = None

    @staticmethod
    def is_project(path: str) -> bool:
        path = os.path.abspath(path)
        return os.path.isfile(os.path.join(path, "project.json")) or (
            os.path.isdir(os.path.join(path, "objects"))
            and os.path.isdir(os.path.join(path, "scenes"))
        )

    @classmethod
    def create_new(cls, parent_dir: str, name: str) -> "Project":
        """Create project folder under parent_dir/name."""
        name = name.strip()
        if not name:
            raise ValueError("프로젝트 이름이 비어 있습니다")
        root = os.path.join(os.path.abspath(parent_dir), name)
        if os.path.exists(root) and os.listdir(root):
            # allow empty dir
            if Project.is_project(root):
                raise ValueError("이미 프로젝트가 있는 폴더입니다")
        os.makedirs(os.path.join(root, "objects"), exist_ok=True)
        os.makedirs(os.path.join(root, "scenes"), exist_ok=True)
        os.makedirs(os.path.join(root, "assets"), exist_ok=True)
        meta = {
            "name": name,
            "created": datetime.now().isoformat(timespec="seconds"),
            "version": 1,
            "default_scene": "main.json",
        }
        with open(os.path.join(root, "project.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        # empty main scene
        main_scene = {
            "name": "main",
            "width": 800,
            "height": 600,
            "background_color": [30, 30, 40],
            "instances": [],
        }
        with open(os.path.join(root, "scenes", "main.json"), "w", encoding="utf-8") as f:
            json.dump(main_scene, f, ensure_ascii=False, indent=2)
        proj = cls(root)
        proj.name = name
        add_recent(root)
        return proj

    def load_meta(self):
        if os.path.isfile(self.project_json):
            with open(self.project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.name = data.get("name", self.name)

    def save_meta(self):
        data = {
            "name": self.name,
            "version": 1,
            "default_scene": os.path.basename(self.current_scene_path)
            if self.current_scene_path
            else "main.json",
        }
        with open(self.project_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def ensure_dirs(self):
        os.makedirs(self.objects_dir, exist_ok=True)
        os.makedirs(self.scenes_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        if not os.path.isfile(self.project_json):
            self.save_meta()

    def scan(self):
        self.ensure_dirs()
        self.load_meta()
        self.objects.clear()
        if not os.path.isdir(self.objects_dir):
            return
        for name in sorted(os.listdir(self.objects_dir)):
            folder = os.path.join(self.objects_dir, name)
            if not os.path.isdir(folder):
                continue
            if name.startswith("."):
                continue
            obj = ProjectObject(name, folder)
            obj.load()
            self.objects[obj.name] = obj

    def create_object(self, name: str) -> ProjectObject:
        name = name.strip()
        if not name:
            raise ValueError("Object 이름이 비어 있습니다")
        if not re.match(r"^[A-Za-z_가-힣ㄱ-ㅎㅏ-ㅣ][A-Za-z0-9_가-힣ㄱ-ㅎㅏ-ㅣ]*$", name):
            raise ValueError("Object 이름은 한글/영문/숫자/_만 사용할 수 있고 숫자로 시작할 수 없습니다")
        if name in self.objects:
            raise ValueError(f"이미 존재하는 Object: {name}")
        folder = os.path.join(self.objects_dir, name)
        os.makedirs(os.path.join(folder, "events"), exist_ok=True)
        obj = ProjectObject(name, folder)
        obj.save()
        self.objects[name] = obj
        return obj

    def delete_object(self, name: str):
        if name not in self.objects:
            return
        folder = self.objects[name].folder
        del self.objects[name]
        if os.path.isdir(folder):
            shutil.rmtree(folder)

    def save_all_objects(self):
        for obj in self.objects.values():
            obj.save()

    def get_object(self, name: str) -> Optional[ProjectObject]:
        return self.objects.get(name)

    def list_object_names(self) -> List[str]:
        return sorted(self.objects.keys())

    def build_combined_rea(self) -> str:
        parts = []
        for name in self.list_object_names():
            parts.append(self.objects[name].to_rea_source())
        return "\n".join(parts)

    def list_assets(self) -> List[str]:
        """Image files plus generated .anim.json resources."""
        if not os.path.isdir(self.assets_dir):
            return []
        out = []
        for n in sorted(os.listdir(self.assets_dir), key=str.lower):
            low = n.lower()
            if low.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                out.append(n)
        anim_dir = os.path.join(self.assets_dir, "animations")
        if os.path.isdir(anim_dir):
            for n in sorted(os.listdir(anim_dir), key=str.lower):
                if n.lower().endswith(".anim.json"):
                    out.append(os.path.join("animations", n).replace("\\", "/"))
        return out

    def list_music(self) -> List[str]:
        """Return imported music files, stored under assets/audio/."""
        audio_dir = os.path.join(self.assets_dir, "audio")
        if not os.path.isdir(audio_dir):
            return []
        exts = (".ogg", ".wav", ".mp3", ".flac", ".mod", ".xm", ".mid", ".midi")
        return [os.path.join("audio", n).replace("\\", "/") for n in sorted(os.listdir(audio_dir), key=str.lower)
                if n.lower().endswith(exts) and os.path.isfile(os.path.join(audio_dir, n))]

    def list_scenes(self) -> List[str]:
        """Return scene file names (*.json) in scenes/."""
        if not os.path.isdir(self.scenes_dir):
            return []
        return sorted(
            n for n in os.listdir(self.scenes_dir) if n.endswith(".json") and not n.startswith("_")
        )

    def scene_path(self, filename: str) -> str:
        if not filename.endswith(".json"):
            filename += ".json"
        return os.path.join(self.scenes_dir, filename)

    def create_scene(self, name: str, width: int = 800, height: int = 600) -> str:
        name = name.strip()
        if not name:
            raise ValueError("씬 이름이 비어 있습니다")
        filename = name if name.endswith(".json") else name + ".json"
        # sanitize base name for file
        base = os.path.splitext(filename)[0]
        path = self.scene_path(filename)
        if os.path.exists(path):
            raise ValueError(f"이미 있는 씬: {filename}")
        data = {
            "name": base,
            "width": width,
            "height": height,
            "background_color": [30, 30, 40],
            "instances": [],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _import_rea_file(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        current_obj = None
        current_event = None
        event_lines: List[str] = []

        def flush_event():
            nonlocal current_event, event_lines
            if current_obj and current_event is not None:
                cleaned = []
                for ln in event_lines:
                    if ln.startswith("        "):
                        cleaned.append(ln[8:])
                    elif ln.startswith("\t\t"):
                        cleaned.append(ln[2:])
                    else:
                        cleaned.append(ln.lstrip() if ln.strip() else "")
                current_obj.events[current_event] = "\n".join(cleaned).rstrip() + ("\n" if cleaned else "")
            current_event = None
            event_lines = []

        def flush_obj():
            nonlocal current_obj
            flush_event()
            if current_obj:
                current_obj.save()
                self.objects[current_obj.name] = current_obj
            current_obj = None

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("오브젝트 ") and stripped.endswith(":"):
                flush_obj()
                name = stripped[len("오브젝트 ") : -1].strip()
                if name not in self.objects:
                    folder = os.path.join(self.objects_dir, name)
                    os.makedirs(os.path.join(folder, "events"), exist_ok=True)
                    current_obj = ProjectObject(name, folder)
                else:
                    current_obj = self.objects[name]
                i += 1
                continue
            matched = False
            for key, label in EVENT_TYPES:
                if stripped == f"{label}:" or stripped.startswith(f"{label}:"):
                    flush_event()
                    current_event = key
                    event_lines = []
                    matched = True
                    break
            if matched:
                i += 1
                continue
            if current_event is not None and current_obj is not None:
                event_lines.append(line)
            i += 1
        flush_obj()


def load_recent() -> List[str]:
    if not os.path.isfile(RECENT_FILE):
        return []
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        paths = data if isinstance(data, list) else data.get("paths", [])
        return [p for p in paths if os.path.isdir(p)]
    except Exception:
        return []


def add_recent(path: str):
    path = os.path.abspath(path)
    recent = load_recent()
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    recent = recent[:15]
    os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True) if os.path.dirname(RECENT_FILE) else None
    try:
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def remove_recent(path: str):
    path = os.path.abspath(path)
    recent = [p for p in load_recent() if os.path.abspath(p) != path]
    try:
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
