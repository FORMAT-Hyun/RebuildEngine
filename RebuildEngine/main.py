#!/usr/bin/env python3
"""Rebuild Engine - runtime entry point."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.core.engine import RebuildEngine
from engine.core.scene import Scene


def main():
    eng = RebuildEngine(width=800, height=600, title="Rebuild Engine 1.0", fps=60)

    objects_dir = os.path.join(ROOT, "objects")
    scene_path = os.path.join(ROOT, "scenes", "main.json")

    if os.path.isdir(objects_dir) and any(os.scandir(objects_dir)):
        from editor.project import Project
        proj = Project(ROOT)
        proj.scan()
        rea = proj.build_combined_rea()
        if rea.strip():
            eng.load_script_source(rea, "project.rea")
        if os.path.isfile(scene_path):
            eng.scene = Scene.load(scene_path, eng)
            for inst in eng.scene.instances:
                inst.engine = eng
                po = proj.objects.get(inst.object_name)
                if po and po.sprite and not inst.sprite:
                    inst.sprite = po.sprite
                eng._run_event(inst, "create")
        else:
            names = proj.list_object_names()
            if names:
                eng.create_instance(names[0], 400, 300)
    else:
        print("[Engine] 프로젝트가 비어 있습니다. editor.py 에서 Object를 만드세요.")

    eng.run()


if __name__ == "__main__":
    main()
