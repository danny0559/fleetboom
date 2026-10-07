"""Persistent gameplay controls shared by every mode."""


class GameplaySettingsMixin:
    def configure_gameplay(self, *, level=None, auto_level=None, level_step=None, speed_multiplier=None):
        if level is not None:
            self.initial_level = max(1, min(11, int(level)))
        if auto_level is not None:
            self.auto_level = bool(auto_level)
        if level_step is not None:
            self.level_step = max(1, min(9999, int(level_step)))
        if speed_multiplier is not None:
            self.speed_multiplier = max(.25, min(3.0, float(speed_multiplier)))
        self.update_gameplay_difficulty(force=True)

    def update_gameplay_difficulty(self, force=False):
        bonus = 0
        if self.auto_level:
            if getattr(self, "defense_active", False):
                state = getattr(self, "defense", None)
                bonus = max(0, state.wave-1) if state else 0
            else:
                bonus = self.round.kills//self.level_step
                if not self.ambient and not getattr(self, "escort_active", False):
                    bonus += self.applied_phase*2
        level = min(11, self.initial_level+bonus)
        if force or level != self.level:
            self._apply_level(level)
            self.on_gameplay_settings_changed()

    def on_gameplay_settings_changed(self):
        """A separate mode can adapt its own simulation here."""
