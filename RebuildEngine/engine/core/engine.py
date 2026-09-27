"""Rebuild Engine core - Game Loop and systems."""

import os
import sys
import pygame
from typing import Dict, Optional, List

from engine.core.object import GameObject, Instance
from engine.core.scene import Scene
from engine.graphics.sprite import SpriteManager
from engine.graphics.camera import Camera
from engine.input.input_manager import InputManager
from engine.collision.collider import check_collision, check_collision_all

from rea import compile_rea, create_interpreter, Environment, ReaRuntimeError
from rea.interpreter import Interpreter


class RebuildEngine:
    def __init__(self, width: int = 800, height: int = 600, title: str = "Rebuild Engine", fps: int = 60):
        pygame.init()
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = False

        self.objects: Dict[str, GameObject] = {}
        self.scene = Scene("main")
        assets_default = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
        self.sprite_manager = SpriteManager(assets_path=os.path.abspath(assets_default))
        self.camera = Camera(width, height)
        self.input = InputManager()
        self.interpreter: Interpreter = create_interpreter()

        self._setup_builtins()
        self.delta_time = 1.0 / fps
        self.frame_count = 0
        self._collision_target = None

    def _setup_builtins(self):
        eng = self

        def key_pressed(name: str) -> bool:
            return eng.input.is_key_held(str(name))

        def key_just_pressed(name: str) -> bool:
            return eng.input.is_key_pressed(str(name))

        def draw_sprite(sprite_name: str, x: float, y: float, *args):
            # called from instance context; we need current instance
            # This is set via _current_instance
            inst = getattr(eng, "_current_instance", None)
            if inst is None:
                return
            spr = eng.sprite_manager.get(str(sprite_name))
            if spr:
                inst.sprite = str(sprite_name)
                # actual drawing happens in draw phase using inst.sprite
                # but for immediate, we can queue
                if not hasattr(eng, "_draw_queue"):
                    eng._draw_queue = []
                eng._draw_queue.append((spr, float(x), float(y), inst.image_index))

        def print_msg(*args):
            print("[Rea]", *args)

        self.interpreter.register_builtin("키를_눌렀다", key_pressed)
        self.interpreter.register_builtin("키를눌렀다", key_pressed)
        self.interpreter.register_builtin("키_눌림", key_pressed)
        self.interpreter.register_builtin("키눌림", key_pressed)
        self.interpreter.register_builtin("그리기", draw_sprite)
        self.interpreter.register_builtin("출력", print_msg)

        # Music helpers use a single SDL_mixer music channel. Paths are relative to assets/.
        def play_music(path: str, loops: int = -1):
            full = str(path)
            if not os.path.isabs(full):
                full = os.path.join(self.sprite_manager.assets_path, full)
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(full)
                pygame.mixer.music.play(int(loops))
            except Exception as e:
                print(f"[오디오 오류] {e}")

        def stop_music():
            try: pygame.mixer.music.stop()
            except Exception: pass

        def set_music_volume(value: float):
            try: pygame.mixer.music.set_volume(max(0.0, min(1.0, float(value))))
            except Exception: pass

        self.interpreter.register_builtin("음악_재생", play_music)
        self.interpreter.register_builtin("음악_정지", stop_music)
        self.interpreter.register_builtin("음악_볼륨", set_music_volume)
        self.interpreter.register_builtin("print", print_msg)

        # Collision helper
        def collides_with(obj_name: str = "") -> bool:
            inst = getattr(eng, "_current_instance", None)
            if not inst:
                return False
            target = str(obj_name) if obj_name else ""
            if target:
                return check_collision(inst, eng.scene.instances, target) is not None
            return any(check_collision(inst, [other], other.object_name) is not None
                       for other in eng.scene.instances if other is not inst and other.active)

        self.interpreter.register_builtin("충돌한다", collides_with)
        self.interpreter.register_builtin("충돌", collides_with)

    def load_script(self, path: str):
        """Load a .rea file and register objects."""
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        self.load_script_source(source, path)

    def load_script_source(self, source: str, filename: str = "<string>"):
        try:
            program = compile_rea(source)
            self.interpreter.load(program)
            for obj_def in program.objects:
                go = GameObject(obj_def.name, source)
                go.events = obj_def.events
                self.objects[obj_def.name] = go
                print(f"[Engine] 오브젝트 등록: {obj_def.name} (이벤트: {list(obj_def.events.keys())})")
        except SyntaxError as e:
            print(f"[문법 오류] {filename}: {e}")
            raise
        except Exception as e:
            print(f"[로드 오류] {filename}: {e}")
            raise

    def get_object(self, name: str) -> Optional[GameObject]:
        return self.objects.get(name)

    def create_instance(self, object_name: str, x: float = 0, y: float = 0) -> Optional[Instance]:
        obj = self.objects.get(object_name)
        if not obj:
            print(f"[경고] 오브젝트 '{object_name}' 를 찾을 수 없습니다.")
            return None
        inst = Instance(obj, x, y, self)
        self.scene.add_instance(inst)
        # Run create event
        self._run_event(inst, "create")
        return inst

    def _run_event(self, inst: Instance, event_name: str):
        self._current_instance = inst
        inst.sync_to_env()
        try:
            self.interpreter.run_event(inst.object_name, event_name, inst.env)
        except ReaRuntimeError as e:
            print(f"[런타임 오류] {inst.object_name}.{event_name}: {e}")
        except Exception as e:
            print(f"[오류] {inst.object_name}.{event_name}: {e}")
        inst.sync_from_env()
        self._current_instance = None

    def _update_instances(self):
        # Sort by depth for consistency (higher depth later? usually lower first)
        for inst in list(self.scene.instances):
            if not inst.active:
                continue
            # Update image_index for animation
            if inst.image_speed != 0:
                inst.image_index += inst.image_speed
                inst.env.set("image_index", inst.image_index)

            self._run_event(inst, "step")

            # Apply simple velocity if set
            try:
                hs = inst.env.get("hspeed") if inst.env.has("hspeed") else 0
                vs = inst.env.get("vspeed") if inst.env.has("vspeed") else 0
                inst.x += float(hs)
                inst.y += float(vs)
                inst.env.set("x", inst.x)
                inst.env.set("y", inst.y)
            except Exception:
                pass

    def _check_collisions(self):
        instances = [i for i in self.scene.instances if i.active]
        for inst in instances:
            if "collision" not in inst.object.events:
                continue
            hit = False
            for other in instances:
                if other is inst:
                    continue
                if check_collision(inst, [other], other.object_name) is not None:
                    hit = True
                    break
            if hit:
                self._run_event(inst, "collision")

    def _draw(self):
        self.screen.fill(self.scene.background_color)
        self.camera.update()

        # Sort instances by depth (lower depth drawn first)
        sorted_insts = sorted(self.scene.instances, key=lambda i: i.depth)

        self._draw_queue = []

        for inst in sorted_insts:
            if not inst.active or not inst.visible:
                continue
            self._current_instance = inst
            inst.sync_to_env()
            had_queue_before = len(self._draw_queue)
            # Run draw event (may call 그리기)
            self._run_event(inst, "draw")
            # Auto-draw only if sprite is set AND draw event did not call 그리기
            if inst.sprite and len(self._draw_queue) == had_queue_before:
                spr = self.sprite_manager.get(inst.sprite)
                sx, sy = self.camera.apply(inst.x, inst.y)
                frame = spr.get_frame(inst.image_index)
                self.screen.blit(frame, (sx, sy))
            self._current_instance = None

        # Process any queued draws from 그리기()
        for spr, x, y, idx in self._draw_queue:
            sx, sy = self.camera.apply(x, y)
            frame = spr.get_frame(idx)
            self.screen.blit(frame, (sx, sy))
        self._draw_queue.clear()

        pygame.display.flip()

    def run(self):
        self.running = True
        print(f"[Engine] 시작: {self.title} ({self.width}x{self.height})")
        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            self.input.update(events)
            self.delta_time = self.clock.get_time() / 1000.0
            self._update_instances()
            self._check_collisions()
            self._draw()

            self.clock.tick(self.fps)
            self.frame_count += 1

        pygame.quit()
        print("[Engine] 종료")

    def quit(self):
        self.running = False
