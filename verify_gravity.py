"""Integration checks against real Tk Canvas objects; closes windows on completion."""
import math
import tkinter as tk
from spaceship15 import GravityOverlay, LauncherUI


def main():
    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = GravityOverlay(tk.Toplevel(root), dict(mode="game", ships=3,
                                 planets=1, transparent_bg=False))
        overlay.win.withdraw()
        # The original BOOM loop must survive the added gravity abilities.
        overlay.auto_level = True
        overlay.level_step = 1
        ship = overlay.ships[0]
        x, y = ship.x, ship.y
        for _ in range(5):
            overlay.advance_ships(1/60, ship.x, ship.y)
        assert ship.exploding and overlay.explode_count == 1
        assert overlay.level == 2 and ship.explode_items
        debris_ids = ship.explode_items[:]
        for _ in range(45):
            overlay.advance_ships(1/60, -10000, -10000)
        assert overlay.ships[0] is not ship
        assert not any(overlay.canvas.type(item) for item in debris_ids)
        overlay.auto_level = False
        ship = overlay.ships[0]
        ship._shoot_timer = 0
        overlay.advance_ships(1/60, ship.x+70, ship.y)
        assert overlay.bullets, "Original weapons were not restored"
        print("PASS: mouse capture BOOM, score/level progression, explosion cleanup, respawn, bullets")
        ship = overlay.ships[0]
        overlay.spawn("BLACK_HOLE", 500, 400)
        ship.portal_until = 0
        ship.x, ship.y = 640, 400
        initial = math.hypot(ship.x-500, ship.y-400)
        overlay.affect_ship(ship, 1/60)
        assert math.hypot(ship.x-500, ship.y-400) < initial
        for _ in range(400):
            if overlay.affect_ship(ship, 1/60) == "absorbed":
                break
        else:
            raise AssertionError("Black hole did not absorb ship")
        overlay._respawn_ship(0)
        assert overlay.ships[0] is not ship
        overlay.clear_space()
        # A black-hole kill must run the same visible BOOM and score lifecycle.
        overlay.last_spawn = -10
        overlay.spawn("BLACK_HOLE", 500, 400)
        hole = overlay.celestials[0]
        assert hole.update(.5) and hole.frame
        ship = overlay.ships[0]
        ship.portal_until = 0
        ship.x, ship.y = 500, 400
        score = overlay.explode_count
        overlay.advance_ships(1/60, -10000, -10000)
        assert ship.exploding and overlay.explode_count == score+1 and overlay.absorbed == 1
        for _ in range(45):
            overlay.advance_ships(1/60, -10000, -10000)
        overlay.clear_space()
        ship = overlay.ships[1]
        ship.portal_until = 0
        overlay.last_spawn = -10
        overlay.spawn("WORMHOLE", 350, 350)
        body = overlay.celestials[0]
        body.update(.1)
        ship.x, ship.y = 355, 350
        assert overlay.affect_ship(ship, 1/60) is True
        assert overlay.transported == 1
        assert abs(ship.x-body.destination[0]-65) < .01
        assert overlay.affect_ship(ship, 1/60) is False
        ship.portal_until = 0
        ship.x, ship.y = body.destination
        overlay.affect_ship(ship, 1/60)
        assert overlay.transported == 2 and ship.x == 415
        overlay.clear_space()
        overlay.last_spawn = -10
        overlay.spawn("STAR", 500, 400)
        ship.portal_until = 0
        ship.x, ship.y = 650, 400
        points = []
        for _ in range(1800):
            assert overlay.affect_ship(ship, 1/60) is True
            points.append((ship.x, ship.y))
        points = points[600:]
        width = max(x for x,y in points)-min(x for x,y in points)
        height = max(y for x,y in points)-min(y for x,y in points)
        assert 2.4 < width/height < 2.9, (width, height)
        overlay.clear_space()
        baseline = len(overlay.canvas.find_all())
        for _ in range(10):
            overlay.last_spawn = -10
            overlay.spawn("WORMHOLE", 500, 400)
            overlay.celestials[-1].update(.1)
        assert len(overlay.celestials) == 6
        for body in overlay.celestials:
            assert body.update(30) is False
        overlay.celestials.clear()
        assert len(overlay.canvas.find_all()) == baseline
        overlay.set_background_transparent(True)
        overlay.set_background_transparent(False)
        print("PASS: attraction, absorption/respawn, bidirectional portals/cooldown,")
        print("horizontal orbit, six-body limit, lifetime cleanup, background switching")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()
    launcher = LauncherUI()
    try:
        launcher.root.withdraw()
        launcher.start()
        launcher.overlay.win.withdraw()
        launcher.control_panel.withdraw()
        launcher.overlay.set_tool("STAR")
        launcher.stop()
        assert launcher.overlay is None
        print("PASS: launcher, control panel, tool selection, return to settings")
    finally:
        launcher.root.destroy()


if __name__ == "__main__":
    main()
