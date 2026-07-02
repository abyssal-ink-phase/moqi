# moqi
moqi— an experimental 3D , hazards, and an expandable board. A question, not an answer — playable sandbox, basic AI, room to grow.
moqi(墨棋 / Ink Chess) — a humble description:

moqi("ink chess," 墨棋) is an experimental prototype of a 3D asymmetric chess-like environment. It asks a simple but open-ended question: What happens when you take traditional board games — with their perfect information, symmetric rules, and flat grids — and replace them with a 3D space, fog of war, asymmetric unit types, an expandable map, and a living hazard (the "Ink Chess" itself) that drifts, grows, and devours pieces?

Right now, moqiis a playable sandbox, not a finished benchmark. The rule engine (logic/engine.py) is fully implemented — six unit types (scout, rook, knight, cannon, engineer, seeder) plus a core per player, fog-of-war via chunked lazy loading, "mist-edge" expansion by knights, phase-jump and fleet transfer by rooks, mines, and the ink sphere as a gravity-driven environmental hazard. The frontend (static/index.html) runs on Three.js with interactive camera, piece selection, hotkeys, undo, save/load, and a victory screen. You can play 2–10 players, human or simple AI.

But the AI is deliberately kept basic — random moves plus a handcrafted greedy scorer — and no reinforcement learning training or balance tuning has been done yet. So calling it a "multi-agent benchmark" would be premature.

So what is moqigood for, as it stands?

Game design exploration: Test how asymmetric abilities, 3D movement, and environmental hazards interact in a concrete, runnable system.

Teaching tool: A self-contained example of a turn-based multiplayer engine + HTTP server + Three.js frontend, compact enough to read through in an afternoon.

Research starting point: If you're interested in multi-agent RL in partially observable, procedurally expanding environments, moqicould become a testbed — once proper interfaces (e.g., Gymnasium) and stronger agents are added.

The real contribution here is the question, not the answer. We hope this prototype invites others to explore the same space, improve the AI, refine the rules, and maybe one day turn moqiinto something worthy of the word "benchmark." Until then, it's an honest attempt to push beyond traditional chess variants — warts and all.
