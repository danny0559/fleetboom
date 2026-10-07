"""Player ability placement, two-click portals, cancellation and transient links."""
import math
import random
import time
import tkinter as tk
from .config import COSTS, NAMES, COLORS
from .celestials import TacticalCelestial


class AbilitiesMixin:
    def set_tool(self, tool):
        if tool != self.tool:
            self.cancel_portal()
        self.last_activity = self.visual_elapsed
        super().set_tool(tool)

    def spawn_event(self, event):
        # Clicking HUD selects a tool without dropping an unwanted body beneath it.
        current = self.canvas.find_withtag("current")
        if current and "challenge_hud" in self.canvas.gettags(current[0]):
            return
        self.spawn(self.tool, event.x, event.y)

    def spawn(self, kind, x, y):
        self.last_pointer_input = self.visual_elapsed
        if self.paused or self.round.ended:
            return False
        x, y = max(90, min(self.w-90, x)), max(140, min(self.h-100, y))
        if self.pending_portal:
            px, py, price_tool = self.pending_portal
            if math.hypot(x-px, y-py) < 140:
                self.notice("出口再放远一点 · 右键取消")
                return False
            if self.mode == "game" and not self.round.spend(price_tool):
                self.notice("能量不足，追击飞船回能后再放出口 · 右键取消")
                return False
            self.cancel_portal()
            self.add_body("WORMHOLE", px, py, (x, y))
            line = self.canvas.create_line(px, py, x, y, fill="#7bb6ce", width=1,
                                          dash=(3, 7), arrow=tk.LAST, tags="portal_link")
            self.portal_links.append([line, 0.0])
            self.last_spawn = time.monotonic()
            self.notice("虫洞已连接 · 蓝色入口 → 紫色出口")
            self.refresh_hud()
            return True
        for body in reversed(self.celestials):
            if body.kind == "BLACK_HOLE" and math.hypot(x-body.x, y-body.y) <= body.click_radius:
                return self.detonate(body)
        now = time.monotonic()
        if now-self.last_spawn < .35:
            return False
        if self.mode == "game" and self.round.energy < COSTS[kind]:
            self.notice(f"能量不足：{NAMES[kind]}需要 {COSTS[kind]} · 追击飞船恢复能量")
            return False
        actual = random.choice(tuple(COLORS)) if kind == "RANDOM" else kind
        if actual == "WORMHOLE":
            # Keep the quoted cost; random portals still cost only the random price.
            self.pending_portal = (x, y, kind)
            self.canvas.create_oval(x-26, y-26, x+26, y+26, outline="#82efff", width=2,
                                    dash=(4, 5), tags="portal_preview")
            self.preview_line = self.canvas.create_line(x, y, x, y, fill="#638b9d",
                                dash=(3, 8), arrow=tk.LAST, tags="portal_preview")
            self.notice("入口已选 · 再点一次放出口，右键取消（完成后扣能量）")
            return True
        if self.mode == "game":
            self.round.spend(kind)
        self.add_body(actual, x, y)
        self.last_spawn = now
        if actual == "BLACK_HOLE":
            self.notice("黑洞已部署 · 吞噬蓄能后，再点核心引爆")
        else:
            self.notice("恒星已部署 · 聚船后追上一艘，触发连锁 BOOM")
        self.refresh_hud()
        return True

    def add_body(self, kind, x, y, destination=None):
        if len(self.celestials) >= 6:
            self.celestials.pop(0).destroy()
        body = TacticalCelestial(self.canvas, kind, x, y, destination, self.art)
        self.celestials.append(body)
        body.update(.001)
        return body

    def cancel_portal(self):
        self.pending_portal = None
        self.canvas.delete("portal_preview")

    def clear_space(self):
        self.cancel_portal()
        self.canvas.delete("portal_link")
        self.portal_links.clear()
        super().clear_space()

    def update_portal_preview(self, dt, mx, my):
        if self.pending_portal:
            x, y, _ = self.pending_portal
            self.canvas.coords(self.preview_line, x, y, max(90, min(self.w-90, mx)),
                               max(140, min(self.h-100, my)))
        alive = []
        for link in self.portal_links:
            link[1] += dt
            if link[1] >= 1:
                self.canvas.delete(link[0])
            else:
                alive.append(link)
        self.portal_links = alive
