#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py
=========
Web 操作面板后端(真实执行, 非模拟)。配合 index.html 使用。

启动:  python main.py web            (默认 http://0.0.0.0:8000)

API:
  POST /api/get-token          {phone}                -> 返回该账号可用的 access_token
  POST /api/execute-operation  {phone, token, operation}  operation: sign | blind-box | all
  GET  /api/status             最新一次运行快照
"""

from __future__ import annotations

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(config_path=None):
    from flask import Flask, jsonify, request, send_from_directory

    from automation import load_config, make_client, resolve_token, run_account

    app = Flask(__name__, static_folder=None)

    def _find_account(cfg, phone=None):
        accounts = cfg.get("accounts", []) or []
        if phone:
            for acc in accounts:
                if acc.get("phone") == phone:
                    return acc
        return accounts[0] if accounts else None

    @app.route("/")
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        return send_from_directory(BASE_DIR, path)

    @app.route("/api/get-token", methods=["POST"])
    def api_get_token():
        try:
            data = request.get_json(silent=True) or {}
            cfg = load_config(config_path)
            acc = _find_account(cfg, data.get("phone"))
            if not acc:
                return jsonify({"success": False, "message": "未配置账号"}), 404
            token = resolve_token(acc)
            if not token:
                return jsonify({"success": False,
                                "message": "该账号未配置 access_token(见 config.yaml)"}), 400
            return jsonify({"success": True, "token": token,
                            "message": f"账号 {acc.get('name')} Token 已就绪"})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"success": False, "message": str(exc)}), 500

    @app.route("/api/execute-operation", methods=["POST"])
    def api_execute_operation():
        try:
            data = request.get_json(silent=True) or {}
            phone = data.get("phone")
            token = (data.get("token") or "").strip()
            operation = data.get("operation")
            cfg = load_config(config_path)
            acc = _find_account(cfg, phone)
            if not acc:
                return jsonify({"success": False, "message": "未配置账号"}), 404
            if not token or token != resolve_token(acc):
                return jsonify({"success": False, "message": "Token 无效或不匹配"}), 401
            if operation not in ("sign", "blind-box", "all"):
                return jsonify({"success": False, "message": "无效的操作类型"}), 400

            do_sign = operation in ("sign", "all")
            do_blind = operation in ("blind-box", "all")
            # 与 App/H5 行为一致: 今日已签则不再调用 event-start(避免重复计奖)
            result = run_account(acc, cfg, do_sign=do_sign,
                                 do_blind=do_blind, force=False)

            text_parts = []
            if do_sign:
                s = result.get("sign", {})
                text_parts.append("签到: " +
                                  (s.get("error") or {"already_signed": "今日已签到，无需重复",
                                                      "signed_ok": "签到成功",
                                                      "submitted": "已提交，等待确认"}.get(s.get("state"), s.get("state") or "?")))
            if do_blind:
                b = result.get("blindBox", {})
                if b.get("error"):
                    text_parts.append(f"盲盒: {b['error']}")
                else:
                    ok = [x for x in b.get("claimed", []) if x.get("ok")]
                    text_parts.append(f"盲盒: 领取 {len(ok)} 个")
            message = "; ".join(text_parts) or "完成"
            return jsonify({"success": bool(result.get("ok", False)),
                            "message": message, "detail": result})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"success": False, "message": str(exc)}), 500

    @app.route("/api/status")
    def api_status():
        dash = os.path.join(BASE_DIR, "sign-data.json")
        try:
            with open(dash, "r", encoding="utf-8") as fh:
                return jsonify(json.load(fh))
        except (OSError, ValueError):
            return jsonify({"timestamp": None, "accounts": []})

    return app


def run_server(app, host="0.0.0.0", port=8000, debug=False):
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(create_app())
