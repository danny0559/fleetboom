"""Field priority, balanced star orbits and one-way portal transport."""
import math
import time


class PhysicsMixin:
    def affect_ship(self, ship, dt):
        ship.gravity_body = None
        if self.round.elapsed < getattr(ship, "grace_until", 0):
            return False
        candidates = []
        now = time.monotonic()
        for body in self.celestials:
            if body.kind == "WORMHOLE" and now < getattr(ship, "portal_until", 0):
                continue
            # The second portal is an output only; it must never pull ships back.
            for center in [(body.x, body.y)]:
                d = math.hypot(ship.x-center[0], ship.y-center[1])
                if d < body.radius:
                    # Nearby portals can lift ships out of a star's stable orbit.
                    priority = 0 if (body.kind == "WORMHOLE" and d < 105 or body.kind == "BLACK_HOLE" and d < 100*body.visual_scale) else 2
                    if body.kind == "STAR" and getattr(ship, "orbit_body", None) is body:
                        priority = 1
                    candidates.append((priority, d/body.radius, d, body, center))
        if not candidates:
            ship.orbit_body = None
            return False
        _, _, d, body, center = min(candidates, key=lambda row: row[:2])
        movement_dt = dt*self.speed_multiplier
        ship.gravity_body = body
        cx, cy = center
        if body.kind == "STAR":
            if getattr(ship, "orbit_body", None) is not body:
                counts = [sum(1 for s in self.ships if not s.exploding and
                          getattr(s, "orbit_body", None) is body and getattr(s, "orbit_lane", -1) == i)
                          for i in range(3)]
                ship.orbit_lane = min(range(3), key=lambda i: counts[i])
                ship.orbit_body = body
                ship.orbit_angle = math.atan2((ship.y-cy)/.38, ship.x-cx)
            ship.orbit_radius = body.ORBITS[ship.orbit_lane]
            ship.orbit_angle += movement_dt*95/ship.orbit_radius
            a, r = ship.orbit_angle, ship.orbit_radius
            blend = 1-math.exp(-movement_dt*3)
            nx = ship.x+(cx+math.cos(a)*r-ship.x)*blend
            ny = ship.y+(cy+math.sin(a)*r*.38-ship.y)*blend
        else:
            ship.orbit_body = None
            a = math.atan2(ship.y-cy, ship.x-cx)
            if body.kind == "BLACK_HOLE":
                if d < body.capture_radius:
                    return "absorbed"
                a += movement_dt*(1.5+60/max(d, 25))
                d = max(0, d-movement_dt*(65+800/max(d, 20)))
            else:
                if d < 29:
                    target = body.destination
                    dx, dy = target[0]-body.x, target[1]-body.y
                    length = max(1, math.hypot(dx, dy))
                    ux, uy = dx/length, dy/length
                    # A short exit offset enables delivery into a nearby black hole.
                    ship.x, ship.y = target[0]+18*ux, target[1]+18*uy
                    ship.vx, ship.vy = 150*ux*self.speed_multiplier, 150*uy*self.speed_multiplier
                    ship.set_new_target()
                    ship.portal_until = now+1.8
                    self.transported += 1
                    ship.angle = ship.v_ang = math.atan2(uy, ux)
                    ship.flame_ang = ship.angle+math.pi
                    ship._last_t = time.time()
                    ship.draw(150*self.speed_multiplier, dt)
                    return True
                d = max(0, d-movement_dt*145)
            nx, ny = cx+math.cos(a)*d, cy+math.sin(a)*d
        ship.vx, ship.vy = (nx-ship.x)/dt, (ny-ship.y)/dt
        ship.x, ship.y = nx, ny
        ship.angle = math.atan2(ship.vy, ship.vx)
        ship.v_ang, ship.flame_ang = ship.angle, ship.angle+math.pi
        ship.phase += dt*8
        ship._last_t = time.time()
        ship.draw(math.hypot(ship.vx, ship.vy), dt)
        return True
