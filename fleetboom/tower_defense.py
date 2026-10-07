"""Optional star-lane tower-defense mode; rendering and input wrap pure td_rules."""
import math
import tkinter as tk

from .escort import EscortOverlay
from .ships import BoomShip
from .td_rules import DefenseState, TOWER_TYPES


TOOLS = {"RANDOM": None, "BLACK_HOLE": "LASER", "WORMHOLE": "GRAVITY", "STAR": "NOVA"}


class TowerDefenseOverlay(EscortOverlay):
    def __init__(self, win, config, on_stop_callback=None):
        self.defense_active = False
        self.defense = None
        self.defense_tool = "LASER"
        self.selected_tower = None
        self.enemy_views = {}
        self.tower_views = {}
        self.defense_fx = []
        super().__init__(win, config, on_stop_callback)
        for key in ("t", "T"):
            self.win.bind(key, lambda e: self.start_defense())
        for key in ("n", "N"):
            self.win.bind(key, lambda e: self.next_wave())
        for key in ("u", "U"):
            self.win.bind(key, lambda e: self.upgrade_selected())
        self.win.bind("<space>", lambda e: self.next_wave() if self.defense_active else
                      self.spawn(self.tool, self.win.winfo_pointerx()-self.win.winfo_rootx(),
                                 self.win.winfo_pointery()-self.win.winfo_rooty()))
        self.canvas.bind("<Button-3>", self.right_click)
        if config.get("tower_defense", False):
            self.start_defense()

    def right_click(self, event):
        if self.defense_active:
            if self.paused or self.round.ended:
                return
            tower = self.tower_at(event.x, event.y)
            if tower:
                refund = self.defense.sell(tower)
                self.canvas.delete(f"td_tower_{id(tower)}")
                self.tower_views.pop(id(tower), None)
                self.selected_tower = None
                self.notice(f"已出售 · 返还 {refund} 晶体")
            else:
                self.clear_space()
            self.refresh_hud()
        elif self.pending_portal:
            self.cancel_portal()
        else:
            self.clear_space()

    def leave_defense(self):
        self.defense_active = False
        self.defense = None
        self.selected_tower = None
        self.canvas.delete("td_scene")
        self.enemy_views.clear()
        self.tower_views.clear()
        self.defense_fx.clear()
        self.restore_tool_labels()
        if self.hud_ready:
            self.canvas.itemconfig(self.energy_bar, fill="#59d9ee")

    def start_challenge(self):
        self.leave_defense()
        super().start_challenge()

    def enter_ambient(self):
        self.leave_defense()
        super().enter_ambient()

    def start_escort(self):
        self.leave_defense()
        super().start_escort()

    def start_defense(self):
        self.defense_active = True
        self.escort_active = False
        self.ambient = False
        self.mode = "game"
        self.restart()
        self.notice("塔防开始 · 1 激光 / 2 引力 / 3 爆裂 · 左键建造，选中塔后 U 升级 · N 出兵")
        self.notice_until = 7

    def restart(self):
        if not self.defense_active:
            return super().restart()
        self.canvas.delete("td_scene")
        self.defense = None
        self.enemy_views.clear()
        self.tower_views.clear()
        self.defense_fx.clear()
        self.selected_tower = None
        self.defense_tool = "LASER"
        count = self.base_ships
        self.base_ships = 0
        try:
            super().restart()
        finally:
            self.base_ships = count
        self.defense = DefenseState(self.w, self.h)
        self.update_gameplay_difficulty(force=True)
        points = [value for point in self.defense.route for value in point]
        self.canvas.create_line(*points, fill="#152b40", width=28*self.defense.scale,
                                joinstyle=tk.ROUND, tags="td_scene")
        self.canvas.create_line(*points, fill="#4b718a", width=1, dash=(5, 12),
                                arrow=tk.LAST, tags="td_scene")
        x, y = self.defense.route[-1]
        radius = 32*self.defense.scale
        self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                outline="#91ead2", width=3, fill="#16332f", tags="td_scene")
        self.canvas.create_text(x, y, text="基地", fill="#c5ffea",
                                font=("Microsoft YaHei UI", 11, "bold"), tags="td_scene")
        x, y = self.defense.route[0]
        self.canvas.create_text(x, y-30*self.defense.scale, text="敌舰入口", fill="#ce8796",
                                font=("Microsoft YaHei UI", 9), tags="td_scene")
        self.preview = self.canvas.create_oval(0, 0, 1, 1, outline="#6a99ac", dash=(3, 8), tags="td_scene")
        self.canvas.itemconfig(self.exit_hint, text=
            "1 激光 / 2 引力 / 3 爆裂 · 左键建造/选塔 · U 升级 · 右键售塔 · N 下一波 · R 重开 · V 漫游")
        self.refresh_hud()

    def restore_tool_labels(self):
        if not self.hud_ready:
            return
        from .config import COSTS, NAMES
        for index, key in enumerate(TOOLS):
            for item in self.canvas.find_withtag(f"tool_{key}"):
                if self.canvas.type(item) == "text":
                    self.canvas.itemconfig(item, text=f"{index}  {NAMES[key]}  ·  {COSTS[key]}能量")

    def set_tool(self, tool):
        if not self.defense_active:
            return super().set_tool(tool)
        self.defense_tool = TOOLS[tool]
        self.selected_tower = None
        self.refresh_hud()
        self.win.focus_force()

    def tower_at(self, x, y):
        if not self.defense:
            return None
        return next((t for t in self.defense.towers if math.hypot(t.x-x, t.y-y) < 25*self.defense.scale), None)

    def spawn(self, kind, x, y):
        if not self.defense_active:
            return super().spawn(kind, x, y)
        if self.paused or self.round.ended:
            return False
        tower = self.tower_at(x, y)
        if tower:
            self.selected_tower = tower
            self.notice(f"{TOWER_TYPES[tower.kind]['name']} Lv.{tower.level} · U 升级 {35*tower.level} 晶体 · 右键出售"
                        if tower.level < 3 else "已满级 · 右键出售返还 70% 晶体")
        else:
            tower, message = self.defense.build(self.defense_tool, x, y)
            if tower:
                self.add_tower_view(tower)
                self.selected_tower = tower
            self.notice(message)
        self.refresh_hud()
        return tower is not None

    def upgrade_selected(self):
        if not self.defense_active or self.paused or self.round.ended:
            return
        _, message = self.defense.upgrade(self.selected_tower)
        self.notice(message)
        self.refresh_hud()

    def clear_space(self):
        if not self.defense_active or not self.defense:
            return super().clear_space()
        self.selected_tower = None
        self.defense_tool = None
        if self.hud_ready:
            self.notice("已取消建造选择 · 1/2/3 选择塔，右键点击已有塔出售")
            self.refresh_hud()

    def next_wave(self):
        if not self.defense_active or self.paused or self.round.ended:
            return
        if self.defense.send_wave():
            self.notice(f"第 {self.defense.wave} 波敌舰进入航线")
        else:
            self.notice("先击退当前波次，再开始下一波")

    def add_tower_view(self, tower):
        c = self.canvas
        tag = ("td_scene", f"td_tower_{id(tower)}")
        radius = 18*self.defense.scale
        color = TOWER_TYPES[tower.kind]["color"]
        shape = []
        for i in range(6):
            a = i*math.tau/6
            shape.extend((tower.x+math.cos(a)*radius, tower.y+math.sin(a)*radius))
        c.create_polygon(*shape, fill="#122331", outline=color, width=2, tags=tag)
        barrel = c.create_line(tower.x, tower.y, tower.x+radius, tower.y, fill=color,
                              width=4, capstyle=tk.ROUND, tags=tag)
        label = c.create_text(tower.x, tower.y+28*self.defense.scale, text="Ⅰ", fill=color,
                              font=("Segoe UI", 10, "bold"), tags=tag)
        self.tower_views[id(tower)] = (barrel, label)

    def draw_defense(self, dt, mx, my):
        state, c = self.defense, self.canvas
        living = {e.number: e for e in state.enemies}
        for enemy in state.enemies:
            if enemy.number not in self.enemy_views:
                ship = BoomShip(c, self.w, self.h, style="RIB_CAGE" if enemy.tank else "SPEAR",
                                enable_bullets=False, ship_scale_getter=self.get_ship_scale)
                self.paint_ship(ship)
                c.itemconfig(ship.hull, outline="#d59dff" if enemy.tank else "#ff8a9a", fill="#3c2438")
                bars = (c.create_line(0, 0, 1, 1, fill="#392e40", width=3, tags="td_scene"),
                        c.create_line(0, 0, 1, 1, fill="#f5a3ae", width=3, tags="td_scene"))
                self.enemy_views[enemy.number] = (ship, bars)
                self.ships.append(ship)
            ship, bars = self.enemy_views[enemy.number]
            ship.x, ship.y = enemy.x, enemy.y
            a, b = state.route[enemy.segment:enemy.segment+2]
            ship.angle = ship.v_ang = math.atan2(b[1]-a[1], b[0]-a[0])
            ship.flame_ang = ship.angle+math.pi
            ship.phase += dt*8
            ship.draw(enemy.speed, dt)
            x, y = ship.x-20, ship.y-26*self.ship_scale
            c.coords(bars[0], x, y, x+40, y)
            c.coords(bars[1], x, y, x+40*max(0, enemy.hp/enemy.max_hp), y)
        killed = {effect[6] for effect in state.effects if effect[0] == "boom"}
        for number, (ship, bars) in list(self.enemy_views.items()):
            if number in living:
                continue
            for bar in bars:
                c.delete(bar)
            if not ship.exploding:
                if number in killed:
                    ship.explode()
                else:
                    ship.destroy()
                    self.ships.remove(ship)
                    del self.enemy_views[number]
                    continue
            if not ship._update_explosion(dt):
                ship.destroy()
                self.ships.remove(ship)
                del self.enemy_views[number]
        for tower in state.towers:
            barrel, label = self.tower_views[id(tower)]
            r = (22+2*tower.level)*state.scale
            c.coords(barrel, tower.x, tower.y, tower.x+math.cos(tower.aim)*r, tower.y+math.sin(tower.aim)*r)
            c.itemconfig(label, text=("Ⅰ", "Ⅱ", "Ⅲ")[tower.level-1])
        for effect in state.effects:
            kind, x, y, tx, ty, color = effect[:6]
            if kind == "shot":
                item = c.create_line(x, y, tx, ty, fill=color, width=2, tags="td_scene")
                self.defense_fx.append([item, .14])
            elif kind in ("blast", "leak", "boom"):
                r = (75 if kind == "blast" else 22)*state.scale
                item = c.create_oval(x-r, y-r, x+r, y+r, outline=color, width=2, tags="td_scene")
                self.defense_fx.append([item, .25])
        for effect in list(self.defense_fx):
            effect[1] -= dt
            if effect[1] <= 0:
                c.delete(effect[0])
                self.defense_fx.remove(effect)
        tower = self.selected_tower
        radius = state.tower_range(tower) if tower else (
                 TOWER_TYPES[self.defense_tool]["range"]*state.scale if self.defense_tool else 0)
        x, y = (tower.x, tower.y) if tower else (mx, my)
        c.coords(self.preview, x-radius, y-radius, x+radius, y+radius)
        c.itemconfig(self.preview, state="normal" if radius and y > 130 and y < self.h-100 else "hidden")
        # Effects are transient; never replay them in the frozen end-of-round scene.
        state.effects.clear()

    def tick(self, dt, mx, my):
        if not self.defense_active:
            return super().tick(dt, mx, my)
        if self.paused or not self.defense:
            return
        dt = max(0, min(.1, dt))
        self.visual_elapsed += dt
        self.dock_hover = self.h-90 <= my <= self.h and abs(mx-self.w/2) <= min(580, self.w-40)/2
        if not self.round.ended:
            self.update_gameplay_difficulty()
            self.defense.tick(dt)
            self.update_gameplay_difficulty()
            self.round.score, self.round.kills = self.defense.score, self.defense.kills
            self.round.elapsed = self.defense.elapsed
        for planet in self.planets:
            planet.update(dt)
        self.draw_defense(dt, mx, my)
        if self.defense.outcome and not self.round.ended:
            self.finish()
        if self.visual_elapsed > getattr(self, "notice_until", -1):
            self.canvas.itemconfig(self.notice_text, text="")
        if self.round.ended and self.visual_elapsed > getattr(self, "result_until", float("inf")):
            self.canvas.delete("result_card")
        self.refresh_hud()

    def on_gameplay_settings_changed(self):
        if self.defense_active and self.defense:
            self.defense.configure_gameplay(self.level, self.speed_multiplier)

    def refresh_hud(self):
        super().refresh_hud()
        if not self.defense_active or not self.defense or not self.hud_ready:
            return
        state, c = self.defense, self.canvas
        c.itemconfig(self.counter_text, text=f"基地 {state.health}/{state.max_health} · 波次 {state.wave}/{state.max_waves} · 晶体 {state.credits}",
                     fill="#eaf2ff" if state.health > 5 else "#ff8a9a")
        c.itemconfig(self.energy_text, text=(f"准备 {math.ceil(state.waiting)}s · N 提前出兵" if state.waiting else
                                          f"敌舰 {len(state.enemies)+state.pending} · 击败 {state.kills}"))
        c.coords(self.energy_bar, 31, 79, 31+124*state.health/state.max_health, 82)
        c.itemconfig(self.energy_bar, fill="#91ead2" if state.health > 5 else "#ff697b")
        for index, (key, kind) in enumerate(TOOLS.items()):
            for item in c.find_withtag(f"tool_{key}"):
                if c.type(item) == "text":
                    c.itemconfig(item, text=f"{index}  {TOWER_TYPES[kind]['name']} · {TOWER_TYPES[kind]['cost']}" if kind else "0  选择 / 查看")
                else:
                    c.itemconfig(item, outline="#ffc979" if kind == self.defense_tool else "#335773",
                                 width=2 if kind == self.defense_tool else 1)

    def show_result(self):
        super().show_result()
        if not self.defense_active:
            return
        for item in self.canvas.find_withtag("result_card"):
            if self.canvas.type(item) != "text":
                continue
            text = self.canvas.itemcget(item, "text")
            if text == "挑战完成":
                self.canvas.itemconfig(item, text="基地守住了！" if self.defense.outcome == "victory" else "基地失守 · 再试一次")
            elif text.startswith("击败 "):
                self.canvas.itemconfig(item, text=f"击退 {self.defense.kills} 艘 · 波次 {self.defense.wave}/{self.defense.max_waves}\n基地剩余 {self.defense.health} · 防御塔 {len(self.defense.towers)}")
            elif text == "G 再挑战":
                self.canvas.itemconfig(item, text="T 再塔防")
        self.canvas.tag_bind("replay", "<Button-1>", lambda e: self.result_action(self.start_defense))
