```markdown
# Ink Chess (墨棋)

> **Asymmetric 3D Civilization Survival Game**  
> Set in the *Abyss Ink Era* universe – a ruthless test of strategic foresight under the encroaching Ink Tide.

[🇨🇳 中文版](README_CN.md) | [🌐 English](README.md)

---

## What is Ink Chess?

Ink Chess is a **turn-based 3D asymmetric strategy game** played on an expandable cubic board (up to 99×99×99). Each player controls a single **Civilization Core** and 26 customizable units chosen from seven unique types. The goal: be the last core standing while a growing **Ink Tide** slowly consumes the board.

**Key features:**

- True 3D movement & combat (X/Y/Z axes)
- 7 distinct unit classes with unique abilities
- Fog of war, mine placement, space expansion
- Dynamic Ink Tide disaster – moves, swallows, grows
- AI opponents & hot‑seat multiplayer
- Undo, save & load game states
- Fully interactive Three.js frontend

---

## Quick Start

```bash
# Prerequisites: Python 3.8+, Go 1.18+

git clone https://github.com/abyssal-ink-phase/moqi.git
cd moqi
pip install flask pyinstaller  # if needed
python launcher.py
# Open http://localhost:8080 in your browser
```

> **Note:** The backend is written in Go (`engine.go`, `board.go`) and compiled automatically. On first run, `launcher.py` will build it if not present.

---

## Rules Summary

### Board
- Initial size: `[3 × (3 + players)]³` (e.g., 18×18×18 for 2 players)
- Maximum expansion: 99×99×99 (fog permanently locks beyond that)

### Units (each player gets 1 Core + 26 custom slots)

| Unit | Movement | Special Ability |
|------|----------|----------------|
| **Civilization Core** | 1 step any direction | If destroyed → player eliminated + Ink Tide +5 size |
| **Scout** (*Kan Tan Bing*) | 1 step orthogonally | Snipe over 1 empty cell; creates 5×5×5 illumination zone; 9×9×9 anti‑mine safe zone |
| **Stellar Voyager** (*Xing Hang Zhe*, Rook) | Unlimited straight (no jump) | Phase swap with Core; Fleet transport (carry up to 25 units in 3×3×3 area) |
| **Pulse Cannon** (*Mai Chong Pao*, Cannon) | Unlimited straight | Attack using exactly one screen (any piece except mines) |
| **Hyperdimensional Wanderer** (*Chao Kong Jian Man You Zhe*, Knight) | Infinite chain jumps | Can expand board by detonating fog edges (3×3×3); uses visible mines as jump boards |
| **Configurator** (*Ge Zhi Gou Xing Zhe*, Engineer) | Up to 3 steps (ignores obstacles) | Place invisible permanent mines; Hell mode: place anywhere in 7×7×7 area |
| **Ark Sower** (*Bo Zhong Fang Zhou*, Breeder) | Up to 6 steps (or 0 when producing) | Produces new units (except Core/mines) every 2 rounds when Core survives; can self‑replicate |

### Ink Tide Disaster
- Appears after `(players + 2)` rounds at a random edge cell
- Moves twice per turn: first toward nearest unit in XY plane, then in Z axis
- Swallows all pieces/mines inside its cube instantly
- Grows: +1 every few rounds (depends on player count), +1 per 10 global deaths, +5 when a Core dies
- Ends game when size reaches 99 or covers entire board

### Victory
- Last surviving Core wins
- If all Cores are swallowed by Ink Tide → draw (total extinction)

Full detailed rules (in Chinese) are available in [墨棋规则白皮书](rules_zh.md).

---

## Project Structure

```
├── launcher.py          # HTTP server, routes, auto‑build Go binary
├── engine.py            # Game logic (≈850 lines)
├── board.py             # 3D board management (≈230 lines)
├── static/
│   └── index.html       # Three.js frontend (≈550 lines)
├── saves/               # Saved game states
├── rules_zh.md          # Complete rulebook (Chinese)
└── README.md            # This file
```

---

## Contributing

Contributions are welcome! Please use **English** for issues and pull requests so everyone can participate.

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

Before submitting, please check existing issues and keep code style consistent.

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- World setting inspired by *渊墨纪元宇宙笔记*
- 3D rendering powered by [Three.js](https://threejs.org/)
- Built with ❤️ for the love of abstract strategy games
```
