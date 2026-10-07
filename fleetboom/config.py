"""Shared tuning values, celestial names, colors and project asset location."""
from pathlib import Path


KEY = "#00ff00"
COSTS = {"RANDOM": 16, "BLACK_HOLE": 40, "WORMHOLE": 28, "STAR": 20}
DURATION = 90.0
COLORS = {"BLACK_HOLE": "#ffbd72", "WORMHOLE": "#5ce8ec", "STAR": "#ffc76a"}
NAMES = {"RANDOM": "随机天体", "BLACK_HOLE": "黑洞", "WORMHOLE": "虫洞", "STAR": "恒星"}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ORBITS = (102, 145, 188)
BLACK_HOLE_LIFE = 30
BLACK_HOLE_GROWTH_PER_SHIP = .06
BLACK_HOLE_MAX_SCALE = 2.0
BLACK_HOLE_GROWTH_TIME = .35
