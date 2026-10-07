"""Charged detonation, chain reactions, ship capture, score feedback and cleanup."""
import math
from .rules import Shockwave


class CombatMixin:
    def detonate(self, body):
        if self.paused or self.round.ended or body not in self.celestials:
            return False
        self.celestials.remove(body)
        body.destroy()
        self.round.next_chain += 1
        radius = 140+15*min(body.charge, 20)
        items = tuple(self.canvas.create_oval(body.x, body.y, body.x, body.y,
                      outline=color, width=width, tags="nova_fx")
                      for color, width in (("#6e4529", 8), ("#ffdb8d", 3), ("#fff5d5", 1)))
        self.waves.append(Shockwave(body.x, body.y, self.round.next_chain,
                                   radius=radius, life=.8, items=items))
        self.notice(f"黑洞引爆！蓄能 {body.charge} · 冲击范围 {radius} 像素")
        return True

    def clear_waves(self):
        for wave in self.waves:
            for item in wave.items:
                self.canvas.delete(item)
        self.waves.clear()

    def ship_exploded(self, ship):
        self.last_activity = self.visual_elapsed
        result = self.round.kill(ship.chain)
        if result is None:
            return
        chain, count, awarded = result
        self.explode_count = self.round.kills
        self.update_gameplay_difficulty()
        if ship.boom_source != "blackhole":
            self.waves.append(Shockwave(ship.x, ship.y, chain))
        label = self.canvas.create_text(ship.x+20, ship.y-50, text=f"+{awarded}",
                 fill="#ffdd97", font=("Segoe UI", 13, "bold"), tags="score_popup")
        self.popups.append([label, ship.x+20, ship.y-50, 0.0])
        if count > 1:
            self.canvas.itemconfig(self.chain_text, text=f"BOOM ×{count}  /  CHAIN REACTION")
            self.chain_until = self.visual_elapsed+1.5
        self.refresh_hud()

    def advance_waves(self, dt):
        # Iterate a snapshot: each secondary BOOM launches its wave on the next tick.
        active = []
        current = self.waves
        self.waves = []
        for wave in current:
            wave.age += dt
            radius = wave.radius*min(1, wave.age/wave.life)
            for i, item in enumerate(wave.items):
                r = radius*(1-i*.04)
                self.canvas.coords(item, wave.x-r, wave.y-r, wave.x+r, wave.y+r)
            for ship in self.ships:
                if ship.exploding or self.round.elapsed < getattr(ship, "grace_until", 0):
                    continue
                if math.hypot(ship.x-wave.x, ship.y-wave.y) <= radius:
                    ship.explode(wave.chain, "shockwave")
            if wave.age < wave.life:
                active.append(wave)
            else:
                for item in wave.items:
                    self.canvas.delete(item)
        self.waves = active+self.waves
        chains = {wave.chain for wave in self.waves}
        self.round.chains = {key: value for key, value in self.round.chains.items() if key in chains}

    def advance_ships(self, dt, mx, my):
        for i, ship in enumerate(self.ships):
            if ship.exploding:
                if not ship._update_explosion(dt):
                    self._respawn_ship(i)
                continue
            protected = self.round.elapsed < getattr(ship, "grace_until", 0)
            catch_r = ship.catch_radius*(.9+.35*ship._ship_scale())
            if self.enable_explosions and not protected and math.hypot(mx-ship.x, my-ship.y) < catch_r:
                ship._catch_accum += dt
                if ship._catch_accum >= ship.catch_hold:
                    ship.explode()
                    continue
            else:
                ship._catch_accum = 0
            result = self.affect_ship(ship, dt)
            if result == "absorbed":
                if self.enable_explosions:
                    if not protected:
                        self.absorbed += 1
                        ship.gravity_body.charge += 1
                        ship.explode(source="blackhole")
                else:
                    self.absorbed += 1
                    ship.gravity_body.charge += 1
                    self._respawn_ship(i)
            elif not result:
                ship.update_motion(mx, my)
            if self.enable_bullets:
                ship.try_shoot(mx, my, dt, self.bullets)
        self.bullets = [bullet for bullet in self.bullets if bullet.update(dt, self.w, self.h)]

    def update_popups(self, dt):
        alive = []
        for popup in self.popups:
            popup[3] += dt
            item, x, y, age = popup
            if age >= .75:
                self.canvas.delete(item)
            else:
                self.canvas.coords(item, x, y-age*48)
                alive.append(popup)
        self.popups = alive
