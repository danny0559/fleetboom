"""FleetBoom 2.1 — original BOOM gameplay plus cinematic gravity abilities."""
import math
import random
import time
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk, ImageOps

import spaceship14 as legacy


COLORS = {"BLACK_HOLE": "#ffbd72", "WORMHOLE": "#5ce8ec", "STAR": "#ffc76a"}
NAMES = {"RANDOM": "随机天体", "BLACK_HOLE": "黑洞", "WORMHOLE": "虫洞", "STAR": "恒星"}
ASSETS = Path(__file__).resolve().parent / "assets"


class ArtCache:
    """Share decoded artwork and pre-sized sprites between all six active bodies."""
    def __init__(self, master):
        self.master = master
        with Image.open(ASSETS / "blackhole-v2.png") as image:
            self.blackhole = image.convert("RGBA")
        self.frames = {}

    def hole(self, step):
        if step not in self.frames:
            width = 36 + step * 20
            image = self.blackhole.resize((width, round(width*2/3)), Image.Resampling.LANCZOS)
            self.frames[step] = ImageTk.PhotoImage(image, master=self.master)
        return self.frames[step]


class BoomShip(legacy.SciFiShip):
    """Original chase/weapon rules, with a brief flash and timed debris burst."""
    def update_motion(self, mx, my):
        radius, accumulator = self.catch_radius, self._catch_accum
        try:
            self.catch_radius = 0  # Capture is handled once per frame by the overlay.
            return super().update(mx, my)
        finally:
            self.catch_radius, self._catch_accum = radius, accumulator

    def explode(self):
        if self.exploding or not self.enable_explosions:
            return
        self.exploding = True
        self.state = "EXPLODE"
        self.explode_t = 0
        self._hide_ship()
        if callable(self.on_explode):
            self.on_explode()
        self.boom_debris = []
        for _ in range(24):
            a = random.uniform(0, math.tau)
            speed = random.uniform(70, 240)
            color = random.choice(("#fff0c4", "#ffb960", "#ff704a", "#8ee8ff"))
            item = self.canvas.create_line(self.x, self.y, self.x, self.y,
                                          fill=color, width=random.choice((1, 2)), capstyle=tk.ROUND)
            self.boom_debris.append((item, a, speed, color))
            self.explode_items.append(item)
        self.boom_rings = [self.canvas.create_oval(0, 0, 1, 1, outline=color, width=width)
                           for color, width in (("#754329", 7), ("#ffb76c", 2), ("#9aeaff", 1))]
        self.flash = self.canvas.create_oval(0, 0, 1, 1, fill="#fff5db", outline="")
        self.boom_word = self.canvas.create_text(self.x, self.y-34, text="BOOM!",
                            fill="#fff1c1", font=("Segoe UI", 16, "bold"))
        self.explode_items.extend(self.boom_rings + [self.flash, self.boom_word])

    def _update_explosion(self, dt):
        self.explode_t += dt
        t = self.explode_t
        if t >= .65:
            return False
        for item, a, speed, color in self.boom_debris:
            r = speed * t
            tail = max(0, r-12*(1-t/.65))
            self.canvas.coords(item, self.x+math.cos(a)*tail, self.y+math.sin(a)*tail,
                               self.x+math.cos(a)*r, self.y+math.sin(a)*r)
            self.canvas.itemconfig(item, fill=self.fade_color(color, min(1, t/.65)))
        for i, item in enumerate(self.boom_rings):
            r = (7+t*(120+i*45))
            self.canvas.coords(item, self.x-r, self.y-r, self.x+r, self.y+r)
        flash_r = max(0, 22*(1-t/.18))
        self.canvas.coords(self.flash, self.x-flash_r, self.y-flash_r, self.x+flash_r, self.y+flash_r)
        self.canvas.itemconfig(self.flash, state="normal" if t < .18 else "hidden")
        self.canvas.coords(self.boom_word, self.x, self.y-34-t*36)
        self.canvas.itemconfig(self.boom_word, state="normal" if t < .42 else "hidden")
        return True

    @staticmethod
    def fade_color(color, amount):
        rgb = [int(color[i:i+2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(a+(b-a)*amount):02x}" for a, b in zip(rgb, (9, 18, 32)))


class Celestial:
    def __init__(self, canvas, kind, x, y, destination=None, art=None):
        self.canvas, self.kind = canvas, kind
        self.x, self.y = x, y
        self.destination = destination
        self.age = 0.0
        self.life = {"BLACK_HOLE": 14, "WORMHOLE": 20, "STAR": 26}[kind]
        self.radius = {"BLACK_HOLE": 230, "WORMHOLE": 190, "STAR": 260}[kind]
        self.tag = f"celestial_{id(self)}"
        self.art = art
        self.sprite = canvas.create_image(x, y, tags=self.tag) if kind == "BLACK_HOLE" else None
        self.rings = [canvas.create_oval(0, 0, 1, 1, outline=COLORS[kind],
                      width=2 if i == 0 else 1, tags=self.tag) for i in range(4)]
        self.core = canvas.create_oval(0, 0, 1, 1, outline="", tags=self.tag)
        self.sparks = [canvas.create_oval(0, 0, 1, 1, fill=COLORS[kind],
                       outline="", tags=self.tag) for _ in range(18)]
        self.label = canvas.create_text(x, y + 66, fill=COLORS[kind],
                     font=("Microsoft YaHei UI", 9), tags=self.tag)
        self.flows = []
        if kind == "WORMHOLE":
            self.flows = [canvas.create_line(0, 0, 1, 1, fill=color, width=width,
                          smooth=True, tags=self.tag) for color, width in
                          (("#123c55", 8), ("#277c98", 4), ("#9cffff", 1.5))]
            self.exit_flows = [canvas.create_line(0, 0, 1, 1, fill=color, width=width,
                               smooth=True, tags=self.tag) for color, width in
                               (("#342548", 8), ("#8d559e", 4), ("#ffc5ff", 1.5))]
        if kind == "STAR":
            self.surface = [canvas.create_oval(0, 0, 1, 1, fill=color, outline="", tags=self.tag)
                            for color in ("#562b24", "#a34625", "#dd6529", "#ff9c40", "#ffd983", "#fff3c7")]
            self.flares = [canvas.create_line(0, 0, 1, 1, fill="#ffb34f", width=2,
                          smooth=True, tags=self.tag) for _ in range(5)]

    def destroy(self):
        self.canvas.delete(self.tag)

    def update(self, dt):
        self.age += dt
        if self.age >= self.life:
            self.destroy()
            return False
        c = self.canvas
        grow = min(1, self.age / .45, (self.life - self.age) / .8)
        pulse = 1 + .06 * math.sin(self.age * 3)
        if self.kind == "BLACK_HOLE" and self.art:
            self.frame = self.art.hole(max(0, min(16, round(16*grow))))
            c.itemconfig(self.sprite, image=self.frame)
            for item in self.rings + [self.core]:
                c.itemconfig(item, state="hidden")
            for i, spark in enumerate(self.sparks):
                a = i*math.tau/18 + self.age*(.7+i%3*.08)
                r = (78+i%3*22)*grow
                x = self.x+math.cos(a)*r
                y = self.y+math.sin(a)*r*.29+math.cos(a)*r*.16
                c.coords(spark, x-1, y-1, x+1, y+1)
            c.coords(self.label, self.x, self.y+116*grow)
            c.itemconfig(self.label, text=f"黑洞  ·  {math.ceil(self.life-self.age)}s")
            return True
        centers = [(self.x, self.y)]
        if self.destination:
            centers.append(self.destination)
        # A portal pair shares one lifetime and one set of canvas items.
        if len(centers) == 2 and not hasattr(self, "exit_items"):
            self.exit_items = [c.create_oval(0, 0, 1, 1, outline="#f5a7ff",
                               width=2, tags=self.tag) for _ in range(3)]
            self.exit_label = c.create_text(*self.destination, text="出口", fill="#f5a7ff",
                                           font=("Microsoft YaHei UI", 9), tags=self.tag)
        for i, ring in enumerate(self.rings):
            r = (34 + i * 10) * grow * pulse
            flatten = .36 if self.kind in ("STAR", "BLACK_HOLE") and i > 0 else 1
            c.coords(ring, self.x-r, self.y-r*flatten, self.x+r, self.y+r*flatten)
        r = (20 if self.kind == "STAR" else 17) * grow
        c.coords(self.core, self.x-r, self.y-r, self.x+r, self.y+r)
        c.itemconfig(self.core, fill="#fff1bf" if self.kind == "STAR" else "#080c20")
        for i, spark in enumerate(self.sparks):
            a = i * math.tau / 18 + self.age * (1.3 if self.kind == "BLACK_HOLE" else .6)
            r = (38 + (i % 3) * 9) * grow
            flat = .38 if self.kind != "WORMHOLE" else 1
            x, y = self.x + math.cos(a)*r, self.y + math.sin(a)*r*flat
            c.coords(spark, x-1.6, y-1.6, x+1.6, y+1.6)
        c.itemconfig(self.label, text=f"{NAMES[self.kind]}  {math.ceil(self.life-self.age)}s")
        if self.destination:
            x, y = self.destination
            for i, item in enumerate(self.exit_items):
                r = (28 + i*10) * grow * pulse
                c.coords(item, x-r, y-r, x+r, y+r)
            c.coords(self.exit_label, x, y+60)
            for items, center, sign in ((self.flows, (self.x, self.y), 1),
                                        (self.exit_flows, self.destination, -1)):
                coords = []
                for j in range(100):
                    u = j/99
                    a = u*math.tau*2.6 + self.age*sign*1.6
                    radius = (7+u*43)*grow
                    coords.extend((center[0]+math.cos(a)*radius, center[1]+math.sin(a)*radius*.78))
                for line in items:
                    c.coords(line, *coords)
        if self.kind == "STAR":
            for i, item in enumerate(self.surface):
                radius = (42-i*4.1)*grow*pulse
                c.coords(item, self.x-radius, self.y-radius, self.x+radius, self.y+radius)
            for i, item in enumerate(self.flares):
                a = i*math.tau/5+self.age*.13
                coords = []
                for j in range(15):
                    u = j/14
                    r = (31+math.sin(u*math.pi)*(10+5*math.sin(self.age+i)))*grow
                    angle = a+u*.35
                    coords.extend((self.x+math.cos(angle)*r, self.y+math.sin(angle)*r))
                c.coords(item, *coords)
            c.coords(self.label, self.x, self.y+78)
        return True


class GravityOverlay(legacy.TransparentOverlay):
    def __init__(self, win, config, on_stop_callback=None):
        self.celestials = []
        self.tool = "RANDOM"
        self.absorbed = self.transported = 0
        self.last_spawn = -10.0
        self.art = ArtCache(win)
        super().__init__(win, config, on_stop_callback)
        for i, ship in enumerate(self.ships):
            style, x, y = ship.style, ship.x, ship.y
            ship.destroy()
            self.ships[i] = self.make_ship(style)
            self.ships[i].x, self.ships[i].y = x, y
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
        for ship in self.ships:
            self.paint_ship(ship)
        self.refresh_hud()

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

    def make_ship(self, style=None):
        ship = BoomShip(self.canvas, self.w, self.h, style=style,
                        enable_bullets=self.enable_bullets, enable_explosions=self.enable_explosions,
                        on_explode=self._on_ship_explode, ship_scale_getter=self.get_ship_scale)
        ship.set_difficulty(self.level)
        self.paint_ship(ship)
        return ship

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

    def refresh_hud(self):
        if self.counter_text:
            self.canvas.itemconfig(self.counter_text, text=
                f"FLEET BOOM   爆炸 {self.explode_count}   Lv.{self.level}   /   {NAMES[self.tool]}   ·   吞噬 {self.absorbed}   ·   传送 {self.transported}   ·   天体 {len(self.celestials)}/6")

    def _on_ship_explode(self):
        super()._on_ship_explode()
        self.refresh_hud()

    def _apply_level(self, level):
        super()._apply_level(level)
        self.refresh_hud()

    def spawn_event(self, event):
        self.spawn(self.tool, event.x, event.y)

    def spawn(self, kind, x, y):
        now = time.monotonic()
        if now - self.last_spawn < .35:
            return
        self.last_spawn = now
        if kind == "RANDOM":
            kind = random.choice(tuple(COLORS))
        x, y = max(70, min(self.w-70, x)), max(130, min(self.h-80, y))
        dest = None
        if kind == "WORMHOLE":
            # Select the distant half of the screen, so every pair produces a useful jump.
            dx = self.w*.78 if x < self.w/2 else self.w*.22
            dest = (dx, random.uniform(150, max(151, self.h-100)))
        if len(self.celestials) >= 6:
            self.celestials.pop(0).destroy()
        self.celestials.append(Celestial(self.canvas, kind, x, y, dest, self.art))
        self.refresh_hud()

    def clear_space(self):
        for body in self.celestials:
            body.destroy()
        self.celestials.clear()
        for ship in self.ships:
            ship.orbit_body = None
            ship.gravity_body = None
        self.refresh_hud()

    def affect_ship(self, ship, dt):
        """Nearest field owns a ship; portal cooldown prevents immediate return jumps."""
        now = time.monotonic()
        if now < getattr(ship, "portal_until", 0):
            return False
        candidates = []
        for body in self.celestials:
            centers = [(body.x, body.y)] + ([body.destination] if body.destination else [])
            for center in centers:
                d = math.hypot(ship.x-center[0], ship.y-center[1])
                if d < body.radius:
                    candidates.append((d/body.radius, d, body, center))
        if not candidates:
            ship.orbit_body = None
            ship.gravity_body = None
            return False
        _, d, body, center = min(candidates, key=lambda value: value[0])
        cx, cy = center
        if body.kind == "STAR":
            if getattr(ship, "orbit_body", None) is not body:
                ship.orbit_body = body
                ship.orbit_angle = math.atan2((ship.y-cy)/.38, ship.x-cx)
                ship.orbit_radius = max(85, min(210, math.hypot(ship.x-cx, (ship.y-cy)/.38)))
            ship.orbit_angle += dt * (95 / ship.orbit_radius)
            a, r = ship.orbit_angle, ship.orbit_radius
            target_x, target_y = cx+math.cos(a)*r, cy+math.sin(a)*r*.38
            blend = 1-math.exp(-dt*3)
            nx, ny = ship.x+(target_x-ship.x)*blend, ship.y+(target_y-ship.y)*blend
        else:
            a = math.atan2(ship.y-cy, ship.x-cx)
            if body.kind == "BLACK_HOLE":
                if d < 43:
                    return "absorbed"
                a += dt * (1.5 + 60/max(d, 25))
                d = max(0, d - dt*(65 + 800/max(d, 20)))
            else:
                if d < 29:
                    target = body.destination if center == (body.x, body.y) else (body.x, body.y)
                    ship.x, ship.y = target[0]+65, target[1]
                    ship.vx, ship.vy = 150, 0
                    ship.set_new_target()
                    ship.portal_until = now + 1.8
                    ship.orbit_body = None
                    self.transported += 1
                    ship.angle = ship.v_ang = 0
                    ship.flame_ang = math.pi
                    ship._last_t = time.time()
                    ship.draw(150, dt)
                    return True
                d = max(0, d-dt*145)
            nx, ny = cx+math.cos(a)*d, cy+math.sin(a)*d
        ship.vx, ship.vy = (nx-ship.x)/dt, (ny-ship.y)/dt
        ship.x, ship.y = nx, ny
        ship.angle = math.atan2(ship.vy, ship.vx)
        ship.v_ang, ship.flame_ang = ship.angle, ship.angle+math.pi
        ship.phase += dt*8
        ship._last_t = time.time()
        ship.draw(math.hypot(ship.vx, ship.vy), dt)
        return True

    def advance_ships(self, dt, mx, my):
        for i, ship in enumerate(self.ships):
            if ship.exploding:
                if not ship._update_explosion(dt):
                    self._respawn_ship(i)
                continue
            # Hover capture remains active even while a field is steering the ship.
            catch_r = ship.catch_radius*(.9+.35*ship._ship_scale())
            if self.enable_explosions and math.hypot(mx-ship.x, my-ship.y) < catch_r:
                ship._catch_accum += dt
                if ship._catch_accum >= ship.catch_hold:
                    ship.explode()
                    continue
            else:
                ship._catch_accum = 0
            result = self.affect_ship(ship, dt)
            if result == "absorbed":
                self.absorbed += 1
                if self.enable_explosions:
                    ship.explode()
                else:
                    self._respawn_ship(i)
            elif not result:
                if isinstance(ship, BoomShip):
                    ship.update_motion(mx, my)
                else:
                    ship.update(mx, my)
            if self.enable_bullets:
                ship.try_shoot(mx, my, dt, self.bullets)
        self.bullets = [b for b in self.bullets if b.update(dt, self.w, self.h)]

    def animate(self):
        if not self._running:
            return
        now = time.time()
        dt = max(.001, min(.05, now-self._last_t))
        self._last_t = now
        self.celestials = [body for body in self.celestials if body.update(dt)]
        for planet in self.planets:
            planet.update(dt)
        self.advance_ships(dt, self.win.winfo_pointerx()-self.win.winfo_rootx(),
                           self.win.winfo_pointery()-self.win.winfo_rooty())
        self.refresh_hud()
        self.canvas.tag_raise(self.exit_hint)
        if self.counter_text:
            self.canvas.tag_raise(self.counter_text)
        self.win.after(16, self.animate)


class LauncherUI(legacy.LauncherUI):
    def __init__(self):
        super().__init__()
        self.root.title("FleetBoom 2.1 · BOOM 回归")
        self.mode_var.set("game")
        self.transparent_bg_var.set(False)
        self.ships_var.set("24")
        self.planets_var.set("3")
        self.ship_scale_var.set(1.35)
        self._refresh_mode_ui()
        self.theme(self.root)

    def _build(self):
        super()._build()
        frame = self.root.winfo_children()[0]
        for child in frame.winfo_children():
            if isinstance(child, tk.LabelFrame) and child.cget("text") == "模式":
                for radio in child.winfo_children():
                    if isinstance(radio, tk.Radiobutton):
                        radio.config(text="BOOM 游戏（追击 / 爆炸 / 子弹 / 天体）" if radio.cget("value") == "game"
                                     else "星海屏保（无爆炸，可放置天体）")
            if isinstance(child, tk.Checkbutton):
                child.config(text="透明桌面背景（默认显示深蓝星海）")
            if isinstance(child, tk.Label) and "版本" in child.cget("text"):
                child.config(text="段小油  |  2.1 · BOOM + 星际引力")
        tk.Label(frame, text="追上飞船 → BOOM！黑洞吞噬也计入击败数\n左键生成天体；1 / 2 / 3 指定，0 随机；右键清场\n恒星横向公转 · 虫洞双向传送",
                 justify="left").grid(row=8, column=0, columnspan=2, pady=(10, 0), sticky="w")

    @staticmethod
    def theme(widget):
        options = widget.keys()
        for key, value in (("background", "#101d33"), ("foreground", "#d8e8f6"),
                           ("activebackground", "#263f5c"), ("activeforeground", "#ffffff"),
                           ("selectcolor", "#263f5c"), ("insertbackground", "#8ae9ff"),
                           ("troughcolor", "#233550")):
            if key in options:
                widget.config(**{key: value})
        if "font" in options:
            widget.config(font=("Microsoft YaHei UI", 10))
        for child in widget.winfo_children():
            LauncherUI.theme(child)

    def start(self):
        if self.overlay is not None:
            return
        config = dict(mode=self.mode_var.get(),
                      ships=self._safe_int(self.ships_var.get(), 24, 1, 80),
                      planets=self._safe_int(self.planets_var.get(), 3, 0, 80),
                      level=1 if self.auto_var.get() else self.level_var.get(),
                      auto_level=self.auto_var.get() and self.mode_var.get() == "game",
                      level_step=self._safe_int(self.level_step_var.get(), 10, 1, 9999),
                      transparent_bg=self.transparent_bg_var.get(),
                      ship_scale=self.ship_scale_var.get(), planet_scale=self.planet_scale_var.get())
        self.root.withdraw()
        self.overlay = GravityOverlay(tk.Toplevel(self.root), config, self._on_overlay_stop)
        self._open_control_panel(config)

    def _open_control_panel(self, config):
        cp = tk.Toplevel(self.root)
        self.control_panel = cp
        cp.title("星际引力 · 控制台")
        cp.attributes("-topmost", True)
        cp.geometry("+40+110")
        tk.Label(cp, text="STELLAR / 星际引力", font=("Segoe UI", 14, "bold")).pack(padx=18, pady=12)
        tools = tk.Frame(cp)
        tools.pack(padx=14)
        for i, kind in enumerate(NAMES):
            tk.Button(tools, text=NAMES[kind], width=9,
                      command=lambda k=kind: self.overlay.set_tool(k)).grid(row=i//2, column=i%2, padx=3, pady=3)
        tk.Label(cp, text="选择天体后，在星海中点击放置\n透明处可按空格在指针位置放置\n天体限时存在，最多同时 6 个", justify="left").pack(padx=14, pady=10)
        self.live_transparent_var = tk.BooleanVar(value=self.overlay.transparent_bg)
        tk.Checkbutton(cp, text="透明桌面背景", variable=self.live_transparent_var,
                       command=self._toggle_live_bg).pack()
        self.live_ship_scale_var = tk.DoubleVar(value=self.overlay.ship_scale)
        self.live_planet_scale_var = tk.DoubleVar(value=self.overlay.planet_scale)
        tk.Scale(cp, label="舰船大小", from_=.3, to=2.5, resolution=.05,
                 orient="horizontal", variable=self.live_ship_scale_var,
                 command=lambda v: self._apply_live_scales(), length=240).pack(padx=14)
        if config["mode"] == "game":
            self.live_auto_var = tk.BooleanVar(value=self.overlay.auto_level)
            self.live_level_var = tk.IntVar(value=self.overlay.level)
            self.live_step_var = tk.IntVar(value=self.overlay.level_step)
            tk.Checkbutton(cp, text="自动升级", variable=self.live_auto_var,
                           command=self._toggle_live_auto).pack()
            game = tk.Frame(cp)
            game.pack(padx=14, pady=8)
            tk.Label(game, text="等级").grid(row=0, column=0)
            self.live_level_spin = tk.Spinbox(game, from_=1, to=11, width=6,
                                            textvariable=self.live_level_var, command=self._apply_live_level)
            self.live_level_spin.grid(row=0, column=1)
            tk.Button(game, text="应用", command=self._apply_live_level).grid(row=0, column=2)
            tk.Label(game, text="升级击败数").grid(row=1, column=0)
            tk.Spinbox(game, from_=1, to=9999, width=6, textvariable=self.live_step_var).grid(row=1, column=1)
            tk.Button(game, text="应用", command=self._apply_live_step).grid(row=1, column=2)
            self._sync_live_level_widgets()
        codex = tk.Frame(cp)
        codex.pack(pady=4)
        tk.Button(codex, text="飞船图鉴", command=self._open_ship_codex).pack(side="left")
        tk.Button(codex, text="子弹图鉴", command=self._open_bullet_codex).pack(side="left")
        tk.Button(cp, text="清除天体", command=lambda: self.overlay.clear_space()).pack(fill="x", padx=18, pady=8)
        tk.Button(cp, text="结束 / 返回设置", command=self.stop).pack(fill="x", padx=18, pady=(0, 14))
        cp.protocol("WM_DELETE_WINDOW", cp.withdraw)
        self.theme(cp)


if __name__ == "__main__":
    app = LauncherUI()
    if "--smoke-test" in sys.argv:
        app.root.withdraw()
        try:
            app.start()
            app.overlay.win.withdraw()
            app.control_panel.withdraw()
            for kind, x in (("BLACK_HOLE", 420), ("STAR", 700), ("WORMHOLE", 1000)):
                app.overlay.last_spawn = -10
                app.overlay.spawn(kind, x, 400)
                assert app.overlay.celestials[-1].update(.5)
            ship = app.overlay.ships[0]
            ship.explode()
            assert app.overlay.explode_count == 1 and ship.explode_items
            app.root.update_idletasks()
            app.stop()
        finally:
            app.root.destroy()
    else:
        app.run()
