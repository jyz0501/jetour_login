#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
=======
捷途签到自动化 CLI。

用法示例:
  python main.py check                 # 只查询各账号今日状态/积分(不写任何数据)
  python main.py run                   # 执行签到 + 领盲盒 + 快照(按 config.yaml)
  python main.py run --no-blind-box    # 只签到不碰盲盒
  python main.py run --account 家人     # 只处理指定账号
  python main.py web                   # 启动本地操作面板(真实执行, 非模拟)

凭据: 见 config.yaml 顶部说明; 最常用方式:
  export JETOUR_ACCESS_TOKEN='...'
"""

from __future__ import annotations

import argparse
import os
import sys

from automation import load_config, run_cli


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="捷途签到自动化")
    p.add_argument("--config", default=None, help="配置文件路径(默认 config.yaml)")
    sub = p.add_subparsers(dest="command", required=False)

    c = sub.add_parser("check", help="只查询, 不执行签到/盲盒等写操作")
    c.add_argument("--account", default=None, help="仅处理指定账号")

    t = sub.add_parser("tasks", help="查看任务中心每日任务完成状态(只读)")
    t.add_argument("--account", default=None, help="仅处理指定账号")

    r = sub.add_parser("run", help="执行每日自动化(签到/内容任务/领盲盒/快照)")
    r.add_argument("--account", default=None, help="仅处理指定账号")
    r.add_argument("--no-sign", action="store_true", help="跳过签到")
    r.add_argument("--no-content", action="store_true", help="跳过每日内容任务(分享/浏览)")
    r.add_argument("--no-blind-box", action="store_true", help="跳过盲盒领取")
    r.add_argument("--no-save", action="store_true", help="不写历史/面板文件")
    r.add_argument("--force", action="store_true", help="已签到也强制调用 event-start")
    r.add_argument("--notify", action="store_true", help="按 config 推送结果(需 notify_webhook)")
    r.set_defaults(func=None)

    w = sub.add_parser("web", help="启动 Web 操作面板(0.0.0.0:8000)")
    w.add_argument("--host", default="0.0.0.0")
    w.add_argument("--port", type=int, default=8000)
    w.add_argument("--debug", action="store_true")

    t = sub.add_parser("token", help="显示解析出的 token 是否存在(不打印明文)")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "web":
        # Flask 仅在此入口按需加载
        from server import create_app, run_server

        run_server(create_app(), host=args.host, port=args.port, debug=args.debug)
        return 0

    if args.command == "token":
        cfg = load_config(args.config)
        for acc in cfg.get("accounts", []):
            from automation import resolve_token

            tok = resolve_token(acc)
            masked = (tok[:6] + "…" + tok[-4:]) if tok else "(未设置)"
            print(f"{acc.get('name') or '账号'}: {masked}")
        return 0

    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
