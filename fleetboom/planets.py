"""Decorative drifting planets and their live size controls."""
import math
import random
import tkinter as tk


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
