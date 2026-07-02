# logic/board.py

from typing import List, Tuple, Set, Dict, Optional

Coord = Tuple[int, int, int]

CHUNK_SIZE = 9          # 每个区块 9³
SUB_SIZE = 3            # 每个子区域 3³
INITIAL_CHUNKS = 2      # 每个方向 2 个区块，总共 8 个区块，拼成 18³
MAX_BOUNDARY = 99

class Board:
    def __init__(self, initial_chunks_per_side: int = 2):
        self.chunks: Dict[Tuple[int, int, int], Set[Coord]] = {}
        self.bounds = [0, 0, 0, 0, 0, 0]
        self.max_boundary = MAX_BOUNDARY
        self.revealed_regions: Set[Tuple[Tuple[int, int, int], int, int, int]] = set()
        
        half = initial_chunks_per_side // 2
        start = -half
        end = half if initial_chunks_per_side % 2 == 1 else half - 1
        for cx in range(start, end + 1):
            for cy in range(start, end + 1):
                for cz in range(start, end + 1):
                    self._load_chunk((cx, cy, cz))
                    for sx in range(3):
                        for sy in range(3):
                            for sz in range(3):
                                self.revealed_regions.add(((cx, cy, cz), sx, sy, sz))
        self._update_bounds()

    def _chunk_key(self, coord: Coord) -> Tuple[int, int, int]:
        x, y, z = coord
        return (x // CHUNK_SIZE, y // CHUNK_SIZE, z // CHUNK_SIZE)

    def _chunk_origin(self, key: Tuple[int, int, int]) -> Coord:
        cx, cy, cz = key
        return (cx * CHUNK_SIZE, cy * CHUNK_SIZE, cz * CHUNK_SIZE)

    def _load_chunk(self, key: Tuple[int, int, int]) -> bool:
        if key in self.chunks:
            return True
        ox, oy, oz = self._chunk_origin(key)
        if (abs(ox) >= self.max_boundary or abs(oy) >= self.max_boundary or abs(oz) >= self.max_boundary):
            return False
        cells = set()
        for dx in range(CHUNK_SIZE):
            for dy in range(CHUNK_SIZE):
                for dz in range(CHUNK_SIZE):
                    x = ox + dx
                    y = oy + dy
                    z = oz + dz
                    if (abs(x) < self.max_boundary and abs(y) < self.max_boundary and abs(z) < self.max_boundary):
                        cells.add((x, y, z))
        self.chunks[key] = cells
        self._update_bounds()
        return True

    def _update_bounds(self):
        if not self.chunks:
            self.bounds = [0, 0, 0, 0, 0, 0]
            return
        all_x, all_y, all_z = [], [], []
        for cells in self.chunks.values():
            for x, y, z in cells:
                all_x.append(x); all_y.append(y); all_z.append(z)
        self.bounds = [min(all_x), max(all_x), min(all_y), max(all_y), min(all_z), max(all_z)]

    def _sub_index(self, coord: Coord) -> Tuple[int, int, int]:
        x, y, z = coord
        return ((x % CHUNK_SIZE) // SUB_SIZE,
                (y % CHUNK_SIZE) // SUB_SIZE,
                (z % CHUNK_SIZE) // SUB_SIZE)

    def in_bounds(self, coord: Coord) -> bool:
        key = self._chunk_key(coord)
        if key not in self.chunks:
            return False
        if coord not in self.chunks[key]:
            return False
        sub = self._sub_index(coord)
        return (key, sub[0], sub[1], sub[2]) in self.revealed_regions

    def on_mist_edge(self, coord: Coord) -> bool:
        if not self.in_bounds(coord):
            return False
        x, y, z = coord
        for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            nb = (x+dx, y+dy, z+dz)
            if not self.in_bounds(nb):
                nb_key = self._chunk_key(nb)
                if nb_key not in self.chunks:
                    ox, oy, oz = self._chunk_origin(nb_key)
                    if (abs(ox) < self.max_boundary and abs(oy) < self.max_boundary and abs(oz) < self.max_boundary):
                        return True
        return False

    def expand(self, anchor: Coord, direction: Coord) -> bool:
        if not self.on_mist_edge(anchor):
            return False
        dx, dy, dz = direction
        target_coord = (anchor[0] + dx * SUB_SIZE,
                        anchor[1] + dy * SUB_SIZE,
                        anchor[2] + dz * SUB_SIZE)
        if (abs(target_coord[0]) >= self.max_boundary or
            abs(target_coord[1]) >= self.max_boundary or
            abs(target_coord[2]) >= self.max_boundary):
            return False
        chunk_key = self._chunk_key(target_coord)
        if chunk_key not in self.chunks:
            if not self._load_chunk(chunk_key):
                return False
        sub_x = (target_coord[0] % CHUNK_SIZE) // SUB_SIZE
        sub_y = (target_coord[1] % CHUNK_SIZE) // SUB_SIZE
        sub_z = (target_coord[2] % CHUNK_SIZE) // SUB_SIZE
        sub_x = max(0, min(2, sub_x))
        sub_y = max(0, min(2, sub_y))
        sub_z = max(0, min(2, sub_z))
        self.revealed_regions.add((chunk_key, sub_x, sub_y, sub_z))
        self._update_bounds()
        return True

    def get_revealed_regions(self) -> List[Tuple[Tuple[int,int,int], int, int, int]]:
        return list(self.revealed_regions)

    def neighbors(self, coord: Coord, include_diagonals: bool = False) -> List[Coord]:
        if not self.in_bounds(coord):
            return []
        x, y, z = coord
        result = []
        for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            nb = (x+dx, y+dy, z+dz)
            if self.in_bounds(nb):
                result.append(nb)
        if include_diagonals:
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    for dz in (-1,0,1):
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        nb = (x+dx, y+dy, z+dz)
                        if self.in_bounds(nb) and nb not in result:
                            result.append(nb)
        return result

    def line_between(self, start: Coord, end: Coord) -> List[Coord]:
        if not self.in_bounds(start) or not self.in_bounds(end):
            return []
        x1, y1, z1 = start
        x2, y2, z2 = end
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        sz = 1 if z2 > z1 else -1
        if dx >= dy and dx >= dz:
            err_1 = 2 * dy - dx
            err_2 = 2 * dz - dx
            while True:
                p = (x1, y1, z1)
                if self.in_bounds(p):
                    points.append(p)
                if x1 == x2:
                    break
                if err_1 > 0:
                    y1 += sy
                    err_1 -= 2 * dx
                if err_2 > 0:
                    z1 += sz
                    err_2 -= 2 * dx
                err_1 += 2 * dy
                err_2 += 2 * dz
                x1 += sx
        elif dy >= dx and dy >= dz:
            err_1 = 2 * dx - dy
            err_2 = 2 * dz - dy
            while True:
                p = (x1, y1, z1)
                if self.in_bounds(p):
                    points.append(p)
                if y1 == y2:
                    break
                if err_1 > 0:
                    x1 += sx
                    err_1 -= 2 * dy
                if err_2 > 0:
                    z1 += sz
                    err_2 -= 2 * dy
                err_1 += 2 * dx
                err_2 += 2 * dz
                y1 += sy
        else:
            err_1 = 2 * dy - dz
            err_2 = 2 * dx - dz
            while True:
                p = (x1, y1, z1)
                if self.in_bounds(p):
                    points.append(p)
                if z1 == z2:
                    break
                if err_1 > 0:
                    y1 += sy
                    err_1 -= 2 * dz
                if err_2 > 0:
                    x1 += sx
                    err_2 -= 2 * dz
                err_1 += 2 * dy
                err_2 += 2 * dx
                z1 += sz
        return points

    def is_straight_line(self, start: Coord, end: Coord) -> bool:
        x1, y1, z1 = start
        x2, y2, z2 = end
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)
        non_zero = [d for d in (dx,dy,dz) if d != 0]
        if len(non_zero) == 0:
            return False
        return all(d == non_zero[0] for d in non_zero)

    def cube_range(self, center: Coord, half: int) -> List[Coord]:
        cx, cy, cz = center
        result = []
        for x in range(cx - half, cx + half + 1):
            for y in range(cy - half, cy + half + 1):
                for z in range(cz - half, cz + half + 1):
                    p = (x, y, z)
                    if self.in_bounds(p):
                        result.append(p)
        return result

    def distance(self, a: Coord, b: Coord) -> float:
        return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5

    def get_all_cells(self) -> Set[Coord]:
        all_cells = set()
        for cells in self.chunks.values():
            all_cells.update(cells)
        return all_cells

    def get_loaded_chunk_keys(self) -> List[Tuple[int, int, int]]:
        return list(self.chunks.keys())