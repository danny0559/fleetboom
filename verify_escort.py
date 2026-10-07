"""Real Canvas checks for the optional escort mode and compatibility boundaries."""
import random
import tkinter as tk

from fleetboom.escort import EscortOverlay
from fleetboom.ui import LauncherUI


def isolate(scene):
    for i, ship in enumerate(scene.ships):
        ship.x, ship.y = 100+i*70, 160
        ship.grace_until = 1000
        ship.portal_until = 0
        ship.orbit_body = None
        ship.draw(0, .02)


def check_escort():
    random.seed(726)
    root = tk.Tk()
    root.withdraw()
    scene = None
    try:
        scene = EscortOverlay(tk.Toplevel(root), dict(mode="game", ships=24,
                              planets=1, level=1, transparent_bg=False, escort=True))
        assert scene.escort_active and not scene.ambient
        assert [s.role for s in scene.ships].count("cargo") == 6
        assert [s.role for s in scene.ships].count("pirate") == 2
        isolate(scene)
        cargo = scene.ships[0]
        cargo.x, cargo.y = 450, 400
        cargo.grace_until = 0
        scene.advance_ships(.1, cargo.x, cargo.y)
        assert not cargo.exploding, "Mouse chasing must not kill friendly cargo"
        pirate = scene.ships[6]
        pirate.x, pirate.y = 600, 400
        pirate.grace_until = 0
        before = abs(pirate.x-cargo.x)
        scene.advance_ships(.05, -10000, -10000)
        assert abs(pirate.x-cargo.x) < before, "Pirates must pursue cargo"
        scene.advance_ships(.1, pirate.x, pirate.y)
        assert pirate.exploding and scene.round.kills == 1 and scene.waves
        isolate(scene)
        cargo.x, cargo.y = scene.beacon
        old_score = scene.round.score
        scene.round.energy = 50
        scene.advance_ships(.02, -10000, -10000)
        assert scene.mission.delivered == 1 and scene.round.score == old_score+250
        assert scene.round.energy == 62 and scene.ships[0].role == "cargo"
        assert scene.ships[0].marker != cargo.marker
        assert not scene.canvas.type(cargo.marker), "Delivered markers must be deleted"
        scene.clear_waves()
        isolate(scene)
        cargo = scene.ships[0]
        cargo.grace_until = 0
        cargo.x, cargo.y = 500, 400
        pirate = scene.ships[7]
        pirate.grace_until = 0
        pirate.x, pirate.y = 501, 400
        score, kills = scene.round.score, scene.round.kills
        scene.advance_ships(.02, -10000, -10000)
        assert cargo.exploding and scene.mission.lost == 1
        assert scene.round.score == score and scene.round.kills == kills
        assert not scene.waves, "Friendly losses must not award or propagate attacks"
        print("PASS: role markers, friendly mouse safety, pirate chase/BOOM, delivery/rewards, raid losses")

        scene.restart()
        isolate(scene)
        scene.round.energy = 100
        assert scene.spawn("WORMHOLE", 500, 400)
        assert scene.spawn("WORMHOLE", *scene.beacon)
        cargo = scene.ships[0]
        cargo.x, cargo.y = 500, 400
        cargo.grace_until = 0
        scene.advance_ships(.02, -10000, -10000)
        assert scene.transported == 1 and scene.mission.delivered == 1
        scene.clear_space()
        scene.last_spawn = -10
        assert scene.spawn("BLACK_HOLE", 650, 400)
        hole = scene.celestials[-1]
        isolate(scene)
        cargo = scene.ships[1]
        cargo.x, cargo.y = hole.x, hole.y
        cargo.grace_until = 0
        scene.advance_ships(.02, -10000, -10000)
        assert cargo.exploding and scene.mission.lost == 1 and hole.charge == 1
        scene.advance_ships(.02, -10000, -10000)
        assert scene.mission.lost == 1 and hole.charge == 1
        print("PASS: wormhole delivery, friendly black-hole risk/charge, no duplicate losses")

        scene.restart()
        isolate(scene)
        scene.round.elapsed = 19.99
        scene.tick(.02, -10000, -10000)
        assert scene.mission.raid_phase == 1 and len(scene.ships) == 10
        scene.tick(.02, -10000, -10000)
        assert len(scene.ships) == 10
        scene.paused = True
        elapsed = scene.round.elapsed
        scene.tick(10, -10000, -10000)
        assert scene.round.elapsed == elapsed
        scene.paused = False
        scene.mission.delivered = 11
        scene.ships[0].x, scene.ships[0].y = scene.beacon
        scene.tick(.02, -10000, -10000)
        assert scene.mission.won and scene.round.ended
        assert scene.canvas.find_withtag("result_card")
        score, delivered = scene.round.score, scene.mission.delivered
        scene.tick(.05, -10000, -10000)
        assert (scene.round.score, scene.mission.delivered) == (score, delivered)
        scene.restart()
        isolate(scene)
        scene.mission.lost = 6
        scene.tick(.02, -10000, -10000)
        assert scene.round.ended and scene.mission.failed
        scene.restart()
        scene.tick(95, -10000, -10000)
        assert scene.round.ended and scene.round.elapsed == 90
        scene.set_scales(ship_scale=1.7, planet_scale=.8)
        scene.enter_ambient()
        assert not scene.escort_active and len(scene.ships) == 24
        assert not scene.canvas.find_withtag("escort_beacon")
        assert all(not hasattr(ship, "role") for ship in scene.ships)
        scene.start_challenge()
        assert not scene.escort_active and not scene.ambient
        scene.start_escort()
        assert scene.mission.delivered == scene.mission.lost == 0
        assert scene.ship_scale == 1.7 and scene.planet_scale == .8
        print("PASS: timed raids, pause, victory/failure/timeout, final-stat freeze, mode cleanup and scales")
    finally:
        if scene:
            scene.stop()
        root.destroy()


def check_launcher():
    app = LauncherUI()
    try:
        app.mode_var.set("escort")
        app.start()
        assert app.overlay.escort_active
        assert app.control_panel.cget("background") == "#1e1e20"
        assert not app.control_panel.winfo_viewable()
        print("PASS: launcher enters escort, charcoal settings remain hidden by default")
    finally:
        app.stop()
        app.root.destroy()


if __name__ == "__main__":
    check_escort()
    check_launcher()
