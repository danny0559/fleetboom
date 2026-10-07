"""Ship silhouettes, movement, weapons and BOOM animation."""
import math
import random
import time
import tkinter as tk
from .projectiles import Bullet


class SciFiShip:
    STYLES = [
        "SPEAR",
        "TWIN_ENGINE",
        "DIAMOND_DELTA",
        "BOOMERANG",
        "STEALTH",
        "RIB_CAGE",
        "THRUSTER_FINS",
    ]

    # ✅ 子弹速度整体更舒服（慢一点）；且难度不影响子弹速度/life/dist
    BULLET_PROFILES = [
        ("LASER",  ["#66B3FF", "#EAF2FF"], 760.0, 0.14, 260.0),
        ("PLASMA", ["#FFD966", "#FFB86B"], 600.0, 0.22, 240.0),
        ("SPARK",  ["#FF6B6B", "#FFD966"], 690.0, 0.18, 210.0),
        ("WAVE",   ["#B388FF", "#A78BFA"], 580.0, 0.20, 250.0),
        ("SHARD",  ["#ECFFF6", "#EAF2FF"], 720.0, 0.16, 220.0),
    ]

    def __init__(self, canvas, w, h, style=None,
                 enable_bullets=True, enable_explosions=True,
                 on_explode=None,
                 ship_scale_getter=None):
        self.canvas = canvas
        self.w = w
        self.h = h
        self.enable_bullets = enable_bullets
        self.enable_explosions = enable_explosions
        self.on_explode = on_explode
        self.ship_scale_getter = ship_scale_getter  # callable -> float

        self.x = random.randint(180, w - 180)
        self.y = random.randint(180, h - 180)
        self.tx = self.x
        self.ty = self.y

        # ✅ 同等级速度尽量统一：基础值不再随机大幅波动
        self.speed = 0.62 + random.uniform(-0.03, 0.03)
        self.flee_mult = 2.65 + random.uniform(-0.06, 0.06)

        self.flee_trigger = 52.0
        self.escape_dist = 88.0
        self.catch_radius = 13.0
        self.catch_hold = 0.06
        self._catch_accum = 0.0

        self.turn_wander = 0.028
        self.turn_flee = 0.037
        self.vmax_wander = 260.0
        self.vmax_flee = 460.0

        self._base_speed = self.speed
        self._base_flee_mult = self.flee_mult

        kind, palette, bspd, cd, trig = random.choice(self.BULLET_PROFILES)
        self.bullet_kind = kind
        self.bullet_palette = palette
        self.bullet_speed = bspd
        self.shoot_cooldown = cd
        self.shoot_trigger = trig
        self._shoot_timer = random.uniform(0.0, self.shoot_cooldown)

        # ✅ 固定子弹 life/dist：不随难度变化
        self.bullet_life = 0.20
        self.bullet_max_dist = 330.0

        self.state = "IDLE"
        self.idle_timer = random.randint(35, 200)
        self.coast_timer = 0.0

        self.angle = random.random() * math.tau
        self.col = random.choice(["#EAF2FF", "#F3ECFF", "#ECFFF6", "#FFF4E6", "#EEF2FF"])
        self.flame_col = random.choice(["#66B3FF", "#FFD966"])

        if style is not None and style not in self.STYLES:
            style = None
        self.style = style if style is not None else random.choice(self.STYLES)
        self.is_twin = (self.style == "TWIN_ENGINE")

        self.phase = random.random() * math.tau
        self._last_t = time.time()

        self.vx = 0.0
        self.vy = 0.0
        self.v_ang = self.angle
        self.flame_ang = self.v_ang + math.pi
        self.slip = 0.0

        self.exploding = False
        self.explode_t = 0.0
        self.explode_items = []

        self.hull = canvas.create_polygon(0, 0, 0, 0, 0, 0,
                                          outline=self.col, fill="", width=1, joinstyle=tk.ROUND)

        self.detail_lines = [
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
        ]

        self.engine_center = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")
        self.engine_left = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")
        self.engine_right = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")

        self.flame_c = [
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(3, 6)),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(1, 8)),
        ]
        self.flame_l = [
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(3, 6)),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(1, 8)),
        ]
        self.flame_r = [
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(3, 6)),
            canvas.create_line(0, 0, 0, 0, fill=self.flame_col, width=1, smooth=True, dash=(1, 8)),
        ]

        self._apply_style_visibility()
        self.draw(current_speed=0.0, dt=1 / 60)

    def _ship_scale(self):
        if callable(self.ship_scale_getter):
            try:
                return max(0.3, min(2.5, float(self.ship_scale_getter())))
            except Exception:
                return 1.0
        return 1.0

    def set_difficulty(self, level: int, speed_multiplier=1.0):
        level = max(1, min(11, int(level)))
        t = (level - 1) / 10.0

        # ✅ Lv.11 特别档：保证“追不上”
        extra = 0.0
        if level == 11:
            extra = 0.85

        self.speed = self._base_speed * (1.0 + 1.25 * t + extra)
        self.flee_mult = self._base_flee_mult * (1.0 + 1.10 * t + extra)

        self.flee_trigger = 52.0 + 92.0 * t + 55.0 * extra
        self.escape_dist = 88.0 + 110.0 * t + 95.0 * extra

        self.turn_wander = 0.028 + 0.034 * t + 0.030 * extra
        self.turn_flee = 0.038 + 0.048 * t + 0.040 * extra

        self.vmax_wander = 260.0 + 320.0 * t + 260.0 * extra
        self.vmax_flee = 480.0 + 720.0 * t + 560.0 * extra

        multiplier = max(.25, min(3.0, float(speed_multiplier)))
        self.speed *= multiplier
        self.vmax_wander *= multiplier
        self.vmax_flee *= multiplier

        self.catch_radius = 13.0

    def set_bullet_limits(self, bullet_life: float, bullet_dist: float):
        self.bullet_life = max(0.08, float(bullet_life))
        self.bullet_max_dist = max(120.0, float(bullet_dist))

    @staticmethod
    def _angle_diff(a, b):
        return (b - a + math.pi) % (2 * math.pi) - math.pi

    @staticmethod
    def _lerp_angle(a, b, t):
        return a + SciFiShip._angle_diff(a, b) * t

    def _rot_ship(self, px, py):
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        return (px * ca - py * sa + self.x, px * sa + py * ca + self.y)

    def _set_poly(self, item, pts):
        coords = []
        for px, py in pts:
            rx, ry = self._rot_ship(px, py)
            coords.extend([rx, ry])
        self.canvas.coords(item, *coords)

    def _set_line(self, item, pts):
        coords = []
        for px, py in pts:
            rx, ry = self._rot_ship(px, py)
            coords.extend([rx, ry])
        self.canvas.coords(item, *coords)

    def _draw_rotated_ellipse_outline(self, item, cx, cy, a, b, ang, segments=14):
        pts = []
        ca, sa = math.cos(ang), math.sin(ang)
        for i in range(segments + 1):
            tt = (i / segments) * 2 * math.pi
            px = a * math.cos(tt)
            py = b * math.sin(tt)
            rx = px * ca - py * sa + cx
            ry = px * sa + py * ca + cy
            pts.extend([rx, ry])
        self.canvas.coords(item, *pts)

    def _apply_drag(self, dt, strong=False):
        k = 4.0 if strong else 2.4
        decay = math.exp(-k * dt)
        self.vx *= decay
        self.vy *= decay

    def _apply_style_visibility(self):
        self.canvas.itemconfig(self.engine_center, state=("hidden" if self.is_twin else "normal"))
        self.canvas.itemconfig(self.engine_left, state=("normal" if self.is_twin else "hidden"))
        self.canvas.itemconfig(self.engine_right, state=("normal" if self.is_twin else "hidden"))

        for it in self.flame_c:
            self.canvas.itemconfig(it, state=("hidden" if self.is_twin else "normal"))
        for it in self.flame_l:
            self.canvas.itemconfig(it, state=("normal" if self.is_twin else "hidden"))
        for it in self.flame_r:
            self.canvas.itemconfig(it, state=("normal" if self.is_twin else "hidden"))

    def _shape_for_style(self, L, W):
        s = self.style
        lines = []

        eng_center = (-L * 1.15, 0.0)
        eng_left = (-L * 1.15, -W * 0.45)
        eng_right = (-L * 1.15, W * 0.45)

        if s == "SPEAR":
            hull = [
                (L * 1.40, 0.00),
                (L * 0.30, -W * 0.20),
                (-L * 0.50, -W * 0.55),
                (-L * 1.05, -W * 0.25),
                (-L * 1.25, 0.00),
                (-L * 1.05, W * 0.25),
                (-L * 0.50, W * 0.55),
                (L * 0.30, W * 0.20),
            ]
            lines += [
                [(-L * 0.80, 0), (L * 1.10, 0)],
                [(-L * 0.20, -W * 0.15), (-L * 0.60, -W * 0.40)],
                [(-L * 0.20, W * 0.15), (-L * 0.60, W * 0.40)],
            ]
            mode = "center"

        elif s == "TWIN_ENGINE":
            hull = [
                (L * 0.85, 0.00),
                (L * 0.40, -W * 0.40),
                (L * 0.10, -W * 0.40),
                (-L * 0.40, -W * 0.85),
                (-L * 0.80, -W * 0.85),
                (-L * 1.25, -W * 0.60),
                (-L * 1.00, -W * 0.20),
                (-L * 1.15, 0.00),
                (-L * 1.00, W * 0.20),
                (-L * 1.25, W * 0.60),
                (-L * 0.80, W * 0.85),
                (-L * 0.40, W * 0.85),
                (L * 0.10, W * 0.40),
                (L * 0.40, W * 0.40),
            ]
            lines += [
                [(-L * 0.80, -W * 0.60), (-L * 1.20, -W * 0.60)],
                [(-L * 0.80, W * 0.60), (-L * 1.20, W * 0.60)],
                [(-L * 0.30, -W * 0.30), (L * 0.50, 0), (-L * 0.30, W * 0.30)],
            ]
            mode = "twin"

        elif s == "DIAMOND_DELTA":
            hull = [
                (L * 1.10, 0.00),
                (L * 0.10, -W * 0.90),
                (-L * 0.90, -W * 0.40),
                (-L * 1.20, -W * 0.15),
                (-L * 1.25, 0.00),
                (-L * 1.20, W * 0.15),
                (-L * 0.90, W * 0.40),
                (L * 0.10, W * 0.90),
            ]
            lines += [
                [(-L * 0.90, 0), (L * 0.80, 0)],
                [(L * 0.10, -W * 0.60), (-L * 0.80, -W * 0.30)],
                [(L * 0.10, W * 0.60), (-L * 0.80, W * 0.30)],
            ]
            mode = "center"

        elif s == "BOOMERANG":
            hull = [
                (L * 0.60, 0.00),
                (L * 0.00, -W * 1.10),
                (-L * 0.80, -W * 1.20),
                (-L * 0.50, -W * 0.40),
                (-L * 0.20, 0.00),
                (-L * 0.50, W * 0.40),
                (-L * 0.80, W * 1.20),
                (L * 0.00, W * 1.10),
            ]
            lines += [
                [(L * 0.40, 0), (-L * 0.10, 0)],
                [(L * 0.20, -W * 0.30), (-L * 0.60, -W * 1.00)],
                [(L * 0.20, W * 0.30), (-L * 0.60, W * 1.00)],
            ]
            mode = "center"
            eng_center = (-L * 0.30, 0.0)

        elif s == "STEALTH":
            hull = [
                (L * 0.75, 0.00),
                (L * 0.20, -W * 1.00),
                (-L * 0.40, -W * 1.00),
                (-L * 0.80, -W * 0.50),
                (-L * 0.50, -W * 0.25),
                (-L * 1.00, 0.00),
                (-L * 0.50, W * 0.25),
                (-L * 0.80, W * 0.50),
                (-L * 0.40, W * 1.00),
                (L * 0.20, W * 1.00),
            ]
            lines += [
                [(-L * 0.40, 0), (L * 0.50, 0)],
                [(L * 0.20, -W * 0.50), (-L * 0.40, -W * 0.50)],
                [(L * 0.20, W * 0.50), (-L * 0.40, W * 0.50)],
            ]
            mode = "center"

        elif s == "RIB_CAGE":
            hull = [
                (L * 0.80, 0.00),
                (L * 0.30, -W * 0.40),
                (L * 0.20, -W * 0.70),
                (-L * 0.10, -W * 0.30),
                (-L * 0.50, -W * 0.80),
                (-L * 0.80, -W * 0.30),
                (-L * 1.10, -W * 0.50),
                (-L * 1.20, 0.00),
                (-L * 1.10, W * 0.50),
                (-L * 0.80, W * 0.30),
                (-L * 0.50, W * 0.80),
                (-L * 0.10, W * 0.30),
                (L * 0.20, W * 0.70),
                (L * 0.30, W * 0.40),
            ]
            lines += [
                [(-L * 0.90, 0), (L * 0.60, 0)],
                [(L * 0.20, -W * 0.70), (0, 0)],
                [(-L * 0.50, -W * 0.80), (0, 0)],
                [(L * 0.20, W * 0.70), (0, 0)],
                [(-L * 0.50, W * 0.80), (0, 0)],
            ]
            mode = "center"

        else:  # THRUSTER_FINS
            hull = [
                (L * 0.90, 0.00),
                (L * 0.30, -W * 0.30),
                (-L * 0.50, -W * 0.45),
                (-L * 0.80, -W * 0.25),
                (-L * 0.90, -W * 0.80),
                (-L * 1.25, -W * 0.80),
                (-L * 1.10, -W * 0.20),
                (-L * 1.30, 0.00),
                (-L * 1.10, W * 0.20),
                (-L * 1.25, W * 0.80),
                (-L * 0.90, W * 0.80),
                (-L * 0.80, W * 0.25),
                (-L * 0.50, W * 0.45),
                (L * 0.30, W * 0.30),
            ]
            lines += [
                [(-L * 0.80, 0), (L * 0.70, 0)],
                [(-L * 0.85, -W * 0.50), (-L * 1.15, -W * 0.50)],
                [(-L * 0.85, W * 0.50), (-L * 1.15, W * 0.50)],
            ]
            mode = "twin"
            eng_left = (-L * 1.15, -W * 0.50)
            eng_right = (-L * 1.15, W * 0.50)

        lines = lines[:5]
        return hull, lines, mode, {"center": eng_center, "left": eng_left, "right": eng_right}

    def _all_items(self):
        return [self.hull] + self.detail_lines + [
            self.engine_center, self.engine_left, self.engine_right
        ] + self.flame_c + self.flame_l + self.flame_r

    def destroy(self):
        for it in self._all_items():
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        for it in self.explode_items:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        self.explode_items.clear()

    def _hide_ship(self):
        for it in self._all_items():
            self.canvas.itemconfig(it, state="hidden")

    def explode(self):
        if self.exploding or (not self.enable_explosions):
            return
        self.exploding = True
        self.state = "EXPLODE"
        self.explode_t = 0.0
        self._hide_ship()

        if callable(self.on_explode):
            try:
                self.on_explode()
            except Exception:
                pass

        boom_cols = ["#FFD966", "#FFB86B", "#FF6B6B", "#66B3FF", "#EAF2FF"]
        n_rays = random.randint(10, 16)
        for _ in range(n_rays):
            ang = random.random() * math.tau
            r0 = random.uniform(2, 6)
            r1 = random.uniform(24, 46)
            x0 = self.x + math.cos(ang) * r0
            y0 = self.y + math.sin(ang) * r0
            x1 = self.x + math.cos(ang) * r1
            y1 = self.y + math.sin(ang) * r1
            col = random.choice(boom_cols)
            dash = () if random.random() < 0.55 else (3, 6)
            it = self.canvas.create_line(x0, y0, x1, y1, fill=col, width=1,
                                         capstyle=tk.ROUND, dash=dash)
            self.explode_items.append(it)

        ring = self.canvas.create_oval(self.x, self.y, self.x, self.y, outline=random.choice(boom_cols), width=1)
        ring2 = self.canvas.create_oval(self.x, self.y, self.x, self.y, outline=random.choice(boom_cols),
                                        width=1, dash=(2, 6))
        self.explode_items += [ring, ring2]

    def _update_explosion(self, dt):
        self.explode_t += dt
        t = self.explode_t
        D = 0.42
        if t >= D:
            return False

        r = 6 + (t / D) * 68
        r2 = 10 + (t / D) * 96

        if len(self.explode_items) >= 2:
            ring = self.explode_items[-2]
            ring2 = self.explode_items[-1]
            self.canvas.coords(ring, self.x - r, self.y - r, self.x + r, self.y + r)
            self.canvas.coords(ring2, self.x - r2, self.y - r2, self.x + r2, self.y + r2)

        push = 1.0 + (t / D) * 0.55
        for it in self.explode_items[:-2]:
            coords = self.canvas.coords(it)
            if len(coords) == 4:
                x0, y0, x1, y1 = coords
                dx0, dy0 = x0 - self.x, y0 - self.y
                dx1, dy1 = x1 - self.x, y1 - self.y
                self.canvas.coords(it,
                                   self.x + dx0 * push, self.y + dy0 * push,
                                   self.x + dx1 * push, self.y + dy1 * push)

        return True

    def try_shoot(self, mx, my, dt, bullets_out_list):
        if self.exploding or (not self.enable_bullets):
            return

        self._shoot_timer -= dt
        if self._shoot_timer > 0.0:
            return

        d = math.hypot(mx - self.x, my - self.y)
        if d > self.shoot_trigger:
            return

        # 机头偏移随飞船缩放
        nose_off = 12.0 * self._ship_scale()
        sx = self.x + math.cos(self.angle) * nose_off
        sy = self.y + math.sin(self.angle) * nose_off

        dx = mx - sx
        dy = my - sy
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        ux, uy = dx / dist, dy / dist

        spd = self.bullet_speed

        spread = 0.0
        if self.bullet_kind in ("SPARK", "SHARD"):
            spread = math.radians(6)
        elif self.bullet_kind == "PLASMA":
            spread = math.radians(3)
        elif self.bullet_kind == "WAVE":
            spread = math.radians(4)

        if spread > 0:
            a = math.atan2(uy, ux) + random.uniform(-spread, spread)
            ux, uy = math.cos(a), math.sin(a)

        vx = ux * spd
        vy = uy * spd

        col = random.choice(self.bullet_palette)

        if self.bullet_kind == "SPARK":
            base_ang = math.atan2(uy, ux)
            for k in (-1, 0, 1):
                a = base_ang + k * math.radians(6)
                bvx, bvy = math.cos(a) * spd, math.sin(a) * spd
                bullets_out_list.append(
                    Bullet(self.canvas, sx, sy, bvx, bvy, kind="SPARK", color=col,
                           life_override=self.bullet_life, max_dist_override=self.bullet_max_dist)
                )
        else:
            bullets_out_list.append(
                Bullet(self.canvas, sx, sy, vx, vy, kind=self.bullet_kind, color=col,
                       life_override=self.bullet_life, max_dist_override=self.bullet_max_dist)
            )

        jitter = random.uniform(-0.03, 0.03)
        self._shoot_timer = max(0.06, self.shoot_cooldown + jitter)

    def set_new_target(self):
        r = 260
        self.tx = self.x + random.randint(-r, r)
        self.ty = self.y + random.randint(-r, r)
        margin = 160
        self.tx = max(margin, min(self.w - margin, self.tx))
        self.ty = max(margin, min(self.h - margin, self.ty))
        self.state = "WANDER"

    def update(self, mx, my):
        now = time.time()
        dt = max(0.001, min(0.05, now - self._last_t))
        self._last_t = now

        if self.exploding:
            return self._update_explosion(dt)

        # 捕获半径随飞船缩放，让大船更容易“贴住”
        catch_r = self.catch_radius * (0.9 + 0.35 * self._ship_scale())
        d_mouse = math.hypot(mx - self.x, my - self.y)
        if d_mouse < catch_r:
            self._catch_accum += dt
            if self._catch_accum >= self.catch_hold:
                self.explode()
                return True
        else:
            self._catch_accum = max(0.0, self._catch_accum - dt * 0.8)

        if d_mouse < self.flee_trigger:
            self.state = "FLEE"
            ang = math.atan2(self.y - my, self.x - mx)
            self.tx = self.x + math.cos(ang) * self.escape_dist
            self.ty = self.y + math.sin(ang) * self.escape_dist
            margin = 160
            self.tx = max(margin, min(self.w - margin, self.tx))
            self.ty = max(margin, min(self.h - margin, self.ty))

        if self.state == "IDLE":
            self.idle_timer -= 1
            if self.idle_timer <= 0:
                self.set_new_target()

            self._apply_drag(dt, strong=True)
            self.x += self.vx * dt
            self.y += self.vy * dt

        elif self.state == "COAST":
            self.coast_timer -= dt
            self._apply_drag(dt, strong=False)
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.coast_timer <= 0.0 or (abs(self.vx) + abs(self.vy) < 18.0):
                self.state = "IDLE"
                self.idle_timer = random.randint(40, 220)

        else:
            dx = self.tx - self.x
            dy = self.ty - self.y
            dist = math.hypot(dx, dy)

            if dist > 1e-6:
                targ = math.atan2(dy, dx)
                turn = self.turn_flee if self.state == "FLEE" else self.turn_wander
                self.angle = self._lerp_angle(self.angle, targ, turn)

            # ✅ 修复：飞船越大，视觉上越容易被指针贴住，所以速度/上限随缩放补偿
            sc = self._ship_scale()
            scale_boost = 1.0 + max(0.0, sc - 1.0) * 0.55
            sp = self.speed * (self.flee_mult if self.state == "FLEE" else 1.0) * scale_boost

            # ✅ 隐藏 bug 修复：原本先把 state 设为 COAST，再判断 self.state != "WANDER" 永远 True
            prev_state = self.state

            if dist <= max(10.0, sp * 0.9):
                self.state = "COAST"
                self.coast_timer = 0.65 if prev_state != "WANDER" else 0.5
            else:
                dirx = dx / dist
                diry = dy / dist

                desired_vx = dirx * (sp * 60.0)
                desired_vy = diry * (sp * 60.0)

                vel_follow = 0.16 if self.state == "FLEE" else 0.13
                self.vx += (desired_vx - self.vx) * vel_follow
                self.vy += (desired_vy - self.vy) * vel_follow

                vmax = (self.vmax_flee if self.state == "FLEE" else self.vmax_wander) * scale_boost
                vv = math.hypot(self.vx, self.vy)
                if vv > vmax:
                    s = vmax / vv
                    self.vx *= s
                    self.vy *= s

                self.x += self.vx * dt
                self.y += self.vy * dt

                margin = 160
                self.x = max(margin, min(self.w - margin, self.x))
                self.y = max(margin, min(self.h - margin, self.y))

        speed = math.hypot(self.vx, self.vy)
        if speed > 1e-3:
            raw_v_ang = math.atan2(self.vy, self.vx)
            self.v_ang = self._lerp_angle(self.v_ang, raw_v_ang, 0.10)

        prev = getattr(self, "_prev_v_ang", self.v_ang)
        ang_vel = self._angle_diff(prev, self.v_ang) / dt
        self._prev_v_ang = self.v_ang

        slip_target = max(-0.26, min(0.26, ang_vel * 0.08))
        if speed < 80.0:
            slip_target *= (speed / 80.0)
        self.slip += (slip_target - self.slip) * 0.06

        tail_ang = self.angle + math.pi
        target_flame_ang = (self.v_ang + math.pi + self.slip) if speed > 60.0 else tail_ang

        max_turn_rate = math.radians(85 if speed > 120.0 else 52)
        diff = self._angle_diff(self.flame_ang, target_flame_ang)
        max_step = max_turn_rate * dt
        diff = max(-max_step, min(max_step, diff))
        self.flame_ang += diff

        self.phase = (self.phase + dt * (12.0 if self.state == "FLEE" else 5.0)) % math.tau
        self.draw(current_speed=speed, dt=dt)

        return True

    def draw(self, current_speed: float, dt: float):
        # ✅ 关键：飞船尺寸用滑块实时缩放
        sc = self._ship_scale()
        L = 11 * sc
        W = 6.5 * sc

        hull, lines, mode, eng = self._shape_for_style(L, W)
        self._set_poly(self.hull, hull)

        for i, item in enumerate(self.detail_lines):
            if i < len(lines):
                self.canvas.itemconfig(item, state="normal")
                self._set_line(item, lines[i])
            else:
                self.canvas.itemconfig(item, state="hidden")

        pulse = 1.0 + 0.20 * math.sin(self.phase * 2.2)
        eng_r = (2.0 * sc) * pulse

        if mode == "twin":
            self.canvas.itemconfig(self.engine_center, state="hidden")
            self.canvas.itemconfig(self.engine_left, state="normal")
            self.canvas.itemconfig(self.engine_right, state="normal")

            elx, ely = self._rot_ship(eng["left"][0], eng["left"][1])
            erx, ery = self._rot_ship(eng["right"][0], eng["right"][1])
            self.canvas.coords(self.engine_left, elx - eng_r, ely - eng_r, elx + eng_r, ely + eng_r)
            self.canvas.coords(self.engine_right, erx - eng_r, ery - eng_r, erx + eng_r, ery + eng_r)

            self._draw_thrust_trails(elx, ely, current_speed, which="L", scale=sc)
            self._draw_thrust_trails(erx, ery, current_speed, which="R", scale=sc)

            for it in self.flame_c:
                self.canvas.itemconfig(it, state="hidden")
        else:
            self.canvas.itemconfig(self.engine_center, state="normal")
            self.canvas.itemconfig(self.engine_left, state="hidden")
            self.canvas.itemconfig(self.engine_right, state="hidden")

            ecx, ecy = self._rot_ship(eng["center"][0], eng["center"][1])
            self.canvas.coords(self.engine_center, ecx - eng_r, ecy - eng_r, ecx + eng_r, ecy + eng_r)

            self._draw_thrust_trails(ecx, ecy, current_speed, which="C", scale=sc)

            for it in self.flame_l + self.flame_r:
                self.canvas.itemconfig(it, state="hidden")

    def _draw_thrust_trails(self, ecx, ecy, current_speed, which="C", scale=1.0):
        norm = min(1.0, current_speed / 650.0)
        norm = norm * norm

        a1 = (1.6 + norm * 16.0) * (1.0 + 0.10 * math.sin(self.phase * 4.0))
        b1 = 0.7 + norm * 1.0

        a2 = (2.2 + norm * 22.0) * (1.0 + 0.08 * math.sin(self.phase * 3.2 + 1.0))
        b2 = 0.6 + norm * 0.8

        a3 = (2.8 + norm * 28.0) * (1.0 + 0.06 * math.sin(self.phase * 2.6 + 2.2))
        b3 = 0.55 + norm * 0.7

        # ✅ 尾焰也随飞船缩放
        a1 *= scale
        b1 *= scale
        a2 *= scale
        b2 *= scale
        a3 *= scale
        b3 *= scale

        offset_scale = min(1.0, current_speed / 220.0)

        def center_for(a, extra):
            off = (a * 0.60 + extra * scale) * offset_scale
            return (ecx + math.cos(self.flame_ang) * off,
                    ecy + math.sin(self.flame_ang) * off)

        c1 = center_for(a1, 2.0)
        c2 = center_for(a2, 7.0)
        c3 = center_for(a3, 14.0)

        flames = self.flame_c if which == "C" else (self.flame_l if which == "L" else self.flame_r)

        for it in flames:
            self.canvas.itemconfig(it, state="normal")

        self._draw_rotated_ellipse_outline(flames[0], c1[0], c1[1], a1, b1, self.flame_ang, segments=14)
        self._draw_rotated_ellipse_outline(flames[1], c2[0], c2[1], a2, b2, self.flame_ang, segments=14)
        self._draw_rotated_ellipse_outline(flames[2], c3[0], c3[1], a3, b3, self.flame_ang, segments=14)


class BoomShip(SciFiShip):
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


class ChallengeShip(BoomShip):
    def explode(self, chain=None, source="mouse"):
        if self.owner.round.ended or self.owner.paused:
            return
        if self.owner.round.elapsed < getattr(self, "grace_until", 0):
            return
        self.chain, self.boom_source = chain, source
        super().explode()
