#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
automation.py
=============
捷途签到自动化编排：
  - 读取 config.yaml 的账号/开关
  - 每日任务: 未签则 event-start 签到 -> 领盲盒 -> 拉取快照 -> 存历史 -> 推送
  - 提供 CLI(main.py)与 Web 面板(server.py)共用的纯函数
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

from jetour_client import JetourApiError, JetourClient, beijing_now

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.yaml"

_ENV_FILE_LOADED = False


def _load_env_file() -> None:
    """一次性加载项目根 .env(已 gitignore)。不覆盖已存在的环境变量。"""
    global _ENV_FILE_LOADED
    if _ENV_FILE_LOADED:
        return
    _ENV_FILE_LOADED = True
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


# --------------------------------------------------------------------------- 配置
def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("timezone", "Asia/Shanghai")
    cfg.setdefault("accounts", [])
    cfg.setdefault("notify_webhook", "")
    cfg.setdefault("options", {})
    if not cfg["accounts"]:
        # 完全无账号配置时仍可工作(单默认账号, 从环境变量取 token)
        cfg["accounts"] = [{"name": "默认账号", "token_env": "JETOUR_ACCESS_TOKEN"}]
    return cfg


def resolve_token(account: dict) -> str:
    """按优先级取 access_token(先加载项目 .env 作为兜底)。"""
    _load_env_file()
    token = (account.get("token") or "").strip()
    env_name = (account.get("token_env") or "").strip()
    if not token and env_name:
        token = os.environ.get(env_name, "") or ""
    if not token:
        token = os.environ.get("JETOUR_ACCESS_TOKEN", "") or ""
    if not token:
        token = os.environ.get("ACCESS_TOKEN", "") or ""
    return token.strip()


def make_client(account: dict, cfg: dict | None = None) -> JetourClient:
    cfg = cfg or {}
    opt = cfg.get("options", {})
    token = resolve_token(account)
    return JetourClient(
        token,
        task_id=account.get("task_id"),
        event_code=account.get("event_code"),
        scene_code=account.get("scene_code"),
        timeout=int(opt.get("request_timeout", 30)),
    )


def account_enabled(client: JetourClient, account: dict, op: str, default: bool = True) -> bool:
    actions = account.get("actions") or {}
    flag = actions.get(op)
    return default if flag is None else bool(flag)


# --------------------------------------------------------------------------- 统计
def calc_sign_stats(record_str: str) -> dict:
    """从签到记录串计算本月统计(1/2 计已签)。"""
    total = len(record_str or "")
    signed = sum(1 for c in record_str if c in ("1", "2"))
    makeup = record_str.count("2")
    missed = record_str.count("0")
    rate = round(signed * 100.0 / total, 1) if total else 0.0
    return {
        "totalDays": total,
        "signedDays": signed,
        "makeupDays": makeup,
        "missedDays": missed,
        "signRate": rate,
    }


