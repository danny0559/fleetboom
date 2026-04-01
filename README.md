# Fleet Boom | 舰队爆炸！！！

> A fullscreen transparent Tkinter mini-game and animated screensaver where you chase agile sci-fi ships with your mouse.  
> 一个全屏透明的 Tkinter 小游戏 / 屏保程序：你用鼠标追逐会机动逃逸的科幻飞船。

## Overview | 简介

**Fleet Boom** is a lightweight Python + Tkinter Canvas project that mixes:

- evasive line-art spaceships
- multiple bullet visual styles
- drifting planets in the background
- fullscreen transparent overlay presentation
- game mode and screensaver mode

**Fleet Boom（舰队爆炸）** 是一个轻量级的 **Python + Tkinter Canvas** 项目，融合了：

- 线框科幻飞船
- 多种子弹视觉效果
- 缓慢漂移的行星背景
- 全屏透明覆盖层表现
- 游戏模式与屏保模式

It is designed to feel lively, stylish, and surprisingly dynamic while staying simple and low-overhead.  
它的目标是在保持实现简单、计算开销较低的前提下，呈现出足够灵动、有科幻感的视觉效果。

## Screenshot | 运行截图

Below are real screenshots captured from the program.  
下面是程序实际运行截图。

### Main View | 主界面

![Fleet Boom Screenshot 1](docs/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-04-01%20235404.png)

### Alternate Scene | 场景展示

![Fleet Boom Screenshot 2](docs/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-04-01%20235439.png)

### Control / Variation | 变化效果

![Fleet Boom Screenshot 3](docs/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-04-01%20235454.png)

## Highlights | 特色亮点

- **Transparent fullscreen presentation** with optional dark gradient background  
  **透明全屏显示**，并可切换为深色渐变背景

- **Sci-fi line-art ships** with layered outlines, engine glow, nav lights, and animated thrust  
  **线框科幻飞船**，包含分层轮廓、发动机核心、小航灯与动态尾焰

- **Multiple bullet archetypes** such as laser, plasma, spark, wave, and shard  
  **多种子弹类型**，包括激光、等离子、火花、波动和碎片

- **Drifting planet background** with rings, moons, highlights, and slow motion  
  **漂移行星背景**，带星环、卫星、高光和缓慢随机移动

- **Game mode + screensaver mode** in one launcher  
  **一个启动器中同时提供游戏模式与屏保模式**

- **Live controls** for difficulty, scaling, and transparency  
  **支持实时调整** 难度、缩放和背景透明效果

## Modes | 模式说明

### Game Mode | 游戏模式

- Chase the ships with your mouse
- Stay close long enough to trigger an explosion
- Ships can shoot back with different projectile styles
- Difficulty can scale automatically

- 用鼠标追逐飞船
- 持续贴近飞船可触发爆炸并计数
- 飞船会使用不同风格的子弹进行反击
- 难度可自动提升

### Screensaver Mode | 屏保模式

- No combat pressure
- Pure ambient motion and spaceship behavior
- Great for showcasing the visual style

- 没有战斗压力
- 更偏向纯展示的动态背景效果
- 很适合用来展示程序的视觉风格

## Controls | 操作方式

- **Mouse**: chase ships / move threat source  
  **鼠标**：追逐飞船 / 作为飞船的威胁来源

- **ESC**: exit fullscreen overlay  
  **ESC**：退出全屏覆盖层

- **Control panel**: tweak ship scale, planet scale, transparency, level, and auto-leveling  
  **控制面板**：可调整飞船大小、星球大小、透明背景、等级和自动升级

## Run | 运行方式

### Requirements | 环境要求

- Python 3.10+ recommended
- Standard library only for the main app (`tkinter`, `math`, `random`, etc.)

- 推荐使用 Python 3.10+
- 主程序仅依赖 Python 标准库（如 `tkinter`、`math`、`random` 等）

### Start | 启动

```bash
python spaceship14.py
```

## Project Structure | 项目结构

```text
fleetboom/
├─ spaceship14.py   # Main application | 主程序
├─ README.md        # Project introduction | 项目说明
├─ LICENSE
└─ docs/            # Screenshots and extra assets | 截图与附加资源
```

## Why It Stands Out | 为什么它更有趣

Instead of using heavy assets or complex engines, Fleet Boom builds its look with lightweight vector-style drawing and motion design:

- layered ship outlines
- animated engine cores
- responsive thrust direction
- small navigation lights
- drifting background elements

Fleet Boom 没有依赖复杂贴图或重型引擎，而是通过轻量的矢量风格绘制和动态设计来塑造观感：

- 分层飞船轮廓
- 动态发动机核心
- 会随姿态变化的尾焰方向
- 轻量航灯呼吸效果
- 缓慢漂移的背景元素

That makes it a nice example of how far you can push pure Tkinter Canvas visuals with careful design.  
这也让它成为一个很好的示例：只用 Tkinter Canvas，也能做出相当有表现力的视觉效果。

## Author | 作者

Created by **Danny0559**.  
作者：**Danny0559**
