"""Real controls, movement multipliers and persistent difficulty settings."""
import math

from fleetboom.ui import LauncherUI


def check_settings():
    app = LauncherUI()
    try:
        app.ships_var.set("3")
        app.planets_var.set("1")
        app.level_var.set("4")
        app.auto_var.set(False)
        app.level_step_var.set("3")
        app.speed_var.set(1.5)
        app.start()
        scene = app.overlay
        assert scene.initial_level == scene.level == 4
        assert not scene.auto_level and scene.level_step == 3 and scene.speed_multiplier == 1.5
        assert app.initial_speed_slider.cget("from") == .25
        assert app.speed_slider.cget("to") == 3
        scene.start_challenge()
        scene.tick(20, -10000, -10000)
        assert scene.level == 4 and scene.round.elapsed == 20, "Manual level and real challenge time must stay fixed"
        scene.enter_ambient()
        scene.configure_gameplay(level=1, auto_level=True, level_step=2, speed_multiplier=1)
        for ship in scene.ships[:2]:
            ship.grace_until = 0
            ship.explode()
        assert scene.round.kills == 2 and scene.level == 2
        app.live_level_var.set("5")
        app.live_auto_var.set(False)
        app.live_step_var.set("7")
        app.live_speed_var.set(2)
        app._apply_live_gameplay()
        assert scene.level == 5 and scene.speed_multiplier == 2
        ship = scene.ships[-1]
        speed = ship.speed
        app._apply_live_gameplay()
        assert ship.speed == speed, "Applying a multiplier twice must not compound it"
        scene.configure_gameplay(speed_multiplier=1)
        assert abs(ship.speed*2-speed) < .001
        scene.configure_gameplay(speed_multiplier=2)
        for action in (scene.restart, scene.start_challenge, scene.enter_ambient,
                       scene.start_escort, scene.start_defense):
            action()
            assert scene.initial_level == scene.level == 5
            assert not scene.auto_level and scene.level_step == 7 and scene.speed_multiplier == 2
        print("PASS: launcher/live controls, manual and automatic levels, unchanged challenge clock, repeat-safe speed and mode/restart persistence")

        state = scene.defense
        scene.next_wave()
        scene.tick(.05, -10000, -10000)
        enemy = state.enemies[0]
        enemy.hp *= .6
        fraction = enemy.hp/enemy.max_hp
        old_speed = enemy.speed
        old_hp = enemy.max_hp
        scene.configure_gameplay(level=5, speed_multiplier=1)
        assert abs(enemy.speed*2-old_speed) < .001
        scene.configure_gameplay(level=9)
        assert enemy.max_hp > old_hp and abs(enemy.hp/enemy.max_hp-fraction) < .001
        scene.defense.wave = 3
        scene.configure_gameplay(level=2, auto_level=True)
        assert scene.level == scene.defense.difficulty == 4
        print("PASS: tower-defense live speed/HP tuning, preserved damage percentage, automatic wave difficulty")

        scene.start_escort()
        scene.configure_gameplay(level=1, auto_level=False, speed_multiplier=1)
        cargo = scene.ships[0]
        cargo.x = cargo.y = 300
        scene.move_toward(cargo, (900, 300), 72, .05)
        one = cargo.x-300
        cargo.x = cargo.y = 300
        scene.configure_gameplay(speed_multiplier=2)
        scene.move_toward(cargo, (900, 300), 72, .05)
        assert abs(cargo.x-300-one*2) < .001
        scene.enter_ambient()
        scene.round.energy = 100
        assert scene.spawn("STAR", 600, 400)
        ship = scene.ships[0]
        star = scene.celestials[-1]
        deltas = []
        for multiplier in (1, 2):
            scene.configure_gameplay(speed_multiplier=multiplier)
            ship.grace_until = 0
            ship.x, ship.y = star.x+102, star.y
            ship.orbit_body = None
            assert scene.affect_ship(ship, .02)
            deltas.append(ship.orbit_angle)
        assert math.isclose(deltas[1], deltas[0]*2)
        print("PASS: escort movement and celestial orbit speed obey multiplier")

        app.live_level_var.set("8")
        app.live_auto_var.set(False)
        app.live_step_var.set("4")
        app.live_speed_var.set(.75)
        app._apply_live_gameplay()
        app.stop()
        assert app.overlay is None
        assert app.level_var.get() == "8" and app.speed_var.get() == .75
        app.start()
        assert app.overlay.level == 8 and app.overlay.speed_multiplier == .75
        assert app.control_panel.cget("background") == "#1e1e20"
        assert not app.control_panel.winfo_viewable()
        print("PASS: return-to-settings/relaunch persistence and hidden charcoal panel")
    finally:
        app.stop()
        app.root.destroy()


if __name__ == "__main__":
    check_settings()
