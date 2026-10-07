"""Charcoal launcher/settings UI, live size sliders and panel actions."""
import tkinter as tk
from .tower_defense import TowerDefenseOverlay


class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.mode_var = tk.StringVar(value="game")
        self.planets_var = tk.StringVar(value="3")
        self.ships_var = tk.StringVar(value="24")
        self.transparent_bg_var = tk.BooleanVar(value=False)
        self.ship_scale_var = tk.DoubleVar(value=1.35)
        self.planet_scale_var = tk.DoubleVar(value=1.0)
        self.level_var = tk.StringVar(value="1")
        self.auto_var = tk.BooleanVar(value=True)
        self.level_step_var = tk.StringVar(value="10")
        self.speed_var = tk.DoubleVar(value=1.0)
        self.overlay = None
        self.control_panel = None
        self._build()
        self.theme(self.root)
        self.root.title("FleetBoom 3.2 · 星海漫游")
        self.title_label.config(font=("Segoe UI", 23, "bold"))

    def _build(self):
        frame = tk.Frame(self.root, padx=26, pady=24)
        frame.pack()
        self.title_label = tk.Label(frame, text="FLEET / BOOM", anchor="w")
        self.title_label.pack(anchor="w")
        tk.Label(frame, text="让星海安静漂浮，也能随手引发一场 BOOM。", anchor="w").pack(anchor="w", pady=(6, 18))
        modes = tk.Frame(frame)
        modes.pack(anchor="w")
        tk.Radiobutton(modes, text="漫游 · 轻互动", variable=self.mode_var, value="game").pack(side="left")
        tk.Radiobutton(modes, text="90 秒挑战", variable=self.mode_var, value="screensaver").pack(side="left", padx=12)
        tk.Radiobutton(modes, text="星际护航", variable=self.mode_var, value="escort").pack(side="left")
        tk.Radiobutton(modes, text="星际塔防", variable=self.mode_var, value="tower_defense").pack(side="left", padx=(12, 0))
        settings = tk.Frame(frame)
        settings.pack(fill="x", pady=14)
        tk.Label(settings, text="飞船").grid(row=0, column=0, padx=(0, 8))
        tk.Spinbox(settings, from_=1, to=80, width=5, textvariable=self.ships_var).grid(row=0, column=1)
        tk.Label(settings, text="行星").grid(row=0, column=2, padx=(20, 8))
        tk.Spinbox(settings, from_=0, to=80, width=5, textvariable=self.planets_var).grid(row=0, column=3)
        sizes = tk.Frame(frame)
        sizes.pack(fill="x", pady=(0, 10))
        self.initial_ship_slider = tk.Scale(sizes, label="飞船大小", from_=.3, to=2.5,
                    resolution=.05, orient="horizontal", variable=self.ship_scale_var, length=290)
        self.initial_ship_slider.pack(fill="x")
        self.initial_planet_slider = tk.Scale(sizes, label="星球大小", from_=.3, to=2.5,
                    resolution=.05, orient="horizontal", variable=self.planet_scale_var, length=290)
        self.initial_planet_slider.pack(fill="x", pady=(4, 0))
        self._gameplay_controls(frame)
        tk.Checkbutton(frame, text="透明桌面背景", variable=self.transparent_bg_var).pack(anchor="w")
        tk.Button(frame, text="进入星海", command=self.start, width=34, pady=8).pack(pady=(20, 8))
        tk.Label(frame, text="底边唤出工具 · G 挑战 · E 护航 · T 塔防 · V 漫游 · ESC 返回", fg="#7893ad").pack()

    def _gameplay_controls(self, parent, live=False):
        box = tk.LabelFrame(parent, text="难度与速度", padx=8, pady=5)
        box.pack(fill="x", pady=(4, 8), padx=12 if live else 0)
        level = self.live_level_var if live else self.level_var
        auto = self.live_auto_var if live else self.auto_var
        step = self.live_step_var if live else self.level_step_var
        speed = self.live_speed_var if live else self.speed_var
        callback = self._apply_live_gameplay if live else self._refresh_mode_ui
        tk.Label(box, text="基础难度").grid(row=0, column=0, sticky="w")
        spin = tk.Spinbox(box, from_=1, to=11, width=4, textvariable=level, command=callback)
        spin.grid(row=0, column=1, sticky="w", padx=6)
        tk.Checkbutton(box, text="自动升级", variable=auto, command=callback).grid(row=0, column=2, sticky="w")
        tk.Label(box, text="每击败几艘升一级").grid(row=1, column=0, columnspan=2, sticky="w")
        threshold = tk.Spinbox(box, from_=1, to=9999, width=5, textvariable=step, command=callback)
        threshold.grid(row=1, column=2, sticky="w", pady=3)
        slider = tk.Scale(box, label="飞船速度（倍率）", from_=.25, to=3.0, resolution=.05,
                          orient="horizontal", variable=speed, length=240,
                          command=(lambda value: self._apply_live_gameplay()) if live else None)
        slider.grid(row=2, column=0, columnspan=3, sticky="ew")
        for widget in (spin, threshold):
            widget.bind("<Return>", lambda e: callback())
            widget.bind("<FocusOut>", lambda e: callback())
        if live:
            self.live_level_spin = spin
            self.live_step_spin = threshold
            self.speed_slider = slider
            self.live_status = tk.Label(box, text="")
            self.live_status.grid(row=3, column=0, columnspan=3, sticky="w")
        else:
            self.level_spin = spin
            self.initial_speed_slider = slider

    def _refresh_mode_ui(self):
        # Manual base level remains editable while automatic progression is enabled.
        return

    @staticmethod
    def theme(widget):
        """Neutral charcoal settings UI, with readable controls on the same palette."""
        options = widget.keys()
        bg = "#1e1e20"
        if isinstance(widget, (tk.Button, tk.Entry, tk.Spinbox)):
            bg = "#303033"
        for key, value in (("background", bg), ("foreground", "#ededee"),
                           ("activebackground", "#444448"), ("activeforeground", "#ffffff"),
                           ("selectcolor", "#38383c"), ("insertbackground", "#ededee"),
                           ("troughcolor", "#414145"), ("highlightbackground", "#1e1e20"),
                           ("highlightcolor", "#82828a"), ("disabledforeground", "#87878e")):
            if key in options:
                widget.config(**{key: value})
        if "font" in options:
            widget.config(font=("Microsoft YaHei UI", 10))
        for child in widget.winfo_children():
            LauncherUI.theme(child)

    def start(self):
        if self.overlay is not None:
            return
        config = dict(mode="game", ambient=self.mode_var.get() == "game",
              escort=self.mode_var.get() == "escort",
              tower_defense=self.mode_var.get() == "tower_defense",
              ships=self._safe_int(self.ships_var.get(), 24, 1, 80),
              planets=self._safe_int(self.planets_var.get(), 3, 0, 80),
              level=self._safe_int(self.level_var.get(), 1, 1, 11), auto_level=self.auto_var.get(),
              level_step=self._safe_int(self.level_step_var.get(), 10, 1, 9999),
              speed_multiplier=self.speed_var.get(),
              transparent_bg=self.transparent_bg_var.get(), ship_scale=self.ship_scale_var.get(),
              planet_scale=self.planet_scale_var.get())
        self.root.withdraw()
        self.overlay = TowerDefenseOverlay(tk.Toplevel(self.root), config, self._on_overlay_stop)
        self._open_control_panel(config)
        self.overlay.win.focus_force()

    def _open_control_panel(self, config):
        cp = tk.Toplevel(self.root)
        self.control_panel = cp
        cp.title("BOOM · 星海设置")
        cp.attributes("-topmost", True)
        shell = tk.Canvas(cp, highlightthickness=0)
        shell.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(cp, orient="vertical", command=shell.yview)
        shell.config(yscrollcommand=scrollbar.set)
        panel = tk.Frame(shell)
        shell.create_window(0, 0, window=panel, anchor="nw")
        panel.bind("<Configure>", lambda e: shell.config(scrollregion=shell.bbox("all")))
        cp.bind("<MouseWheel>", lambda e: shell.yview_scroll(int(-e.delta/120), "units"))
        tk.Label(panel, text="星海设置 · F2 收起").pack(padx=16, pady=12)
        tk.Button(panel, text="漫游 (V)", command=lambda: self.panel_action(self.overlay.enter_ambient)).pack(fill="x", padx=16, pady=3)
        tk.Button(panel, text="90 秒挑战 (G)", command=lambda: self.panel_action(self.overlay.start_challenge)).pack(fill="x", padx=16, pady=3)
        tk.Button(panel, text="星际护航 (E)", command=lambda: self.panel_action(self.overlay.start_escort)).pack(fill="x", padx=16, pady=3)
        tk.Button(panel, text="星际塔防 (T)", command=lambda: self.panel_action(self.overlay.start_defense)).pack(fill="x", padx=16, pady=3)
        self.live_transparent_var = tk.BooleanVar(value=self.overlay.transparent_bg)
        tk.Checkbutton(panel, text="透明桌面背景", variable=self.live_transparent_var,
                       command=self._toggle_live_bg).pack(padx=16, pady=8)
        self.live_ship_scale_var = tk.DoubleVar(value=self.overlay.ship_scale)
        self.live_planet_scale_var = tk.DoubleVar(value=self.overlay.planet_scale)
        self.ship_scale_slider = tk.Scale(panel, label="飞船大小", from_=.3, to=2.5,
                 resolution=.05, orient="horizontal", variable=self.live_ship_scale_var,
                 command=lambda v: self._apply_live_scales(), length=220)
        self.ship_scale_slider.pack(padx=16)
        self.planet_scale_slider = tk.Scale(panel, label="星球大小", from_=.3, to=2.5,
                 resolution=.05, orient="horizontal", variable=self.live_planet_scale_var,
                 command=lambda v: self._apply_live_scales(), length=220)
        self.planet_scale_slider.pack(padx=16, pady=(4, 0))
        self.live_level_var = tk.StringVar(value=str(self.overlay.initial_level))
        self.live_auto_var = tk.BooleanVar(value=self.overlay.auto_level)
        self.live_step_var = tk.StringVar(value=str(self.overlay.level_step))
        self.live_speed_var = tk.DoubleVar(value=self.overlay.speed_multiplier)
        self._gameplay_controls(panel, live=True)
        tk.Button(panel, text="暂停 / 继续 (P)", command=lambda: self.overlay.toggle_pause()).pack(fill="x", padx=16, pady=(12, 3))
        tk.Button(panel, text="重新开始 (R)", command=lambda: self.overlay.restart()).pack(fill="x", padx=16, pady=3)
        tk.Button(panel, text="清除天体", command=lambda: self.overlay.clear_space()).pack(fill="x", padx=16, pady=3)
        tk.Button(panel, text="返回设置 (ESC)", command=self.stop).pack(fill="x", padx=16, pady=(3, 14))
        cp.protocol("WM_DELETE_WINDOW", cp.withdraw)
        self.theme(cp)
        cp.update_idletasks()
        height = min(panel.winfo_reqheight(), cp.winfo_screenheight()-100)
        shell.config(width=panel.winfo_reqwidth(), height=height)
        if panel.winfo_reqheight() > height:
            scrollbar.pack(side="right", fill="y")
        cp.resizable(False, False)
        cp.geometry(f"+30+{max(20, min(160, cp.winfo_screenheight()-height-50))}")
        cp.withdraw()
        cp.bind("<F2>", lambda e: self.toggle_panel())
        cp.bind("<Escape>", lambda e: self.toggle_panel())
        self.overlay.win.bind("<F2>", lambda e: self.toggle_panel())
        self._update_live_status()

    def _apply_live_gameplay(self):
        if self.overlay is None or not hasattr(self, "live_level_var"):
            return
        level = self._safe_int(self.live_level_var.get(), self.overlay.initial_level, 1, 11)
        step = self._safe_int(self.live_step_var.get(), self.overlay.level_step, 1, 9999)
        self.live_level_var.set(str(level))
        self.live_step_var.set(str(step))
        self.overlay.configure_gameplay(level=level, auto_level=self.live_auto_var.get(),
                                       level_step=step, speed_multiplier=self.live_speed_var.get())
        self._save_gameplay_settings()

    def _save_gameplay_settings(self):
        if self.overlay is not None:
            self.level_var.set(str(self.overlay.initial_level))
            self.auto_var.set(self.overlay.auto_level)
            self.level_step_var.set(str(self.overlay.level_step))
            self.speed_var.set(self.overlay.speed_multiplier)

    def _update_live_status(self):
        if self.overlay is None or self.control_panel is None:
            return
        progression = ("手动固定难度" if not self.overlay.auto_level else
                       "自动：按波次升级" if self.overlay.defense_active else
                       "自动：按击败数升级" if self.overlay.ambient or self.overlay.escort_active else
                       "自动：击败数与挑战阶段升级")
        self.live_status.config(text=f"当前 Lv.{self.overlay.level} · 速度 {self.overlay.speed_multiplier:.2f}×\n{progression}")
        self._live_status_job = self.control_panel.after(400, self._update_live_status)

    def panel_action(self, action):
        action()
        self.control_panel.withdraw()
        self.overlay.win.focus_force()

    def toggle_panel(self):
        cp = self.control_panel
        if cp.winfo_viewable():
            cp.withdraw()
            self.overlay.win.focus_force()
        else:
            cp.deiconify()
            cp.lift()
            cp.focus_force()

    def _safe_int(self, s, default, lo, hi):
        try:
            v = int(str(s).strip())
            return max(lo, min(hi, v))
        except Exception:
            return default

    def _apply_live_scales(self):
        if self.overlay is None:
            return
        try:
            ss = float(self.live_ship_scale_var.get())
        except Exception:
            ss = 1.0
        try:
            ps = float(self.live_planet_scale_var.get())
        except Exception:
            ps = 1.0
        self.overlay.set_scales(ship_scale=ss, planet_scale=ps)

    def _toggle_live_bg(self):
        if self.overlay is None:
            return
        self.overlay.set_background_transparent(bool(self.live_transparent_var.get()))

    def stop(self):
        if self.overlay is not None:
            try:
                self.overlay.stop()
            except Exception:
                pass

    def _on_overlay_stop(self):
        self._save_gameplay_settings()
        self.overlay = None
        try:
            if self.control_panel is not None:
                if getattr(self, "_live_status_job", None):
                    self.control_panel.after_cancel(self._live_status_job)
                    self._live_status_job = None
                self.control_panel.destroy()
        except Exception:
            pass
        self.control_panel = None
        self.root.deiconify()

    def run(self):
        self.root.mainloop()
