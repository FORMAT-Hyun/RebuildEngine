"""Inspector for instances, objects, sprites, music and scenes.

Sprites and sprite-sheet animations are intentionally treated as one resource
family, similar to a GameMaker-style Sprite resource.
"""
from __future__ import annotations
import os, json, pygame
from typing import Optional, Any, Callable, List
from .ui import draw_rect, draw_text, TextInput, Checkbox, Button, BG_PANEL, BG_PANEL2, TEXT, TEXT_DIM, ACCENT, BORDER, INPUT_BG, BG_HOVER, BG_ACTIVE


class Inspector:
    MODE_NONE = 0
    MODE_INSTANCE = 1
    MODE_OBJECT = 2
    MODE_SPRITE = 3
    MODE_MUSIC = 4
    MODE_SCENE = 5

    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.mode = self.MODE_NONE
        self.instance = None
        self.object_def = None
        self.sprite_name: Optional[str] = None
        self.sprite_info = {}
        self.music_name: Optional[str] = None
        self.scene_data = None
        self.fields = {}
        self.on_change: Optional[Callable] = None
        self.on_object_change: Optional[Callable] = None
        self.on_sprite_assign: Optional[Callable] = None
        self.on_sprite_asset_change: Optional[Callable] = None
        self.on_music_change: Optional[Callable] = None
        self.on_music_action: Optional[Callable] = None
        self.on_scene_change: Optional[Callable] = None
        self.on_scene_action: Optional[Callable] = None
        self.sprite_list: List[str] = []
        self.sprite_picker_open = False
        self.sprite_scroll = 0
        self.sprite_manager = None
        self._thumb_cache = {}
        self._preview_cache = {}
        self._music_path = ""
        self._scene_path = ""
        self.music_loop = True
        self.music_volume = 1.0
        self._build_fields()

    def set_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._layout_fields()

    def set_sprite_list(self, files):
        self.sprite_list = list(files)

    def _build_fields(self):
        self.fields = {
            "name": TextInput((0,0,100,24), "", on_change=self._on_name),
            "x": TextInput((0,0,100,24), "0", numeric=True, on_change=lambda v:self._on_num("x",v)),
            "y": TextInput((0,0,100,24), "0", numeric=True, on_change=lambda v:self._on_num("y",v)),
            "depth": TextInput((0,0,100,24), "0", numeric=True, on_change=lambda v:self._on_num("depth",v)),
            "width": TextInput((0,0,100,24), "32", numeric=True, on_change=lambda v:self._on_num("width",v)),
            "height": TextInput((0,0,100,24), "32", numeric=True, on_change=lambda v:self._on_num("height",v)),
            "visible": Checkbox((0,0,20,20), True, on_change=self._on_visible),
            "music_volume": TextInput((0,0,100,24), "1.0", numeric=True, on_change=self._on_music_volume),
            "music_loop": Checkbox((0,0,20,20), True, on_change=self._on_music_loop),
            "scene_width": TextInput((0,0,100,24), "800", numeric=True, on_change=lambda v:self._on_scene_num("width",v)),
            "scene_height": TextInput((0,0,100,24), "600", numeric=True, on_change=lambda v:self._on_scene_num("height",v)),
            "scene_bg_r": TextInput((0,0,100,24), "30", numeric=True, on_change=lambda v:self._on_scene_num("bg_r",v)),
            "scene_bg_g": TextInput((0,0,100,24), "30", numeric=True, on_change=lambda v:self._on_scene_num("bg_g",v)),
            "scene_bg_b": TextInput((0,0,100,24), "40", numeric=True, on_change=lambda v:self._on_scene_num("bg_b",v)),
            "scene_camera_x": TextInput((0,0,100,24), "0", numeric=True, on_change=lambda v:self._on_scene_num("camera_x",v)),
            "scene_camera_y": TextInput((0,0,100,24), "0", numeric=True, on_change=lambda v:self._on_scene_num("camera_y",v)),
            "sprite_fps": TextInput((0,0,100,24), "10", numeric=True, on_change=self._on_sprite_fps),
            "sprite_fw": TextInput((0,0,100,24), "32", numeric=True),
            "sprite_fh": TextInput((0,0,100,24), "32", numeric=True),
            "sprite_loop": Checkbox((0,0,20,20), True, on_change=self._on_sprite_loop),
        }
        self.sprite_btn_rect = pygame.Rect(0,0,100,26)
        self.sprite_save_btn = Button((0,0,100,26), "저장", on_click=lambda:self._sprite_asset_action("save"), accent=True)
        self.music_play_btn = Button((0,0,100,26), "▶ 재생", on_click=lambda:self._music_action("play"), accent=True)
        self.music_stop_btn = Button((0,0,100,26), "■ 정지", on_click=lambda:self._music_action("stop"))
        self.scene_save_btn = Button((0,0,100,26), "저장", on_click=lambda:self._scene_action("save"), accent=True)
        self.scene_reload_btn = Button((0,0,100,26), "다시 불러오기", on_click=lambda:self._scene_action("reload"))
        self._layout_fields()

    def _layout_fields(self):
        x=self.rect.x+12; w=max(80,self.rect.w-24); y=self.rect.y+36
        for key in ("name","x","y"):
            self.fields[key].rect=pygame.Rect(x,y+14,w,24); y+=40
        self.sprite_label_y=y; self.sprite_btn_rect=pygame.Rect(x,y+14,w,26); y+=44
        for key in ("depth","width","height"):
            self.fields[key].rect=pygame.Rect(x,y+14,w,24); y+=40
        self.fields["visible"].rect=pygame.Rect(x,y+14,20,20)

    def _deactivate_all_inputs(self):
        for f in self.fields.values():
            if isinstance(f, TextInput): f.active=False

    def clear(self):
        self.mode=self.MODE_NONE; self.instance=None; self.object_def=None; self.sprite_name=None; self.sprite_info={}; self.music_name=None; self.scene_data=None; self._music_path=""; self._scene_path=""; self.sprite_picker_open=False
        self._deactivate_all_inputs()

    def _current_sprite(self):
        if self.mode==self.MODE_INSTANCE and self.instance: return self.instance.sprite or ""
        if self.mode==self.MODE_OBJECT and self.object_def: return self.object_def.sprite or ""
        return ""

    def set_instance(self, inst):
        if inst is None:
            if self.mode==self.MODE_INSTANCE: self.clear()
            return
        self.mode=self.MODE_INSTANCE; self.instance=inst; self.object_def=None; self.sprite_name=None; self.music_name=None; self.scene_data=None; self.sprite_picker_open=False
        self.fields["name"].set_value(getattr(inst,"object_name","")); self.fields["x"].set_value(f"{float(inst.x):.1f}"); self.fields["y"].set_value(f"{float(inst.y):.1f}")
        self.fields["depth"].set_value(f"{float(getattr(inst,'depth',0)):.0f}"); self.fields["width"].set_value(f"{float(getattr(inst,'width',32)):.0f}"); self.fields["height"].set_value(f"{float(getattr(inst,'height',32)):.0f}"); self.fields["visible"].value=bool(getattr(inst,"visible",True))
        self._deactivate_all_inputs()

    def set_object(self,obj):
        if obj is None:
            if self.mode==self.MODE_OBJECT: self.clear()
            return
        self.mode=self.MODE_OBJECT; self.object_def=obj; self.instance=None; self.sprite_name=None; self.music_name=None; self.scene_data=None; self.sprite_picker_open=False
        self.fields["name"].set_value(obj.name); self.fields["x"].set_value("-"); self.fields["y"].set_value("-"); self.fields["depth"].set_value("0"); self.fields["width"].set_value(str(obj.width or 32)); self.fields["height"].set_value(str(obj.height or 32)); self.fields["visible"].value=True
        self._deactivate_all_inputs()

    def set_sprite_resource(self, filename: Optional[str], full_path: Optional[str]=None):
        if not filename:
            self.clear(); return
        self.mode=self.MODE_SPRITE; self.sprite_name=filename; self.instance=None; self.object_def=None; self.music_name=None; self.scene_data=None; self.sprite_picker_open=False
        path=full_path or filename
        info={"name":filename,"type":"image","source":filename,"width":32,"height":32,"frames":1,"fps":0.0,"loop":True,"frame_width":0,"frame_height":0,"path":path}
        if filename.endswith('.anim.json'):
            try:
                with open(path,'r',encoding='utf-8') as f: data=json.load(f)
                source=str(data.get('source','')); source_path=source if os.path.isabs(source) else os.path.join(os.path.dirname(path), source) if os.path.dirname(path).endswith('animations') else os.path.join(os.path.dirname(path), source)
                # Old resources are relative to assets/, not animations/.
                if not os.path.exists(source_path) and self.sprite_manager:
                    source_path=os.path.join(self.sprite_manager.assets_path, source)
                w=h=32
                if os.path.exists(source_path):
                    img=pygame.image.load(source_path); w,h=img.get_size()
                fw=int(data.get('frame_width',w)); fh=int(data.get('frame_height',h)); frames=max(1,(w//max(1,fw))*(h//max(1,fh)))
                info.update({"type":"animation","source":source,"width":fw,"height":fh,"frames":frames,"fps":float(data.get('fps',10)),"loop":bool(data.get('loop',True)),"frame_width":fw,"frame_height":fh,"path":path})
            except Exception: pass
        else:
            try:
                img=pygame.image.load(path); info["width"],info["height"]=img.get_size()
            except Exception: pass
        self.sprite_info=info
        self.fields["sprite_fw"].set_value(str(info["frame_width"] or info["width"]))
        self.fields["sprite_fh"].set_value(str(info["frame_height"] or info["height"]))
        self.fields["sprite_fps"].set_value(f"{float(info['fps']):g}")
        self.fields["sprite_loop"].value=bool(info["loop"])
        self._deactivate_all_inputs()
        self._preview_cache.clear()

    def set_music(self,filename,full_path=None):
        self.mode=self.MODE_MUSIC; self.music_name=filename or ""; self.instance=None; self.object_def=None; self.sprite_name=None; self.scene_data=None; self._music_path=full_path or ""; self.sprite_picker_open=False
        self.fields["music_volume"].set_value(f"{self.music_volume:.2f}"); self.fields["music_loop"].value=self.music_loop; self._deactivate_all_inputs()

    def set_scene(self,scene,path=None):
        if scene is None: self.clear(); return
        self.mode=self.MODE_SCENE; self.scene_data=scene; self.instance=None; self.object_def=None; self.sprite_name=None; self.music_name=None; self._scene_path=path or getattr(scene,'path','') or ""; self.sprite_picker_open=False
        bg=(tuple(getattr(scene,'background_color',(30,30,40)))+(30,30,40))[:3]
        vals={"scene_width":getattr(scene,'width',800),"scene_height":getattr(scene,'height',600),"scene_bg_r":bg[0],"scene_bg_g":bg[1],"scene_bg_b":bg[2],"scene_camera_x":getattr(scene,'camera_x',0),"scene_camera_y":getattr(scene,'camera_y',0)}
        for k,v in vals.items(): self.fields[k].set_value(str(v))
        self._deactivate_all_inputs()

    def refresh_from_instance(self):
        if self.mode!=self.MODE_INSTANCE or not self.instance: return
        for k,val in (("x",self.instance.x),("y",self.instance.y),("depth",getattr(self.instance,'depth',0)),("width",getattr(self.instance,'width',32)),("height",getattr(self.instance,'height',32))):
            if not self.fields[k].active: self.fields[k].set_value(f"{float(val):.1f}")

    def _on_num(self,key,v):
        try:
            if v in ("","-",".","-."): return
            n=float(v)
            if self.mode==self.MODE_INSTANCE and self.instance:
                if key in ("x","y"): setattr(self.instance,key,n)
                elif key=="depth": self.instance.depth=n
                else: setattr(self.instance,key,max(1,n))
                self._notify()
            elif self.mode==self.MODE_OBJECT and self.object_def and key in ("width","height"):
                setattr(self.object_def,key,max(1,int(n))); self._notify_object()
        except Exception: pass

    def _on_name(self,v): pass
    def _on_visible(self,v):
        if self.mode==self.MODE_INSTANCE and self.instance: self.instance.visible=bool(v); self._notify()
    def _notify(self):
        if self.on_change: self.on_change(self.instance)
    def _notify_object(self):
        if self.on_object_change: self.on_object_change(self.object_def)

    def _apply_sprite_picker(self,name):
        self.sprite_picker_open=False
        if self.on_sprite_assign: self.on_sprite_assign(name or "")

    def _on_sprite_fps(self,v):
        if self.mode!=self.MODE_SPRITE or self.sprite_info.get('type')!='animation': return
        try: self.sprite_info['fps']=max(0.01,min(240,float(v)))
        except Exception: pass

    def _on_sprite_loop(self,v):
        if self.mode==self.MODE_SPRITE and self.sprite_info.get('type')=='animation': self.sprite_info['loop']=bool(v)

    def _notify_sprite_asset(self):
        if self.on_sprite_asset_change and self.mode==self.MODE_SPRITE:
            self.on_sprite_asset_change(self.sprite_name,self.sprite_info)

    def _sprite_asset_action(self,action):
        if action=='save' and self.mode==self.MODE_SPRITE and self.sprite_info.get('type')=='animation':
            try:
                self.sprite_info['frame_width']=max(1,int(float(self.fields['sprite_fw'].value)))
                self.sprite_info['frame_height']=max(1,int(float(self.fields['sprite_fh'].value)))
                self.sprite_info['fps']=max(0.01,min(240,float(self.fields['sprite_fps'].value)))
            except Exception:
                pass
            self._notify_sprite_asset()

    def _on_music_volume(self,v):
        if self.mode!=self.MODE_MUSIC: return
        try: self.music_volume=max(0,min(1,float(v))); self.fields['music_volume'].set_value(f'{self.music_volume:.2f}'); self._notify_music()
        except Exception: pass
    def _on_music_loop(self,v):
        if self.mode==self.MODE_MUSIC: self.music_loop=bool(v); self._notify_music()
    def _notify_music(self):
        if self.on_music_change: self.on_music_change(self.music_name,self.music_volume,self.music_loop)
    def _music_action(self,a):
        if self.mode==self.MODE_MUSIC and self.on_music_action: self.on_music_action(a,self.music_name,self.music_volume,self.music_loop)

    def _on_scene_num(self,attr,v):
        if self.mode!=self.MODE_SCENE or not self.scene_data: return
        try:
            if v in ('','-','.', '-.'): return
            if attr in ('width','height'): setattr(self.scene_data,attr,max(1,int(float(v))))
            elif attr.startswith('bg_'):
                bg=list((tuple(getattr(self.scene_data,'background_color',(30,30,40)))+(30,30,40))[:3]); idx={'bg_r':0,'bg_g':1,'bg_b':2}[attr]; bg[idx]=max(0,min(255,int(float(v)))); self.scene_data.background_color=tuple(bg)
            else: setattr(self.scene_data,attr,float(v))
            self._notify_scene()
        except Exception: pass
    def _notify_scene(self):
        if self.on_scene_change: self.on_scene_change(self.scene_data)
    def _scene_action(self,a):
        if self.mode==self.MODE_SCENE and self.on_scene_action: self.on_scene_action(a,self.scene_data)

    def handle_event(self,event):
        if self.mode==self.MODE_NONE: return False
        if self.mode==self.MODE_MUSIC and (self.music_play_btn.handle_event(event) or self.music_stop_btn.handle_event(event)): return True
        if self.mode==self.MODE_SCENE and (self.scene_save_btn.handle_event(event) or self.scene_reload_btn.handle_event(event)): return True
        if self.mode==self.MODE_SPRITE and self.sprite_save_btn.handle_event(event): return True
        if self.sprite_picker_open:
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                r=self._picker_rect()
                if r.collidepoint(event.pos):
                    idx=int((event.pos[1]-r.y)//24)
                    if idx==0: self._apply_sprite_picker(""); return True
                    idx-=1
                    if 0<=idx<len(self.sprite_list): self._apply_sprite_picker(self.sprite_list[idx])
                    return True
                self.sprite_picker_open=False
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.rect.collidepoint(event.pos) and self.mode in (self.MODE_INSTANCE,self.MODE_OBJECT):
            if self.sprite_btn_rect.collidepoint(event.pos):
                self.sprite_picker_open=not self.sprite_picker_open; self._deactivate_all_inputs(); return True
        if event.type in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEMOTION,pygame.MOUSEWHEEL) and hasattr(event,'pos') and not self.rect.collidepoint(event.pos):
            return False
        handled=False
        for key,f in self.fields.items():
            if self.mode==self.MODE_OBJECT and key in ('x','y','depth','visible'): continue
            if self.mode!=self.MODE_INSTANCE and key in ('x','y','depth','visible','width','height') and self.mode not in (self.MODE_OBJECT,): continue
            if self.mode!=self.MODE_SPRITE and key.startswith('sprite_'): continue
            if self.mode!=self.MODE_MUSIC and key.startswith('music_'): continue
            if self.mode!=self.MODE_SCENE and key.startswith('scene_'): continue
            if f.handle_event(event): handled=True
        return handled or self.sprite_picker_open

    def _picker_rect(self):
        return pygame.Rect(self.sprite_btn_rect.x,self.sprite_btn_rect.bottom+2,self.sprite_btn_rect.w,min(190,24*(1+len(self.sprite_list))+4))

    def _draw_common_sprite_picker(self,surf):
        r=self._picker_rect(); draw_rect(surf,r,(25,27,34),border=1,border_color=ACCENT,radius=4); items=['(없음)']+self.sprite_list
        for i,name in enumerate(items):
            ir=pygame.Rect(r.x+2,r.y+2+i*24,r.w-4,22)
            if ir.collidepoint(pygame.mouse.get_pos()): draw_rect(surf,ir,BG_HOVER,radius=2)
            if name==(self._current_sprite() or '(없음)'): draw_rect(surf,ir,BG_ACTIVE,radius=2)
            label=os.path.basename(name) if name.endswith('.anim.json') else name
            draw_text(surf,label,(ir.x+6,ir.y+3),TEXT,11)

    def _sprite_thumb(self,name,size=(20,20)):
        key=(name,size)
        if key in self._thumb_cache:return self._thumb_cache[key]
        try:
            spr=self.sprite_manager.get(name); th=pygame.transform.scale(spr.get_frame(0),size).convert_alpha(); self._thumb_cache[key]=th; return th
        except Exception:return None

    def _draw_header(self,surf,title):
        draw_rect(surf,self.rect,BG_PANEL,border=1); draw_rect(surf,pygame.Rect(self.rect.x,self.rect.y,self.rect.w,28),BG_PANEL2); draw_text(surf,title,(self.rect.x+8,self.rect.y+6),TEXT,13,bold=True)

    def draw(self,surf):
        title='Inspector'
        titles={self.MODE_INSTANCE:'Inspector · Instance',self.MODE_OBJECT:'Inspector · Object',self.MODE_SPRITE:'Inspector · Sprite',self.MODE_MUSIC:'Inspector · 음악',self.MODE_SCENE:'Inspector · Scene'}
        self._draw_header(surf,titles.get(self.mode,title))
        if self.mode==self.MODE_NONE:
            draw_text(surf,'오브젝트 / 인스턴스 / 스프라이트 / 음악 / 씬 선택',(self.rect.x+10,self.rect.y+50),TEXT_DIM,11); return
        if self.mode==self.MODE_SPRITE: self._draw_sprite(surf); return
        if self.mode==self.MODE_MUSIC: self._draw_music(surf); return
        if self.mode==self.MODE_SCENE: self._draw_scene(surf); return
        x=self.rect.x+12; w=max(80,self.rect.w-24); y=self.rect.y+36
        for label,key in [('이름','name'),('X','x'),('Y','y')]:
            dim=self.mode==self.MODE_OBJECT and key in ('x','y'); draw_text(surf,label,(x,y),TEXT_DIM if not dim else (80,80,90),11); self.fields[key].draw(surf) if not dim else None; y+=40
        draw_text(surf,'Sprite',(x,self.sprite_label_y),TEXT_DIM,11); cur=self._current_sprite() or '(없음)'; draw_rect(surf,self.sprite_btn_rect,INPUT_BG,border=1,border_color=ACCENT if self.sprite_picker_open else BORDER,radius=4)
        th=self._sprite_thumb(cur) if cur!='(없음)' else None
        if th: surf.blit(th,(self.sprite_btn_rect.x+4,self.sprite_btn_rect.y+3)); draw_text(surf,os.path.basename(cur),(self.sprite_btn_rect.x+28,self.sprite_btn_rect.y+5),TEXT,11)
        else: draw_text(surf,os.path.basename(cur),(self.sprite_btn_rect.x+8,self.sprite_btn_rect.y+5),TEXT_DIM if cur=='(없음)' else TEXT,11)
        draw_text(surf,'▼',(self.sprite_btn_rect.right-18,self.sprite_btn_rect.y+5),TEXT_DIM,10)
        y=self.sprite_btn_rect.bottom+10
        for label,key in [('Depth','depth'),('Width','width'),('Height','height')]:
            dim=self.mode==self.MODE_OBJECT and key=='depth'; draw_text(surf,label,(x,y),TEXT_DIM if not dim else (80,80,90),11); self.fields[key].rect=pygame.Rect(x,y+14,w,24); self.fields[key].draw(surf) if not dim else None; y+=40
        if self.mode==self.MODE_INSTANCE:
            self.fields['visible'].rect=pygame.Rect(x,y+14,20,20); draw_text(surf,'Visible',(x,y),TEXT_DIM,11); self.fields['visible'].draw(surf); draw_text(surf,'표시' if self.fields['visible'].value else '숨김',(x+28,y+14),TEXT,12)
        else: draw_text(surf,'Sprite는 Inspector에서 Object 기본값으로 지정',(x,y+8),TEXT_DIM,10)
        if self.sprite_picker_open:self._draw_common_sprite_picker(surf)

    def _draw_sprite(self,surf):
        x=self.rect.x+12; w=max(80,self.rect.w-24); info=self.sprite_info; name=os.path.basename(self.sprite_name or '')
        draw_text(surf,'이름',(x,self.rect.y+38),TEXT_DIM,11); draw_text(surf,name,(x,self.rect.y+56),TEXT,13,bold=True)
        draw_text(surf,'종류',(x,self.rect.y+84),TEXT_DIM,11); draw_text(surf,'애니메이션' if info.get('type')=='animation' else '단일 스프라이트',(x,self.rect.y+102),TEXT,12)
        # Preview without rebuilding a scaled surface every frame.
        try:
            if self.sprite_manager and self.sprite_name:
                spr=self.sprite_manager.get(self.sprite_name); frame=spr.get_frame(0); key=(self.sprite_name,frame.get_width(),frame.get_height())
                if key not in self._preview_cache:self._preview_cache[key]=pygame.transform.scale(frame,(96,96))
                prev=self._preview_cache[key]; box=pygame.Rect(self.rect.right-110,self.rect.y+46,96,96); draw_rect(surf,box,INPUT_BG,border=1); surf.blit(prev,prev.get_rect(center=box.center))
        except Exception: pass
        draw_text(surf,'원본',(x,self.rect.y+132),TEXT_DIM,11); draw_text(surf,str(info.get('source','')),(x,self.rect.y+150),TEXT,10)
        draw_text(surf,f"크기  {info.get('width',32)} × {info.get('height',32)}",(x,self.rect.y+178),TEXT_DIM,11)
        draw_text(surf,f"프레임  {info.get('frames',1)}개",(x,self.rect.y+202),TEXT_DIM,11)
        if info.get('type')=='animation':
            y=self.rect.y+228; draw_text(surf,'프레임 너비',(x,y),TEXT_DIM,11); self.fields['sprite_fw'].rect=pygame.Rect(x,y+15,w,24); self.fields['sprite_fw'].draw(surf); y+=43
            draw_text(surf,'프레임 높이',(x,y),TEXT_DIM,11); self.fields['sprite_fh'].rect=pygame.Rect(x,y+15,w,24); self.fields['sprite_fh'].draw(surf); y+=43
            draw_text(surf,'FPS',(x,y),TEXT_DIM,11); self.fields['sprite_fps'].rect=pygame.Rect(x,y+15,w,24); self.fields['sprite_fps'].draw(surf); y+=43
            draw_text(surf,'반복 재생',(x,y),TEXT_DIM,11); self.fields['sprite_loop'].rect=pygame.Rect(x,y+15,20,20); self.fields['sprite_loop'].draw(surf); draw_text(surf,'켜짐' if info.get('loop',True) else '꺼짐',(x+28,y+18),TEXT,11); y+=44
            self.sprite_save_btn.rect=pygame.Rect(x,y,w,28); self.sprite_save_btn.draw(surf)
        else:
            draw_text(surf,'애니메이션으로 만들려면 + → 스프라이트 애니메이션',(x,self.rect.bottom-36),TEXT_DIM,10)

    def _draw_music(self,surf):
        x=self.rect.x+12; w=max(80,self.rect.w-24); draw_text(surf,'파일',(x,self.rect.y+38),TEXT_DIM,11); draw_rect(surf,pygame.Rect(x,self.rect.y+54,w,40),INPUT_BG,border=1,radius=4); draw_text(surf,os.path.basename(self.music_name or ''),(x+8,self.rect.y+66),TEXT,12)
        draw_text(surf,'볼륨 (0~1)',(x,self.rect.y+108),TEXT_DIM,11); self.fields['music_volume'].rect=pygame.Rect(x,self.rect.y+126,w,24); self.fields['music_volume'].draw(surf)
        draw_text(surf,'반복 재생',(x,self.rect.y+160),TEXT_DIM,11); self.fields['music_loop'].rect=pygame.Rect(x,self.rect.y+178,20,20); self.fields['music_loop'].draw(surf); draw_text(surf,'켜짐' if self.music_loop else '꺼짐',(x+28,self.rect.y+181),TEXT,11)
        self.music_play_btn.rect=pygame.Rect(x,self.rect.y+216,(w-4)//2,28); self.music_stop_btn.rect=pygame.Rect(self.music_play_btn.rect.right+4,self.rect.y+216,w-(self.music_play_btn.rect.w+4),28); self.music_play_btn.draw(surf); self.music_stop_btn.draw(surf)

    def _draw_scene(self,surf):
        x=self.rect.x+12; w=max(80,self.rect.w-24); name=getattr(self.scene_data,'name','Scene')
        draw_text(surf,'씬 이름',(x,self.rect.y+38),TEXT_DIM,11); draw_text(surf,name,(x,self.rect.y+56),TEXT,13,bold=True)
        y=self.rect.y+84
        for label,key in [('너비','scene_width'),('높이','scene_height'),('배경 R','scene_bg_r'),('배경 G','scene_bg_g'),('배경 B','scene_bg_b'),('카메라 X','scene_camera_x'),('카메라 Y','scene_camera_y')]:
            draw_text(surf,label,(x,y),TEXT_DIM,11); self.fields[key].rect=pygame.Rect(x,y+14,w,24); self.fields[key].draw(surf); y+=40
        btn_w=max(80,(w-4)//2)
        self.scene_save_btn.rect=pygame.Rect(x,y,btn_w,28); self.scene_reload_btn.rect=pygame.Rect(x+btn_w+4,y,w-btn_w-4,28)
        self.scene_save_btn.draw(surf); self.scene_reload_btn.draw(surf)
        draw_text(surf,f"인스턴스 {len(getattr(self.scene_data,'instances',[]) or [])}개",(x,self.rect.bottom-22),TEXT_DIM,10)
