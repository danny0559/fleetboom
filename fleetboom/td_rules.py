"""Window-independent tower-defense simulation and tuning values."""
import math
from dataclasses import dataclass, field


TOWER_TYPES = {
    "LASER": dict(name="激光塔", cost=45, range=165, damage=18, cooldown=.45, color="#80eaff"),
    "GRAVITY": dict(name="引力塔", cost=65, range=145, damage=4, cooldown=.65, color="#cca2ff"),
    "NOVA": dict(name="爆裂塔", cost=85, range=155, damage=32, cooldown=1.8, color="#ffc17e"),
}


@dataclass
class Invader:
    number: int
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    reward: int
    tank: bool = False
    segment: int = 0
    progress: float = 0
    slow_until: float = 0


@dataclass
class Tower:
    kind: str
    x: float
    y: float
    level: int = 1
    cooldown: float = 0
    invested: int = 0
    aim: float = 0


@dataclass
class DefenseState:
    """Routes are in canvas coordinates; speed and ranges scale with the viewport."""
    width: int
    height: int
    credits: int = 160
    health: int = 20
    max_health: int = 20
    max_waves: int = 5
    wave: int = 0
    elapsed: float = 0
    kills: int = 0
    score: int = 0
    waiting: float = 12
    pending: int = 0
    spawn_clock: float = 0
    serial: int = 0
    outcome: str = ""
    difficulty: int = 1
    speed_multiplier: float = 1.0
    enemies: list = field(default_factory=list)
    towers: list = field(default_factory=list)
    effects: list = field(default_factory=list)

    def __post_init__(self):
        self.scale = min(self.width/1280, self.height/720)
        self.route = [(self.width*x, self.height*y) for x, y in
                      ((.06, .36), (.30, .36), (.30, .65), (.62, .65),
                       (.62, .32), (.88, .32), (.94, .50))]
        self.lengths = [math.dist(a, b) for a, b in zip(self.route, self.route[1:])]

    def route_distance(self, x, y):
        distances = []
        for (ax, ay), (bx, by) in zip(self.route, self.route[1:]):
            dx, dy = bx-ax, by-ay
            t = max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            distances.append(math.hypot(x-ax-t*dx, y-ay-t*dy))
        return min(distances)

    def configure_gameplay(self, level, speed_multiplier):
        level = max(1, min(11, int(level)))
        speed_multiplier = max(.25, min(3.0, float(speed_multiplier)))
        health_ratio = (1+.10*(level-1))/(1+.10*(self.difficulty-1))
        speed_ratio = (speed_multiplier*(1+.035*(level-1)) /
                       (self.speed_multiplier*(1+.035*(self.difficulty-1))))
        for enemy in self.enemies:
            enemy.hp *= health_ratio
            enemy.max_hp *= health_ratio
            enemy.speed *= speed_ratio
        self.difficulty = level
        self.speed_multiplier = speed_multiplier

    def build(self, kind, x, y):
        if self.outcome:
            return None, "本局已结束，按 T 再开一局"
        if kind not in TOWER_TYPES:
            return None, "先选择防御塔"
        cost = TOWER_TYPES[kind]["cost"]
        if self.credits < cost:
            return None, "晶体不足，击败敌舰或完成一波后获得晶体"
        if not (45*self.scale < x < self.width-45*self.scale and 130 < y < self.height-105):
            return None, "请在星海中的空地建造"
        if self.route_distance(x, y) < 36*self.scale:
            return None, "不能占用航线，放在航线旁边"
        if any(math.hypot(x-t.x, y-t.y) < 58*self.scale for t in self.towers):
            return None, "防御塔之间需要留出空间"
        tower = Tower(kind, x, y, invested=cost)
        self.towers.append(tower)
        self.credits -= cost
        return tower, f"{TOWER_TYPES[kind]['name']}已部署"

    def upgrade(self, tower):
        if self.outcome or tower not in self.towers:
            return False, "请选择防御塔"
        if tower.level >= 3:
            return False, "已达到最高等级"
        cost = 35*tower.level
        if self.credits < cost:
            return False, f"升级需要 {cost} 晶体"
        self.credits -= cost
        tower.invested += cost
        tower.level += 1
        return True, f"升级至 {tower.level} 级"

    def sell(self, tower):
        if self.outcome or tower not in self.towers:
            return 0
        refund = int(tower.invested*.7)
        self.credits += refund
        self.towers.remove(tower)
        return refund

    def tower_range(self, tower):
        return (TOWER_TYPES[tower.kind]["range"]+15*(tower.level-1))*self.scale

    def send_wave(self):
        if self.outcome or self.pending or self.enemies or self.wave >= self.max_waves:
            return False
        self.wave += 1
        self.pending = 6+2*self.wave
        self.spawn_clock = 0
        self.waiting = 0
        return True

    def spawn_enemy(self):
        self.serial += 1
        tank = self.serial % 5 == 0
        hp = (45+18*self.wave)*(2 if tank else 1)*(1+.10*(self.difficulty-1))
        x, y = self.route[0]
        enemy = Invader(self.serial, x, y, hp, hp,
                       (68+5*self.wave)*self.scale*(.65 if tank else 1)*self.speed_multiplier*(1+.035*(self.difficulty-1)),
                       9+self.wave, tank)
        self.enemies.append(enemy)
        self.pending -= 1

    def hurt(self, enemy, damage):
        if enemy not in self.enemies:
            return
        enemy.hp -= damage
        if enemy.hp <= 0:
            self.enemies.remove(enemy)
            self.credits += enemy.reward
            self.kills += 1
            self.score += 100
            self.effects.append(("boom", enemy.x, enemy.y, enemy.x, enemy.y, "#ffd28f", enemy.number))

    def tick(self, dt):
        self.effects.clear()
        if self.outcome:
            return
        dt = max(0, min(.1, dt))
        self.elapsed += dt
        if self.waiting > 0:
            self.waiting = max(0, self.waiting-dt)
            if self.waiting == 0:
                self.send_wave()
        if self.pending:
            self.spawn_clock -= dt
            if self.spawn_clock <= 0:
                self.spawn_enemy()
                self.spawn_clock += .9
        for enemy in list(self.enemies):
            speed = enemy.speed*(.45 if self.elapsed < enemy.slow_until else 1)
            enemy.progress += speed*dt
            while enemy.segment < len(self.lengths) and enemy.progress >= self.lengths[enemy.segment]:
                enemy.progress -= self.lengths[enemy.segment]
                enemy.segment += 1
            if enemy.segment >= len(self.lengths):
                self.enemies.remove(enemy)
                self.health = max(0, self.health-(3 if enemy.tank else 1))
                self.effects.append(("leak", enemy.x, enemy.y, enemy.x, enemy.y, "#ff697b"))
                if self.health == 0:
                    self.outcome = "defeat"
                    return
                continue
            a, b = self.route[enemy.segment:enemy.segment+2]
            u = enemy.progress/self.lengths[enemy.segment]
            enemy.x, enemy.y = a[0]+(b[0]-a[0])*u, a[1]+(b[1]-a[1])*u
        for tower in self.towers:
            tower.cooldown = max(0, tower.cooldown-dt)
            targets = [e for e in self.enemies if math.hypot(e.x-tower.x, e.y-tower.y) <= self.tower_range(tower)]
            if not targets or tower.cooldown > 0:
                continue
            enemy = max(targets, key=lambda e: (e.segment, e.progress))
            spec = TOWER_TYPES[tower.kind]
            tower.aim = math.atan2(enemy.y-tower.y, enemy.x-tower.x)
            tower.cooldown = spec["cooldown"]*.9**(tower.level-1)
            damage = spec["damage"]*1.55**(tower.level-1)
            self.effects.append(("shot", tower.x, tower.y, enemy.x, enemy.y, spec["color"]))
            if tower.kind == "GRAVITY":
                for nearby in targets:
                    nearby.slow_until = self.elapsed+1.3
                    self.hurt(nearby, damage)
            elif tower.kind == "NOVA":
                for nearby in list(self.enemies):
                    if math.hypot(nearby.x-enemy.x, nearby.y-enemy.y) <= 75*self.scale:
                        self.hurt(nearby, damage)
                self.effects.append(("blast", enemy.x, enemy.y, enemy.x, enemy.y, spec["color"]))
            else:
                self.hurt(enemy, damage)
        if self.wave and not self.pending and not self.enemies and self.waiting == 0:
            self.credits += 25
            if self.wave >= self.max_waves:
                self.outcome = "victory"
            else:
                self.waiting = 8
