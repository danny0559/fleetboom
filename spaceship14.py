import tkinter as tk
import random
import math
import time
import sys

KEY = "#00ff00"  # 透明抠像色（画布背景用它）


# -----------------------
# 子弹系统：多种特效
# -----------------------
class Bullet:
    """
    Tk Canvas 子弹对象（纯视觉特效）
    kind:
      LASER  : 细直线激光（可虚线）
      PLASMA : 发光球 + 尾迹（两条）
      SPARK  : 星火碎点（抖动散射）
      WAVE   : 波动轨迹（正弦摆动）
      SHARD  : 尖刺碎片（小三角）
    """
    def __init__(self, canvas, x, y, vx, vy, kind="LASER", color="#66B3FF",
                 life_override=None, max_dist_override=None):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.x0 = x
        self.y0 = y
        self.vx = vx  # px/s
        self.vy = vy

        self.kind = kind
        self.color = color

        self.age = 0.0
        self.life = 0.6 if life_override is None else float(life_override)
        self.dead = False

        self.trail = []
        self.max_trail = 8

        # 距离上限（用于“持续距离”）
        self.max_dist = None if max_dist_override is None else float(max_dist_override)

        self.items = []
        self._build_items()

    def _build_items(self):
        c = self.canvas
        if self.kind == "LASER":
            dash = () if random.random() < 0.6 else (3, 6)
            it = c.create_line(self.x, self.y, self.x, self.y, fill=self.color, width=1,
                               capstyle=tk.ROUND, dash=dash)
            self.items.append(it)
            self.life = min(self.life, 0.30)
            self.max_trail = 2

        elif self.kind == "PLASMA":
            r = 2.4
            tail1 = c.create_line(self.x, self.y, self.x, self.y, fill=self.color, width=1, smooth=True)
            tail2 = c.create_line(self.x, self.y, self.x, self.y, fill=self.color, width=1, smooth=True, dash=(2, 6))
            orb = c.create_oval(self.x - r, self.y - r, self.x + r, self.y + r, outline=self.color, width=1)
            self.items += [tail1, tail2, orb]
            self.max_trail = 10

        elif self.kind == "SPARK":
            n = 3
            for _ in range(n):
                r = random.uniform(1.1, 1.8)
                it = c.create_oval(self.x - r, self.y - r, self.x + r, self.y + r,
                                   outline=self.color, width=1)
                self.items.append(it)

        elif self.kind == "WAVE":
            it = c.create_line(self.x, self.y, self.x, self.y, fill=self.color, width=1, smooth=True)
            self.items.append(it)
            self.max_trail = 14

        elif self.kind == "SHARD":
            it = c.create_polygon(self.x, self.y, self.x, self.y, self.x, self.y,
                                  outline=self.color, fill="", width=1, joinstyle=tk.ROUND)
            self.items.append(it)

        else:
            it = c.create_line(self.x, self.y, self.x, self.y, fill=self.color, width=1)
            self.items.append(it)

    def destroy(self):
        if self.dead:
            return
        for it in self.items:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        self.items.clear()
        self.dead = True

    def _out_of_bounds(self, w, h, pad=80):
        return (self.x < -pad or self.x > w + pad or self.y < -pad or self.y > h + pad)

    def update(self, dt, w, h):
        if self.dead:
            return False

        self.age += dt
        if self.age > self.life:
            self.destroy()
            return False

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.max_dist is not None:
            if math.hypot(self.x - self.x0, self.y - self.y0) > self.max_dist:
                self.destroy()
                return False

        if self._out_of_bounds(w, h):
            self.destroy()
            return False

        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        try:
            self._draw()
        except tk.TclError:
            self.destroy()
            return False

        return True

    def _draw(self):
        c = self.canvas

        if self.kind == "LASER":
            tail = 18
            nx, ny = self._norm(self.vx, self.vy)
            sx = self.x - nx * tail
            sy = self.y - ny * tail
            c.coords(self.items[0], sx, sy, self.x, self.y)

        elif self.kind == "PLASMA":
            if len(self.trail) >= 2:
                coords = []
                for px, py in self.trail:
                    coords += [px, py]
                c.coords(self.items[0], *coords)

                n = max(6, len(coords) // 2)
                start = len(coords) - n
                if start % 2 == 1:
                    start -= 1
                if start < 0:
                    start = 0
                coords2 = coords[start:]
                if len(coords2) < 4 and len(coords) >= 4:
                    coords2 = coords[-4:]
                if len(coords2) % 2 == 1:
                    coords2 = coords2[:-1]
                c.coords(self.items[1], *coords2)

            r = 2.4 + 0.6 * math.sin(self.age * 18.0)
            c.coords(self.items[2], self.x - r, self.y - r, self.x + r, self.y + r)

        elif self.kind == "SPARK":
            for i, it in enumerate(self.items):
                jitter = 2.2 * math.sin(self.age * 26.0 + i * 1.9)
                r = 1.2 + 0.4 * math.sin(self.age * 22.0 + i)
                ox = jitter * (0.5 - i * 0.15)
                oy = jitter * (-0.3 + i * 0.2)
                c.coords(it, self.x + ox - r, self.y + oy - r, self.x + ox + r, self.y + oy + r)

        elif self.kind == "WAVE":
            if len(self.trail) >= 2:
                nx, ny = self._norm(self.vx, self.vy)
                fx, fy = -ny, nx
                amp = 6.0 * math.sin(self.age * 10.0)
                coords = []
                for k, (px, py) in enumerate(self.trail):
                    t = k / max(1, len(self.trail) - 1)
                    wob = amp * math.sin(self.age * 14.0 + t * 8.0)
                    coords += [px + fx * wob, py + fy * wob]
                c.coords(self.items[0], *coords)

        elif self.kind == "SHARD":
            nx, ny = self._norm(self.vx, self.vy)
            hx, hy = self.x, self.y
            side = 4.6
            back = 6.5
            fx, fy = -ny, nx
            p1 = (hx, hy)
            p2 = (hx - nx * back + fx * side, hy - ny * back + fy * side)
            p3 = (hx - nx * back - fx * side, hy - ny * back - fy * side)
            c.coords(self.items[0], p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])

        else:
            c.coords(self.items[0], self.x, self.y, self.x, self.y)

    @staticmethod
    def _norm(vx, vy):
        d = math.hypot(vx, vy)
        if d < 1e-6:
            return (1.0, 0.0)
        return (vx / d, vy / d)


