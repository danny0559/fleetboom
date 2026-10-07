"""Black-hole, portal and star artwork, orbit guides and charge indicators."""
import math
import tkinter as tk
from .config import (COLORS, NAMES, ORBITS, BLACK_HOLE_LIFE,
                     BLACK_HOLE_GROWTH_PER_SHIP, BLACK_HOLE_MAX_SCALE,
                     BLACK_HOLE_GROWTH_TIME)


class Celestial:
    def __init__(self, canvas, kind, x, y, destination=None, art=None):
        self.canvas, self.kind = canvas, kind
        self.x, self.y = x, y
        self.destination = destination
        self.age = 0.0
        self.visual_scale = 1.0
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
        if self.kind == "BLACK_HOLE":
            grow *= self.visual_scale
        pulse = 1 + .06 * math.sin(self.age * 3)
        if self.kind == "BLACK_HOLE" and self.art:
            # Quantized image sizes share a bounded cache across all black holes.
            step = max(0, round((356*grow-36)/20))
            self.frame = self.art.hole(step)
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


class TacticalCelestial(Celestial):
    ORBITS = ORBITS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.charge = 0
        self.residents = 0
        self.orbit_items = []
        self.charge_glow = None
        if self.kind == "STAR":
            self.radius = 280
            self.orbit_items = [self.canvas.create_oval(self.x-r, self.y-r*.38,
                                self.x+r, self.y+r*.38, outline="#49382b", width=1,
                                dash=(2, 8), tags=self.tag) for r in self.ORBITS]
            for item in self.orbit_items:
                self.canvas.tag_lower(item, self.core)
        elif self.kind == "BLACK_HOLE":
            self.life = BLACK_HOLE_LIFE
            self.charge_glow = self.canvas.create_line(0, 0, 1, 1, smooth=True,
                                  fill="#5b3921", tags=self.tag)

    @property
    def capture_radius(self):
        return 43*self.visual_scale

    @property
    def click_radius(self):
        return 62*self.visual_scale

    def update(self, dt):
        if self.kind == "BLACK_HOLE":
            target = min(BLACK_HOLE_MAX_SCALE, 1+self.charge*BLACK_HOLE_GROWTH_PER_SHIP)
            self.visual_scale += (target-self.visual_scale)*(1-math.exp(-max(0, dt)/BLACK_HOLE_GROWTH_TIME))
            self.radius = 230*self.visual_scale
        if not super().update(dt):
            return False
        c = self.canvas
        if self.kind == "WORMHOLE":
            c.itemconfig(self.label, text=f"入口 ↓ · {math.ceil(self.life-self.age)}s")
            if hasattr(self, "exit_label"):
                c.itemconfig(self.exit_label, text="出口 ↑")
        elif self.kind == "STAR":
            power = min(1, self.residents/12)
            color = self.mix("#49382b", "#e9b56e", power)
            for item in self.orbit_items:
                c.itemconfig(item, outline=color)
            c.itemconfig(self.surface[0], fill=self.mix("#562b24", "#ce8b36", power))
            c.itemconfig(self.surface[-1], fill=self.mix("#fff3c7", "#ffffff", power))
            c.itemconfig(self.label, text=f"恒星 · 聚集 {self.residents} 艘 · {math.ceil(self.life-self.age)}s")
        elif self.kind == "BLACK_HOLE":
            power = min(1, self.charge/12)
            coords = []
            for i in range(65):
                a = i*math.tau/64
                grow = min(1, self.age/.45, (self.life-self.age)/.8)
                r = (127+8*power)*self.visual_scale*grow*(1+.02*math.sin(self.age*4))
                coords.extend((self.x+math.cos(a)*r, self.y+math.sin(a)*r*.29+math.cos(a)*r*.16))
            c.coords(self.charge_glow, *coords)
            c.itemconfig(self.charge_glow, fill=self.mix("#5b3921", "#ffe9b1", power), width=1+3*power)
            c.itemconfig(self.label, text=f"蓄能 {self.charge} · 点击引爆 · {math.ceil(self.life-self.age)}s")
        return True

    @staticmethod
    def mix(start, end, amount):
        return "#"+"".join(f"{round(int(start[i:i+2],16)*(1-amount)+int(end[i:i+2],16)*amount):02x}"
                          for i in (1, 3, 5))
