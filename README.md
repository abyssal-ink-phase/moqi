Mochess · 烬寂推演
English
Introduction
Mochess is a 3D turn-based strategy board game designed for both human play and multi-agent reinforcement learning research. It features deterministic rules, high branching factor, fog-of-war, and a dynamic "Ink Chess" that grows and devours pieces. The game is implemented with a pure Python backend (no third-party libraries) and a Three.js 3D frontend, making it lightweight and portable. It is open-sourced under GPLv3.

Features
6 unit types: Scout (snipe), Rook (phase jump & fleet transport), Knight (expand fog-of-war), Cannon (attack over obstacles), Engineer (lay mines), Seeder (produce new units).

Fog-of-war: The map expands only when a Knight explores, revealing 3x3x3 areas. This introduces the classic exploration-exploitation trade-off.

Dynamic Ink Chess: A black sphere that moves toward clusters of pieces, grows in size, and devours everything in its radius. It adds a constant threat and emergent complexity.

Built-in heuristic AI: A rule-based opponent that evaluates moves by capturing value, safety, and ink threat, ready for immediate play.

Save/Load & Undo: Full game state serialization and history rollback.

Pure Python + Three.js: No external dependencies for the backend; frontend can run locally without internet.

Reinforcement Learning (Work in Progress)
Mochess is evolving into a standard RL environment. Planned features:

gym.Env API wrapper for easy integration.

Flat discrete action space with invalid-action masking.

State encoder using PointNet-like aggregation over piece coordinates.

Self-play training pipelines with MAPPO / QMIX examples.

See the dev-rl branch for ongoing development.

中文
介绍
墨棋（Mochess）是一款 3D 回合制策略棋盘游戏，适合人类娱乐，也专为多智能体强化学习教学而设计。它拥有确定的规则、极高的分支因子、战争迷雾以及会动态扩张并吞噬棋子的“墨棋”机制。后端采用纯 Python（无需任何第三方库），前端基于 Three.js 构建 3D 可视化，轻量且易于分发。本项目遵循 GPLv3 开源协议。

特性
6 种兵种：兵（隔空切割）、车（相位跃迁 & 舰队运载）、马（拓荒揭开迷雾）、炮（隔子攻击）、工兵（布雷）、种兵（生产新单位）。

战争迷雾：只有马可以拓荒，逐步揭示 3×3×3 的新区域，带来探索与利用的经典决策困境。

动态墨棋：一个黑色球体会自动追踪棋子密集区，随时间增大并吞噬范围内的一切，形成持续的紧迫感和复杂局势。

内置启发式 AI：基于贪心评分（吃子、安全、墨棋威胁）的电脑对手，开箱即玩。

存档 / 读档 & 悔棋：完整的游戏状态序列化与历史回退功能。

纯 Python + Three.js：后端零依赖，前端可离线运行，无需联网。

强化学习（开发中）
墨棋正在向标准强化学习环境演进，计划提供：

gym.Env 接口封装，方便接入常见算法库。

扁平化的离散动作空间，配合非法动作掩码。

基于棋子坐标聚合的 PointNet 风格状态编码器。

自博弈训练示例，支持 MAPPO / QMIX 等多智能体算法。

详细进展请关注 dev-rl 分支。

License
This project is licensed under the GPLv3 – see the LICENSE file for details.

Note: Gameplay mechanics and installation instructions are omitted here; you can add them as you have prepared.

