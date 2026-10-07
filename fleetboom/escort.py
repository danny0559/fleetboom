"""Optional escort mode. Existing roaming/challenge rules remain in the base class."""
import math
import random
import time
from dataclasses import dataclass

from .controller import ChallengeOverlay
from .ships import ChallengeShip


@dataclass
class EscortMission:
    goal: int = 12
    loss_limit: int = 6
    delivered: int = 0
    lost: int = 0
    raid_phase: int = 0

    @property
    def won(self):
        return self.delivered >= self.goal

    @property
    def failed(self):
        return self.lost >= self.loss_limit


class EscortShip(ChallengeShip):
    """Retain the original hull and BOOM, adding an unmistakable role marker."""
    def __init__(self, *args, role, **kwargs):
        self.role = role
        self.marker = None
        self.next_attack = 0.0
        super().__init__(*args, **kwargs)
        self.marker = self.canvas.create_polygon(0, 0, 0, 0, 0, 0,
                         fill="#ffd984" if role == "cargo" else "#ff6574", outline="")

    def draw(self, current_speed, dt):
        super().draw(current_speed, dt)
        if self.marker is not None:
            r = 4*self._ship_scale()
            x, y = self.x, self.y-19*self._ship_scale()
            self.canvas.coords(self.marker, x, y-r, x+r, y, x, y+r, x-r, y)
            self.canvas.itemconfig(self.marker, state="hidden" if self.exploding else "normal")

    def explode(self, chain=None, source="mouse"):
        if self.exploding:
            return
        super().explode(chain, source)
        if self.exploding:
            self.canvas.itemconfig(self.marker, state="hidden")

    def destroy(self):
        if self.marker is not None:
            self.canvas.delete(self.marker)
        super().destroy()


