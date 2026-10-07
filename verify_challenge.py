"""Deterministic gameplay and real Tk Canvas integration checks for FleetBoom 3."""
import random
import math
import tkinter as tk

from spaceship16 import COSTS, ChallengeOverlay, LauncherUI, RoundState


def check_rules():
    state = RoundState(energy=40)
    assert state.spend("BLACK_HOLE") and state.energy == 0
    assert not state.spend("STAR") and state.energy == 0
    first = state.kill()
    second = state.kill(first[0])
    assert first[1:] == (1, 100) and second[1:] == (2, 150)
    assert state.score == 250 and state.energy == 16 and state.best_chain == 2
    third = state.kill()
    assert third[1] == 1, "Separate explosions must start separate spatial chains"
    state.energy = 99
    state.kill()
    assert state.energy == 100
    state.advance(-1)
    assert state.elapsed == 0
    state.advance(20)
    assert state.phase == 1
    state.advance(55)
    assert state.phase == 4 and state.remaining == 15
    state.advance(1000)
    before = (state.energy, state.score, state.kills)
    assert state.ended and state.elapsed == 90
    assert state.kill() is None and not state.spend("RANDOM")
    state.advance(1)
    assert before == (state.energy, state.score, state.kills)
    print("PASS: energy pricing/refunds/cap, spatial combo scoring, phase/deadline, end-of-round lock")


def freeze_positions(overlay, positions):
    for ship, position in zip(overlay.ships, positions):
        ship.x, ship.y = position
        ship.tx, ship.ty = position
        ship.vx = ship.vy = 0
        ship.state = "IDLE"
        ship.idle_timer = 10000
        ship.portal_until = ship.grace_until = 0
        ship.draw(0, 1/60)


