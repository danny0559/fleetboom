"""Deterministic TD economy/combat checks plus real Tk integration."""
import tkinter as tk
from types import SimpleNamespace

from fleetboom.td_rules import DefenseState
from fleetboom.tower_defense import TowerDefenseOverlay
from fleetboom.ui import LauncherUI


def check_rules():
    state = DefenseState(1280, 720)
    assert state.build("LASER", *state.route[0])[0] is None
    assert state.credits == 160
    tower, _ = state.build("LASER", 1280*.23, 720*.45)
    assert tower and state.credits == 115
    assert state.build("LASER", tower.x+5, tower.y)[0] is None
    assert state.upgrade(tower)[0] and tower.level == 2 and state.credits == 80
    assert state.upgrade(tower)[0] and tower.level == 3 and state.credits == 10
    assert not state.upgrade(tower)[0]
    assert state.build("NOVA", 1280*.7, 720*.47)[0] is None
    assert state.sell(tower) == 105 and state.credits == 115 and not state.towers
    assert state.sell(tower) == 0
    assert state.send_wave() and state.pending == 8
    assert not state.send_wave()
    state.spawn_enemy()
    enemy = state.enemies[0]
    money = state.credits
    state.hurt(enemy, enemy.hp)
    state.hurt(enemy, 100)
    assert state.kills == 1 and state.credits == money+10
    print("PASS: route/overlap/cost validation, upgrades/max level/refunds, wave gating and single kill reward")

    for kind in ("GRAVITY", "NOVA"):
        state = DefenseState(1280, 720)
        tower, _ = state.build(kind, 1280*.23, 720*.45)
        state.send_wave()
        state.spawn_enemy()
        state.spawn_enemy()
        for enemy in state.enemies:
            enemy.progress = tower.x-state.route[0][0]
        hp = [e.hp for e in state.enemies]
        state.spawn_clock = 99
        state.tick(.02)
        assert all(e.hp < before for e, before in zip(state.enemies, hp))
        if kind == "GRAVITY":
            assert all(e.slow_until > state.elapsed for e in state.enemies)
            enemy = state.enemies[0]
            progress = enemy.progress
            state.tick(.1)
            assert abs(enemy.progress-progress-enemy.speed*.45*.1) < .001
    print("PASS: gravity area slow, movement reduction, nova area damage")

    undefended = DefenseState(1280, 720)
    undefended.send_wave()
    for _ in range(6000):
        undefended.tick(.1)
        if undefended.outcome:
            break
    assert undefended.outcome == "defeat" and undefended.health == 0
    state = DefenseState(1280, 720)
    for kind, x, y in (("LASER", .23, .45), ("GRAVITY", .39, .55), ("LASER", .7, .47)):
        assert state.build(kind, 1280*x, 720*y)[0]
    state.send_wave()
    for _ in range(6000):
        state.tick(.1)
        for tower in state.towers:
            if tower.level < 3 and state.credits >= 35*tower.level:
                state.upgrade(tower)
        if state.outcome:
            break
    assert state.outcome == "victory" and state.wave == 5 and state.kills == 60
    assert state.health > 0 and state.elapsed > 90
    stats = (state.credits, state.health, state.kills, state.wave)
    state.tick(100)
    assert stats == (state.credits, state.health, state.kills, state.wave)
    print("PASS: undefended defeat, five-wave victory with a valid build, no 90s cutoff, frozen results")


def check_canvas():
    root = tk.Tk()
    root.withdraw()
    scene = None
    try:
        scene = TowerDefenseOverlay(tk.Toplevel(root), dict(mode="game", ships=24,
                    planets=1, level=1, transparent_bg=False, ambient=True))
        assert scene.spawn("STAR", 500, 400)
        scene.start_defense()
        assert not scene.celestials and not scene.escort_active
        assert scene.defense_active and not scene.ships
        scene.set_tool("BLACK_HOLE")
        assert scene.spawn("BLACK_HOLE", scene.w*.23, scene.h*.45)
        tower = scene.defense.towers[0]
        scene.upgrade_selected()
        assert tower.level == 2
        scene.next_wave()
        scene.tick(.05, -10000, -10000)
        assert scene.enemy_views and scene.ships
        enemy = scene.defense.enemies[0]
        view = scene.enemy_views[enemy.number][0]
        scene.defense.hurt(enemy, enemy.hp)
        scene.draw_defense(.02, -10000, -10000)
        assert view.exploding and scene.canvas.type(view.boom_word) == "text"
        for _ in range(40):
            scene.draw_defense(.02, -10000, -10000)
        assert enemy.number not in scene.enemy_views
        scene.paused = True
        elapsed, money = scene.defense.elapsed, scene.defense.credits
        scene.tick(10, -10000, -10000)
        assert not scene.spawn("STAR", scene.w*.7, scene.h*.47)
        scene.right_click(SimpleNamespace(x=tower.x, y=tower.y))
        assert tower in scene.defense.towers
        assert scene.defense.elapsed == elapsed and scene.defense.credits == money
        scene.paused = False
        scene.clear_space()
        assert tower in scene.defense.towers and scene.defense_tool is None
        scene.right_click(SimpleNamespace(x=tower.x, y=tower.y))
        assert not scene.defense.towers and not scene.tower_views
        print("PASS: celestial cleanup, build/upgrade/sell, original BOOM rendering, pause and safe cancellation")

        scene.restart()
        scene.next_wave()
        scene.defense.spawn_enemy()
        enemy = scene.defense.enemies[0]
        enemy.segment = len(scene.defense.lengths)-1
        enemy.progress = scene.defense.lengths[-1]-.001
        scene.defense.health = 1
        scene.tick(.1, -10000, -10000)
        assert scene.round.ended and scene.defense.outcome == "defeat"
        assert scene.canvas.find_withtag("result_card")
        scene.tick(.1, -10000, -10000)
        assert scene.defense.health == 0
        scene.set_scales(ship_scale=1.8, planet_scale=.8)
        scene.enter_ambient()
        assert not scene.defense_active and len(scene.ships) == 24
        assert not scene.canvas.find_withtag("td_scene")
        assert scene.canvas.itemcget(scene.energy_bar, "fill") == "#59d9ee"
        assert all("激光塔" not in scene.canvas.itemcget(i, "text") for i in scene.canvas.find_withtag("tool_BLACK_HOLE") if scene.canvas.type(i) == "text")
        scene.start_escort()
        assert scene.escort_active and not scene.defense_active
        scene.start_defense()
        assert not scene.canvas.find_withtag("escort_beacon") and not scene.escort_active
        scene.start_challenge()
        assert not scene.defense_active and not scene.escort_active and not scene.ambient
        assert scene.ship_scale == 1.8 and scene.planet_scale == .8
        print("PASS: defeat card/freeze, restart, all mode transitions, tool restoration and scale preservation")
    finally:
        if scene:
            scene.stop()
        root.destroy()


def check_launcher():
    app = LauncherUI()
    try:
        app.mode_var.set("tower_defense")
        app.start()
        assert app.overlay.defense_active
        assert app.control_panel.cget("background") == "#1e1e20"
        assert not app.control_panel.winfo_viewable()
        print("PASS: launcher tower-defense choice and hidden charcoal control panel")
    finally:
        app.stop()
        app.root.destroy()


if __name__ == "__main__":
    check_rules()
    check_canvas()
    check_launcher()
