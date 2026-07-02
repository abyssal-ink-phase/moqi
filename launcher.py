#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import http.server
import json
import webbrowser
import os
import sys
import socket
from pathlib import Path
from urllib.parse import urlparse

# ---------- 新增：判断打包环境 ----------
if getattr(sys, 'frozen', False):
    # 打包后的 exe 运行态：资源在临时目录 _MEIPASS 里
    BASE_DIR = Path(sys._MEIPASS)
else:
    # 普通 py 运行态：就是项目根目录
    BASE_DIR = Path(__file__).resolve().parent
# ----------------------------------------

sys.path.insert(0, str(BASE_DIR))

from logic.engine import MochessEngine


class MochessHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 请求处理器，自动适配 static/ 子目录"""

    def translate_path(self, path):
        """重写父类方法，优先在 static/ 子目录下查找文件"""
        # 如果是 API 路径，直接返回原始路径（父类会处理）
        if path.startswith('/state') or path.startswith('/list_saves') or \
           path.startswith('/ai/') or path.startswith('/action') or \
           path.startswith('/init') or path.startswith('/save') or \
           path.startswith('/load') or path.startswith('/favicon.ico'):
            return super().translate_path(path)

        # 尝试在 static/ 目录下查找（使用 BASE_DIR）
        static_path = BASE_DIR / "static" / path.lstrip('/')
        if static_path.exists():
            return str(static_path)

        # 回退到根目录
        return super().translate_path(path)

    def do_GET(self):
        parsed = urlparse(self.path)

        # 处理 favicon.ico
        if parsed.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return

        # ---- API 接口 ----
        if parsed.path == '/state':
            try:
                state = engine.get_state()
                self._send_json(state)
            except Exception as e:
                self._log_error(f"/state 错误: {e}")
                self._send_error(500, f"Internal Server Error: {e}")
            return

        if parsed.path == '/list_saves':
            try:
                saves = []
                saves_dir = BASE_DIR / "saves"
                if saves_dir.exists():
                    for f in saves_dir.iterdir():
                        if f.suffix == ".json":
                            saves.append(f.stem)
                self._send_json({"success": True, "saves": saves})
            except Exception as e:
                self._log_error(f"/list_saves 错误: {e}")
                self._send_error(500, str(e))
            return

        if parsed.path == '/ai/state':
            try:
                state = engine.get_state()
                state["legal_moves"] = engine.get_legal_moves(state["current_player"])
                self._send_json(state)
            except Exception as e:
                self._log_error(f"/ai/state 错误: {e}")
                self._send_error(500, str(e))
            return

        # 其他请求（静态文件）交给父类处理
        super().do_GET()

    def do_POST(self):
        global engine

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
            data = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_error(400, f"Invalid POST data: {e}")
            return

        path = self.path

        # ---- /init ----
        if path == '/init':
            try:
                player_count = data.get('player_count', 2)
                player_types = data.get('player_types', ['human'] * player_count)
                config = data.get('config', {})
                print(f"🔧 初始化游戏: {player_count} 人, 类型: {player_types}, 配置: {config}")
                engine = MochessEngine(player_count=player_count, config=config, player_types=player_types)
                print("✅ 引擎初始化成功")
                self._send_json({"success": True, "message": "游戏初始化成功"})
            except Exception as e:
                self._log_error(f"/init 错误: {e}")
                self._send_json({"success": False, "message": f"初始化失败: {e}"})
            return

        # ---- /action ----
        if path == '/action':
            try:
                player = data.get("player")
                action = data.get("action")
                piece_id = data.get("piece_id")
                target = tuple(data.get("target")) if data.get("target") else None

                response = {"success": False, "message": "未知指令"}
                if action == "move":
                    mode = data.get("mode", "move")
                    ok, msg, events = engine.move_piece(player, piece_id, target, mode=mode)
                    response = {"success": ok, "message": msg, "events": events}
                    if ok:
                        engine.advance_turn()
                elif action == "phase_jump":
                    core_id = data.get("core_id")
                    ok, msg, events = engine.rook_phase_jump(player, piece_id, core_id)
                    response = {"success": ok, "message": msg, "events": events}
                    if ok:
                        engine.advance_turn()
                elif action == "lay_mine":
                    ok, msg = engine.engineer_lay_mine(player, piece_id, target)
                    response = {"success": ok, "message": msg}
                    if ok:
                        engine.advance_turn()
                elif action == "fleet_transfer":
                    passengers = data.get("passengers", [])
                    ok, msg, events = engine.rook_fleet_transfer(player, piece_id, target, passengers)
                    response = {"success": ok, "message": msg, "events": events}
                    if ok:
                        engine.advance_turn()
                elif action == "expand":
                    ok, msg = engine.expand_space(player, piece_id, target)
                    response = {"success": ok, "message": msg}
                    if ok:
                        engine.advance_turn()
                elif action == "seeder_produce":
                    unit_type = data.get("unit_type")
                    ok, msg, events = engine.seeder_produce(player, piece_id, target, unit_type)
                    response = {"success": ok, "message": msg, "events": events}
                    if ok:
                        engine.advance_turn()
                elif action == "undo":
                    ok, msg = engine.undo()
                    response = {"success": ok, "message": msg}
                else:
                    response = {"success": False, "message": f"未知 action: {action}"}

                self._send_json(response)
            except Exception as e:
                self._log_error(f"/action 错误: {e}")
                self._send_error(500, str(e))
            return

        # ---- /save ----
        if path == '/save':
            try:
                save_name = data.get("name", "default")
                saves_dir = BASE_DIR / "saves"
                saves_dir.mkdir(exist_ok=True)
                snapshot = engine.serialize_state()
                from datetime import datetime
                snapshot["saved_at"] = datetime.now().isoformat()
                filepath = saves_dir / f"{save_name}.json"
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, indent=2, ensure_ascii=False)
                print(f"💾 存档保存到: {filepath}")
                self._send_json({"success": True, "message": f"存档已保存为 {save_name}"})
            except Exception as e:
                self._log_error(f"/save 错误: {e}")
                self._send_json({"success": False, "message": f"保存失败: {e}"})
            return

        # ---- /load ----
        if path == '/load':
            try:
                save_name = data.get("name", "default")
                filepath = BASE_DIR / "saves" / f"{save_name}.json"
                if not filepath.exists():
                    self._send_json({"success": False, "message": "存档不存在"})
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        snapshot = json.load(f)
                    if engine.restore_state(snapshot):
                        self._send_json({"success": True, "message": f"已加载存档 {save_name}"})
                    else:
                        self._send_json({"success": False, "message": "加载存档失败（状态恢复出错）"})
            except Exception as e:
                self._log_error(f"/load 错误: {e}")
                self._send_json({"success": False, "message": f"加载异常: {e}"})
            return

        # ---- /list_saves (POST) ----
        if path == '/list_saves':
            try:
                saves = []
                saves_dir = BASE_DIR / "saves"
                if saves_dir.exists():
                    for f in saves_dir.iterdir():
                        if f.suffix == ".json":
                            saves.append(f.stem)
                self._send_json({"success": True, "saves": saves})
            except Exception as e:
                self._log_error(f"/list_saves 错误: {e}")
                self._send_json({"success": False, "message": str(e)})
            return

        # ---- /ai/act ----
        if path == '/ai/act':
            try:
                player = data.get("player")
                action = data.get("action")
                piece_id = data.get("piece_id")
                target = tuple(data.get("target")) if data.get("target") else None
                params = data.get("params", {})

                if player is None or action is None or piece_id is None:
                    self._send_json({"success": False, "message": "缺少必要参数"})
                    return

                ok, msg, events = False, "", None
                if action == "move":
                    ok, msg, events = engine.move_piece(player, piece_id, target, mode='move')
                elif action == "lay_mine":
                    ok, msg = engine.engineer_lay_mine(player, piece_id, target)
                elif action == "phase_jump":
                    core_id = params.get("core_id")
                    if core_id is None:
                        cores = [p for p in engine.pieces if p.type == "core" and p.owner == player and p.alive]
                        if cores:
                            core_id = cores[0].id
                    if core_id:
                        ok, msg, events = engine.rook_phase_jump(player, piece_id, core_id)
                    else:
                        msg = "找不到核心"
                elif action == "fleet_transfer":
                    passengers = params.get("passengers", [])
                    ok, msg, events = engine.rook_fleet_transfer(player, piece_id, target, passengers)
                elif action == "expand":
                    ok, msg = engine.expand_space(player, piece_id, target)
                elif action == "seeder_produce":
                    unit_type = params.get("unit_type")
                    if unit_type:
                        ok, msg, events = engine.seeder_produce(player, piece_id, target, unit_type)
                    else:
                        msg = "缺少 unit_type"
                elif action == "snipe":
                    ok, msg, events = engine.move_piece(player, piece_id, target, mode='snipe')
                else:
                    msg = f"未知 action: {action}"

                if ok:
                    engine.advance_turn()
                self._send_json({"success": ok, "message": msg, "events": events})
            except Exception as e:
                self._log_error(f"/ai/act 错误: {e}")
                self._send_error(500, str(e))
            return

        # ---- /ai/auto ----
        if path == '/ai/auto':
            try:
                player = engine.current_player
                legal_moves = engine.get_legal_moves(player)
                if not legal_moves:
                    self._send_json({"success": False, "message": "当前玩家没有合法走法", "move": None})
                    return

                import random
                chosen = random.choice(legal_moves)
                action = chosen['action']
                piece_id = chosen['piece_id']
                target = tuple(chosen['target'])
                params = chosen.get('params', {})

                ok, msg, events = False, "", None
                if action == "move":
                    ok, msg, events = engine.move_piece(player, piece_id, target, mode='move')
                elif action == "lay_mine":
                    ok, msg = engine.engineer_lay_mine(player, piece_id, target)
                elif action == "phase_jump":
                    core_id = params.get("core_id")
                    if core_id is None:
                        cores = [p for p in engine.pieces if p.type == "core" and p.owner == player and p.alive]
                        if cores:
                            core_id = cores[0].id
                    if core_id:
                        ok, msg, events = engine.rook_phase_jump(player, piece_id, core_id)
                    else:
                        msg = "找不到核心"
                elif action == "fleet_transfer":
                    passengers = params.get("passengers", [])
                    ok, msg, events = engine.rook_fleet_transfer(player, piece_id, target, passengers)
                elif action == "expand":
                    ok, msg = engine.expand_space(player, piece_id, target)
                elif action == "seeder_produce":
                    unit_type = params.get("unit_type")
                    if unit_type:
                        ok, msg, events = engine.seeder_produce(player, piece_id, target, unit_type)
                    else:
                        msg = "缺少 unit_type"
                elif action == "snipe":
                    ok, msg, events = engine.move_piece(player, piece_id, target, mode='snipe')
                else:
                    msg = f"未知 action: {action}"

                if ok:
                    engine.advance_turn()
                self._send_json({
                    "success": ok,
                    "message": msg,
                    "move": {"action": action, "piece_id": piece_id, "target": list(target), "params": params}
                })
            except Exception as e:
                self._log_error(f"/ai/auto 错误: {e}")
                self._send_error(500, str(e))
            return

        # 其他 POST 路径
        self._send_error(404, "Not Found")

    # ---------- 辅助方法 ----------
    def _send_json(self, obj, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(obj).encode())
        except (ConnectionAbortedError, BrokenPipeError):
            pass

    def _send_error(self, code, message):
        try:
            self.send_response(code)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(message.encode())
        except (ConnectionAbortedError, BrokenPipeError):
            pass

    def _log_error(self, msg):
        print(f"❌ {msg}")
        import traceback
        traceback.print_exc()

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


# 全局引擎
engine = MochessEngine(player_count=2)


def find_free_port(start=8080):
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                port += 1


def main():
    os.chdir(str(BASE_DIR))  # 改用 BASE_DIR

    # 检测 index.html 位置
    if (BASE_DIR / "static" / "index.html").exists():
        url_path = "/static/index.html"
    else:
        url_path = "/index.html"

    port = find_free_port(8080)
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, MochessHandler)

    print(f"✅ 墨棋服务器已启动： http://localhost:{port}{url_path}")
    print("   在浏览器中打开上述地址，或等待自动跳转...")
    print("   按 Ctrl+C 停止服务器。")

    webbrowser.open(f"http://localhost:{port}{url_path}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已安全停止。")
        httpd.server_close()


if __name__ == "__main__":
    main()