def check_canvas():
    random.seed(317)
    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = ChallengeOverlay(tk.Toplevel(root), dict(mode="game", ships=5,
                          planets=0, transparent_bg=False, level=1))
        overlay.win.withdraw()
        assert overlay.round.elapsed < .1
        for kind in COSTS:
            overlay.clear_space()
            overlay.round.energy = 100
            overlay.last_spawn = -10
            assert overlay.spawn(kind, 500, 400)
            if overlay.pending_portal:
                assert overlay.round.energy == 100
                assert overlay.spawn(kind, 1000, 400)
            assert overlay.round.energy == 100-COSTS[kind]
            assert overlay.celestials[-1].update(.5)
        overlay.round.energy = 0
        count = len(overlay.celestials)
        overlay.last_spawn = -10
        assert not overlay.spawn("BLACK_HOLE", 500, 400)
        assert count == len(overlay.celestials) and overlay.round.energy == 0
        overlay.toggle_pause()
        before = (overlay.round.elapsed, overlay.round.energy, overlay.ships[0].x)
        overlay.tick(30, -10000, -10000)
        assert before == (overlay.round.elapsed, overlay.round.energy, overlay.ships[0].x)
        assert not overlay.spawn("RANDOM", 500, 400)
        overlay.toggle_pause()
        print("PASS: costed deployment, all celestial artwork, insufficient-energy feedback, pause lock")

        overlay.restart()
        overlay.round.energy = 0
        freeze_positions(overlay, [(400,400), (480,400), (560,400), (640,400), (900,400)])
        overlay.ships[0].explode()
        assert overlay.round.kills == 1
        for _ in range(30):
            overlay.tick(.05, -10000, -10000)
        assert overlay.round.kills == 4, overlay.round.kills
        assert overlay.round.best_chain == 4 and overlay.round.score == 700
        assert not overlay.ships[4].exploding
        assert overlay.round.energy > 40
        # Respawn protection prevents waves from farming their own replacement ships.
        overlay._respawn_ship(4)
        fresh = overlay.ships[4]
        fresh.x, fresh.y = overlay.ships[0].x, overlay.ships[0].y
        score = overlay.round.score
        fresh.explode()
        assert not fresh.exploding and overlay.round.score == score
        print("PASS: four-ship chain propagation, distance exclusion, combo score/refund, respawn protection")

        overlay.restart()
        freeze_positions(overlay, [(600,400), (100,200), (100,600), (900,200), (1000,600)])
        ship = overlay.ships[0]
        for _ in range(5):
            overlay.tick(1/60, ship.x, ship.y)
        assert ship.exploding and overlay.round.kills == 1
        overlay.restart()
        overlay.last_spawn = -10
        assert overlay.spawn("BLACK_HOLE", 600, 400)
        ship = overlay.ships[0]
        ship.x, ship.y = 600, 400
        ship.portal_until = 0
        overlay.tick(.02, -10000, -10000)
        assert ship.exploding and overlay.absorbed == 1 and overlay.round.kills == 1
        overlay.restart()
        ship = overlay.ships[0]
        ship._shoot_timer = 0
        overlay.tick(.02, ship.x+70, ship.y)
        assert overlay.bullets
        print("PASS: original mouse BOOM, black-hole BOOM/scoring, original weapons")

        overlay.restart()
        overlay.tick(20, -10000, -10000)
        assert overlay.round.phase == 1 and len(overlay.ships) == 11
        overlay.tick(55, -10000, -10000)
        assert overlay.round.phase == 4 and len(overlay.ships) == 39
        overlay.tick(15, -10000, -10000)
        assert overlay.round.ended and overlay.canvas.find_withtag("result_card")
        before = (overlay.round.score, overlay.round.energy, overlay.round.elapsed, len(overlay.celestials))
        overlay.tick(100, overlay.ships[0].x, overlay.ships[0].y)
        assert not overlay.spawn("STAR", 500, 400)
        assert before == (overlay.round.score, overlay.round.energy, overlay.round.elapsed, len(overlay.celestials))
        overlay.restart()
        assert not overlay.canvas.find_withtag("result_card")
        assert not overlay.canvas.find_withtag("score_popup")
        assert len(overlay.ships) == 5 and not overlay.waves and not overlay.bullets
        assert overlay.round.energy == 70 and overlay.round.score == 0 and overlay.round.elapsed == 0
        print("PASS: reinforcement phases, final rush, result card, frozen results, complete replay reset")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()

    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = ChallengeOverlay(tk.Toplevel(root), dict(mode="screensaver", ships=2,
                               planets=0, transparent_bg=False))
        overlay.win.withdraw()
        overlay.round.energy = 0
        assert overlay.spawn("BLACK_HOLE", 500, 400)
        overlay.tick(100, -10000, -10000)
        assert overlay.round.elapsed == 0 and not overlay.round.ended
        assert overlay.round.energy == 0
        overlay.ships[0].explode()
        assert not overlay.ships[0].exploding and overlay.round.kills == 0
        print("PASS: free celestial screensaver, no challenge timer or BOOM")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()

    app = LauncherUI()
    try:
        app.root.withdraw()
        app.start()
        app.overlay.win.withdraw()
        app.control_panel.withdraw()
        app.root.update_idletasks()
        assert app.overlay.ambient and app.control_panel.state() == "withdrawn"
        app.overlay.restart()
        app.stop()
        assert app.overlay is None
        print("PASS: new launcher, control panel, restart and return to settings")
    finally:
        app.root.destroy()


def check_quiet_ui():
    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = ChallengeOverlay(tk.Toplevel(root), dict(mode="game", ambient=True,
                                    ships=3, planets=0, transparent_bg=False))
        overlay.win.withdraw()
        overlay.tick(.01, -10000, -10000)
        overlay.tick(7, -10000, -10000)
        for tag in ("hud_stats", "hud_tools", "hud_help"):
            assert all(overlay.canvas.itemcget(item, "state") == "hidden"
                       for item in overlay.canvas.find_withtag(tag)), tag
        overlay.tick(.02, overlay.w/2, overlay.h-48)
        assert all(overlay.canvas.itemcget(item, "state") == "normal"
                   for item in overlay.canvas.find_withtag("hud_tools"))
        overlay.toggle_hud()
        overlay.tick(8, -10000, -10000)
        assert all(overlay.canvas.itemcget(item, "state") == "normal"
                   for item in overlay.canvas.find_withtag("hud_tools"))
        overlay.toggle_hud()
        overlay.tick(100, -10000, -10000)
        assert overlay.ambient and not overlay.round.ended and len(overlay.ships) == 3
        # Once movement stops, a drifting ship crossing the pointer is not an attack.
        overlay.last_pointer = (500, 400)
        overlay.last_pointer_input = overlay.visual_elapsed-5
        freeze_positions(overlay, [(500,400), (100,200), (1000,600)])
        for _ in range(6):
            overlay.tick(.02, 500, 400)
        assert not overlay.ships[0].exploding and overlay.round.kills == 0
        ship = overlay.ships[0]
        ship.portal_until = ship.grace_until = 0
        score = overlay.round.score
        ship.explode()
        assert ship.exploding and overlay.round.score > score
        overlay.start_challenge()
        assert not overlay.ambient and not overlay.round.ended and overlay.round.elapsed == 0
        overlay.tick(90, -10000, -10000)
        assert overlay.round.ended and overlay.canvas.find_withtag("result_card")
        score = overlay.round.score
        phase = overlay.ships[0].phase
        overlay.tick(.05, -10000, -10000)
        assert overlay.round.score == score and overlay.ships[0].phase != phase
        overlay.tick(13, -10000, -10000)
        assert not overlay.canvas.find_withtag("result_card")
        overlay.enter_ambient()
        assert overlay.ambient and not overlay.round.ended and len(overlay.ships) == 3
        assert overlay.round.score == 0 and overlay.round.energy == 70
        print("PASS: idle HUD hides, bottom-edge tools, HUD pin, stationary-cursor safety, endless roaming,")
        print("optional challenge, drifting final scene, small result auto-hide, return to roaming")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()