class EscortOverlay(ChallengeOverlay):
    """Opt-in subclass: only delegates to escort rules while escort_active is true."""
    def __init__(self, win, config, on_stop_callback=None):
        self.escort_active = False
        self.mission = EscortMission()
        self.next_role = "cargo"
        self.beacon_pulse = 0.0
        super().__init__(win, config, on_stop_callback)
        for key in ("e", "E"):
            self.win.bind(key, lambda e: self.start_escort())
        self.canvas.itemconfig(self.exit_hint, text=
            "左键创造天体 · G 原挑战 / E 护航 / V 漫游 · H 工具 · F2 设置 · ESC 返回")
        if config.get("escort", False):
            self.start_escort()

    def start_escort(self):
        self.escort_active = True
        self.ambient = False
        self.mode = "game"
        self.enable_explosions = self.enable_bullets = True
        self.restart()
        self.notice("护航开始 · 金色运输船送往灯塔，追上红色海盗 BOOM · 虫洞可抄近路")
        self.notice_until = 6

    def start_challenge(self):
        self.escort_active = False
        super().start_challenge()

    def enter_ambient(self):
        self.escort_active = False
        super().enter_ambient()

    def make_ship(self, style=None):
        if not self.escort_active:
            return super().make_ship(style)
        ship = EscortShip(self.canvas, self.w, self.h, style=style, role=self.next_role,
                  enable_bullets=False, enable_explosions=True,
                  on_explode=lambda: self.ship_exploded(ship), ship_scale_getter=self.get_ship_scale)
        ship.owner = self
        ship.chain = None
        ship.set_difficulty(self.level, self.speed_multiplier)
        self.paint_ship(ship)
        color, fill = (("#ffd984", "#51412a") if ship.role == "cargo" else ("#ff6574", "#4b2332"))
        ship.col = color
        self.canvas.itemconfig(ship.hull, outline=color, fill=fill)
        for item in ship.detail_lines:
            self.canvas.itemconfig(item, fill=color)
        return ship

    def position_escort_ship(self, ship):
        ship.grace_until = self.round.elapsed+2
        ship.portal_until = 0
        if ship.role == "cargo":
            ship.x = random.uniform(85, max(86, self.w*.22))
            ship.y = random.uniform(self.h*.28, self.h*.72)
        else:
            ship.x = random.uniform(self.w*.60, self.w*.85)
            ship.y = random.choice((145, self.h-125))
        ship.tx, ship.ty = ship.x, ship.y
        ship.draw(0, 1/60)

    def _respawn_ship(self, idx):
        if not self.escort_active:
            return super()._respawn_ship(idx)
        self.next_role = self.ships[idx].role
        self.ships[idx].destroy()
        self.ships[idx] = self.make_ship()
        self.position_escort_ship(self.ships[idx])

    def restart(self):
        self.canvas.delete("escort_beacon")
        if not self.escort_active:
            self.canvas.itemconfig(self.exit_hint, text=
                "左键创造天体 · G 原挑战 / E 护航 / V 漫游 · H 工具 · F2 设置 · ESC 返回")
            return super().restart()
        self.mission = EscortMission()
        self.beacon_pulse = 0
        # Reuse session cleanup, but retain the original fleet-count setting for G/V.
        base_count = self.base_ships
        self.base_ships = 0
        try:
            super().restart()
        finally:
            self.base_ships = base_count
        self.beacon = (self.w-125, self.h/2)
        self.beacon_ring = self.canvas.create_oval(0, 0, 1, 1, outline="#ffe1a0", width=2,
                                                  tags="escort_beacon")
        x, y = self.beacon
        self.canvas.create_polygon(x, y-22, x+16, y, x, y+22, x-16, y,
                         fill="#fff2cb", outline="#ffd984", tags="escort_beacon")
        self.canvas.create_text(x, y+79, text="送达灯塔", fill="#d7bc82",
                         font=("Microsoft YaHei UI", 9), tags="escort_beacon")
        for role, count in (("cargo", 6), ("pirate", 2)):
            self.next_role = role
            for _ in range(count):
                ship = self.make_ship()
                self.ships.append(ship)
                self.position_escort_ship(ship)
        self.round.energy = 100
        self.canvas.itemconfig(self.exit_hint, text=
            "金船→灯塔 · 追红船 BOOM · 虫洞转运 · 黑洞/爆炸会误伤 · E 护航 / G 原挑战 / V 漫游")
        self.refresh_hud()

    def ship_exploded(self, ship):
        if not self.escort_active or ship.role == "pirate":
            return super().ship_exploded(ship)
        self.mission.lost += 1
        # Friendly losses do not award kills, energy or propagate a new shockwave.
        self.notice(f"运输船损失 {self.mission.lost}/{self.mission.loss_limit} · 留意海盗与爆炸范围")

    def move_toward(self, ship, target, speed, dt):
        speed *= self.speed_multiplier
        if ship.role == "pirate":
            speed *= 1+.045*(self.level-1)
        dx, dy = target[0]-ship.x, target[1]-ship.y
        distance = max(.001, math.hypot(dx, dy))
        step = min(distance, speed*dt)
        ship.vx, ship.vy = dx/distance*speed, dy/distance*speed
        ship.x += dx/distance*step
        ship.y += dy/distance*step
        ship.angle = ship.v_ang = math.atan2(dy, dx)
        ship.flame_ang = ship.angle+math.pi
        ship.phase += dt*8
        ship._last_t = time.time()
        ship.draw(speed, dt)

    def advance_ships(self, dt, mx, my):
        if not self.escort_active:
            return super().advance_ships(dt, mx, my)
        for i, ship in enumerate(self.ships):
            if self.mission.won or self.mission.failed:
                break
            if ship.exploding:
                if not ship._update_explosion(dt):
                    self._respawn_ship(i)
                continue
            protected = self.round.elapsed < ship.grace_until
            if ship.role == "pirate" and not protected:
                close = math.hypot(mx-ship.x, my-ship.y) < max(28, 24*ship._ship_scale())
                ship._catch_accum = ship._catch_accum+dt if close else 0
                if ship._catch_accum >= ship.catch_hold:
                    ship.explode()
                    continue
            field = self.affect_ship(ship, dt)
            if field == "absorbed":
                self.absorbed += 1
                ship.gravity_body.charge += 1
                ship.explode(source="blackhole")
                continue
            if ship.role == "cargo":
                if not field:
                    self.move_toward(ship, self.beacon, 72, dt)
                if math.hypot(ship.x-self.beacon[0], ship.y-self.beacon[1]) < 60:
                    self.mission.delivered += 1
                    self.round.score += 250
                    self.round.energy = min(100, self.round.energy+12)
                    self.beacon_pulse = 1
                    self.notice(f"运输船安全送达！{self.mission.delivered}/{self.mission.goal} · +250 分 · +12 能量")
                    self._respawn_ship(i)
            else:
                cargo = [s for s in self.ships if s.role == "cargo" and not s.exploding]
                if cargo:
                    target = min(cargo, key=lambda s: math.hypot(s.x-ship.x, s.y-ship.y))
                    if not field:
                        self.move_toward(ship, (target.x, target.y), 86+8*self.mission.raid_phase, dt)
                    if (not protected and self.round.elapsed >= ship.next_attack
                            and self.round.elapsed >= target.grace_until
                            and math.hypot(target.x-ship.x, target.y-ship.y) < 24):
                        target.explode(source="raid")
                        ship.next_attack = self.round.elapsed+4

    def tick(self, dt, mx, my):
        if not self.escort_active:
            return super().tick(dt, mx, my)
        if self.paused:
            return
        if self.round.ended:
            return super().tick(dt, mx, my)
        dt = max(0, dt)
        self.visual_elapsed += dt
        self.last_pointer = (mx, my)
        self.dock_hover = self.h-90 <= my <= self.h and abs(mx-self.w/2) <= min(580, self.w-40)/2
        self.round.advance(dt)
        if self.round.ended:
            self.finish()
            return
        phase = min(3, int(self.round.elapsed//20))
        if phase > self.mission.raid_phase:
            for _ in range((phase-self.mission.raid_phase)*2):
                self.next_role = "pirate"
                ship = self.make_ship()
                self.ships.append(ship)
                self.position_escort_ship(ship)
            self.mission.raid_phase = phase
            self.notice("海盗增援抵达 · 用虫洞转移运输船，或追击海盗清路")
        motion_dt = max(.001, min(.05, dt))
        self.update_portal_preview(motion_dt, mx, my)
        for body in self.celestials:
            if body.kind == "STAR":
                body.residents = sum(not s.exploding and getattr(s, "orbit_body", None) is body for s in self.ships)
        self.celestials = [b for b in self.celestials if b.update(motion_dt)]
        for planet in self.planets:
            planet.update(motion_dt)
        self.advance_waves(motion_dt)
        if not self.mission.failed:
            self.advance_ships(motion_dt, mx, my)
        self.update_popups(motion_dt)
        self.beacon_pulse = max(0, self.beacon_pulse-motion_dt*1.8)
        x, y = self.beacon
        radius = 60+15*self.beacon_pulse+3*math.sin(self.visual_elapsed*2)
        self.canvas.coords(self.beacon_ring, x-radius, y-radius, x+radius, y+radius)
        self.canvas.itemconfig(self.beacon_ring, width=2+3*self.beacon_pulse)
        for attr, item in (("chain_until", self.chain_text), ("notice_until", self.notice_text)):
            if self.visual_elapsed > getattr(self, attr, -1):
                self.canvas.itemconfig(item, text="")
        if self.mission.won or self.mission.failed:
            self.finish()
        self.refresh_hud()

    def refresh_hud(self):
        super().refresh_hud()
        if self.escort_active and self.hud_ready and self.counter_text:
            self.canvas.itemconfig(self.counter_text, text=
                f"护航 {self.mission.delivered}/{self.mission.goal} · 损失 {self.mission.lost}/{self.mission.loss_limit} · {math.ceil(self.round.remaining)}s")

    def show_result(self):
        super().show_result()
        if not self.escort_active:
            return
        for item in self.canvas.find_withtag("result_card"):
            if self.canvas.type(item) != "text":
                continue
            text = self.canvas.itemcget(item, "text")
            if text == "挑战完成":
                self.canvas.itemconfig(item, text="护航成功！" if self.mission.won else "护航结束 · 再试一次")
            elif text.startswith("击败 "):
                self.canvas.itemconfig(item, text=f"送达 {self.mission.delivered}/{self.mission.goal} · 损失 {self.mission.lost}\n击败海盗 {self.round.kills} · 传送 {self.transported}")
            elif text == "G 再挑战":
                self.canvas.itemconfig(item, text="E 再护航")
        self.canvas.tag_bind("replay", "<Button-1>", lambda e: self.result_action(self.start_escort))
