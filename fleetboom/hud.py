"""Small HUD, auto-hide behavior, tool dock, pause and result cards."""
import math
import tkinter as tk
from .config import COSTS, NAMES


class HudMixin:
    def build_hud(self):
        c = self.canvas
        c.create_rectangle(18, 18, 365, 91, fill="#091322",
                           outline="#24415d", tags=("challenge_hud", "hud_stats"))
        if self.counter_text:
            c.addtag_withtag("challenge_hud", self.counter_text)
            c.addtag_withtag("hud_stats", self.counter_text)
            c.coords(self.counter_text, 31, 29)
            c.itemconfig(self.counter_text, font=("Microsoft YaHei UI", 11, "bold"))
        else:
            c.create_text(24, 22, text="FLEET BOOM / 星海屏保", anchor="nw", fill="#eaf2ff",
                          font=("Segoe UI", 12, "bold"), tags=("challenge_hud", "hud_stats"))
        c.addtag_withtag("challenge_hud", self.exit_hint)
        c.addtag_withtag("hud_help", self.exit_hint)
        c.coords(self.exit_hint, 24, self.h-24)
        c.itemconfig(self.exit_hint, anchor="sw", text="左键创造天体 · 追上飞船 BOOM · G 挑战 / V 漫游 · H 工具 · F2 设置 · ESC 返回",
                     font=("Microsoft YaHei UI", 9), fill="#7695ae")
        self.energy_text = c.create_text(31, 55, anchor="nw", fill="#9aeaff",
                         font=("Microsoft YaHei UI", 10), tags=("challenge_hud", "hud_stats"))
        c.create_rectangle(31, 79, 155, 82, fill="#1a3046", outline="", tags=("challenge_hud", "hud_stats"))
        self.energy_bar = c.create_rectangle(31, 79, 118, 82, fill="#59d9ee", outline="", tags=("challenge_hud", "hud_stats"))
        self.chain_text = c.create_text(self.w/2, 118, fill="#ffdb8e",
                          font=("Segoe UI", 18, "bold"), tags="challenge_hud")
        self.notice_text = c.create_text(self.w/2, self.h-98, fill="#ffce86", width=min(530, self.w-60),
                           font=("Microsoft YaHei UI", 10), tags="challenge_hud")
        width = min(580, self.w-40)
        x0 = (self.w-width)/2
        for i, tool in enumerate(COSTS):
            left = x0+i*width/4
            tag = f"tool_{tool}"
            c.create_rectangle(left+3, self.h-68, left+width/4-3, self.h-30,
                               fill="#10243a", outline="#335773", tags=("challenge_hud", "hud_tools", tag))
            price = f"{COSTS[tool]}能量" if self.mode == "game" else "免费"
            label = f"{i}  {NAMES[tool]}  ·  {price}"
            c.create_text(left+width/8, self.h-49, text=label, fill="#d8eaf5",
                          font=("Microsoft YaHei UI", 10), tags=("challenge_hud", "hud_tools", tag))
            c.tag_bind(tag, "<Button-1>", lambda e, k=tool: self.choose_tool(k))
        self.hud_ready = True
        self.refresh_hud()

    def choose_tool(self, tool):
        self.set_tool(tool)
        return "break"

    def toggle_hud(self):
        self.hud_pinned = not self.hud_pinned
        self.last_activity = self.visual_elapsed
        self.refresh_hud()

    def update_visibility(self):
        c = self.canvas
        recent = self.visual_elapsed-self.last_activity < 4
        show_stats = self.hud_pinned or recent or (self.mode == "game" and not self.ambient and not self.round.ended)
        c.itemconfig("hud_stats", state="normal" if show_stats else "hidden")
        c.itemconfig("hud_tools", state="normal" if self.hud_pinned or self.dock_hover else "hidden")
        c.itemconfig("hud_help", state="normal" if self.hud_pinned or self.visual_elapsed < 6 else "hidden")
        for body in self.celestials:
            c.itemconfig(body.label, state="normal" if show_stats else "hidden")
            if hasattr(body, "exit_label"):
                c.itemconfig(body.exit_label, state="normal" if show_stats else "hidden")

    def refresh_hud(self):
        if not self.hud_ready:
            return
        c = self.canvas
        if self.counter_text:
            c.itemconfig(self.counter_text, text=
                (f"漫游  /  {self.round.score:,} 分   连锁 ×{self.round.best_chain}" if self.ambient else
                 f"{math.ceil(self.round.remaining):02d}s  /  {self.round.score:,} 分   连锁 ×{self.round.best_chain}"),
                fill="#ffb775" if not self.ambient and self.round.remaining <= 15 else "#eaf2ff")
        c.itemconfig(self.energy_text, text=(
            f"能量 {int(self.round.energy)}   ·   {NAMES[self.tool]} {COSTS[self.tool]}"
            if self.mode == "game" else "自由星海 · 天体免费"))
        c.coords(self.energy_bar, 31, 79, 31+124*self.round.energy/100, 82)
        for tool in COSTS:
            rect = c.find_withtag(f"tool_{tool}")[0]
            c.itemconfig(rect, outline="#ffc979" if tool == self.tool else "#335773",
                         width=2 if tool == self.tool else 1)
        c.tag_raise("challenge_hud")
        if self.counter_text:
            c.tag_raise(self.counter_text)
        self.update_visibility()
        c.tag_raise("result_card")
        c.tag_raise("pause_card")

    def notice(self, message):
        self.last_activity = self.visual_elapsed
        self.canvas.itemconfig(self.notice_text, text=message)
        self.notice_until = self.visual_elapsed+2

    @staticmethod
    def result_action(action):
        action()
        return "break"

    def show_result(self):
        c = self.canvas
        c.delete("pause_card")
        cx, cy = self.w-220, 158
        self.result_until = self.visual_elapsed+12
        c.create_rectangle(cx-196, cy-132, cx+196, cy+132, fill="#091729",
                           outline="#68889d", tags="result_card")
        c.create_text(cx, cy-100, text="挑战完成", fill="#fff0d2",
                      font=("Microsoft YaHei UI", 17, "bold"), tags="result_card")
        c.create_text(cx, cy-49, text=f"{self.round.score:,}", fill="#ffd186",
                      font=("Segoe UI", 31, "bold"), tags="result_card")
        c.create_text(cx, cy+10, text=f"击败 {self.round.kills} · 最长连锁 ×{self.round.best_chain}\n吞噬 {self.absorbed} · 传送 {self.transported}",
                      fill="#c2e3f1", font=("Microsoft YaHei UI", 11), tags="result_card")
        for x, label, tag, action in ((cx-92, "G 再挑战", "replay", self.start_challenge),
                                       (cx+92, "V 返回漫游", "return", self.enter_ambient)):
            c.create_rectangle(x-80, cy+68, x+80, cy+110, fill="#1b3550",
                               outline="#68889d", tags=("result_card", tag))
            c.create_text(x, cy+89, text=label, fill="#e4f6ff",
                           font=("Microsoft YaHei UI", 11), tags=("result_card", tag))
            c.tag_bind(tag, "<Button-1>", lambda e, f=action: self.result_action(f))

    def show_pause(self):
        self.canvas.delete("pause_card")
        if self.paused:
            self.canvas.create_rectangle(self.w/2-220, self.h/2-64, self.w/2+220, self.h/2+64,
                  fill="#0b1b30", outline="#537a99", tags="pause_card")
            self.canvas.create_text(self.w/2, self.h/2, text="已暂停\nP 继续 · R 重新开始",
                  fill="#e1f3ff", font=("Microsoft YaHei UI", 22, "bold"), tags="pause_card")