def check_tactics():
    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = ChallengeOverlay(tk.Toplevel(root), dict(mode="game", ambient=True,
                                   ships=6, planets=0, transparent_bg=False))
        overlay.win.withdraw()
        overlay.round.energy = 100
        assert overlay.spawn("WORMHOLE", 450, 350)
        assert overlay.pending_portal and not overlay.celestials and overlay.round.energy == 100
        assert not overlay.spawn("WORMHOLE", 460, 360)
        overlay.cancel_portal()
        assert not overlay.canvas.find_withtag("portal_preview") and overlay.round.energy == 100
        assert overlay.spawn("WORMHOLE", 450, 350)
        overlay.round.energy = 0
        assert not overlay.spawn("WORMHOLE", 900, 400)
        assert overlay.pending_portal and not overlay.celestials
        overlay.set_tool("STAR")
        assert not overlay.pending_portal
        overlay.round.energy = 100
        overlay.last_spawn = -10
        assert overlay.spawn("WORMHOLE", 900, 400)
        assert overlay.spawn("WORMHOLE", 450, 350)
        portal = overlay.celestials[-1]
        assert overlay.canvas.itemcget(portal.label, "text").startswith("入口")
        assert overlay.canvas.itemcget(portal.exit_label, "text").startswith("出口")
        ship = overlay.ships[0]
        ship.x, ship.y = 900, 400
        ship.grace_until = ship.portal_until = 0
        assert overlay.affect_ship(ship, .02) is True
        assert abs(math.hypot(ship.x-450, ship.y-350)-18) < .001
        assert ship.vx < 0 and ship.vy < 0
        ship.x, ship.y = 450, 350
        ship.portal_until = 0  # Even after cooldown, the output cannot return a ship.
        transported = overlay.transported
        assert overlay.affect_ship(ship, .02) is False
        assert (ship.x, ship.y) == (450, 350) and overlay.transported == transported
        overlay.clear_space()
        overlay.transported = 0
        print("PASS: entrance/exit labels, leftward output direction, no reverse attraction or transport")
        overlay.last_spawn = -10
        overlay.round.energy = 100
        assert overlay.spawn("STAR", 500, 400)
        star = overlay.celestials[-1]
        freeze_positions(overlay, [(450+i*20, 420) for i in range(6)])
        for _ in range(600):
            for ship in overlay.ships:
                overlay.affect_ship(ship, 1/60)
        counts = [sum(s.orbit_lane == lane for s in overlay.ships) for lane in range(3)]
        assert counts == [2, 2, 2], counts
        for ship in overlay.ships:
            r = ship.orbit_radius
            ellipse = ((ship.x-star.x)/r)**2+((ship.y-star.y)/(r*.38))**2
            assert .85 < ellipse < 1.05, ellipse
        overlay.tick(.01, -10000, -10000)
        assert star.residents == 6
        assert overlay.canvas.itemcget(star.surface[0], "fill") != "#562b24"
        print("PASS: portal staging/cancel/no charge on failure, three balanced elliptical lanes, star brightness")

        overlay.round.energy = 100
        overlay.last_spawn = -10
        assert overlay.spawn("BLACK_HOLE", 900, 400)
        hole = overlay.celestials[-1]
        overlay.last_spawn = -10
        assert overlay.spawn("WORMHOLE", 602, 400)
        assert overlay.spawn("WORMHOLE", hole.x, hole.y)
        portal = overlay.celestials[-1]
        assert portal.destination == (hole.x, hole.y) and hole in overlay.celestials
        ship = overlay.ships[0]
        ship.x, ship.y = 602, 400
        ship.portal_until = ship.grace_until = 0
        assert ship.orbit_body is star
        assert overlay.affect_ship(ship, .02) is True
        assert overlay.transported == 1 and ship.x == hole.x+18
        for i, other in enumerate(overlay.ships[1:]):
            other.x, other.y = 100, 170+i*70
            other.state = "IDLE"
            other.idle_timer = 10000
            other.vx = other.vy = 0
        overlay.advance_ships(.02, -10000, -10000)
        assert ship.exploding and hole.charge == 1 and overlay.absorbed == 1
        assert overlay.round.kills == 1
        overlay.advance_ships(.02, -10000, -10000)
        assert hole.charge == 1, "A consumed ship must only charge the hole once"
        energy = overlay.round.energy
        overlay.paused = True
        assert not overlay.spawn("BLACK_HOLE", hole.x, hole.y)
        overlay.paused = False
        assert overlay.spawn("STAR", hole.x, hole.y), "Clicking the core must detonate, regardless of selected tool"
        assert hole not in overlay.celestials and not overlay.canvas.find_withtag(hole.tag)
        assert overlay.round.energy == energy
        nova = overlay.waves[0]
        assert nova.radius == 155 and nova.items
        victim = overlay.ships[1]
        victim.x, victim.y = hole.x+140, hole.y
        for _ in range(18):
            overlay.advance_waves(.05)
        assert victim.exploding and overlay.round.kills == 2
        assert not overlay.canvas.find_withtag("nova_fx")
        overlay.restart()
        assert not overlay.waves and not overlay.portal_links and not overlay.pending_portal
        assert not overlay.canvas.find_withtag("portal_preview")
        assert not overlay.canvas.find_withtag("portal_link")
        print("PASS: star-to-portal pickup, delivery into black hole, single charge per ship,")
        print("manual charged detonation, extended blast/score, pause lock and effect cleanup")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()


