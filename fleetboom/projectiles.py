"""Canvas projectile appearance, trails and lifetime management."""
import math
import random
import tkinter as tk


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