# -----------------------
# 样式星球（有填充/高光/陨坑/环/小卫星）+ 永久缓慢随机飘移 + 支持缩放
# -----------------------
class StyledPlanet:
    def __init__(self, canvas, w, h, scale_getter=None):
        self.canvas = canvas
        self.w = w
        self.h = h
        self.scale_getter = scale_getter  # callable -> float

        self.base_r = random.randint(10, 20)
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)

        # 永久非常慢随机飘移（px/s），且目标速度会缓慢变换
        ang = random.random() * math.tau
        spd = random.uniform(3.0, 10.0)
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd

        ang2 = random.random() * math.tau
        spd2 = random.uniform(3.0, 10.0)
        self._tvx = math.cos(ang2) * spd2
        self._tvy = math.sin(ang2) * spd2
        self._drift_timer = random.uniform(1.4, 3.6)

        palettes = [
            ("#B388FF", "#6D28D9", "#E9D5FF"),
            ("#A78BFA", "#5B21B6", "#EDE9FE"),
            ("#C084FC", "#701A75", "#F5D0FE"),
            ("#D8B4FE", "#7C3AED", "#F3E8FF"),
            ("#8B5CF6", "#4C1D95", "#DDD6FE"),
        ]
        self.col_main, self.col_dark, self.col_hi = random.choice(palettes)

        # 主体填充 + 描边
        # self.disk_fill = canvas.create_oval(0, 0, 0, 0, outline="", fill=self.col_main)
        # 使用 stipple 模拟透明度，gray50 表示 50% 密集度的网点
        self.disk_fill = canvas.create_oval(0, 0, 0, 0, outline="", fill=self.col_main, stipple="gray75")
        self.disk_edge = canvas.create_oval(0, 0, 0, 0, outline=self.col_hi, width=1, fill="")

        # 阴影/高光弧
        self.shadow_arc = canvas.create_arc(0, 0, 0, 0, outline=self.col_dark, width=2,
                                            style=tk.ARC, start=210, extent=140)
        self.hi_arc = canvas.create_arc(0, 0, 0, 0, outline=self.col_hi, width=2,
                                        style=tk.ARC, start=25, extent=95)

        # 陨坑
        self.craters = []
        self._crater_specs = []
        n = random.randint(2, 5)
        for _ in range(n):
            rr = random.uniform(0.12, 0.28)
            ox = random.uniform(-0.35, 0.35)
            oy = random.uniform(-0.30, 0.30)
            col = random.choice([self.col_dark, self.col_hi])
            it = canvas.create_oval(0, 0, 0, 0, outline=col, width=1, fill="")
            self.craters.append(it)
            self._crater_specs.append((ox, oy, rr, random.uniform(0.7, 1.4)))

        # 星环
        self.has_ring = random.choice([True, False, False])
        self.ring = canvas.create_oval(0, 0, 0, 0, outline=self.col_hi, width=1,
                                       dash=(3, 6), fill="") if self.has_ring else None
        self.ring2 = canvas.create_oval(0, 0, 0, 0, outline=self.col_dark, width=1,
                                        dash=(2, 8), fill="") if self.has_ring else None

        # 小卫星（可选）
        self.has_moon = random.choice([True, False, False])
        self.moon = canvas.create_oval(0, 0, 0, 0, outline=self.col_hi, width=1, fill="") if self.has_moon else None
        self._moon_phase = random.random() * math.tau

        self.draw()

    def _scale(self):
        if callable(self.scale_getter):
            try:
                return max(0.3, min(2.5, float(self.scale_getter())))
            except Exception:
                return 1.0
        return 1.0

    def draw(self):
        s = self._scale()
        r = self.base_r * s
        x, y = self.x, self.y

        self.canvas.coords(self.disk_fill, x - r, y - r, x + r, y + r)
        self.canvas.coords(self.disk_edge, x - r, y - r, x + r, y + r)

        self.canvas.coords(self.shadow_arc, x - r * 1.02, y - r * 1.02, x + r * 1.02, y + r * 1.02)
        self.canvas.coords(self.hi_arc, x - r * 0.92, y - r * 0.92, x + r * 0.92, y + r * 0.92)

        for it, (ox, oy, rr, asp) in zip(self.craters, self._crater_specs):
            cr = r * rr
            cx = x + ox * r
            cy = y + oy * r
            self.canvas.coords(it, cx - cr * asp, cy - cr, cx + cr * asp, cy + cr)

        if self.ring:
            rx = r * 1.55
            ry = r * 0.55
            self.canvas.coords(self.ring, x - rx, y - ry, x + rx, y + ry)
        if self.ring2:
            rx = r * 1.75
            ry = r * 0.68
            self.canvas.coords(self.ring2, x - rx, y - ry, x + rx, y + ry)

        if self.moon:
            self._moon_phase = (self._moon_phase + 0.010) % math.tau
            mr = max(2.0, r * 0.22)
            orbit = r * 1.95
            mx = x + math.cos(self._moon_phase) * orbit
            my = y + math.sin(self._moon_phase) * orbit * 0.55
            self.canvas.coords(self.moon, mx - mr, my - mr, mx + mr, my + mr)

    def update(self, dt):
        # 永久随机飘移：目标速度缓慢变化（不会一整排同向）
        self._drift_timer -= dt
        if self._drift_timer <= 0.0:
            self._drift_timer = random.uniform(1.2, 3.8)
            ang = random.random() * math.tau
            spd = random.uniform(3.0, 11.0)
            self._tvx = math.cos(ang) * spd
            self._tvy = math.sin(ang) * spd

        follow = 0.08
        self.vx += (self._tvx - self.vx) * follow
        self.vy += (self._tvy - self.vy) * follow

        self.x += self.vx * dt
        self.y += self.vy * dt

        # 屏幕环绕
        pad = 120
        if self.x < -pad:
            self.x = self.w + pad
        if self.x > self.w + pad:
            self.x = -pad
        if self.y < -pad:
            self.y = self.h + pad
        if self.y > self.h + pad:
            self.y = -pad

        self.draw()


