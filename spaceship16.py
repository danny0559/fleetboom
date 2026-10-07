"""FleetBoom entry point. Edit the focused modules in fleetboom/ for future changes."""
if __package__:
    from .fleetboom.config import COSTS, DURATION
    from .fleetboom.rules import RoundState, Shockwave
    from .fleetboom.celestials import TacticalCelestial
    from .fleetboom.ships import ChallengeShip
    from .fleetboom.controller import ChallengeOverlay
    from .fleetboom.ui import LauncherUI
else:
    from fleetboom.config import COSTS, DURATION
    from fleetboom.rules import RoundState, Shockwave
    from fleetboom.celestials import TacticalCelestial
    from fleetboom.ships import ChallengeShip
    from fleetboom.controller import ChallengeOverlay
    from fleetboom.ui import LauncherUI

__all__ = ["COSTS", "DURATION", "RoundState", "Shockwave", "TacticalCelestial",
           "ChallengeShip", "ChallengeOverlay", "LauncherUI"]

if __name__ == "__main__":
    LauncherUI().run()
