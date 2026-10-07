# FleetBoom 模块修改指南

新版启动入口仍是 `../spaceship16.py`，具体功能放在本目录。新版不再导入 `spaceship14.py` 或 `spaceship15.py`，旧版本保留供独立运行。

## 修改时找哪个文件

| 想修改的内容 | 文件 | 职责 |
|---|---|---|
| 基础难度、自动升级策略、速度倍率、跨模式设置 | `settings.py` | 共享设置，供每种玩法应用自己的难度与速度 |
| 塔防敌舰、波次、晶体、伤害、升级与胜负 | `td_rules.py` | 无窗口依赖的塔防模拟与数值配置 |
| 塔防航线、塔与敌舰绘制、建造操作、塔防界面 | `tower_defense.py` | 独立塔防模式，非塔防时沿用原模式 |
| 护航目标、运输船、海盗追击、灯塔与送达奖励 | `escort.py` | 独立护航模式，继承原控制器；不开护航时调用原玩法 |
| 天体费用、持续时间、颜色、轨道半径 | `config.py` | 共用配置与素材路径 |
| 能量恢复、得分、连锁奖励、挑战计时 | `rules.py` | 独立规则与冲击波数据，不依赖窗口 |
| 鼠标放置天体、两步虫洞、取消放置 | `abilities.py` | 能力选择、消耗、放置预览与清场 |
| 虫洞传送方向、黑洞吸引、恒星公转 | `physics.py` | 天体对飞船的运动影响 |
| 连锁爆炸、黑洞蓄能引爆、冲击波范围 | `combat.py` | 爆炸传播、击败与回能 |
| 飞船外形、移动、BOOM 特效 | `ships.py` | 飞船绘制与状态 |
| 黑洞、虫洞、恒星的外观与动画 | `celestials.py` | 天体绘制、生命周期与蓄能表现 |
| 子弹外观和运动 | `projectiles.py` | 弹丸对象 |
| 装饰行星的外观、大小和运动 | `planets.py` | 行星对象 |
| 底边工具条、信息卡、自动隐藏、成绩卡 | `hud.py` | 游戏画面上的轻量界面 |
| 启动设置、灰黑色控制面板、大小/速度滑块、难度控件 | `ui.py` | 设置窗口与实时参数控制 |
| 背景、画布、透明桌面、整体缩放 | `world.py` | 场景基础设施 |
| 漫游/挑战切换、暂停、重开、主循环 | `controller.py` | 组织场景、规则和各功能模块 |
| 图片加载与缓存 | `assets.py` | 从相邻 `../assets/` 加载素材 |

例如：修虫洞进出口先看 `physics.py`，调整虫洞外观看 `celestials.py`；改面板背景看 `ui.py`，改遮挡星海的提示卡看 `hud.py`。新增玩法可能涉及几个模块，但不需要替换整个启动文件。

## 模块如何配合

`controller.py` 的 `ChallengeOverlay` 将能力、物理、战斗和 HUD 的 mixin 与 `World` 组合，并驱动更新循环。功能模块使用同一个场景状态；新增方法应放在对应职责的模块里，避免在多个模块复制同名方法。

启动界面创建 `TowerDefenseOverlay`，继承 `EscortOverlay`。塔防使用独立的 `DefenseState` 模拟；仅进入护航时使用 `EscortOverlay` 的规则，漫游和原挑战继续交给 `ChallengeOverlay`。护航的计数和目标在 `EscortMission`，船只标识在 `EscortShip`；原控制器无需增加新模式分支。

包内使用相对导入。规则和配置模块不应反向导入界面或控制器，以免循环依赖。`spaceship16.py` 保留原有公开类名，已有验证脚本可以继续使用。

## 启动与验证

在 FleetBoom 仓库根目录执行（安装依赖后）：

```powershell
& '.\.venv\Scripts\python.exe' '.\spaceship16.py'
# 也可按模块启动
& '.\.venv\Scripts\python.exe' -m fleetboom
# 验证规则及真实 Tk Canvas 交互
& '.\.venv\Scripts\python.exe' '.\verify_challenge.py'
& '.\.venv\Scripts\python.exe' '.\verify_escort.py'
& '.\.venv\Scripts\python.exe' '.\verify_tower_defense.py'
& '.\.venv\Scripts\python.exe' '.\verify_settings.py'
```

运行需要 Tkinter、Pillow，以及本包相邻的 `assets/` 素材目录。搬动源码时应同时保留 `spaceship16.py`、`fleetboom/` 和 `assets/`。
