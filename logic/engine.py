# logic/engine.py

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from logic.board import Board, Coord, CHUNK_SIZE, SUB_SIZE
from collections import deque
import random
import json  # 新增：用于安全替换 eval

# --- 数据模型 ---

@dataclass
class Piece:
    id: str
    type: str        # core, scout, knight, rook, cannon, engineer, seeder
    owner: int       # 玩家ID 1..n
    position: Coord
    alive: bool = True
    can_act: bool = True
    rooted: bool = False
    has_authorization: bool = False

@dataclass
class Mine:
    owner: int
    position: Coord
    visible_to_all: bool = False

@dataclass
class InkChess:
    position: Coord
    size: int

# --- 引擎主类 ---

class MochessEngine:
    def __init__(self, player_count: int = 2, config: dict = None, player_types: list = None):
        if player_count < 2 or player_count > 10:
            raise ValueError("玩家数必须在2~10之间")
        base_size = 3 * (3 + player_count)
        if base_size < 18:
            base_size = 18
        chunks_side = (base_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        if chunks_side < 2:
            chunks_side = 2
        self.board = Board(initial_chunks_per_side=chunks_side)
        self.player_count = player_count
        self.players = list(range(1, player_count + 1))
        self.current_player = 1
        self.turn_number = 0
        self.pieces: List[Piece] = []
        self.mines: List[Mine] = []
        self.ink_chess = InkChess(position=(0, 0, 110), size=3)
        self.ink_on_board = False
        self.death_counter = 0
        self.game_over = False
        self.winner = None
        self.core_timer: Dict[int, int] = {p: 0 for p in self.players}

        # ----- 新增：玩家类型（'human' 或 'ai'）-----
        if player_types is None:
            player_types = ['human'] * player_count
        self.player_types = player_types

        if config is not None:
            self._init_pieces_with_config(config)
        else:
            self._init_pieces()

        # 悔棋历史栈
        self.history: List[dict] = []
        self.max_history: int = 20
        self._save_state()

    # ---------- 棋子生成 ----------
    def _init_pieces(self):
        all_cells = list(self.board.get_all_cells())
        if not all_cells:
            raise RuntimeError("棋盘没有可用坐标，请检查区块加载。")
        candidate_cores = []
        for coord in all_cells:
            x, y, z = coord
            valid = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        if not self.board.in_bounds((x+dx, y+dy, z+dz)):
                            valid = False
                            break
                    if not valid:
                        break
                if not valid:
                    break
            if valid:
                candidate_cores.append(coord)
        if not candidate_cores:
            candidate_cores = all_cells

        core_positions = []
        for pid in self.players:
            attempts = 0
            while attempts < 100:
                core = random.choice(candidate_cores)
                conflict = False
                for other in core_positions:
                    if self.board.distance(other, core) < 4:
                        conflict = True
                        break
                if not conflict:
                    core_positions.append(core)
                    break
                attempts += 1
            else:
                core_positions.append(random.choice(candidate_cores))

        offsets = [(dx, dy, dz) for dx in (-1,0,1) for dy in (-1,0,1) for dz in (-1,0,1)]
        offsets.remove((0,0,0))

        for idx, pid in enumerate(self.players):
            cx, cy, cz = core_positions[idx]
            random.shuffle(offsets)
            types = (["scout"]*5 + ["rook"]*4 + ["knight"]*4 +
                     ["cannon"]*4 + ["engineer"]*4 + ["seeder"]*5)
            random.shuffle(types)

            self.pieces.append(Piece(f"core_{pid}_0", "core", pid, (cx, cy, cz)))

            for j, (typ, (dx, dy, dz)) in enumerate(zip(types, offsets)):
                x, y, z = cx + dx, cy + dy, cz + dz
                if self.board.in_bounds((x, y, z)):
                    self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (x, y, z)))
                else:
                    placed = False
                    for _ in range(30):
                        nx = cx + random.randint(-2, 2)
                        ny = cy + random.randint(-2, 2)
                        nz = cz + random.randint(-2, 2)
                        if self.board.in_bounds((nx, ny, nz)):
                            if not any(p.position == (nx, ny, nz) and p.alive for p in self.pieces):
                                self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (nx, ny, nz)))
                                placed = True
                                break
                    if not placed:
                        self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (cx, cy, cz)))

    def _init_pieces_with_config(self, config: dict):
        all_cells = list(self.board.get_all_cells())
        if not all_cells:
            raise RuntimeError("棋盘没有可用坐标，请检查区块加载。")
        candidate_cores = []
        for coord in all_cells:
            x, y, z = coord
            valid = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        if not self.board.in_bounds((x+dx, y+dy, z+dz)):
                            valid = False
                            break
                    if not valid:
                        break
                if not valid:
                    break
            if valid:
                candidate_cores.append(coord)
        if not candidate_cores:
            candidate_cores = all_cells

        core_positions = []
        for pid in self.players:
            attempts = 0
            while attempts < 100:
                core = random.choice(candidate_cores)
                conflict = False
                for other in core_positions:
                    if self.board.distance(other, core) < 4:
                        conflict = True
                        break
                if not conflict:
                    core_positions.append(core)
                    break
                attempts += 1
            else:
                core_positions.append(random.choice(candidate_cores))

        offsets = [(dx, dy, dz) for dx in (-1,0,1) for dy in (-1,0,1) for dz in (-1,0,1)]
        offsets.remove((0,0,0))

        for idx, pid in enumerate(self.players):
            cx, cy, cz = core_positions[idx]
            player_cfg = config.get(str(pid), {})
            scout = player_cfg.get('scout', 0)
            rook = player_cfg.get('rook', 0)
            knight = player_cfg.get('knight', 0)
            cannon = player_cfg.get('cannon', 0)
            engineer = player_cfg.get('engineer', 0)
            seeder = player_cfg.get('seeder', 0)
            total = scout + rook + knight + cannon + engineer + seeder
            if total != 26:
                raise ValueError(f"玩家 {pid} 的棋子总数 {total} 不等于 26")

            types = (["scout"]*scout + ["rook"]*rook + ["knight"]*knight +
                     ["cannon"]*cannon + ["engineer"]*engineer + ["seeder"]*seeder)
            random.shuffle(types)

            self.pieces.append(Piece(f"core_{pid}_0", "core", pid, (cx, cy, cz)))

            for j, (typ, (dx, dy, dz)) in enumerate(zip(types, offsets)):
                x, y, z = cx + dx, cy + dy, cz + dz
                if self.board.in_bounds((x, y, z)):
                    self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (x, y, z)))
                else:
                    placed = False
                    for _ in range(30):
                        nx = cx + random.randint(-2, 2)
                        ny = cy + random.randint(-2, 2)
                        nz = cz + random.randint(-2, 2)
                        if self.board.in_bounds((nx, ny, nz)):
                            if not any(p.position == (nx, ny, nz) and p.alive for p in self.pieces):
                                self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (nx, ny, nz)))
                                placed = True
                                break
                    if not placed:
                        self.pieces.append(Piece(f"{typ}_{pid}_{j+1}", typ, pid, (cx, cy, cz)))

    # ---------- 状态查询 ----------
    def get_state(self) -> dict:
        player = self.current_player

        light_zones = []
        safe_zones = []
        for p in self.pieces:
            if p.type == "scout" and p.alive:
                light_zones.append({"center": list(p.position), "radius": 2})
                safe_zones.append({"center": list(p.position), "radius": 4})

        mines_data = []
        for m in self.mines:
            visible = self._is_mine_visible_to_player(m, player)
            mines_data.append({
                "owner": m.owner,
                "position": list(m.position),
                "visible": visible
            })

        bounds = self.board.bounds
        return {
            "board_size": [bounds[1] - bounds[0] + 1, bounds[3] - bounds[2] + 1, bounds[5] - bounds[4] + 1],
            "board_bbox": bounds,
            "max_boundary": [99, 99, 99],
            "chunks": self.board.get_loaded_chunk_keys(),
            "chunk_size": CHUNK_SIZE,
            "revealed_regions": self.board.get_revealed_regions(),
            "sub_size": SUB_SIZE,
            "pieces": [{"id": p.id, "type": p.type, "owner": p.owner, "position": list(p.position), "can_act": p.can_act, "rooted": p.rooted}
                       for p in self.pieces if p.alive],
            "mines": mines_data,
            "ink_chess": {"position": list(self.ink_chess.position), "size": self.ink_chess.size},
            "light_zones": light_zones,
            "safe_zones": safe_zones,
            "current_player": self.current_player,
            "turn": self.turn_number,
            "game_over": self.game_over,
            "winner": self.winner
        }

    # ========== 悔棋/存档序列化 ==========
    def _serialize_board(self) -> dict:
        chunks_data = {}
        for key, cells in self.board.chunks.items():
            chunks_data[f"{key[0]},{key[1]},{key[2]}"] = list(cells)
        return {
            "chunks": chunks_data,
            "revealed_regions": [(f"{k[0]},{k[1]},{k[2]}", sx, sy, sz) 
                                 for k, sx, sy, sz in self.board.revealed_regions],
            "bounds": self.board.bounds,
        }

    def _deserialize_board(self, data: dict):
        """从存档数据恢复棋盘，带类型检查和容错"""
        self.board.chunks.clear()
        self.board.revealed_regions.clear()
        
        # 恢复 chunks
        chunks_data = data.get("chunks", {})
        for key_str, cells in chunks_data.items():
            try:
                k = tuple(map(int, key_str.split(',')))
            except Exception:
                print(f"⚠️ 无效的 chunk key: {key_str}")
                continue
            
            # 将 cells 转换为列表（如果是字符串则 JSON 解析，安全替换 eval）
            if isinstance(cells, str):
                try:
                    cells = json.loads(cells) # <--- 安全修复，替换了 eval()
                except:
                    print(f"⚠️ 无法 JSON 解析 cells: {cells}")
                    continue
            if not isinstance(cells, list):
                try:
                    cells = list(cells)
                except:
                    print(f"⚠️ 无法将 cells 转为列表: {cells}")
                    continue
            
            # 确保每个元素都是长度为3的坐标
            if not all(isinstance(c, (list, tuple)) and len(c) == 3 for c in cells):
                print(f"⚠️ 跳过格式错误的 chunks 键 {key_str}: 坐标格式不对")
                continue
            self.board.chunks[k] = {tuple(c) for c in cells}
        
        # 恢复 revealed_regions
        for item in data.get("revealed_regions", []):
            try:
                k_str, sx, sy, sz = item
                k = tuple(map(int, k_str.split(',')))
                self.board.revealed_regions.add((k, sx, sy, sz))
            except Exception as e:
                print(f"⚠️ 跳过无效的 revealed_regions: {item}，错误: {e}")
        
        # 恢复 bounds，如果为空则从 chunks 重建
        self.board.bounds = data.get("bounds", [0, 0, 0, 0, 0, 0])
        if self.board.bounds == [0, 0, 0, 0, 0, 0] and self.board.chunks:
            self.board._update_bounds()
            print(f"✅ 从 chunks 重建边界: {self.board.bounds}")

    def _save_state(self):
        board_data = self._serialize_board()
        pieces_data = []
        for p in self.pieces:
            pieces_data.append({
                "id": p.id,
                "type": p.type,
                "owner": p.owner,
                "position": list(p.position),
                "alive": p.alive,
                "can_act": p.can_act,
                "rooted": p.rooted,
                "has_authorization": p.has_authorization,
            })
        mines_data = []
        for m in self.mines:
            mines_data.append({
                "owner": m.owner,
                "position": list(m.position),
                "visible_to_all": m.visible_to_all,
            })
        snapshot = {
            "board": board_data,
            "pieces": pieces_data,
            "mines": mines_data,
            "ink_chess": {
                "position": list(self.ink_chess.position),
                "size": self.ink_chess.size,
            },
            "ink_on_board": self.ink_on_board,
            "turn_number": self.turn_number,
            "current_player": self.current_player,
            "death_counter": self.death_counter,
            "core_timer": dict(self.core_timer),
            "game_over": self.game_over,
            "winner": self.winner,
            "player_count": self.player_count,
            "players": list(self.players),
        }
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def _restore_state_internal(self, snapshot: dict) -> bool:
        """内部状态恢复，不操作历史栈"""
        self._deserialize_board(snapshot.get("board", {}))
        self.board._update_bounds() 
        self.pieces.clear()
        for p_data in snapshot.get("pieces", []):
            p = Piece(
                id=p_data.get("id", ""),
                type=p_data.get("type", ""),
                owner=p_data.get("owner", 0),
                position=tuple(p_data.get("position", [0, 0, 0])),
                alive=p_data.get("alive", True),
                can_act=p_data.get("can_act", True),
                rooted=p_data.get("rooted", False),
                has_authorization=p_data.get("has_authorization", False),
            )
            self.pieces.append(p)
        
        self.mines.clear()
        for m_data in snapshot.get("mines", []):
            m = Mine(
                owner=m_data.get("owner", 0),
                position=tuple(m_data.get("position", [0, 0, 0])),
                visible_to_all=m_data.get("visible_to_all", False),
            )
            self.mines.append(m)
        
        ink = snapshot.get("ink_chess", {})
        self.ink_chess.position = tuple(ink.get("position", [0, 0, 0]))
        self.ink_chess.size = ink.get("size", 3)
        
        self.ink_on_board = snapshot.get("ink_on_board", False)
        self.turn_number = snapshot.get("turn_number", 0)
        self.current_player = snapshot.get("current_player", 1)
        self.death_counter = snapshot.get("death_counter", 0)
        self.core_timer = dict(snapshot.get("core_timer", {}))
        self.game_over = snapshot.get("game_over", False)
        self.winner = snapshot.get("winner", None)
        self.player_count = snapshot.get("player_count", 2)
        self.players = list(snapshot.get("players", list(range(1, self.player_count+1))))
        
        return True

    def restore_state(self, snapshot: dict) -> bool:
        print("🔍 开始恢复状态，snapshot 的键：", snapshot.keys())  # 调试
        try:
            success = self._restore_state_internal(snapshot)
            print("✅ _restore_state_internal 返回:", success)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False
        if success:
            self.history.clear()
            self._save_state()
        return success

    def undo(self) -> Tuple[bool, str]:
        if self.game_over:
            return False, "游戏已结束，无法悔棋"
        if len(self.history) < 2:
            return False, "没有更多的历史步骤"
        self.history.pop()
        previous = self.history[-1]
        if self._restore_state_internal(previous):
            return True, f"已悔棋到第 {self.turn_number} 回合"
        else:
            return False, "悔棋失败"

    # ---------- 存档接口 ----------
    def serialize_state(self) -> dict:
        board_data = self._serialize_board()
        pieces_data = []
        for p in self.pieces:
            pieces_data.append({
                "id": p.id,
                "type": p.type,
                "owner": p.owner,
                "position": list(p.position),
                "alive": p.alive,
                "can_act": p.can_act,
                "rooted": p.rooted,
                "has_authorization": p.has_authorization,
            })
        mines_data = []
        for m in self.mines:
            mines_data.append({
                "owner": m.owner,
                "position": list(m.position),
                "visible_to_all": m.visible_to_all,
            })
        return {
            "version": "1.0",
            "board": board_data,
            "pieces": pieces_data,
            "mines": mines_data,
            "ink_chess": {
                "position": list(self.ink_chess.position),
                "size": self.ink_chess.size,
            },
            "ink_on_board": self.ink_on_board,
            "turn_number": self.turn_number,
            "current_player": self.current_player,
            "death_counter": self.death_counter,
            "core_timer": dict(self.core_timer),
            "game_over": self.game_over,
            "winner": self.winner,
            "player_count": self.player_count,
            "players": list(self.players),
        }

    def load_from_snapshot(self, snapshot: dict) -> bool:
        return self.restore_state(snapshot)

    # ---------- 辅助方法 ----------
    def _get_player_core(self, player: int) -> Optional[Piece]:
        for p in self.pieces:
            if p.type == "core" and p.owner == player and p.alive:
                return p
        return None

    def _piece_at(self, pos: Coord, alive_only: bool = True) -> Optional[Piece]:
        for p in self.pieces:
            if p.alive and p.position == pos:
                return p
        return None

    def _mine_at(self, pos: Coord) -> Optional[Mine]:
        for m in self.mines:
            if m.position == pos:
                return m
        return None

    def _is_occupied_by_friendly(self, pos: Coord, player: int) -> bool:
        p = self._piece_at(pos)
        return p is not None and p.owner == player

    def _is_occupied_by_any(self, pos: Coord) -> bool:
        return self._piece_at(pos) is not None or self._mine_at(pos) is not None

    def _is_mine_visible_to_player(self, mine: Mine, player: int) -> bool:
        if mine.owner == player:
            return True
        for p in self.pieces:
            if p.type == "scout" and p.alive and p.owner == player:
                if self.board.distance(p.position, mine.position) <= 2:
                    return True
        return False

    def _check_line_clear(self, start: Coord, end: Coord) -> bool:
        line = self.board.line_between(start, end)
        for pos in line[1:-1]:
            if self._is_occupied_by_any(pos):
                return False
        return True

    def _count_blockers(self, start: Coord, end: Coord) -> int:
        line = self.board.line_between(start, end)
        count = 0
        for pos in line[1:-1]:
            if self._piece_at(pos) and not self._mine_at(pos):
                count += 1
        return count

    # ---------- 生产授权 ----------
    def _broadcast_production_pulse(self, player: int):
        for piece in self.pieces:
            if piece.type == "seeder" and piece.owner == player and piece.alive:
                piece.has_authorization = True

    def _check_production_authorization(self, player: int):
        core = self._get_player_core(player)
        if not core or not core.alive:
            return
        if player not in self.core_timer:
            self.core_timer[player] = 0
        self.core_timer[player] += 1
        if self.core_timer[player] >= 2:
            self.core_timer[player] = 0
            self._broadcast_production_pulse(player)

    # ---------- 移动主方法 ----------
    def move_piece(self, player: int, piece_id: str, target: Coord, mode: str = 'move') -> Tuple[bool, str, List[str]]:
        # 操作前保存状态（用于悔棋）
        self._save_state()
        
        piece = next((p for p in self.pieces if p.id == piece_id and p.owner == player), None)
        if not piece or not piece.alive:
            return False, "无效棋子", []
        if not self.board.in_bounds(target):
            return False, "超出棋盘", []

        # ========== 兵处理 ==========
        if piece.type == "scout":
            if mode == 'snipe':
                result = self._scout_snipe(piece, target)
                return result
            else:
                ok, msg = self._move_scout_move(piece, target)
                if not ok:
                    return False, msg, []
                old_pos = piece.position
                piece.position = target
                events = [f"{player}号玩家的兵移动到{target}"]
                target_piece = self._piece_at(target)
                if target_piece and target_piece.owner != player:
                    target_piece.alive = False
                    self.death_counter += 1
                    events.append(f"吃掉敌方{target_piece.type}")
                    if target_piece.type == "core":
                        self._eliminate_player(target_piece.owner)
                        events.append(f"玩家{target_piece.owner}核心被吃，文明覆灭！")
                mine = self._mine_at(target)
                if mine:
                    piece.alive = False
                    self.mines.remove(mine)
                    self.death_counter += 1
                    events.append(f"踩中地雷，兵阵亡！")
                self._check_victory()
                return True, "移动成功", events

        # ========== 炮处理 ==========
        if piece.type == "cannon":
            attack_ok, _ = self._move_cannon(piece, target)
            if attack_ok:
                target_piece = self._piece_at(target)
                target_mine = self._mine_at(target)
                if target_piece and target_piece.owner != player:
                    target_piece.alive = False
                    self.death_counter += 1
                    events = [f"炮击摧毁敌方{target_piece.type}"]
                    if target_piece.type == "core":
                        self._eliminate_player(target_piece.owner)
                        events.append(f"玩家{target_piece.owner}核心被炮击，文明覆灭！")
                    self._check_victory()
                    return True, "炮击成功", events
                elif target_mine:
                    self.mines.remove(target_mine)
                    self._check_victory()
                    return True, "炮击摧毁地雷", ["炮击摧毁地雷"]
                else:
                    return False, "炮必须攻击单位", []
            else:
                if not self.board.is_straight_line(piece.position, target):
                    return False, "炮移动必须直线"
                if not self._check_line_clear(piece.position, target):
                    return False, "移动路径上有阻挡"
                if self._is_occupied_by_friendly(target, player):
                    return False, "目标格有己方棋子"
                old_pos = piece.position
                piece.position = target
                events = [f"{player}号玩家的炮移动到{target}"]
                target_piece = self._piece_at(target)
                if target_piece and target_piece.owner != player:
                    target_piece.alive = False
                    self.death_counter += 1
                    events.append(f"吃掉敌方{target_piece.type}")
                    if target_piece.type == "core":
                        self._eliminate_player(target_piece.owner)
                        events.append(f"玩家{target_piece.owner}核心被吃，文明覆灭！")
                mine = self._mine_at(target)
                if mine:
                    piece.alive = False
                    self.mines.remove(mine)
                    self.death_counter += 1
                    events.append(f"踩中地雷，炮阵亡！")
                self._check_victory()
                return True, "移动成功", events

        # ========== 种兵处理 ==========
        if piece.type == "seeder":
            if mode == 'produce':
                return False, "请使用生产指令", []
            else:
                if piece.rooted:
                    return False, "种兵已永久扎根，无法移动"
                ok, msg = self._move_seeder(piece, target)
                if not ok:
                    return False, msg, []
                old_pos = piece.position
                piece.position = target
                events = [f"{player}号玩家的种兵移动到{target}"]
                target_piece = self._piece_at(target)
                if target_piece and target_piece.owner != player:
                    target_piece.alive = False
                    self.death_counter += 1
                    events.append(f"吃掉敌方{target_piece.type}")
                    if target_piece.type == "core":
                        self._eliminate_player(target_piece.owner)
                        events.append(f"玩家{target_piece.owner}核心被吃，文明覆灭！")
                mine = self._mine_at(target)
                if mine:
                    piece.alive = False
                    self.mines.remove(mine)
                    self.death_counter += 1
                    events.append(f"踩中地雷，种兵阵亡！")
                self._check_victory()
                return True, "移动成功", events

        # ========== 其他兵种 ==========
        if piece.type == "core":
            ok, msg = self._move_core(piece, target)
        elif piece.type == "rook":
            ok, msg = self._move_rook(piece, target)
        elif piece.type == "knight":
            ok, msg = self._move_knight(piece, target)
        elif piece.type == "engineer":
            ok, msg = self._move_engineer(piece, target)
        else:
            return False, "未知兵种", []

        if not ok:
            return False, msg, []

        old_pos = piece.position
        piece.position = target
        events = [f"{player}号玩家的{piece.type}移动到{target}"]
        target_piece = self._piece_at(target)
        if target_piece and target_piece.owner != player:
            target_piece.alive = False
            self.death_counter += 1
            events.append(f"吃掉敌方{target_piece.type}")
            if target_piece.type == "core":
                self._eliminate_player(target_piece.owner)
                events.append(f"玩家{target_piece.owner}核心被吃，文明覆灭！")
        mine = self._mine_at(target)
        if mine:
            piece.alive = False
            self.mines.remove(mine)
            self.death_counter += 1
            events.append(f"踩中地雷，{piece.type}阵亡！")
        self._check_victory()
        return True, "移动成功", events

    # ---------- 种兵移动判定 ----------
    def _move_seeder(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        if piece.rooted:
            return False, "种兵已永久扎根，无法移动"
        if self.board.distance(piece.position, target) > 6:
            return False, "种兵最多移动6格"
        if self._is_occupied_by_friendly(target, piece.owner):
            return False, "目标格有己方棋子"
        return True, ""

    # ---------- 种兵生产指令 ----------
    def seeder_produce(self, player: int, piece_id: str, target: Coord, unit_type: str) -> Tuple[bool, str, List[str]]:
        # 操作前保存状态
        self._save_state()
        
        piece = next((p for p in self.pieces if p.id == piece_id and p.owner == player), None)
        if not piece or not piece.alive:
            return False, "种兵无效", []
        if piece.type != "seeder":
            return False, "只有种兵可以生产", []

        if not piece.has_authorization:
            return False, "未收到生产授权", []

        dx = abs(target[0] - piece.position[0])
        dy = abs(target[1] - piece.position[1])
        dz = abs(target[2] - piece.position[2])
        if dx + dy + dz != 1:
            return False, "生产目标必须相邻", []

        if not self.board.in_bounds(target):
            return False, "目标超出棋盘", []

        if self._is_occupied_by_any(target):
            return False, "目标格已被占据", []

        allowed_types = ["scout", "rook", "knight", "cannon", "engineer", "seeder"]
        if unit_type not in allowed_types:
            return False, "无法生产该类型", []

        new_id = f"{unit_type}_{player}_{len(self.pieces)}"
        new_piece = Piece(new_id, unit_type, player, target, alive=True, can_act=False, rooted=False, has_authorization=False)
        self.pieces.append(new_piece)

        piece.rooted = True
        piece.has_authorization = False

        events = [f"种兵在{target}生产了{unit_type}"]
        self._check_victory()
        return True, "生产成功", events

    # ---------- 兵切割 ----------
    def _scout_snipe(self, piece: Piece, target: Coord) -> Tuple[bool, str, List[str]]:
        dx = target[0] - piece.position[0]
        dy = target[1] - piece.position[1]
        dz = target[2] - piece.position[2]

        if not ((abs(dx) == 2 and dy == 0 and dz == 0) or
                (abs(dy) == 2 and dx == 0 and dz == 0) or
                (abs(dz) == 2 and dx == 0 and dy == 0)):
            return False, "切割目标必须在正前方2格（直线）", []

        mid = ((piece.position[0] + target[0]) // 2,
               (piece.position[1] + target[1]) // 2,
               (piece.position[2] + target[2]) // 2)

        mid_piece = self._piece_at(mid)
        if mid_piece and mid_piece.owner != piece.owner:
            return False, "中间格有敌方棋子阻挡", []
        if self._mine_at(mid):
            return False, "中间格有地雷阻挡", []

        target_piece = self._piece_at(target)
        if target_piece and target_piece.owner != piece.owner:
            target_piece.alive = False
            self.death_counter += 1
            events = [f"兵隔空切割摧毁敌方{target_piece.type}"]
            if target_piece.type == "core":
                self._eliminate_player(target_piece.owner)
                events.append(f"玩家{target_piece.owner}核心被切割，文明覆灭！")
            self._check_victory()
            return True, "切割成功", events

        target_mine = self._mine_at(target)
        if target_mine and self._is_mine_visible_to_player(target_mine, piece.owner):
            self.mines.remove(target_mine)
            self._check_victory()
            return True, "切割地雷成功", ["兵隔空切割摧毁敌方地雷"]

        return False, "目标不是敌方单位或可见地雷", []

    # ---------- 兵普通移动 ----------
    def _move_scout_move(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        dx = abs(target[0] - piece.position[0])
        dy = abs(target[1] - piece.position[1])
        dz = abs(target[2] - piece.position[2])
        if dx + dy + dz == 1:
            if self._is_occupied_by_friendly(target, piece.owner):
                return False, "目标格有己方棋子"
            return True, ""
        return False, "兵只能走1格（正交方向）"

    # ---------- 各兵种移动合法性 ----------
    def _move_core(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        if self.board.distance(piece.position, target) <= 1.8:
            if self._is_occupied_by_friendly(target, piece.owner):
                return False, "目标格有己方棋子"
            return True, ""
        return False, "核心只能移动1格"

    def _move_rook(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        if not self.board.is_straight_line(piece.position, target):
            return False, "车必须直线移动"
        if not self._check_line_clear(piece.position, target):
            return False, "路径上有阻挡"
        return True, ""

    def _move_cannon(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        if not self.board.is_straight_line(piece.position, target):
            return False, "炮必须直线攻击"
        blockers = self._count_blockers(piece.position, target)
        if blockers != 1:
            return False, "炮需要恰好一个炮架"
        target_piece = self._piece_at(target)
        target_mine = self._mine_at(target)
        if not target_piece and not target_mine:
            return False, "炮必须攻击单位"
        if target_piece and target_piece.owner == piece.owner:
            return False, "不能攻击己方"
        return True, ""

    def _move_knight(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        start = piece.position
        if start == target:
            return False, "不能停留在原地"

        dist = self.board.distance(start, target)

        # 1. 无跳板：允许走1格或2格（直线，即正交或体对角线）
        if dist <= 1.8 or (dist <= 2.1 and self.board.is_straight_line(start, target)):
            if self._is_occupied_by_friendly(target, piece.owner):
                return False, "目标格有己方棋子"
            if dist > 1.8:
                mid = ((start[0] + target[0]) // 2,
                       (start[1] + target[1]) // 2,
                       (start[2] + target[2]) // 2)
                if self._is_occupied_by_any(mid):
                    return False, "中间格有障碍物，无法跨越"
            return True, ""

        # 2. 有跳板：无限连跳
        q = deque()
        q.append((start, frozenset([start])))
        while q:
            cur, visited = q.popleft()
            for p in self.pieces:
                if not p.alive or p.id == piece.id or p.position == cur:
                    continue
                land = (2 * p.position[0] - cur[0],
                        2 * p.position[1] - cur[1],
                        2 * p.position[2] - cur[2])
                if not self.board.in_bounds(land):
                    continue
                if land in visited:
                    continue
                if self._is_occupied_by_friendly(land, piece.owner):
                    continue
                if self._mine_at(land) is not None:
                    continue
                if land == target:
                    return True, ""
                new_visited = set(visited)
                new_visited.add(land)
                q.append((land, frozenset(new_visited)))
        return False, "无法通过合法跳跃到达目标"

    def _move_engineer(self, piece: Piece, target: Coord) -> Tuple[bool, str]:
        if self.board.distance(piece.position, target) <= 3:
            if self._is_occupied_by_friendly(target, piece.owner):
                return False, "目标格有己方棋子"
            return True, ""
        return False, "工兵最多移动3格"

    # ---------- 特殊行动 ----------
    def rook_phase_jump(self, player: int, rook_id: str, core_id: str) -> Tuple[bool, str, List[str]]:
        # 操作前保存状态
        self._save_state()
        
        rook = next((p for p in self.pieces if p.id == rook_id and p.owner == player and p.type == "rook"), None)
        core = next((p for p in self.pieces if p.id == core_id and p.owner == player and p.type == "core"), None)
        if not rook or not core or not rook.alive or not core.alive:
            return False, "车或核心无效", []
        if not self.board.is_straight_line(rook.position, core.position):
            return False, "不在同一直线", []
        if not self._check_line_clear(rook.position, core.position):
            return False, "路径有阻挡", []
        rook_pos = rook.position
        core_pos = core.position
        rook.position = core_pos
        core.position = rook_pos
        mine = self._mine_at(core.position)
        if mine:
            core.alive = False
            self.mines.remove(mine)
            self.death_counter += 1
            self._eliminate_player(player)
            return True, "核心换位后踩雷，文明覆灭！", [f"核心踩雷阵亡"]
        return True, "相位跃迁成功", [f"车与核心交换位置"]

    def engineer_lay_mine(self, player: int, engineer_id: str, mine_pos: Coord) -> Tuple[bool, str]:
        # 操作前保存状态
        self._save_state()
        
        eng = next((p for p in self.pieces if p.id == engineer_id and p.owner == player and p.type == "engineer"), None)
        if not eng or not eng.alive:
            return False, "工兵无效"
        if max(abs(eng.position[0] - mine_pos[0]),
               abs(eng.position[1] - mine_pos[1]),
               abs(eng.position[2] - mine_pos[2])) > 3:
            return False, "工兵只能在7×7×7范围内布雷"
        if self._is_occupied_by_any(mine_pos):
            return False, "目标格已被占据"
        for p in self.pieces:
            if p.type == "scout" and p.alive and p.owner != player:
                if (abs(p.position[0] - mine_pos[0]) <= 4 and
                    abs(p.position[1] - mine_pos[1]) <= 4 and
                    abs(p.position[2] - mine_pos[2]) <= 4):
                    return False, "此处位于敌方兵的安全区内，禁止布雷"
        if not self.board.in_bounds(mine_pos):
            return False, "超出棋盘"
        self.mines.append(Mine(owner=player, position=mine_pos))
        return True, "地雷已布置"

    def rook_fleet_transfer(self, player: int, rook_id: str, target: Coord,
                            passengers: List[str]) -> Tuple[bool, str, List[str]]:
        # 操作前保存状态
        self._save_state()
        
        rook = next((p for p in self.pieces if p.id == rook_id and p.owner == player and p.type == "rook"), None)
        if not rook or not rook.alive:
            return False, "车无效", []
        if not self.board.in_bounds(target):
            return False, "目标超出棋盘", []
        if not self.board.is_straight_line(rook.position, target):
            return False, "车必须直线移动", []
        if not self._check_line_clear(rook.position, target):
            return False, "路径上有阻挡", []
        if self._is_occupied_by_friendly(target, player):
            return False, "目标格有己方棋子，不能停靠", []

        if not passengers:
            return False, "未指定携带单位", []
        if len(passengers) > 26:
            return False, "一次最多携带26个单位", []

        passenger_pieces = []
        skipped = []
        for pid in passengers:
            piece = next((p for p in self.pieces if p.id == pid and p.owner == player), None)
            if not piece or not piece.alive:
                skipped.append(f"{pid}(已死亡)")
                continue
            if piece.id == rook.id:
                skipped.append(f"{pid}(自身)")
                continue
            if piece.type == "core":
                skipped.append(f"{pid}(核心)")
                continue
            dx = abs(piece.position[0] - rook.position[0])
            dy = abs(piece.position[1] - rook.position[1])
            dz = abs(piece.position[2] - rook.position[2])
            if max(dx, dy, dz) > 1:
                skipped.append(f"{pid}(不相邻)")
                continue
            passenger_pieces.append(piece)

        if not passenger_pieces:
            if skipped:
                return False, f"所有乘客均被过滤: {', '.join(skipped)}", []
            else:
                return False, "没有可携带的合法乘客", []

        offsets = [(p.position[0] - rook.position[0],
                    p.position[1] - rook.position[1],
                    p.position[2] - rook.position[2]) for p in passenger_pieces]

        events = []

        target_piece = self._piece_at(target)
        target_mine = self._mine_at(target)

        if target_mine:
            rook.alive = False
            self.mines.remove(target_mine)
            self.death_counter += 1
            for p in passenger_pieces:
                p.alive = False
                self.death_counter += 1
            events.append("车落地踩中地雷，车与所有乘客全灭！")
            self._check_victory()
            return True, "舰队转移失败（全灭）", events

        if target_piece and target_piece.owner != player and target_piece.type != "core":
            rook.alive = False
            self.death_counter += 1
            target_piece.alive = False
            self.death_counter += 1
            for p in passenger_pieces:
                p.alive = False
                self.death_counter += 1
            events.append("车落点有敌方非核心单位，同归于尽！")
            self._check_victory()
            return True, "舰队转移失败（同归于尽）", events

        if target_piece and target_piece.owner != player and target_piece.type == "core":
            rook.alive = False
            self.death_counter += 1
            for p in passenger_pieces:
                p.alive = False
                self.death_counter += 1
            events.append("车落点有敌方核心，所有乘客全灭，核心安全！")
            self._check_victory()
            return True, "舰队转移失败（乘客全灭）", events

        old_rook_pos = rook.position
        rook.position = target
        events.append(f"车从 {old_rook_pos} 移动到 {target}")

        for piece, offset in zip(passenger_pieces, offsets):
            land = (target[0] + offset[0],
                    target[1] + offset[1],
                    target[2] + offset[2])
            if not self.board.in_bounds(land):
                piece.alive = False
                self.death_counter += 1
                events.append(f"乘客 {piece.type} 落点超出棋盘，阵亡！")
                continue
            if self._is_occupied_by_friendly(land, player):
                piece.alive = False
                self.death_counter += 1
                events.append(f"乘客 {piece.type} 落点有己方棋子，阵亡！")
                continue
            mine = self._mine_at(land)
            if mine:
                piece.alive = False
                self.mines.remove(mine)
                self.death_counter += 1
                events.append(f"乘客 {piece.type} 踩中地雷，阵亡！")
                continue
            land_piece = self._piece_at(land)
            if land_piece and land_piece.owner != player:
                if land_piece.type == "core":
                    for p in passenger_pieces:
                        if p.alive:
                            p.alive = False
                            self.death_counter += 1
                    events.append("乘客落点有敌方核心，所有乘客全灭！")
                    self._check_victory()
                    return True, "舰队转移失败（乘客全灭）", events
                else:
                    piece.alive = False
                    land_piece.alive = False
                    self.death_counter += 2
                    events.append(f"乘客 {piece.type} 与敌方 {land_piece.type} 同归于尽！")
                    continue
            old_pos = piece.position
            piece.position = land
            events.append(f"乘客 {piece.type} 从 {old_pos} 移动到 {land}")

        self._check_victory()
        return True, "舰队转移成功", events

    # ---------- 马的空间拓荒 ----------
    def expand_space(self, player: int, piece_id: str, target: Coord) -> Tuple[bool, str]:
        # 操作前保存状态
        self._save_state()
        
        piece = next((p for p in self.pieces if p.id == piece_id and p.owner == player), None)
        if not piece or not piece.alive:
            return False, "棋子无效"
        if piece.type != "knight":
            return False, "只有马可以拓荒"

        anchor = piece.position
        if not self.board.on_mist_edge(anchor):
            return False, "马不在迷雾边缘，无法拓荒"

        x, y, z = anchor
        dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        chosen_dir = None
        for dx, dy, dz in dirs:
            nb = (x + dx, y + dy, z + dz)
            if not self.board.in_bounds(nb):
                nb_key = self.board._chunk_key(nb)
                if nb_key not in self.board.chunks:
                    ox, oy, oz = self.board._chunk_origin(nb_key)
                    if (abs(ox) < self.board.max_boundary and abs(oy) < self.board.max_boundary and abs(oz) < self.board.max_boundary):
                        chosen_dir = (dx, dy, dz)
                        break

        if chosen_dir is None:
            return False, "没有可扩展的方向"

        if self.board.expand(anchor, chosen_dir):
            return True, f"拓荒成功，揭示了 3×3×3 新空间"
        else:
            return False, "拓荒失败"

    # ---------- 墨棋 ----------
    def _get_expand_interval(self) -> int:
        if self.player_count <= 3:
            return 3
        elif self.player_count <= 6:
            return 4
        else:
            return 5

    def _ink_expand_with_direction(self):
        all_units = [p.position for p in self.pieces if p.alive]
        if not all_units:
            self.ink_chess.size += 1
            return

        cx, cy, cz = self.ink_chess.position
        dx_sum = 0
        dy_sum = 0
        dz_sum = 0
        for pos in all_units:
            dx_sum += pos[0] - cx
            dy_sum += pos[1] - cy
            dz_sum += pos[2] - cz
        avg_dx = 1 if dx_sum > 0 else -1 if dx_sum < 0 else 0
        avg_dy = 1 if dy_sum > 0 else -1 if dy_sum < 0 else 0
        avg_dz = 1 if dz_sum > 0 else -1 if dz_sum < 0 else 0

        direction = None
        if avg_dz != 0:
            direction = (0, 0, avg_dz)
        elif avg_dx != 0:
            direction = (avg_dx, 0, 0)
        elif avg_dy != 0:
            direction = (0, avg_dy, 0)

        self.ink_chess.size += 1

        if direction:
            dx, dy, dz = direction
            self.ink_chess.position = (
                cx + dx * 0.5,
                cy + dy * 0.5,
                cz + dz * 0.5
            )

        half = self.ink_chess.size // 2
        bounds = self.board.bounds
        min_x, max_x, min_y, max_y, min_z, max_z = bounds
        x, y, z = self.ink_chess.position
        x = max(min_x + half, min(max_x - half, x))
        y = max(min_y + half, min(max_y - half, y))
        z = max(min_z + half, min(max_z - half, z))
        self.ink_chess.position = (x, y, z)

    def _ink_expand(self):
        interval = self._get_expand_interval()
        if self.turn_number % interval == 0:
            self._ink_expand_with_direction()
        if self.death_counter >= 10:
            self._ink_expand_with_direction()
            self.death_counter = 0

    def _ink_gravity_move(self):
        all_units = [p.position for p in self.pieces if p.alive]
        if not all_units:
            return

        cx, cy, cz = self.ink_chess.position

        def xy_dist(pos):
            return ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
        closest = min(all_units, key=xy_dist)
        dx = 1 if closest[0] > cx else -1 if closest[0] < cx else 0
        dy = 1 if closest[1] > cy else -1 if closest[1] < cy else 0
        cx += dx
        cy += dy

        def z_dist(pos):
            return abs(pos[2] - cz)
        closest_z = min(all_units, key=z_dist)
        dz = 1 if closest_z[2] > cz else -1 if closest_z[2] < cz else 0
        cz += dz

        self.ink_chess.position = (cx, cy, cz)

        half = self.ink_chess.size // 2
        bounds = self.board.bounds
        min_x, max_x, min_y, max_y, min_z, max_z = bounds
        x, y, z = self.ink_chess.position
        x = max(min_x + half, min(max_x - half, x))
        y = max(min_y + half, min(max_y - half, y))
        z = max(min_z + half, min(max_z - half, z))
        self.ink_chess.position = (x, y, z)

    def _ink_devour(self):
        half = self.ink_chess.size // 2
        cx, cy, cz = self.ink_chess.position
        center_int = (round(cx), round(cy), round(cz))
        covered = self.board.cube_range(center_int, half)
        for p in self.pieces:
            if p.alive and p.position in covered:
                p.alive = False
                self.death_counter += 1
                if p.type == "core":
                    self._eliminate_player(p.owner)
        self.mines = [m for m in self.mines if m.position not in covered]

    def _ink_chess_turn(self):
        if self.turn_number <= self.player_count + 1:
            return
        if not self.ink_on_board:
            self.ink_on_board = True
            bounds = self.board.bounds
            min_x, max_x, min_y, max_y, min_z, max_z = bounds
            face = random.randint(0, 5)
            if face == 0:
                x = min_x - 1
                y = random.randint(min_y, max_y)
                z = random.randint(min_z, max_z)
            elif face == 1:
                x = max_x + 1
                y = random.randint(min_y, max_y)
                z = random.randint(min_z, max_z)
            elif face == 2:
                x = random.randint(min_x, max_x)
                y = min_y - 1
                z = random.randint(min_z, max_z)
            elif face == 3:
                x = random.randint(min_x, max_x)
                y = max_y + 1
                z = random.randint(min_z, max_z)
            elif face == 4:
                x = random.randint(min_x, max_x)
                y = random.randint(min_y, max_y)
                z = min_z - 1
            else:
                x = random.randint(min_x, max_x)
                y = random.randint(min_y, max_y)
                z = max_z + 1
            self.ink_chess.position = (x, y, z)
        self._ink_gravity_move()
        self._ink_devour()
        self._ink_expand()
        self._save_state()

    # ---------- 回合推进（支持 AI 自动行动，无延迟） ----------
    def advance_turn(self):
        if self.game_over:
            return

        alive_players = [p for p in self.players if self._get_player_core(p) is not None]
        if not alive_players:
            self._check_victory()
            return

        # 切换到下一个玩家
        if self.current_player not in alive_players:
            self.current_player = alive_players[0]
        else:
            idx = alive_players.index(self.current_player)
            next_idx = (idx + 1) % len(alive_players)
            if next_idx == 0:
                self.turn_number += 1
                self._ink_chess_turn()
            self.current_player = alive_players[next_idx]

        # 为新玩家恢复行动力
        self._check_production_authorization(self.current_player)
        for piece in self.pieces:
            if piece.owner == self.current_player and not piece.can_act:
                piece.can_act = True

        # ---- AI 自动行动循环 ----
        max_iterations = 500  # 安全保护
        iterations = 0
        while not self.game_over and iterations < max_iterations:
            iterations += 1
            player = self.current_player
            idx = player - 1
            if idx >= len(self.player_types) or self.player_types[idx] != 'ai':
                break  # 人类玩家，退出

            # 获取合法走法
            legal = self.get_legal_moves(player)
            print(f"🤖 AI 玩家 {player} 的合法走法数量: {len(legal)}")
            if not legal:
                print(f"⚠️ AI 玩家 {player} 没有合法走法，跳过")
                self._switch_to_next_player()
                if self.game_over:
                    break
                self._check_production_authorization(self.current_player)
                for piece in self.pieces:
                    if piece.owner == self.current_player and not piece.can_act:
                        piece.can_act = True
                continue

            # AI 选择走法
            move = self.ai_choose_move(player)
            if move:
                print(f"🤖 AI 玩家 {player} 选择: {move['action']} {move['target']}")
                success = self._execute_move(player, move)
                if success:
                    # 执行成功，切换到下一个玩家
                    self._switch_to_next_player()
                    if self.game_over:
                        break
                    self._check_production_authorization(self.current_player)
                    for piece in self.pieces:
                        if piece.owner == self.current_player and not piece.can_act:
                            piece.can_act = True
                else:
                    # 执行失败，仍然切换（防止死循环）
                    print(f"⚠️ AI 走法执行失败，跳过该玩家")
                    self._switch_to_next_player()
                    if self.game_over:
                        break
                    self._check_production_authorization(self.current_player)
                    for piece in self.pieces:
                        if piece.owner == self.current_player and not piece.can_act:
                            piece.can_act = True
            else:
                # 无走法（理论上不会发生，因为 legal 非空）
                print(f"⚠️ AI 选择走法失败，跳过")
                self._switch_to_next_player()
                if self.game_over:
                    break
                self._check_production_authorization(self.current_player)
                for piece in self.pieces:
                    if piece.owner == self.current_player and not piece.can_act:
                        piece.can_act = True

        if iterations >= max_iterations:
            print("⚠️ AI 循环超过最大迭代次数，强制退出")
        self._check_victory()

    # ----- 辅助切换玩家（用于 AI 循环） -----
    def _switch_to_next_player(self):
        """切换到下一个存活的玩家，不处理墨棋（墨棋在跨回合时由 advance_turn 处理）"""
        alive_players = [p for p in self.players if self._get_player_core(p) is not None]
        if not alive_players:
            self.game_over = True
            return
        if self.current_player not in alive_players:
            self.current_player = alive_players[0]
        else:
            idx = alive_players.index(self.current_player)
            next_idx = (idx + 1) % len(alive_players)
            if next_idx == 0:
                self.turn_number += 1
                self._ink_chess_turn()
            self.current_player = alive_players[next_idx]

    # ---------- 玩家淘汰 ----------
    def _eliminate_player(self, player: int):
        for p in self.pieces:
            if p.owner == player:
                p.alive = False
        self.mines = [m for m in self.mines if m.owner != player]
        self.ink_chess.size += 5

    # ---------- 胜利判定 ----------
    def _check_victory(self):
        alive_cores = [p for p in self.pieces if p.type == "core" and p.alive]
        if len(alive_cores) == 1:
            self.game_over = True
            self.winner = f"玩家{alive_cores[0].owner}胜利"
        elif len(alive_cores) == 0:
            self.game_over = True
            self.winner = "平局（所有核心已毁）"
        else:
            self.game_over = False
            self.winner = None

    # ---------- AI 辅助：获取合法走法（性能优化重写） ----------
    def get_legal_moves(self, player: int) -> List[dict]:
        """返回当前玩家所有合法走法的列表，供 AI 使用"""
        legal_moves = []
        pieces = [p for p in self.pieces if p.alive and p.owner == player and p.can_act]
        # 排除扎根种兵（无法行动）
        pieces = [p for p in pieces if not (p.type == "seeder" and p.rooted)]

        # 6个正交方向
        dirs = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]

        for piece in pieces:
            pos = piece.position
            neighbors = [(pos[0]+dx, pos[1]+dy, pos[2]+dz) for dx, dy, dz in dirs]
            snipes = [(pos[0]+2*dx, pos[1]+2*dy, pos[2]+2*dz) for dx, dy, dz in dirs]

            # 1. 走一格相关的动作（普通移动、布雷、舰队运载、生产）
            for target in neighbors:
                # 普通移动
                if self._is_legal_move_only_check(player, piece.id, target, 'move'):
                    legal_moves.append({'piece_id': piece.id, 'action': 'move', 'target': list(target), 'params': {}})

                # 布雷（工兵）
                if piece.type == 'engineer' and self._is_legal_move_only_check(player, piece.id, target, 'lay_mine'):
                    legal_moves.append({'piece_id': piece.id, 'action': 'lay_mine', 'target': list(target), 'params': {}})

                # 舰队运载（车）—— 需要乘客列表
                if piece.type == 'rook' and self._is_legal_move_only_check(player, piece.id, target, 'fleet_transfer'):
                    # 找出车周围1格内的己方可携带棋子
                    passengers = []
                    for other in pieces:
                        if other.id == piece.id:
                            continue
                        # 用 Chebyshev 距离检查是否相邻
                        if max(abs(other.position[0] - pos[0]),
                               abs(other.position[1] - pos[1]),
                               abs(other.position[2] - pos[2])) <= 1:
                            passengers.append(other.id)
                    if passengers:
                        legal_moves.append({
                            'piece_id': piece.id,
                            'action': 'fleet_transfer',
                            'target': list(target),
                            'params': {'passengers': passengers}
                        })

                # 生产（种兵）—— 列出所有6种兵种
                if piece.type == 'seeder' and self._is_legal_move_only_check(player, piece.id, target, 'seeder_produce'):
                    for unit_type in ['scout', 'rook', 'knight', 'cannon', 'engineer', 'seeder']:
                        legal_moves.append({
                            'piece_id': piece.id,
                            'action': 'seeder_produce',
                            'target': list(target),
                            'params': {'unit_type': unit_type}
                        })

            # 2. 切割（兵）—— 只检查 6 个直线的 2 格位置
            if piece.type == 'scout':
                for target in snipes:
                    if self._is_legal_move_only_check(player, piece.id, target, 'snipe'):
                        legal_moves.append({'piece_id': piece.id, 'action': 'snipe', 'target': list(target), 'params': {}})

            # 3. 拓荒（马）—— 只检查 6 个相邻的迷雾外格子
            if piece.type == 'knight' and self.board.on_mist_edge(pos):
                for target in neighbors:
                    if self._is_legal_move_only_check(player, piece.id, target, 'expand'):
                        legal_moves.append({'piece_id': piece.id, 'action': 'expand', 'target': list(target), 'params': {}})

            # 4. 相位跃迁（车）—— 直接定位当前核心作为目标
            if piece.type == 'rook':
                core = self._get_player_core(player)
                if core:
                    target = core.position
                    if self._is_legal_move_only_check(player, piece.id, target, 'phase_jump'):
                        legal_moves.append({
                            'piece_id': piece.id,
                            'action': 'phase_jump',
                            'target': list(target),
                            'params': {'core_id': core.id} # 显式传递核心 ID
                        })

        return legal_moves

    # ---------- 只读合法性检查（供AI使用，不修改状态） ----------
    def _is_legal_move_only_check(self, player: int, piece_id: str, target: tuple, mode: str = 'move') -> bool:
        """
        检查 (player, piece_id, target, mode) 是否为一个合法的行动，
        但不实际执行，也不修改任何状态。
        返回 True/False
        """
        piece = self._get_piece_by_id(piece_id)
        if not piece or piece.owner != player or not piece.alive:
            return False
        if not piece.can_act:
            return False
        if piece.type == 'seeder' and piece.rooted:
            return False

        start = piece.position
        if not self.board.in_bounds(start) or not self.board.in_bounds(target):
            return False

        # 检查目标是否被己方棋子占据
        target_piece = self._get_piece_at(target)
        if target_piece and target_piece.owner == player:
            return False

        # 根据模式分别检查
        if mode == 'move':
            if start == target:
                return False
            dx = abs(start[0] - target[0])
            dy = abs(start[1] - target[1])
            dz = abs(start[2] - target[2])
            if dx + dy + dz != 1:
                return False
            mine = self._get_mine_at(target)
            if mine and mine.owner != player:
                return False
            return True

        elif mode == 'lay_mine':
            if piece.type != 'engineer':
                return False
            if start == target:
                return False
            dx = abs(start[0] - target[0])
            dy = abs(start[1] - target[1])
            dz = abs(start[2] - target[2])
            if dx + dy + dz != 1:
                return False
            if self._get_mine_at(target):
                return False
            if self._get_piece_at(target):
                return False
            return True

        elif mode == 'phase_jump':
            if piece.type != 'rook':
                return False
            if start == target:
                return False
            if not self.board.in_bounds(target):
                return False
            if self._get_piece_at(target) and self._get_piece_at(target).owner == player:
                return False
            return True

        elif mode == 'fleet_transfer':
            if piece.type != 'rook':
                return False
            if start == target:
                return False
            dx = abs(start[0] - target[0])
            dy = abs(start[1] - target[1])
            dz = abs(start[2] - target[2])
            if dx + dy + dz != 1:
                return False
            if self._get_piece_at(target) and self._get_piece_at(target).owner == player:
                return False
            return True

        elif mode == 'expand':
            if piece.type != 'knight':
                return False
            if not self.board.on_mist_edge(start):
                return False
            dx = target[0] - start[0]
            dy = target[1] - start[1]
            dz = target[2] - start[2]
            if abs(dx) + abs(dy) + abs(dz) != 1:
                return False
            if self.board.in_bounds(target):
                return False
            return True

        elif mode == 'snipe':
            if piece.type != 'scout':
                return False
            if not self.board.is_straight_line(start, target):
                return False
            if start == target:
                return False
            line = self.board.line_between(start, target)
            if not line or line[-1] != target:
                return False
            for pos in line[1:-1]:
                if self._get_piece_at(pos) or self._get_mine_at(pos):
                    return False
            return True

        elif mode == 'seeder_produce':
            if piece.type != 'seeder':
                return False
            if start == target:
                return False
            dx = abs(start[0] - target[0])
            dy = abs(start[1] - target[1])
            dz = abs(start[2] - target[2])
            if dx + dy + dz != 1:
                return False
            if self._get_piece_at(target):
                return False
            return True

        else:
            return False

    # ----- 辅助私有方法（供 AI 检查使用） -----
    def _get_piece_by_id(self, piece_id: str) -> Optional[Piece]:
        for p in self.pieces:
            if p.id == piece_id:
                return p
        return None

    def _get_piece_at(self, pos: Coord) -> Optional[Piece]:
        for p in self.pieces:
            if p.alive and p.position == pos:
                return p
        return None

    def _get_mine_at(self, pos: Coord) -> Optional[Mine]:
        for m in self.mines:
            if m.position == pos:
                return m
        return None

    # ---------- AI 评分与选择 ----------
    def _evaluate_move(self, player: int, piece: Piece, target: Coord, action: str, params: dict) -> float:
        """简单的评分函数，正值表示好走法，吃子得分80，核心保护权重更高"""
        score = 0
        # 1. 吃子奖励（80分）
        target_piece = self._get_piece_at(target)
        if target_piece and target_piece.owner != player:
            score += 80

        # 2. 安全评估：统计目标位置 2 格内的敌方棋子数量
        enemy_count = 0
        nearest_enemy_dist = 999
        for p in self.pieces:
            if p.alive and p.owner != player:
                dist = self.board.distance(target, p.position)
                if dist <= 2:
                    enemy_count += 1
                    score -= (3 - dist) * 10   # 距离越近惩罚越大
                if dist < nearest_enemy_dist:
                    nearest_enemy_dist = dist

        # 核心额外保护（权重最高）
        if piece.type == 'core':
            score += 20   # 基础保护
            if enemy_count > 0:
                score -= 50   # 核心附近有敌人，严重惩罚
            # 如果目标位置比当前位置更远离最近的敌人，加分
            current_nearest = 999
            for p in self.pieces:
                if p.alive and p.owner != player:
                    d = self.board.distance(piece.position, p.position)
                    if d < current_nearest:
                        current_nearest = d
            if nearest_enemy_dist > current_nearest:
                score += 30

        # 3. 墨棋威胁（严重惩罚）
        if self.ink_on_board:
            half = self.ink_chess.size / 2
            dist_ink = self.board.distance(target, self.ink_chess.position)
            if dist_ink <= half:
                score -= 60

        # 4. 轻微惩罚停留原地
        if target == piece.position:
            score -= 5

        return score

    def ai_choose_move(self, player: int) -> Optional[dict]:
        """为 AI 玩家选择最佳走法"""
        legal = self.get_legal_moves(player)
        if not legal:
            return None
        best = None
        best_score = -float('inf')
        for move in legal:
            piece = self._get_piece_by_id(move['piece_id'])
            if not piece:
                continue
            target = tuple(move['target'])
            score = self._evaluate_move(player, piece, target, move['action'], move.get('params', {}))
            if score > best_score:
                best_score = score
                best = move
        return best

    def _execute_move(self, player: int, move: dict) -> bool:
        """执行 AI 选择的走法，返回是否成功"""
        action = move['action']
        piece_id = move['piece_id']
        target = tuple(move['target'])
        params = move.get('params', {})
        ok, msg, events = False, "", []
        if action == 'move':
            ok, msg, events = self.move_piece(player, piece_id, target, mode='move')
        elif action == 'lay_mine':
            ok, msg = self.engineer_lay_mine(player, piece_id, target)
        elif action == 'phase_jump':
            core_id = params.get('core_id')
            if core_id:
                ok, msg, events = self.rook_phase_jump(player, piece_id, core_id)
        elif action == 'fleet_transfer':
            passengers = params.get('passengers', [])
            ok, msg, events = self.rook_fleet_transfer(player, piece_id, target, passengers)
        elif action == 'expand':
            ok, msg = self.expand_space(player, piece_id, target)
        elif action == 'seeder_produce':
            unit_type = params.get('unit_type')
            if unit_type:
                ok, msg, events = self.seeder_produce(player, piece_id, target, unit_type)
        elif action == 'snipe':
            ok, msg, events = self.move_piece(player, piece_id, target, mode='snipe')
        if not ok:
            print(f"⚠️ AI 走法执行失败: {msg}")
        return ok