def check_black_hole_growth():
    root = tk.Tk()
    root.withdraw()
    overlay = None
    try:
        overlay = ChallengeOverlay(tk.Toplevel(root), dict(mode="game", ships=7,
                          planets=0, transparent_bg=False, level=1, ambient=True))
        overlay.add_body("BLACK_HOLE", 500, 400)
        # add_body stores the object on the scene; inspect the actual rendered body.
        hole = overlay.celestials[-1]
        hole.update(.5)
        initial_width = hole.frame.width()
        freeze_positions(overlay, [(50, 150+i*70) for i in range(7)])
        probe = overlay.ships[-1]
        probe.x, probe.y = hole.x+280, hole.y
        assert not overlay.affect_ship(probe, .02)
        for index in range(6):
            ship = overlay.ships[index]
            ship.x, ship.y = hole.x, hole.y
            ship.grace_until = 0
            overlay.advance_ships(.02, -10000, -10000)
            assert hole.charge == index+1 and ship.exploding
            previous = hole.visual_scale
            hole.update(.1)
            assert previous < hole.visual_scale < 1+.06*hole.charge
        for _ in range(15):
            hole.update(.1)
        assert hole.frame.width() > initial_width
        probe.x, probe.y = hole.x+280, hole.y
        probe.grace_until = 0
        assert overlay.affect_ship(probe, .02) is True, "Growth must reach formerly out-of-range ships"
        probe.x, probe.y = hole.x+50, hole.y
        assert overlay.affect_ship(probe, .02) == "absorbed", "The enlarged core must swallow ships"
        hole.charge = 100
        for _ in range(50):
            hole.update(.1)
        assert 1.99 < hole.visual_scale <= 2 and hole.radius <= 460
        overlay.add_body("BLACK_HOLE", 900, 400)
        fresh = overlay.celestials[-1]
        assert fresh.visual_scale == 1 and fresh.charge == 0
        before = overlay.round.energy
        assert overlay.spawn("STAR", hole.x+90, hole.y), "The enlarged click region must detonate"
        assert hole not in overlay.celestials and overlay.round.energy == before
        assert overlay.waves[-1].radius == 440
        print("PASS: actual swallowing grows sprites smoothly, field/core/click regions grow, size cap and independent holes")
    finally:
        if overlay:
            overlay.stop()
        root.destroy()


if __name__ == "__main__":
    check_rules()
    check_canvas()
    check_quiet_ui()
    check_tactics()
    check_black_hole_growth()