# -----------------------
# 线稿飞船（爆炸重生 + 多子弹特效）+ 支持缩放
# -----------------------
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
        self.prev_mx = None
        self.prev_my = None
        self.mouse_vx = 0.0
        self.mouse_vy = 0.0
        self.evade_timer = 0.0
        self.evade_sign = random.choice([-1.0, 1.0])
        self.evade_strength = 0.0

        self.exploding = False
        self.explode_t = 0.0
        self.explode_items = []

        self.hull_shadow = canvas.create_polygon(0, 0, 0, 0, 0, 0,
                                                 outline="#4E5968", fill="", width=1, joinstyle=tk.ROUND)
        self.hull = canvas.create_polygon(0, 0, 0, 0, 0, 0,
                                          outline=self.col, fill="", width=1, joinstyle=tk.ROUND)
        self.hull_inner = canvas.create_polygon(0, 0, 0, 0, 0, 0,
                                                outline="#C8D6EA", fill="", width=1, joinstyle=tk.ROUND)

        self.detail_lines = [
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill=self.col, width=1, capstyle=tk.ROUND),
        ]
        self.detail_glow = [
            canvas.create_line(0, 0, 0, 0, fill="#C8D6EA", width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill="#C8D6EA", width=1, capstyle=tk.ROUND),
            canvas.create_line(0, 0, 0, 0, fill="#C8D6EA", width=1, capstyle=tk.ROUND),
        ]

        self.engine_center = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")
        self.engine_left = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")
        self.engine_right = canvas.create_oval(0, 0, 0, 0, outline=self.col, width=1, fill="")
        self.engine_core_center = canvas.create_oval(0, 0, 0, 0, outline=self.flame_col, width=1, fill="")
        self.engine_core_left = canvas.create_oval(0, 0, 0, 0, outline=self.flame_col, width=1, fill="")
        self.engine_core_right = canvas.create_oval(0, 0, 0, 0, outline=self.flame_col, width=1, fill="")
        self.nav_light_nose = canvas.create_oval(0, 0, 0, 0, outline="#EAF6FF", width=1, fill="")
        self.nav_light_port = canvas.create_oval(0, 0, 0, 0, outline="#7FDBFF", width=1, fill="")
        self.nav_light_starboard = canvas.create_oval(0, 0, 0, 0, outline="#FFD966", width=1, fill="")

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

    def _move_margin(self):
        return 160

    def set_difficulty(self, level: int):
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

    @staticmethod
    def _scale_pts(pts, sx=1.0, sy=None):
        if sy is None:
            sy = sx
        return [(px * sx, py * sy) for px, py in pts]

    def _set_light(self, item, pt, r):
        x, y = self._rot_ship(pt[0], pt[1])
        self.canvas.coords(item, x - r, y - r, x + r, y + r)

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

    def _update_mouse_motion(self, mx, my, dt):
        if self.prev_mx is None or self.prev_my is None:
            self.prev_mx = mx
            self.prev_my = my
            self.mouse_vx = 0.0
            self.mouse_vy = 0.0
            return

        raw_vx = (mx - self.prev_mx) / max(dt, 1e-4)
        raw_vy = (my - self.prev_my) / max(dt, 1e-4)
        self.prev_mx = mx
        self.prev_my = my

        follow = 0.34
        self.mouse_vx += (raw_vx - self.mouse_vx) * follow
        self.mouse_vy += (raw_vy - self.mouse_vy) * follow

    def _set_flee_target(self, mx, my, threat_scale=0.0, force_evade=False):
        away_x = self.x - mx
        away_y = self.y - my
        away_d = math.hypot(away_x, away_y)
        if away_d < 1e-6:
            away_x = math.cos(self.angle + math.pi)
            away_y = math.sin(self.angle + math.pi)
            away_d = 1.0
        away_x /= away_d
        away_y /= away_d

        side_x = -away_y
        side_y = away_x

        if self.evade_timer > 0.0:
            lateral = self.evade_sign * self.evade_strength
        else:
            lateral = 0.0

        if abs(away_x) < 0.18:
            lateral += random.choice([-1.0, 1.0]) * 0.55

        if force_evade:
            self.evade_sign = random.choice([-1.0, 1.0])
            self.evade_strength = random.uniform(0.75, 1.10)
            self.evade_timer = random.uniform(0.18, 0.34)
            lateral = self.evade_sign * self.evade_strength

        lateral += random.uniform(-0.10, 0.10)
        lateral = max(-1.25, min(1.25, lateral))

        margin = self._move_margin()
        edge_band = 120.0
        push_x = 0.0
        push_y = 0.0
        if self.x < margin + edge_band:
            push_x += (margin + edge_band - self.x) / edge_band
        elif self.x > self.w - margin - edge_band:
            push_x -= (self.x - (self.w - margin - edge_band)) / edge_band
        if self.y < margin + edge_band:
            push_y += (margin + edge_band - self.y) / edge_band
        elif self.y > self.h - margin - edge_band:
            push_y -= (self.y - (self.h - margin - edge_band)) / edge_band

        edge_pressure = max(abs(push_x), abs(push_y))
        reach = self.escape_dist * (1.0 + 0.30 * max(0.0, threat_scale) + 0.18 * edge_pressure)
        dir_x = away_x + side_x * lateral + push_x * (0.90 + 0.35 * edge_pressure)
        dir_y = away_y + side_y * lateral + push_y * (0.90 + 0.35 * edge_pressure)
        dir_d = math.hypot(dir_x, dir_y)
        if dir_d < 1e-6:
            dir_x, dir_y = away_x, away_y
            dir_d = 1.0
        dir_x /= dir_d
        dir_y /= dir_d

        self.tx = self.x + dir_x * reach
        self.ty = self.y + dir_y * reach

        self.tx = max(margin, min(self.w - margin, self.tx))
        self.ty = max(margin, min(self.h - margin, self.ty))
        if math.hypot(self.tx - self.x, self.ty - self.y) < 28.0:
            fallback = max(90.0, self.escape_dist * 0.70)
            self.tx = self.x + push_x * fallback
            self.ty = self.y + push_y * fallback
            if abs(push_x) < 1e-6 and abs(push_y) < 1e-6:
                self.tx = self.x + side_x * self.evade_sign * fallback
                self.ty = self.y + side_y * self.evade_sign * fallback
            self.tx = max(margin, min(self.w - margin, self.tx))
            self.ty = max(margin, min(self.h - margin, self.ty))
        self.state = "FLEE"

    def _apply_style_visibility(self):
        self.canvas.itemconfig(self.engine_center, state=("hidden" if self.is_twin else "normal"))
        self.canvas.itemconfig(self.engine_left, state=("normal" if self.is_twin else "hidden"))
        self.canvas.itemconfig(self.engine_right, state=("normal" if self.is_twin else "hidden"))
        self.canvas.itemconfig(self.engine_core_center, state=("hidden" if self.is_twin else "normal"))
        self.canvas.itemconfig(self.engine_core_left, state=("normal" if self.is_twin else "hidden"))
        self.canvas.itemconfig(self.engine_core_right, state=("normal" if self.is_twin else "hidden"))

        for it in self.flame_c:
            self.canvas.itemconfig(it, state=("hidden" if self.is_twin else "normal"))
        for it in self.flame_l:
            self.canvas.itemconfig(it, state=("normal" if self.is_twin else "hidden"))
        for it in self.flame_r:
            self.canvas.itemconfig(it, state=("normal" if self.is_twin else "hidden"))
        for it in self.detail_glow:
            self.canvas.itemconfig(it, state="normal")

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
        return [self.hull_shadow, self.hull, self.hull_inner] + self.detail_lines + self.detail_glow + [
            self.engine_center, self.engine_left, self.engine_right,
            self.engine_core_center, self.engine_core_left, self.engine_core_right,
            self.nav_light_nose, self.nav_light_port, self.nav_light_starboard
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
        margin = self._move_margin()
        self.tx = max(margin, min(self.w - margin, self.tx))
        self.ty = max(margin, min(self.h - margin, self.ty))
        self.state = "WANDER"

    def update(self, mx, my):
        now = time.time()
        dt = max(0.001, min(0.05, now - self._last_t))
        self._last_t = now

        if self.exploding:
            return self._update_explosion(dt)

        self._update_mouse_motion(mx, my, dt)
        if self.evade_timer > 0.0:
            self.evade_timer = max(0.0, self.evade_timer - dt)

        # 捕获半径随飞船缩放，让大船更容易“贴住”
        catch_r = self.catch_radius * (0.9 + 0.35 * self._ship_scale())
        d_mouse = math.hypot(mx - self.x, my - self.y)
        if d_mouse < catch_r:
            self._catch_accum += dt
            if self._catch_accum >= self.catch_hold:
                if self.enable_explosions:
                    self.explode()
                    return True
                self._catch_accum = self.catch_hold * 0.35
                self.evade_timer = max(self.evade_timer, 0.26)
                self.evade_sign = random.choice([-1.0, 1.0])
                self.evade_strength = max(self.evade_strength, 1.0)
        else:
            self._catch_accum = max(0.0, self._catch_accum - dt * 0.8)

        to_ship_x = self.x - mx
        to_ship_y = self.y - my
        to_ship_d = max(1e-6, math.hypot(to_ship_x, to_ship_y))
        approach_speed = (self.mouse_vx * to_ship_x + self.mouse_vy * to_ship_y) / to_ship_d
        incoming = approach_speed > 120.0
        pressure_dist = self.flee_trigger * (1.65 if incoming else 1.0)
        threat_scale = max(0.0, min(1.8, approach_speed / 520.0))
        should_force_evade = (
            incoming
            and d_mouse < self.flee_trigger * 1.45
            and self.evade_timer <= 0.0
        )

        if d_mouse < pressure_dist:
            self._set_flee_target(mx, my, threat_scale=threat_scale, force_evade=should_force_evade)

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

                margin = self._move_margin()
                self.x = max(margin, min(self.w - margin, self.x))
                self.y = max(margin, min(self.h - margin, self.y))

        speed = math.hypot(self.vx, self.vy)
        if speed > 1e-3:
            raw_v_ang = math.atan2(self.vy, self.vx)
            v_follow = 0.20 if speed > 140.0 else 0.14
            self.v_ang = self._lerp_angle(self.v_ang, raw_v_ang, v_follow)

        prev = getattr(self, "_prev_v_ang", self.v_ang)
        ang_vel = self._angle_diff(prev, self.v_ang) / dt
        self._prev_v_ang = self.v_ang

        slip_target = max(-0.18, min(0.18, ang_vel * 0.05))
        if speed < 80.0:
            slip_target *= (speed / 80.0)
        slip_follow = 0.18 if speed > 80.0 else 0.12
        self.slip += (slip_target - self.slip) * slip_follow

        tail_ang = self.angle + math.pi
        move_tail_ang = self.v_ang + math.pi
        move_diff = self._angle_diff(tail_ang, move_tail_ang)
        speed_blend = max(0.0, min(1.0, (speed - 35.0) / 170.0))
        max_offset = math.radians(13.0)
        vel_offset = max(-max_offset, min(max_offset, move_diff)) * speed_blend
        slip_offset = self.slip * (0.30 + 0.25 * speed_blend)
        target_flame_ang = tail_ang + vel_offset + slip_offset

        max_turn_rate = math.radians(150 if speed > 150.0 else 110)
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
        hull_shadow = [(px - 1.4 * sc, py + 0.9 * sc) for px, py in hull]
        hull_inner = self._scale_pts(hull, 0.78, 0.72)
        self._set_poly(self.hull_shadow, hull_shadow)
        self._set_poly(self.hull, hull)
        self._set_poly(self.hull_inner, hull_inner)

        nose_pt = max(hull, key=lambda p: p[0])
        side_candidates = [p for p in hull if p[0] < nose_pt[0] - 0.12 * L]
        if not side_candidates:
            side_candidates = hull
        port_pt = min(side_candidates, key=lambda p: p[1])
        starboard_pt = max(side_candidates, key=lambda p: p[1])
        light_r = 0.85 * sc * (0.92 + 0.16 * math.sin(self.phase * 2.7 + 0.6))
        wing_r = 0.72 * sc * (0.88 + 0.22 * math.sin(self.phase * 2.1 + 1.3))
        self._set_light(self.nav_light_nose, (nose_pt[0] - 0.08 * L, nose_pt[1]), light_r)
        self._set_light(self.nav_light_port, (port_pt[0] * 0.96, port_pt[1] * 0.96), wing_r)
        self._set_light(self.nav_light_starboard, (starboard_pt[0] * 0.96, starboard_pt[1] * 0.96), wing_r)

        for i, item in enumerate(self.detail_lines):
            if i < len(lines):
                self.canvas.itemconfig(item, state="normal")
                self._set_line(item, lines[i])
            else:
                self.canvas.itemconfig(item, state="hidden")
        glow_lines = [self._scale_pts(line, 0.72, 0.72) for line in lines[:len(self.detail_glow)]]
        for i, item in enumerate(self.detail_glow):
            if i < len(glow_lines):
                self.canvas.itemconfig(item, state="normal")
                self._set_line(item, glow_lines[i])
            else:
                self.canvas.itemconfig(item, state="hidden")

        pulse = 1.0 + 0.20 * math.sin(self.phase * 2.2)
        eng_r = (2.0 * sc) * pulse
        core_r = eng_r * (0.46 + 0.10 * math.sin(self.phase * 3.4 + 0.4))

        if mode == "twin":
            self.canvas.itemconfig(self.engine_center, state="hidden")
            self.canvas.itemconfig(self.engine_left, state="normal")
            self.canvas.itemconfig(self.engine_right, state="normal")
            self.canvas.itemconfig(self.engine_core_center, state="hidden")
            self.canvas.itemconfig(self.engine_core_left, state="normal")
            self.canvas.itemconfig(self.engine_core_right, state="normal")

            elx, ely = self._rot_ship(eng["left"][0], eng["left"][1])
            erx, ery = self._rot_ship(eng["right"][0], eng["right"][1])
            self.canvas.coords(self.engine_left, elx - eng_r, ely - eng_r, elx + eng_r, ely + eng_r)
            self.canvas.coords(self.engine_right, erx - eng_r, ery - eng_r, erx + eng_r, ery + eng_r)
            self.canvas.coords(self.engine_core_left, elx - core_r, ely - core_r, elx + core_r, ely + core_r)
            self.canvas.coords(self.engine_core_right, erx - core_r, ery - core_r, erx + core_r, ery + core_r)

            self._draw_thrust_trails(elx, ely, current_speed, which="L", scale=sc)
            self._draw_thrust_trails(erx, ery, current_speed, which="R", scale=sc)

            for it in self.flame_c:
                self.canvas.itemconfig(it, state="hidden")
        else:
            self.canvas.itemconfig(self.engine_center, state="normal")
            self.canvas.itemconfig(self.engine_left, state="hidden")
            self.canvas.itemconfig(self.engine_right, state="hidden")
            self.canvas.itemconfig(self.engine_core_center, state="normal")
            self.canvas.itemconfig(self.engine_core_left, state="hidden")
            self.canvas.itemconfig(self.engine_core_right, state="hidden")

            ecx, ecy = self._rot_ship(eng["center"][0], eng["center"][1])
            self.canvas.coords(self.engine_center, ecx - eng_r, ecy - eng_r, ecx + eng_r, ecy + eng_r)
            self.canvas.coords(self.engine_core_center, ecx - core_r, ecy - core_r, ecx + core_r, ecy + core_r)

            self._draw_thrust_trails(ecx, ecy, current_speed, which="C", scale=sc)

            for it in self.flame_l + self.flame_r:
                self.canvas.itemconfig(it, state="hidden")

    def _draw_thrust_trails(self, ecx, ecy, current_speed, which="C", scale=1.0):
        norm = min(1.0, current_speed / 650.0)
        norm = norm * norm
        stretch = 0.78 + norm * 0.95
        thin = max(0.58, 0.96 - norm * 0.34)

        a1 = (1.7 + norm * 16.0) * stretch * (1.0 + 0.10 * math.sin(self.phase * 4.0))
        b1 = (0.95 + norm * 0.55) * thin

        a2 = (2.6 + norm * 23.0) * stretch * (1.0 + 0.08 * math.sin(self.phase * 3.2 + 1.0))
        b2 = (0.82 + norm * 0.45) * thin

        a3 = (3.4 + norm * 31.0) * stretch * (1.0 + 0.06 * math.sin(self.phase * 2.6 + 2.2))
        b3 = (0.72 + norm * 0.38) * thin

        # ✅ 尾焰也随飞船缩放
        a1 *= scale
        b1 *= scale
        a2 *= scale
        b2 *= scale
        a3 *= scale
        b3 *= scale

        offset_scale = 0.40 + 0.75 * min(1.0, current_speed / 220.0)

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


# -----------------------
# 图鉴：飞船/子弹/说明窗口（Tk Canvas 绘制）
# -----------------------
class CodexUI:
    SHIP_STYLES = [
        "SPEAR",
        "TWIN_ENGINE",
        "DIAMOND_DELTA",
        "BOOMERANG",
        "STEALTH",
        "RIB_CAGE",
        "THRUSTER_FINS",
    ]

    BULLET_KINDS = ["LASER", "PLASMA", "SPARK", "WAVE", "SHARD"]

    @staticmethod
    def ship_shape(style: str, L=10.0, W=10.0):
        s = style
        lines = []

        eng_center = (-L * 1.15, 0.0)
        eng_left = (-L * 1.15, -W * 0.45)
        eng_right = (-L * 1.15, W * 0.45)

        if s == "SPEAR":
            hull = [(L*1.40, 0.00), (L*0.30, -W*0.20), (-L*0.50, -W*0.55), (-L*1.05, -W*0.25),
                    (-L*1.25, 0.00), (-L*1.05, W*0.25), (-L*0.50, W*0.55), (L*0.30, W*0.20)]
            lines += [[(-L*0.80, 0), (L*1.10, 0)], [(-L*0.20, -W*0.15), (-L*0.60, -W*0.40)],
                      [(-L*0.20, W*0.15), (-L*0.60, W*0.40)]]
            mode = "center"

        elif s == "TWIN_ENGINE":
            hull = [(L*0.85, 0.00), (L*0.40, -W*0.40), (L*0.10, -W*0.40), (-L*0.40, -W*0.85),
                    (-L*0.80, -W*0.85), (-L*1.25, -W*0.60), (-L*1.00, -W*0.20), (-L*1.15, 0.00),
                    (-L*1.00, W*0.20), (-L*1.25, W*0.60), (-L*0.80, W*0.85), (-L*0.40, W*0.85),
                    (L*0.10, W*0.40), (L*0.40, W*0.40)]
            lines += [[(-L*0.80, -W*0.60), (-L*1.20, -W*0.60)], [(-L*0.80, W*0.60), (-L*1.20, W*0.60)],
                      [(-L*0.30, -W*0.30), (L*0.50, 0), (-L*0.30, W*0.30)]]
            mode = "twin"

        elif s == "DIAMOND_DELTA":
            hull = [(L*1.10, 0.00), (L*0.10, -W*0.90), (-L*0.90, -W*0.40), (-L*1.20, -W*0.15),
                    (-L*1.25, 0.00), (-L*1.20, W*0.15), (-L*0.90, W*0.40), (L*0.10, W*0.90)]
            lines += [[(-L*0.90, 0), (L*0.80, 0)], [(L*0.10, -W*0.60), (-L*0.80, -W*0.30)],
                      [(L*0.10, W*0.60), (-L*0.80, W*0.30)]]
            mode = "center"

        elif s == "BOOMERANG":
            hull = [(L*0.60, 0.00), (L*0.00, -W*1.10), (-L*0.80, -W*1.20), (-L*0.50, -W*0.40),
                    (-L*0.20, 0.00), (-L*0.50, W*0.40), (-L*0.80, W*1.20), (L*0.00, W*1.10)]
            lines += [[(L*0.40, 0), (-L*0.10, 0)], [(L*0.20, -W*0.30), (-L*0.60, -W*1.00)],
                      [(L*0.20, W*0.30), (-L*0.60, W*1.00)]]
            mode = "center"
            eng_center = (-L * 0.30, 0.0)

        elif s == "STEALTH":
            hull = [(L*0.75, 0.00), (L*0.20, -W*1.00), (-L*0.40, -W*1.00), (-L*0.80, -W*0.50),
                    (-L*0.50, -W*0.25), (-L*1.00, 0.00), (-L*0.50, W*0.25), (-L*0.80, W*0.50),
                    (-L*0.40, W*1.00), (L*0.20, W*1.00)]
            lines += [[(-L*0.40, 0), (L*0.50, 0)], [(L*0.20, -W*0.50), (-L*0.40, -W*0.50)],
                      [(L*0.20, W*0.50), (-L*0.40, W*0.50)]]
            mode = "center"

        elif s == "RIB_CAGE":
            hull = [(L*0.80, 0.00), (L*0.30, -W*0.40), (L*0.20, -W*0.70), (-L*0.10, -W*0.30),
                    (-L*0.50, -W*0.80), (-L*0.80, -W*0.30), (-L*1.10, -W*0.50), (-L*1.20, 0.00),
                    (-L*1.10, W*0.50), (-L*0.80, W*0.30), (-L*0.50, W*0.80), (-L*0.10, W*0.30),
                    (L*0.20, W*0.70), (L*0.30, W*0.40)]
            lines += [[(-L*0.90, 0), (L*0.60, 0)], [(L*0.20, -W*0.70), (0, 0)],
                      [(-L*0.50, -W*0.80), (0, 0)], [(L*0.20, W*0.70), (0, 0)],
                      [(-L*0.50, W*0.80), (0, 0)]]
            mode = "center"

        else:  # THRUSTER_FINS
            hull = [(L*0.90, 0.00), (L*0.30, -W*0.30), (-L*0.50, -W*0.45), (-L*0.80, -W*0.25),
                    (-L*0.90, -W*0.80), (-L*1.25, -W*0.80), (-L*1.10, -W*0.20), (-L*1.30, 0.00),
                    (-L*1.10, W*0.20), (-L*1.25, W*0.80), (-L*0.90, W*0.80), (-L*0.80, W*0.25),
                    (-L*0.50, W*0.45), (L*0.30, W*0.30)]
            lines += [[(-L*0.80, 0), (L*0.70, 0)], [(-L*0.85, -W*0.50), (-L*1.15, -W*0.50)],
                      [(-L*0.85, W*0.50), (-L*1.15, W*0.50)]]
            mode = "twin"
            eng_left = (-L * 1.15, -W * 0.50)
            eng_right = (-L * 1.15,  W * 0.50)

        lines = lines[:5]
        return hull, lines, mode, {"center": eng_center, "left": eng_left, "right": eng_right}

    @staticmethod
    def _bbox(points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _map_points(points, cx, cy, scale, ox, oy):
        out = []
        for x, y in points:
            out.append((cx + (x - ox) * scale, cy + (y - oy) * scale))
        return out

    @staticmethod
    def open_ship_codex(parent):
        win = tk.Toplevel(parent)
        win.title("飞船图鉴")
        win.attributes("-topmost", True)
        win.resizable(False, False)

        bg = "#15161b"
        fg = "#EAF2FF"
        accent = "#63ace5"
        hull_fill = "#2a4d69"
        hull_edge = "#4b86b4"
        eng = "#ff6f00"

        cols = 4
        cell_w, cell_h = 220, 220
        pad = 12
        top_margin = 40
        styles = CodexUI.SHIP_STYLES
        rows = (len(styles) + cols - 1) // cols

        canvas = tk.Canvas(win, width=cols * cell_w + pad * 2, height=rows * cell_h + top_margin + pad,
                           bg=bg, highlightthickness=0)
        canvas.pack()

        canvas.create_text(pad, pad, anchor="nw",
                           text="飞船图鉴（外形/装饰线/引擎位置）",
                           fill=fg, font=("Segoe UI", 12, "bold"))

        for idx, style in enumerate(styles):
            r = idx // cols
            c = idx % cols
            x0 = pad + c * cell_w
            y0 = top_margin + r * cell_h
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            canvas.create_rectangle(x0 + 6, y0 + 6, x1 - 6, y1 - 6,
                                    outline="#2b2f3a", width=1, fill="#101116")

            canvas.create_text(x0 + 14, y0 + 16, anchor="nw", text=style,
                               fill=fg, font=("Consolas", 11, "bold"))

            hull, lines, mode, engines = CodexUI.ship_shape(style, L=10.0, W=10.0)

            bx0, by0, bx1, by1 = CodexUI._bbox(hull)
            bw = max(1e-6, bx1 - bx0)
            bh = max(1e-6, by1 - by0)
            scale = min((cell_w * 0.78) / bw, (cell_h * 0.62) / bh)

            cx = (x0 + x1) * 0.5
            cy = y0 + (y1 - y0) * 0.55

            ox = (bx0 + bx1) * 0.5
            oy = (by0 + by1) * 0.5

            hull_m = CodexUI._map_points(hull, cx, cy, scale, ox, oy)
            hull_coords = []
            for x, y in hull_m:
                hull_coords += [x, y]

            canvas.create_polygon(*hull_coords, outline=hull_edge, fill=hull_fill, width=2)

            for ln in lines:
                ln_m = CodexUI._map_points(ln, cx, cy, scale, ox, oy)
                coords = []
                for x, y in ln_m:
                    coords += [x, y]
                canvas.create_line(*coords, fill=accent, width=2)

            def draw_engine(pt):
                ex, ey = CodexUI._map_points([pt], cx, cy, scale, ox, oy)[0]
                rr = 5
                canvas.create_oval(ex - rr, ey - rr, ex + rr, ey + rr,
                                   outline="#ffcc00", width=2, fill=eng)

            if mode == "center":
                draw_engine(engines["center"])
            else:
                draw_engine(engines["left"])
                draw_engine(engines["right"])

        btn = tk.Button(win, text="关闭", command=win.destroy, width=10)
        btn.pack(pady=(8, 10))
        return win

    @staticmethod
    def open_bullet_codex(parent):
        win = tk.Toplevel(parent)
        win.title("子弹图鉴")
        win.attributes("-topmost", True)
        win.resizable(False, False)

        bg = "#15161b"
        fg = "#EAF2FF"

        cols = 3
        kinds = CodexUI.BULLET_KINDS
        rows = (len(kinds) + cols - 1) // cols
        cell_w, cell_h = 240, 170
        pad = 12
        top_margin = 40

        canvas = tk.Canvas(win, width=cols * cell_w + pad * 2, height=rows * cell_h + top_margin + pad,
                           bg=bg, highlightthickness=0)
        canvas.pack()

        canvas.create_text(pad, pad, anchor="nw",
                           text="子弹图鉴（静态示意图）",
                           fill=fg, font=("Segoe UI", 12, "bold"))

        for idx, kind in enumerate(kinds):
            r = idx // cols
            c = idx % cols
            x0 = pad + c * cell_w
            y0 = top_margin + r * cell_h
            x1 = x0 + cell_w
            y1 = y0 + cell_h

            canvas.create_rectangle(x0 + 6, y0 + 6, x1 - 6, y1 - 6,
                                    outline="#2b2f3a", width=1, fill="#101116")
            canvas.create_text(x0 + 14, y0 + 16, anchor="nw", text=kind,
                               fill=fg, font=("Consolas", 11, "bold"))

            cx = (x0 + x1) * 0.5
            cy = y0 + (y1 - y0) * 0.55

            if kind == "LASER":
                canvas.create_line(cx - 70, cy, cx + 70, cy, fill="#66B3FF", width=2)
                canvas.create_line(cx - 50, cy - 8, cx + 50, cy - 8, fill="#EAF2FF", width=1, dash=(3, 6))

            elif kind == "PLASMA":
                canvas.create_line(cx - 80, cy, cx - 10, cy, fill="#FFD966", width=2, smooth=True)
                canvas.create_line(cx - 80, cy + 10, cx - 10, cy + 10, fill="#FFB86B", width=2, dash=(2, 6))
                canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, outline="#FFD966", width=2)

            elif kind == "SPARK":
                for _ in range(8):
                    dx = random.randint(-60, 60)
                    dy = random.randint(-25, 25)
                    rr = random.choice([2, 2, 3])
                    col = random.choice(["#FF6B6B", "#FFD966"])
                    canvas.create_oval(cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr,
                                       outline=col, width=2)

            elif kind == "WAVE":
                pts = []
                for i in range(0, 13):
                    t = i / 12.0
                    x = cx - 80 + t * 160
                    y = cy + math.sin(t * math.tau * 2.0) * 16
                    pts += [x, y]
                canvas.create_line(*pts, fill="#B388FF", width=2, smooth=True)

            elif kind == "SHARD":
                canvas.create_polygon(cx + 70, cy,
                                      cx - 30, cy - 24,
                                      cx - 20, cy,
                                      outline="#ECFFF6", fill="", width=2)
                canvas.create_polygon(cx + 70, cy,
                                      cx - 30, cy + 24,
                                      cx - 20, cy,
                                      outline="#EAF2FF", fill="", width=2)

            desc_map = {
                "LASER": "细直线激光（可虚线）",
                "PLASMA": "发光球 + 尾迹",
                "SPARK": "星火碎点散射",
                "WAVE": "正弦波动轨迹",
                "SHARD": "尖刺碎片三角",
            }
            canvas.create_text(cx, y1 - 24, anchor="s",
                               text=desc_map.get(kind, ""),
                               fill="#AAB2C5", font=("Segoe UI", 10))

        btn = tk.Button(win, text="关闭", command=win.destroy, width=10)
        btn.pack(pady=(8, 10))
        return win

    @staticmethod
    def open_help(parent):
        win = tk.Toplevel(parent)
        win.title("游戏说明")
        win.attributes("-topmost", True)
        win.resizable(False, False)

        bg = "#15161b"
        fg = "#EAF2FF"
        minor = "#AAB2C5"

        text = (
            "【玩法说明】\n"
            "1）本程序有两种模式：\n"
            "   - 屏保模式：只有飞船/星球漂浮（无子弹、无爆炸）。\n"
            "   - 游戏模式：飞船会开火；你可以“捕获”飞船触发爆炸并计数。\n\n"
            "2）操作方式（游戏模式）：\n"
            "   - 你的“武器/手”就是鼠标指针。\n"
            "   - 鼠标靠近飞船：飞船会尝试逃跑（FLEE）。\n"
            "   - 鼠标非常贴近并保持短暂时间：飞船爆炸（计入击败数）。\n"
            "   - 飞船会在你靠近时射击（不同飞船随机不同子弹特效）。\n\n"
            "3）难度系统：\n"
            "   - 自动升级：从 Lv.1 开始，每达到“升级所需击败数”自动升一级。\n"
            "   - 手动等级：关闭自动升级后可选择 Lv.1~Lv.11。\n"
            "   - 等级越高：飞船更快、转向更灵活、逃跑更敏捷。\n\n"
            "4）快捷键：\n"
            "   - ESC：退出全屏叠加层\n"
            "   - Ctrl + Shift + Q：退出全屏叠加层\n\n"
            "5）控制面板：\n"
            "   - 可实时切换透明背景/不透明深灰渐变背景。\n"
            "   - 可实时调整飞船/星球大小滑块。\n"
            "   - 游戏模式下可调整等级/自动升级/升级阈值。\n"
        )

        frm = tk.Frame(win, bg=bg, padx=14, pady=14)
        frm.pack(fill="both", expand=True)

        title = tk.Label(frm, text="舰队爆炸！！！— 中文玩法说明", bg=bg, fg=fg,
                         font=("Segoe UI", 13, "bold"))
        title.pack(anchor="w")

        msg = tk.Message(frm, text=text, width=560, bg=bg, fg=fg,
                         font=("Segoe UI", 11))
        msg.pack(anchor="w", pady=(10, 8))

        tip = tk.Label(frm, text="提示：你也可以打开【飞船图鉴 / 子弹图鉴】查看所有外观与特效。", bg=bg, fg=minor,
                       font=("Segoe UI", 10, "bold"))
        tip.pack(anchor="w", pady=(4, 10))

        btn = tk.Button(frm, text="关闭", command=win.destroy, width=10)
        btn.pack(anchor="e")

        return win


# -----------------------
# 透明叠加层（管理：飞船、爆炸、子弹）+ 支持实时大小滑块
# -----------------------
class TransparentOverlay:
    def __init__(self, overlay_win, config: dict, on_stop_callback=None):
        self.win = overlay_win
        self.on_stop_callback = on_stop_callback

        self.w = overlay_win.winfo_screenwidth()
        self.h = overlay_win.winfo_screenheight()

        self.mode = config["mode"]
        self.num_ships = int(config["ships"])
        self.num_planets = int(config["planets"])
        self.auto_level = bool(config.get("auto_level", False))
        self.level = int(config.get("level", 1))

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

        self.ships = [
            SciFiShip(
                self.canvas, self.w, self.h, style=st,
                enable_bullets=self.enable_bullets,
                enable_explosions=self.enable_explosions,
                on_explode=self._on_ship_explode,
                ship_scale_getter=self.get_ship_scale
            )
            for st in style_list
        ]
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

    # ---- 新增：供滑块实时读取/设置 ----
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

    def _draw_gradient_bg(self):
        self._clear_gradient_bg()

        # 1) 纵向渐变
        steps = 220
        r1, g1, b1 = self.grad_top
        r2, g2, b2 = self.grad_bottom
        for i in range(steps):
            t = i / max(1, steps - 1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            col = self._rgb_to_hex(r, g, b)

            y0 = int(self.h * (i / steps))
            y1 = int(self.h * ((i + 1) / steps)) + 1
            it = self.canvas.create_rectangle(0, y0, self.w, y1, outline="", fill=col)
            self._bg_items.append(it)

        # 2) 斜向雾化条纹（很淡）
        stripe_gap = 42
        stripe_width = 14
        base = 30
        for x in range(-self.h, self.w, stripe_gap):
            jitter = random.randint(-5, 5)
            v = max(0, min(255, base + jitter))
            col = self._rgb_to_hex(v, v, v)
            it = self.canvas.create_line(
                x, 0, x + self.h, self.h,
                fill=col,
                width=stripe_width,
                capstyle=tk.ROUND
            )
            self._bg_items.append(it)

        # 3) 星尘点（稀疏）
        dust = int((self.w * self.h) / 52000)
        for _ in range(dust):
            x = random.randint(0, self.w)
            y = random.randint(0, self.h)
            v = random.choice([55, 60, 70, 85, 100, 120])
            col = self._rgb_to_hex(v, v, v)
            rr = random.choice([1, 1, 1, 2])
            it = self.canvas.create_oval(x - rr, y - rr, x + rr, y + rr, outline="", fill=col)
            self._bg_items.append(it)

        self._bg_send_to_back()

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

    def _respawn_ship(self, idx):
        try:
            self.ships[idx].destroy()
        except Exception:
            pass
        self.ships[idx] = SciFiShip(
            self.canvas, self.w, self.h, style=None,
            enable_bullets=self.enable_bullets,
            enable_explosions=self.enable_explosions,
            on_explode=self._on_ship_explode,
            ship_scale_getter=self.get_ship_scale
        )
        self.ships[idx].set_difficulty(self.level)
        # ✅ 子弹 life/dist 固定，不随难度变化：无需再 set_bullet_limits

    def _apply_level(self, level: int):
        self.level = max(1, min(11, int(level)))

        for s in self.ships:
            s.set_difficulty(self.level)

        # ✅ 子弹 life/dist 固定，不随难度变化：这里不再根据等级改 bullet 限制

        if self.counter_text is not None:
            self.canvas.itemconfig(
                self.counter_text,
                text=f"爆炸: {self.explode_count}   等级: {self.level}   升级阈值: {self.level_step}"
            )

    def _show_levelup_fx(self, new_level: int):
        cx = self.w // 2
        cy = self.h // 2

        txt = self.canvas.create_text(
            cx, cy,
            text=f"难度提升 → Lv.{new_level}",
            fill="#FFD966",
            font=("Segoe UI", 30, "bold"),
            anchor="center"
        )
        ring = self.canvas.create_oval(cx-10, cy-10, cx+10, cy+10, outline="#66B3FF", width=2, dash=(3, 6))
        self.center_fx_items += [txt, ring]

        start = time.time()
        D = 2.55

        def step():
            if not self._running:
                return
            t = time.time() - start
            if t >= D:
                for it in self.center_fx_items:
                    try:
                        self.canvas.delete(it)
                    except Exception:
                        pass
                self.center_fx_items.clear()
                return

            k = t / D
            r = 22 + 220 * k
            self.canvas.coords(ring, cx-r, cy-r, cx+r, cy+r)
            # 删除判断，直接保持显示状态
            # if int(t * 1) % 2 == 0:
            #     self.canvas.itemconfig(txt, state="normal")
            # else:
            #     self.canvas.itemconfig(txt, state="hidden")
            self.canvas.itemconfig(txt, state="normal")
            self.win.after(16, step)

        step()

    def _on_ship_explode(self):
        if self.mode != "game":
            return

        self.explode_count += 1
        if self.counter_text is not None:
            self.canvas.itemconfig(
                self.counter_text,
                text=f"爆炸: {self.explode_count}   等级: {self.level}   升级阈值: {self.level_step}"
            )

        if self.explode_count % self.level_step == 0:
            if self.auto_level:
                new_level = min(11, 1 + self.explode_count // self.level_step)
                if new_level != self.level:
                    self._apply_level(new_level)
                    self._show_levelup_fx(new_level)
            else:
                self._show_levelup_fx(self.level)

    def animate(self):
        if not self._running:
            return

        now = time.time()
        dt = max(0.001, now - self._last_t)
        self._last_t = now

        mx = self.win.winfo_pointerx()
        my = self.win.winfo_pointery()

        for p in self.planets:
            p.update(dt)

        for i, s in enumerate(self.ships):
            alive = s.update(mx, my)
            if self.enable_bullets:
                s.try_shoot(mx, my, dt, self.bullets)
            if s.exploding and alive is False:
                self._respawn_ship(i)

        if self.enable_bullets:
            new_bullets = []
            for b in self.bullets:
                if b.update(dt, self.w, self.h):
                    new_bullets.append(b)
            self.bullets = new_bullets

        if (not self.transparent_bg) and self._bg_items:
            self._bg_send_to_back()
        try:
            self.canvas.tag_raise(self.exit_hint)
        except Exception:
            pass

        self.win.after(8, self.animate)


# -----------------------
# Windows 可选：点击穿透（不挡鼠标）
# -----------------------
def enable_click_through_windows(win):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


# -----------------------
# 启动配置窗口 + 控制面板
# -----------------------
class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("舰队爆炸！！！")
        self.root.resizable(False, False)

        self.mode_var = tk.StringVar(value="screensaver")
        self.planets_var = tk.StringVar(value="6")
        self.ships_var = tk.StringVar(value="10")

        self.level_var = tk.IntVar(value=1)
        self.auto_var = tk.BooleanVar(value=True)

        self.level_step_var = tk.StringVar(value="10")
        self.transparent_bg_var = tk.BooleanVar(value=True)

        # ✅ 新增：初始大小（滑块范围 0.3~2.5）
        self.ship_scale_var = tk.DoubleVar(value=1.0)
        self.planet_scale_var = tk.DoubleVar(value=1.0)

        self.overlay = None
        self.control_panel = None

        self._build()

    def _build(self):
        pad = 10
        frm = tk.Frame(self.root, padx=pad, pady=pad)
        frm.pack()

        mbox = tk.LabelFrame(frm, text="模式", padx=pad, pady=pad)
        mbox.grid(row=0, column=0, columnspan=2, sticky="ew")

        tk.Radiobutton(mbox, text="屏保模式（无子弹/无爆炸）", value="screensaver",
                       variable=self.mode_var, command=self._refresh_mode_ui).grid(row=0, column=0, sticky="w")
        tk.Radiobutton(mbox, text="游戏模式（有子弹/爆炸/难度）", value="game",
                       variable=self.mode_var, command=self._refresh_mode_ui).grid(row=1, column=0, sticky="w")

        tk.Label(frm, text="星球数量：").grid(row=1, column=0, sticky="e", pady=(10, 0))
        tk.Entry(frm, textvariable=self.planets_var, width=8).grid(row=1, column=1, sticky="w", pady=(10, 0))

        tk.Label(frm, text="飞船数量：").grid(row=2, column=0, sticky="e", pady=(6, 0))
        tk.Entry(frm, textvariable=self.ships_var, width=8).grid(row=2, column=1, sticky="w", pady=(6, 0))

        tk.Checkbutton(frm, text="透明背景（不勾选=深灰渐变不透明底）",
                       variable=self.transparent_bg_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        sbox = tk.LabelFrame(frm, text="大小（启动初始值）", padx=pad, pady=pad)
        sbox.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        tk.Label(sbox, text="飞船大小：").grid(row=0, column=0, sticky="e")
        tk.Scale(sbox, from_=0.3, to=2.5, resolution=0.05, orient="horizontal",
                 variable=self.ship_scale_var, length=220).grid(row=0, column=1, sticky="w")

        tk.Label(sbox, text="星球大小：").grid(row=1, column=0, sticky="e", pady=(6, 0))
        tk.Scale(sbox, from_=0.3, to=2.5, resolution=0.05, orient="horizontal",
                 variable=self.planet_scale_var, length=220).grid(row=1, column=1, sticky="w", pady=(6, 0))

        gbox = tk.LabelFrame(frm, text="游戏设置", padx=pad, pady=pad)
        gbox.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        tk.Checkbutton(gbox, text="自动难度：从 Lv.1 开始，按击败数自动升一级",
                       variable=self.auto_var, command=self._refresh_mode_ui).grid(row=0, column=0, columnspan=3, sticky="w")

        tk.Label(gbox, text="手动等级：").grid(row=1, column=0, sticky="e", pady=(6, 0))
        self.level_spin = tk.Spinbox(gbox, from_=1, to=11, width=6, textvariable=self.level_var)
        self.level_spin.grid(row=1, column=1, sticky="w", pady=(6, 0))
        tk.Label(gbox, text="(1~11)").grid(row=1, column=2, sticky="w", pady=(6, 0))

        tk.Label(gbox, text="升级所需击败数：").grid(row=2, column=0, sticky="e", pady=(6, 0))
        tk.Entry(gbox, textvariable=self.level_step_var, width=8).grid(row=2, column=1, sticky="w", pady=(6, 0))
        tk.Label(gbox, text="(默认10)").grid(row=2, column=2, sticky="w", pady=(6, 0))

        btns = tk.Frame(frm, pady=10)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew")
        tk.Button(btns, text="开始", width=12, command=self.start).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="退出", width=12, command=self.root.destroy).pack(side="left")

        tk.Label(frm, text="作者：段小油  |  版本：1.0", fg="#666").grid(row=7, column=0, columnspan=2, sticky="w")

        self._refresh_mode_ui()

    def _refresh_mode_ui(self):
        mode = self.mode_var.get()
        if mode != "game":
            self.level_spin.config(state="disabled")
        else:
            if self.auto_var.get():
                self.level_spin.config(state="disabled")
            else:
                self.level_spin.config(state="normal")

    def _safe_int(self, s, default, lo, hi):
        try:
            v = int(str(s).strip())
            return max(lo, min(hi, v))
        except Exception:
            return default

    # --- 新增：图鉴/说明按钮回调 ---
    def _open_ship_codex(self):
        parent = self.control_panel if self.control_panel is not None else self.root
        CodexUI.open_ship_codex(parent)

    def _open_bullet_codex(self):
        parent = self.control_panel if self.control_panel is not None else self.root
        CodexUI.open_bullet_codex(parent)

    def _open_help(self):
        parent = self.control_panel if self.control_panel is not None else self.root
        CodexUI.open_help(parent)

    def start(self):
        if self.overlay is not None:
            return

        planets = self._safe_int(self.planets_var.get(), 6, 0, 80)
        ships = self._safe_int(self.ships_var.get(), 10, 1, 80)
        mode = self.mode_var.get()

        if mode == "game":
            auto = bool(self.auto_var.get())
            level = int(self.level_var.get())
            if auto:
                level = 1
        else:
            auto = False
            level = 1

        level_step = self._safe_int(self.level_step_var.get(), 10, 1, 9999)
        transparent_bg = bool(self.transparent_bg_var.get())

        config = {
            "mode": mode,
            "planets": planets,
            "ships": ships,
            "level": level,
            "auto_level": auto,
            "level_step": level_step,
            "transparent_bg": transparent_bg,
            "ship_scale": float(self.ship_scale_var.get()),
            "planet_scale": float(self.planet_scale_var.get()),
        }

        self.root.withdraw()

        ov = tk.Toplevel(self.root)
        self.overlay = TransparentOverlay(ov, config=config, on_stop_callback=self._on_overlay_stop)

        # ✅ 仅透明模式启用点击穿透；不透明全屏需要能接收鼠标/焦点更稳定
        if transparent_bg:
            enable_click_through_windows(ov)

        self._open_control_panel(config)

    def _open_control_panel(self, config):
        cp = tk.Toplevel(self.root)
        self.control_panel = cp
        cp.title("舰队爆炸！！！")
        cp.attributes("-topmost", True)
        cp.resizable(False, False)

        pad = 10
        frm = tk.Frame(cp, padx=pad, pady=pad)
        frm.pack()

        tk.Label(frm, text=f"模式：{'游戏' if config['mode']=='game' else '屏保'}").grid(row=0, column=0, columnspan=3, sticky="w")

        self.live_transparent_var = tk.BooleanVar(value=self.overlay.transparent_bg)
        tk.Checkbutton(frm, text="透明背景（取消=深灰渐变底）", variable=self.live_transparent_var,
                       command=self._toggle_live_bg).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        sizebox = tk.LabelFrame(frm, text="实时大小调整", padx=8, pady=8)
        sizebox.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        self.live_ship_scale_var = tk.DoubleVar(value=float(getattr(self.overlay, "ship_scale", 1.0)))
        self.live_planet_scale_var = tk.DoubleVar(value=float(getattr(self.overlay, "planet_scale", 1.0)))

        tk.Label(sizebox, text="飞船大小：").grid(row=0, column=0, sticky="e")
        self.ship_scale_slider = tk.Scale(
            sizebox, from_=0.3, to=2.5, resolution=0.05, orient="horizontal",
            variable=self.live_ship_scale_var, length=260,
            command=lambda v: self._apply_live_scales()
        )
        self.ship_scale_slider.grid(row=0, column=1, sticky="w")

        tk.Label(sizebox, text="星球大小：").grid(row=1, column=0, sticky="e", pady=(6, 0))
        self.planet_scale_slider = tk.Scale(
            sizebox, from_=0.3, to=2.5, resolution=0.05, orient="horizontal",
            variable=self.live_planet_scale_var, length=260,
            command=lambda v: self._apply_live_scales()
        )
        self.planet_scale_slider.grid(row=1, column=1, sticky="w", pady=(6, 0))

        row_base = 3

        if config["mode"] == "game":
            self.live_level_var = tk.IntVar(value=self.overlay.level)
            self.live_auto_var = tk.BooleanVar(value=self.overlay.auto_level)
            self.live_step_var = tk.IntVar(value=self.overlay.level_step)

            tk.Checkbutton(frm, text="自动升级", variable=self.live_auto_var,
                           command=self._toggle_live_auto).grid(row=row_base, column=0, columnspan=3, sticky="w", pady=(10, 0))

            tk.Label(frm, text="等级：").grid(row=row_base + 1, column=0, sticky="e", pady=(6, 0))
            self.live_level_spin = tk.Spinbox(frm, from_=1, to=11, width=6, textvariable=self.live_level_var,
                                              command=self._apply_live_level)
            self.live_level_spin.grid(row=row_base + 1, column=1, sticky="w", pady=(6, 0))
            tk.Button(frm, text="应用", width=8, command=self._apply_live_level).grid(row=row_base + 1, column=2, padx=(6, 0), pady=(6, 0))

            tk.Label(frm, text="升级所需击败数：").grid(row=row_base + 2, column=0, sticky="e", pady=(6, 0))
            tk.Spinbox(frm, from_=1, to=9999, width=6, textvariable=self.live_step_var).grid(row=row_base + 2, column=1, sticky="w", pady=(6, 0))
            tk.Button(frm, text="应用", width=8, command=self._apply_live_step).grid(row=row_base + 2, column=2, padx=(6, 0), pady=(6, 0))

            self._sync_live_level_widgets()

            row_end = row_base + 3
        else:
            row_end = row_base

        codex_bar = tk.Frame(frm)
        codex_bar.grid(row=row_end, column=0, columnspan=3, pady=(12, 0), sticky="ew")
        tk.Button(codex_bar, text="飞船图鉴", width=10, command=self._open_ship_codex).pack(side="left", padx=(0, 6))
        tk.Button(codex_bar, text="子弹图鉴", width=10, command=self._open_bullet_codex).pack(side="left", padx=(0, 6))
        tk.Button(codex_bar, text="游戏说明", width=10, command=self._open_help).pack(side="left")

        tk.Button(frm, text="结束", width=14, command=self.stop).grid(row=row_end + 1, column=0, columnspan=3, pady=(12, 0))

        cp.protocol("WM_DELETE_WINDOW", lambda: cp.withdraw())

    def _apply_live_scales(self):
        if self.overlay is None:
            return
        try:
            ss = float(self.live_ship_scale_var.get())
        except Exception:
            ss = 1.0
        try:
            ps = float(self.live_planet_scale_var.get())
        except Exception:
            ps = 1.0
        self.overlay.set_scales(ship_scale=ss, planet_scale=ps)

    def _toggle_live_bg(self):
        if self.overlay is None:
            return
        self.overlay.set_background_transparent(bool(self.live_transparent_var.get()))

    def _toggle_live_auto(self):
        if self.overlay is None:
            return
        self.overlay.auto_level = bool(self.live_auto_var.get())
        if self.overlay.auto_level:
            new_level = min(11, 1 + self.overlay.explode_count // self.overlay.level_step)
            self.overlay._apply_level(new_level)
            self.live_level_var.set(self.overlay.level)
        self._sync_live_level_widgets()

    def _sync_live_level_widgets(self):
        if self.overlay is None:
            return
        if not hasattr(self, "live_level_spin"):
            return
        if self.live_auto_var.get():
            self.live_level_spin.config(state="disabled")
        else:
            self.live_level_spin.config(state="normal")

    def _apply_live_step(self):
        if self.overlay is None:
            return
        try:
            step = int(self.live_step_var.get())
        except Exception:
            step = 10
        step = max(1, min(9999, step))
        self.overlay.level_step = step

        if getattr(self.overlay, "auto_level", False):
            new_level = min(11, 1 + self.overlay.explode_count // self.overlay.level_step)
            self.overlay._apply_level(new_level)
            if hasattr(self, "live_level_var"):
                self.live_level_var.set(self.overlay.level)

        if getattr(self.overlay, "counter_text", None) is not None:
            self.overlay.canvas.itemconfig(
                self.overlay.counter_text,
                text=f"爆炸: {self.overlay.explode_count}   等级: {self.overlay.level}   升级阈值: {self.overlay.level_step}"
            )

    def _apply_live_level(self):
        if self.overlay is None:
            return
        if getattr(self.overlay, "auto_level", False):
            return
        try:
            lv = int(self.live_level_var.get())
        except Exception:
            lv = 1
        self.overlay._apply_level(lv)
        self.live_level_var.set(self.overlay.level)

    def stop(self):
        if self.overlay is not None:
            try:
                self.overlay.stop()
            except Exception:
                pass

    def _on_overlay_stop(self):
        self.overlay = None
        try:
            if self.control_panel is not None:
                self.control_panel.destroy()
        except Exception:
            pass
        self.control_panel = None
        self.root.deiconify()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    LauncherUI().run()
