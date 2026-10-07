"""Game-loop coordinator: sessions, phases, pause, replay and entity lifecycle."""
import math
import random
import time
from .rules import RoundState
from .ships import ChallengeShip
from .world import World
from .abilities import AbilitiesMixin
from .physics import PhysicsMixin
from .combat import CombatMixin
from .hud import HudMixin
from .settings import GameplaySettingsMixin


class ChallengeOverlay(GameplaySettingsMixin, AbilitiesMixin, PhysicsMixin, CombatMixin, HudMixin, World):
    def __init__(self, win, config, on_stop_callback=None):
        self.round = RoundState()
        self.paused = False
        self.waves = []
        self.popups = []
        self.applied_phase = 0
        self.visual_elapsed = 0.0
        self.ambient = bool(config.get("ambient", False))
        self.hud_pinned = False
        self.last_activity = 0.0
        self.last_pointer_input = 0.0
        self.last_pointer = None
        self.dock_hover = False
        self.pending_portal = None
        self.portal_links = []
        self.hud_ready = False
        self.booting = True
        self.base_ships = int(config["ships"])
        self.initial_level = int(config.get("level", 1))
        config = dict(config, auto_level=bool(config.get("auto_level", True)))
        super().__init__(win, config, on_stop_callback)
        self.booting = False
        self.build_hud()
        self.canvas.bind("<Button-3>", lambda e: self.cancel_portal() if self.pending_portal else self.clear_space())
        for key in ("p", "P"):
            self.win.bind(key, lambda e: self.toggle_pause())
        for key in ("r", "R"):
            self.win.bind(key, lambda e: self.restart())
        for key in ("g", "G"):
            self.win.bind(key, lambda e: self.start_challenge())
        for key in ("v", "V"):
            self.win.bind(key, lambda e: self.enter_ambient())
        for key in ("h", "H"):
            self.win.bind(key, lambda e: self.toggle_hud())
        self.last_frame = time.monotonic()
        self.animate()

    def make_ship(self, style=None):
        ship = ChallengeShip(self.canvas, self.w, self.h, style=style,
                 enable_bullets=self.enable_bullets, enable_explosions=self.enable_explosions,
                 on_explode=lambda: self.ship_exploded(ship), ship_scale_getter=self.get_ship_scale)
        ship.owner = self
        ship.chain = None
        ship.set_difficulty(self.level, self.speed_multiplier)
        self.paint_ship(ship)
        return ship

    def _respawn_ship(self, idx):
        super()._respawn_ship(idx)
        ship = self.ships[idx]
        ship.grace_until = self.round.elapsed+1.2
        # New ships appear around the playfield edges, away from ongoing chains.
        if random.random() < .5:
            ship.x = random.choice((100, self.w-100))
            ship.y = random.uniform(170, self.h-130)
        else:
            ship.x = random.uniform(100, self.w-100)
            ship.y = random.choice((170, self.h-130))
        ship.tx, ship.ty = ship.x, ship.y
        ship.draw(0, 1/60)

    def tick(self, dt, mx, my):
        if self.paused:
            return
        self.visual_elapsed += max(0.0, dt)
        if self.last_pointer is not None and math.hypot(mx-self.last_pointer[0], my-self.last_pointer[1]) > 7:
            self.last_activity = self.visual_elapsed
            self.last_pointer_input = self.visual_elapsed
        self.last_pointer = (mx, my)
        self.dock_hover = self.h-90 <= my <= self.h and abs(mx-self.w/2) <= min(580, self.w-40)/2
        if self.round.ended:
            # The score is final, but the starfield keeps drifting behind the result.
            self.drift(min(.05, max(.001, dt)))
            self.refresh_hud()
            if self.visual_elapsed > getattr(self, "result_until", float("inf")):
                self.canvas.delete("result_card")
            return
        if self.mode == "game":
            if self.ambient:
                self.round.elapsed += max(0, dt)
                self.round.energy = min(100, self.round.energy+max(0, dt)*.6)
            else:
                self.round.advance(dt)
            if self.round.ended:
                self.finish()
                return
            if not self.ambient and self.round.phase != self.applied_phase:
                self.applied_phase = self.round.phase
                self.update_gameplay_difficulty()
                target = min(80, self.base_ships+self.applied_phase*6+(10 if self.applied_phase == 4 else 0))
                while len(self.ships) < target:
                    self.ships.append(self.make_ship())
                    self._respawn_ship(len(self.ships)-1)
                self.notice("最后 15 秒：舰队暴走！" if self.applied_phase == 4 else "增援舰群抵达！")
        # The round uses elapsed wall time; motion is capped after a delayed UI frame.
        motion_dt = max(.001, min(.05, dt))
        self.update_portal_preview(motion_dt, mx, my)
        for body in self.celestials:
            if body.kind == "STAR":
                body.residents = sum(1 for ship in self.ships if not ship.exploding and
                                     getattr(ship, "orbit_body", None) is body)
        self.celestials = [body for body in self.celestials if body.update(motion_dt)]
        for planet in self.planets:
            planet.update(motion_dt)
        self.advance_waves(motion_dt)
        if self.ambient and self.visual_elapsed-self.last_pointer_input > 1.5:
            # A stationary cursor belongs to the scenery; only deliberate interaction
            # should start a chase in roaming mode.
            self.advance_ships(motion_dt, -10000, -10000)
        else:
            self.advance_ships(motion_dt, mx, my)
        self.update_popups(motion_dt)
        if self.visual_elapsed > getattr(self, "chain_until", -1):
            self.canvas.itemconfig(self.chain_text, text="")
        if self.visual_elapsed > getattr(self, "notice_until", -1):
            self.canvas.itemconfig(self.notice_text, text="")
        self.refresh_hud()

    def drift(self, dt):
        transported = self.transported
        self.celestials = [body for body in self.celestials if body.update(dt)]
        for planet in self.planets:
            planet.update(dt)
        for i, ship in enumerate(self.ships):
            if ship.exploding:
                if not ship._update_explosion(dt):
                    self._respawn_ship(i)
            else:
                result = self.affect_ship(ship, dt)
                if result == "absorbed":
                    self._respawn_ship(i)
                elif not result:
                    ship.update_motion(-10000, -10000)
        self.transported = transported  # Final challenge statistics stay final.

    def start_challenge(self):
        self.ambient = False
        self.mode = "game"
        self.enable_explosions = self.enable_bullets = True
        self.restart()
        self.notice("90 秒挑战开始 · 追击、聚船、连锁 BOOM")

    def enter_ambient(self):
        self.ambient = True
        self.mode = "game"
        self.enable_explosions = self.enable_bullets = True
        self.restart()
        self.notice("进入漫游 · 随时 BOOM，G 开始挑战")

    def animate(self):
        if self.booting or not self._running:
            return
        now = time.monotonic()
        dt = now-self.last_frame
        self.last_frame = now
        self.tick(dt, self.win.winfo_pointerx()-self.win.winfo_rootx(),
                  self.win.winfo_pointery()-self.win.winfo_rooty())
        self.win.after(16, self.animate)

    def toggle_pause(self):
        if self.round.ended:
            return
        self.paused = not self.paused
        self.show_pause()
        self.reset_motion_clock()
        self.win.focus_force()

    def reset_motion_clock(self):
        self.last_frame = time.monotonic()
        for ship in self.ships:
            ship._last_t = time.time()

    def finish(self):
        if self.canvas.find_withtag("result_card"):
            return
        self.round.ended = True
        self.paused = False
        self.cancel_portal()
        self.canvas.delete("portal_link")
        self.portal_links.clear()
        self.clear_waves()
        self.round.chains.clear()
        self.update_popups(1)
        self.refresh_hud()
        self.show_result()

    def restart(self):
        self.canvas.delete("result_card", "pause_card", "score_popup")
        self.clear_space()
        for ship in self.ships:
            ship.destroy()
        for bullet in self.bullets:
            bullet.destroy()
        self.bullets.clear()
        self.ships.clear()
        self.clear_waves()
        self.popups.clear()
        self.round = RoundState()
        self.visual_elapsed = 0.0
        self.last_activity = 0.0
        self.last_pointer_input = 0.0
        self.last_pointer = None
        self.paused = False
        self.absorbed = self.transported = self.explode_count = self.applied_phase = 0
        self.level = self.initial_level
        self.last_spawn = -10
        self.chain_until = self.notice_until = -1
        self.canvas.itemconfig(self.chain_text, text="")
        self.canvas.itemconfig(self.notice_text, text="")
        self.ships = [self.make_ship() for _ in range(self.base_ships)]
        self.reset_motion_clock()
        self.refresh_hud()
        self.win.focus_force()