def sign_result_text(result: dict) -> str:
    """把单个账号的运行结果拼成推送/打印文本。"""
    lines = [f"[{result['name']}] {result['date']}"]
    s = result.get("sign", {})
    if s.get("error"):
        lines.append(f"  签到失败: {s['error']}")
    else:
        lines.append(f"  签到: {s.get('state') or '已签到'}"
                     + (f" (奖励 +{s.get('point')} 捷途币)" if s.get("point") else ""))
    b = result.get("blindBox", {})
    if b.get("enabled") and not b.get("error"):
        ok = [x for x in b.get("claimed", []) if x.get("ok")]
        fail = [x for x in b.get("claimed", []) if not x.get("ok")]
        lines.append(f"  盲盒: 领取 {len(ok)} 个" + (f", {len(fail)} 个失败" if fail else ""))
    elif b.get("error"):
        lines.append(f"  盲盒: {b['error']}")

    def _task_state(x) -> str:
        st = (x or {}).get("state")
        return {"already_done": "今日已入账(跳过)", "submitted": "上报成功",
                "skipped": "跳过",
                "error": "失败: " + str((x or {}).get("error"))}.get(st, st or "?")

    d = result.get("content") or {}
    if d.get("enabled"):
        lines.append(f"  分享内容: {_task_state(d.get('share'))}")
        lines.append(f"  浏览内容: {_task_state(d.get('read'))}")
    lines.append(f"  本月已签 {result['stats']['signedDays']}/{result['stats']['totalDays']} 天"
                 f" (签到率 {result['stats']['signRate']}%)")
    lines.append(f"  捷途币余额: {result['point']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- 账号任务
def run_account(account: dict, cfg: dict | None = None,
                do_sign: bool | None = None, do_blind: bool | None = None,
                do_content: bool | None = None,
                force: bool = False) -> dict:
    """
    执行单账号任务(签到 + 盲盒 + 每日内容任务 + 快照)。
    do_sign/do_blind/do_content 传 None 则按配置; do_content 默认跟随 actions.content_task。
    """
    cfg = cfg or load_config()
    client = make_client(account, cfg)
    name = account.get("name") or "账号"
    now = beijing_now()

    want_sign = account_enabled(client, account, "sign") if do_sign is None else do_sign
    want_blind = (account_enabled(client, account, "blind_box")
                  if do_blind is None else do_blind)
    want_content = (account_enabled(client, account, "content_task", default=False)
                    if do_content is None else do_content)
    today = now.strftime("%Y-%m-%d")

    result = {
        "name": name,
        "date": today,
        "time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "sign": {"enabled": want_sign},
        "blindBox": {"enabled": want_blind},
        "content": {"enabled": want_content, "share": {"state": "skipped"},
                    "read": {"state": "skipped"}},
        "stats": {},
        "point": None,
        "ok": True,
        "error": None,
    }
    try:
        record = client.sign_record()
    except JetourApiError as exc:
        result.update(ok=False, error=f"获取签到记录失败: {exc.message}")
        return result

    state = client.parse_sign_state(record.get("signRecord"),
                                    month_days=record.get("monthDays", 31))
    today_state = state["today"]["state"]
    result["record"] = record.get("signRecord", "")
    result["stats"] = calc_sign_stats(record.get("signRecord", ""))

    # ---- 签到
    if want_sign:
        if today_state == "signed" and not force:
            result["sign"].update(state="already_signed", ok=True)
        else:
            try:
                client.do_sign()
                # 重查一次确认
                record = client.sign_record()
                new_state = client.parse_sign_state(
                    record.get("signRecord"),
                    month_days=record.get("monthDays", 31))["today"]["state"]
                result["sign"].update(
                    state="signed_ok" if new_state == "signed" else "submitted",
                    ok=True, confirmed=(new_state == "signed"))
                result["record"] = record.get("signRecord", "")
                result["stats"] = calc_sign_stats(record.get("signRecord", ""))
            except JetourApiError as exc:
                result["sign"].update(state="error", ok=False, error=exc.message)
                result["ok"] = False
    else:
        result["sign"].update(state=today_state)

    # ---- 盲盒
    if want_blind:
        try:
            limit = int(((account.get("actions") or {}).get("blind_box_max") or 1))
            claimed = client.claim_oldest_box(limit=limit)
            result["blindBox"].update(claimed=claimed, ok=True)
        except JetourApiError as exc:
            result["blindBox"].update(ok=False, error=exc.message)
            result["ok"] = False
    else:
        result["blindBox"].update(skipped=True, ok=True)

    # ---- 每日内容任务(分享/浏览; 以今日积分流水 businessName 判定已入账)
    if want_content:
        try:
            done = client.today_reward_names()
            if "分享内容" in done:
                result["content"]["share"] = {"state": "already_done"}
            else:
                client.do_share_content()
                result["content"]["share"] = {"state": "submitted"}
            if "浏览内容" in done:
                result["content"]["read"] = {"state": "already_done"}
            else:
                act = account.get("actions") or {}
                src = act.get("read_content")
                src = src if isinstance(src, dict) else None
                client.do_browse_content(src)
                result["content"]["read"] = {"state": "submitted"}
        except JetourApiError as exc:
            err = {"state": "error", "error": exc.message}
            for key in ("share", "read"):
                cur = result["content"][key]
                if not cur.get("state") or cur.get("state") == "skipped":
                    result["content"][key] = dict(err)

    # ---- 余额(尽力而为)
    try:
        pt = client.point_detail()
        result["point"] = pt.get("payableBalance")
    except JetourApiError:
        pass

    return result


def run_all(cfg: dict | None = None, only: str | None = None,
            do_sign: bool | None = None, do_blind: bool | None = None,
            do_content: bool | None = None,
            force: bool = False, save: bool = True) -> dict:
    """
    跑全部账号。返回 {ranAt, accounts:[result...], ok}；save=True 时写 state 与 sign-data.json。
    """
    cfg = cfg or load_config()
    accounts = cfg.get("accounts", [])
    if only:
        accounts = [a for a in accounts if (a.get("name") or "") == only]
        if not accounts:
            raise ValueError(f"配置中不存在账号: {only}")

    results = []
    for acc in accounts:
        token = resolve_token(acc)
        if not token:
            results.append({"name": acc.get("name") or "?", "ok": False,
                            "error": "未配置 access_token(环境变量或 config.token)"})
            continue
        results.append(run_account(acc, cfg, do_sign=do_sign,
                                   do_blind=do_blind, do_content=do_content,
                                   force=force))

    summary = {
        "ranAt": beijing_now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "accounts": results,
        "ok": all(r.get("ok", False) for r in results),
    }
    if save:
        persist_state(cfg, summary)
    return summary


# --------------------------------------------------------------------------- 快照 / 存储
def snapshot_for_dashboard(client: JetourClient) -> dict:
    """拉取兼容旧 sign-data.json 的展示数据(尽力而为)。"""
    rec = {"signRecord": {}, "signPage": {}, "point": {}, "member": {},
           "user": {}, "boxCount": {}}
    rec.update(client.overview())
    sign_rec = rec["signRecord"]
    return {
        "signRecord": sign_rec.get("signRecord", ""),
        "signStats": calc_sign_stats(sign_rec.get("signRecord", "")),
        "rewardInfo": {"cycleDays": rec["signPage"].get("cycleDays"),
                       "pointReward": rec["signPage"].get("pointReward")},
        "memberDetail": rec["member"],
        "userDetail": rec["user"],
        "pointDetail": rec["point"],
        "blindBoxCount": rec["boxCount"],
        "boxCount": rec["boxCount"],
    }


def persist_state(cfg: dict, summary: dict) -> None:
    """写历史与旧面板兼容文件。"""
    opt = cfg.get("options", {})
    state_dir = BASE_DIR / str(opt.get("state_dir", "state"))
    state_dir.mkdir(parents=True, exist_ok=True)
    history_limit = int(opt.get("history_limit", 365))

    for acc in summary["accounts"]:
        if not acc.get("ok"):
            continue
        safe = "".join(ch for ch in acc["name"] if ch.isalnum() or ch in "-_") or "account"
        day = acc["date"].replace("-", "")
        rec = {k: acc.get(k) for k in ("name", "date", "time", "sign", "blindBox",
                                       "content", "stats", "point", "record",
                                       "ok", "error")}
        # 追加到按账号命名的历史文件
        hist_file = state_dir / f"history_{safe}.jsonl"
        with open(hist_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # 保留最近 history_limit 行
        lines = hist_file.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) > history_limit:
            hist_file.write_text("\n".join(lines[-history_limit:]) + "\n",
                                 encoding="utf-8")
        # 当日明细
        (state_dir / f"run_{safe}_{day}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    # 旧面板 sign-data.json(单/主账号视角, 多账号仅展示首个)
    dash_path = BASE_DIR / str(opt.get("dashboard_file", "sign-data.json"))
    try:
        primary = next(a for a in summary["accounts"] if a.get("ok"))
        client = make_client(next(acc for acc in cfg["accounts"]
                                  if (acc.get("name") or "") == primary["name"]), cfg)
        snap = snapshot_for_dashboard(client)
    except Exception as exc:  # noqa: BLE001 - 快照失败不阻塞主流程
        snap = {}
    data = {
        "timestamp": summary["ranAt"],
        "summary": summary,
        "taskInfo": {},
        "taskRules": {},
        **snap,
    }
    dash_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding="utf-8")


# --------------------------------------------------------------------------- 推送
def notify(cfg: dict, title: str, content: str) -> None:
    webhook = (cfg.get("notify_webhook") or os.environ.get("NOTIFY_WEBHOOK", "")).strip()
    if not webhook:
        return
    import requests as _rq
    try:
        _rq.post(webhook, json={"title": title, "desp": content, "text": content},
                 timeout=15)
    except Exception as exc:  # noqa: BLE001
        print(f"[notify] 推送失败: {exc}", file=sys.stderr)


# --------------------------------------------------------------------------- CLI 供 main.py 使用
def run_cli(args) -> int:
    cfg = load_config(args.config)
    if args.command == "check":
        return cmd_check(cfg, args)
    if args.command == "tasks":
        return cmd_tasks(cfg, args)
    return cmd_run(cfg, args)


TASK_STATUS_TEXT = {0: "去完成", 3: "已完成", 4: "审核中"}


def cmd_tasks(cfg, args) -> int:
    """只读: 查看任务中心各类任务完成状态。"""
    accounts = cfg.get("accounts", [])
    if args.account:
        accounts = [a for a in accounts if (a.get("name") or "") == args.account]
    failed = 0
    for acc in accounts:
        client = make_client(acc, cfg)
        name = acc.get("name") or "账号"
        print(f"[{name}] 任务中心:")
        for typ in (1, 2):
            try:
                tasks = client.task_center_tasks(typ)
            except JetourApiError as exc:
                failed += 1
                print(f"  类型{typ} 查询失败: {exc.message}")
                continue
            if not tasks:
                continue
            for t in sorted(tasks, key=lambda x: x.get("sort") or 0):
                st = TASK_STATUS_TEXT.get(t.get("status"), "已结束")
                ev = ",".join({(r.get("eventCode") or "") for r in t.get("taskEventRules") or []})
                print(f"  [类型{typ}] {st:<4} {t.get('taskName')} | {t.get('taskDesc')} | {ev}")
    return 1 if failed else 0


def cmd_check(cfg, args) -> int:
    """只查询, 不执行任何写操作。"""
    accounts = cfg.get("accounts", [])
    if args.account:
        accounts = [a for a in accounts if (a.get("name") or "") == args.account]
    failed = 0
    for acc in accounts:
        client = make_client(acc, cfg)
        name = acc.get("name") or "账号"
        try:
            record = client.sign_record()
            state = client.parse_sign_state(record.get("signRecord"),
                                            month_days=record.get("monthDays", 31))
            stats = calc_sign_stats(record.get("signRecord", ""))
            pt = client.point_detail()
            print(f"[{name}] 本月已签 {stats['signedDays']}/{stats['totalDays']} 天,"
                  f" 今日状态={state['today']['state']}, 捷途币={pt.get('payableBalance')}")
            if state["today"]["state"] != "signed":
                print(f"  提示: 今天尚未签到 (record=…{record.get('signRecord', '')[:12]})")
        except JetourApiError as exc:
            failed += 1
            print(f"[{name}] 查询失败: {exc.message}")
    return 1 if failed else 0


def cmd_run(cfg, args) -> int:
    print(f"== {beijing_now():%Y-%m-%d %H:%M:%S} 捷途签到自动化 ==")
    summary = run_all(cfg, only=args.account,
                      do_sign=False if getattr(args, "no_sign", False) else None,
                      do_blind=False if getattr(args, "no_blind_box", False) else None,
                      do_content=False if getattr(args, "no_content", False) else None,
                      force=args.force,
                      save=not args.no_save)
    for r in summary["accounts"]:
        print(sign_result_text(r) if r.get("ok") or r.get("sign") or r.get("blindBox")
              else f"[{r['name']}] {r.get('error', '未知错误')}")
    if not summary["ok"]:
        print("!! 存在失败项", file=sys.stderr)
    if args.notify:
        title = ("捷途签到成功" if summary["ok"] else "捷途签到部分失败")
        lines = [f"{r['name']}: {r.get('error') or 'OK'}" for r in summary["accounts"]]
        notify(cfg, title, "\n".join(lines))
    return 0 if summary["ok"] else 1
