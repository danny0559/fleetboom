"""Fullscreen canvas, starfield background, scaling and world lifecycle."""
import math
import random
import time
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
from .config import KEY, ASSETS
from .assets import ArtCache
from .planets import StyledPlanet
from .ships import SciFiShip


class World:
    def __init__(self, overlay_win, config: dict, on_stop_callback=None):
        self.celestials = []
        self.tool = "RANDOM"
        self.absorbed = self.transported = 0
        self.last_spawn = -10.0
        self.art = ArtCache(overlay_win)
        self.win = overlay_win
        self.on_stop_callback = on_stop_callback

        self.w = overlay_win.winfo_screenwidth()
        self.h = overlay_win.winfo_screenheight()

        self.mode = config["mode"]
        self.num_ships = int(config["ships"])
        self.num_planets = int(config["planets"])
        self.auto_level = bool(config.get("auto_level", False))
        self.level = int(config.get("level", 1))
        self.speed_multiplier = max(.25, min(3.0, float(config.get("speed_multiplier", 1))))

        self.level_step = max(1, int(config.get("level_step", 10)))
        self.transparent_bg = bool(config.get("transparent_bg", True))

        # ✅ 新增：尺寸缩放（默认 1.0）
        self.ship_scale = float(config.get("ship_scale", 1.0))
        self.planet_scale = float(config.get("planet_scale", 1.0))

        self.enable_bullets = (self.mode == "game")
        self.enable_explosions = (self.mode == "game")

        # ✅ 不透明背景：深灰纵向渐变 + 斜向雾化条纹 + 稀疏星尘（无网格）
        self.grad_top = (52, 56, 64)
        self.grad_bottom = (12, 13, 16)
        self._bg_items = []

        bg = KEY if self.transparent_bg else self._rgb_to_hex(*self.grad_top)
        self.canvas = tk.Canvas(overlay_win, width=self.w, height=self.h, bg=bg, highlightthickness=0)
        self.canvas.pack()

        try:
            if self.transparent_bg:
                overlay_win.wm_attributes("-transparentcolor", KEY)
            else:
                overlay_win.wm_attributes("-transparentcolor", "")
        except Exception:
            pass

        overlay_win.wm_attributes("-topmost", True)
        overlay_win.overrideredirect(True)
        overlay_win.geometry(f"{self.w}x{self.h}+0+0")

        if not self.transparent_bg:
            self._draw_gradient_bg()

        self.explode_count = 0
        self.counter_text = None
        if self.mode == "game":
            self.counter_text = self.canvas.create_text(
                18, 18, anchor="nw",
                text=f"爆炸: 0   等级: 1   升级阈值: {self.level_step}",
                fill="#EAF2FF",
                font=("Segoe UI", 12, "bold")
            )

        # ✅ ESC 退出提示（两种模式都显示）
        hint_text = "按 ESC 退出"
        self.exit_hint = self.canvas.create_text(
            18, 46,
            anchor="nw",
            text=hint_text,
            fill="#EAF2FF",
            font=("Segoe UI", 11, "bold")
        )
        self.canvas.tag_raise(self.exit_hint)

        self.center_fx_items = []
        # ✅ 星球：样式行星 + 永久缓慢随机飘移
        self.planets = [StyledPlanet(self.canvas, self.w, self.h, scale_getter=self.get_planet_scale)
                        for _ in range(self.num_planets)]

        bag = []
        style_list = []
        for _ in range(self.num_ships):
            if not bag:
                bag = SciFiShip.STYLES[:]
                random.shuffle(bag)
                if style_list and bag[-1] == style_list[-1]:
                    bag[0], bag[-1] = bag[-1], bag[0]
            style_list.append(bag.pop())

        self.ships = [self.make_ship(st) for st in style_list]
        self.bullets = []

        self._apply_level(self.level)

        self._last_t = time.time()
        self._running = True

        # ✅ 键盘退出
        try:
            self.win.focus_force()
        except Exception:
            pass
        try:
            self.win.bind("<Escape>", lambda e: self.stop())
            self.win.bind("<Control-Shift-q>", lambda e: self.stop())
            self.win.bind("<Control-Shift-Q>", lambda e: self.stop())
            self.win.bind_all("<Escape>", lambda e: self.stop())
            self.win.bind_all("<Control-Shift-q>", lambda e: self.stop())
            self.win.bind_all("<Control-Shift-Q>", lambda e: self.stop())
        except Exception:
            pass

        self.animate()
        self.canvas.itemconfig(self.exit_hint, text="左键：随机天体  ·  1 黑洞 / 2 虫洞 / 3 恒星 / 0 随机  ·  右键清场  ·  ESC 返回")
        self.canvas.bind("<Button-1>", self.spawn_event)
        self.canvas.bind("<Button-3>", lambda e: self.clear_space())
        for key, kind in zip("0123", ("RANDOM", "BLACK_HOLE", "WORMHOLE", "STAR")):
            self.win.bind(key, lambda e, k=kind: self.set_tool(k))
        self.win.bind("c", lambda e: self.clear_space())
        self.win.bind("C", lambda e: self.clear_space())
        self.win.bind("<space>", lambda e: self.spawn(self.tool,
                      self.win.winfo_pointerx()-self.win.winfo_rootx(),
                      self.win.winfo_pointery()-self.win.winfo_rooty()))
        self.refresh_hud()

    def get_ship_scale(self):
        return self.ship_scale

    def get_planet_scale(self):
        return self.planet_scale

    def set_scales(self, ship_scale=None, planet_scale=None):
        if ship_scale is not None:
            try:
                self.ship_scale = max(0.3, min(2.5, float(ship_scale)))
            except Exception:
                pass
        if planet_scale is not None:
            try:
                self.planet_scale = max(0.3, min(2.5, float(planet_scale)))
            except Exception:
                pass

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f"#{r:02x}{g:02x}{b:02x}"

    def _bg_send_to_back(self):
        for it in self._bg_items:
            try:
                self.canvas.tag_lower(it)
            except Exception:
                pass

    def _clear_gradient_bg(self):
        for it in self._bg_items:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        self._bg_items.clear()

    def set_background_transparent(self, transparent: bool):
        self.transparent_bg = bool(transparent)
        try:
            if self.transparent_bg:
                self._clear_gradient_bg()
                self.canvas.config(bg=KEY)
                self.win.wm_attributes("-transparentcolor", KEY)
            else:
                self.win.wm_attributes("-transparentcolor", "")
                self.canvas.config(bg=self._rgb_to_hex(*self.grad_top))
                self._draw_gradient_bg()
        except Exception:
            pass

        try:
            self.canvas.tag_raise(self.exit_hint)
        except Exception:
            pass

    def stop(self):
        if not self._running:
            return
        self._running = False
        try:
            for s in self.ships:
                s.destroy()
        except Exception:
            pass
        try:
            for b in self.bullets:
                b.destroy()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
        if callable(self.on_stop_callback):
            try:
                self.on_stop_callback()
            except Exception:
                pass

    def paint_ship(self, ship):
        ship.col, fill = random.choice([
            ("#8ae9ff", "#173c59"), ("#d1b2ff", "#352b55"),
            ("#ffd992", "#533c29"), ("#9ff5cd", "#214b44")])
        self.canvas.itemconfig(ship.hull, fill=fill, outline=ship.col, width=1.5)
        for item in ship.detail_lines:
            self.canvas.itemconfig(item, fill=ship.col)
        for item in (ship.engine_center, ship.engine_left, ship.engine_right):
            self.canvas.itemconfig(item, fill="#dbfaff", outline="#5ee3ff")

    def _respawn_ship(self, idx):
        self.ships[idx].destroy()
        self.ships[idx] = self.make_ship()
        # Reappear away from the current singularity instead of feeding it forever.
        s = self.ships[idx]
        s.x = random.uniform(80, self.w-80)
        s.y = random.uniform(100, self.h-80)
        s.portal_until = time.monotonic() + 1.5

    def _draw_gradient_bg(self):
        self._clear_gradient_bg()
        c = self.canvas
        self.grad_top, self.grad_bottom = (9, 18, 40), (3, 7, 19)
        with Image.open(ASSETS / "starfield-v2.png") as image:
            self.background_image = ImageTk.PhotoImage(
                ImageOps.fit(image.convert("RGB"), (self.w, self.h), method=Image.Resampling.LANCZOS),
                master=self.win)
        self._bg_items.append(c.create_image(0, 0, image=self.background_image, anchor="nw"))
        self._bg_send_to_back()

    def set_tool(self, kind):
        self.tool = kind
        self.refresh_hud()
        self.win.focus_force()

    def clear_space(self):
        for body in self.celestials:
            body.destroy()
        self.celestials.clear()
        for ship in self.ships:
            ship.orbit_body = None
            ship.gravity_body = None
        self.refresh_hud()

    def _apply_level(self, level):
        self.level = max(1, min(11, int(level)))
        for ship in self.ships:
            ship.set_difficulty(self.level, self.speed_multiplier)
        self.refresh_hud()
