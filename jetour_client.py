#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jetour_client.py
================
捷途 mobile-consumer 网关加密 API 客户端。

所有请求默认走 "encryptFlag/encryptParam" 加密通道(见 jetour_crypto.py)，
即当前 App / H5(uni-app) 渠道同款协议，避免明文 access_token 参数被网关拦截。
GET/POST/PUT 统一处理；失败抛 JetourApiError 并携带网关 message。

典型端点(均已用 encryptParam 实测可用):
  sign    GET  /web/task/sign/sign-record     按月签到记录
  sign    GET  /web/task/sign/sign-page       签到页(连签/奖励)
  sign    GET  /web/task/tasks/load-one       签到任务详情
  sign    POST /web/task/tasks/event-start    执行签到 {eventCode}
  point   GET  /web/point/consumer/detail     捷途币余额
  member  GET  /web/member/consumer/detail    会员账户
  user    GET  /web/user/current/details      用户资料
  box     GET  /web/rights/blind-box/user/paging  盲盒分页
  box     GET  /web/rights/blind-box/user/count   盲盒统计
  box     PUT  /web/rights/blind-box/receive      领取盲盒
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from jetour_crypto import _HOST, build_encrypted_get_url, build_encrypted_post

# 签到任务/事件默认常量(抓包/JS 逆向所得)
DEFAULT_TASK_ID = "3439799346990943525"
DEFAULT_EVENT_CODE = "SJ50001"
DEFAULT_SCENE_CODE = "signInScene"

# ---- 每日内容任务常量(H5/小程序渠道逆向所得; token 走加密通道同样有效) ----
DAILY_SHARE_EVENT = "SJ50005"    # 分享内容任务所需事件(非 App 中台事件 SJ50015)
DAILY_BROWSE_EVENT = "SJ50006"   # 浏览内容任务所需事件
DAILY_READ_SECONDS = 18          # 浏览上报时长, 规则要求 >=15 秒
# 浏览上报默认内容(捷途新闻官置顶帖, 可用 actions.read_content 覆盖)
DEFAULT_READ_CONTENT = {
    "content_user_id": "3546892925050945581",
    "content_user_name": "捷途新闻官",
    "content_id": "6725312061279647281",
    "content_title": "9月9日，不见不散！",
}

_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://h5-app.jetour.com.cn",
    "Referer": "https://h5-app.jetour.com.cn/",
    "encryptFlag": "true",
    "User-Agent": "NetworkingExtension/8624.2.5.10.8 Network/5812.122.1 iOS/26.5.2",
}


class JetourApiError(RuntimeError):
    """网关返回的业务错误 / 网络错误。"""

    def __init__(self, message, status=None, raw=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.raw = raw


def beijing_now():
    """返回北京时间(Asia/Shanghai)的 datetime。"""
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def month_id(dt=None):
    """YYYYMM 月份串。"""
    return (dt or beijing_now()).strftime("%Y%m")


def today_day(dt=None):
    return (dt or beijing_now()).day


class JetourClient:
    """加密请求客户端。一个账号一个实例。"""

    def __init__(
        self,
        access_token: str,
        task_id: str = DEFAULT_TASK_ID,
        event_code: str = DEFAULT_EVENT_CODE,
        scene_code: str = DEFAULT_SCENE_CODE,
        timeout: int = 30,
    ):
        self.access_token = (access_token or "").strip()
        self.task_id = task_id or DEFAULT_TASK_ID
        self.event_code = event_code or DEFAULT_EVENT_CODE
        self.scene_code = scene_code or DEFAULT_SCENE_CODE
        self.timeout = timeout
        self._member = None  # member_detail 缓存

    # ------------------------------------------------------------------ 底层
    def request(self, method: str, path: str, params: dict | None = None,
                body: dict | None = None) -> dict:
        """发加密请求。params 会随 access_token 一起加密进 URL；
        非 GET 时 body 加密成请求体(JSON 字符串)。返回网关 data。"""
        method = method.upper()
        if not self.access_token:
            raise JetourApiError("未配置 access_token，请设置环境变量或 config")

        try:
            if method == "GET":
                url, _ = build_encrypted_get_url(
                    path, token=self.access_token, params=params)
                resp = requests.get(url, headers=_HEADERS, timeout=self.timeout)
            else:
                url, enc_body, _ = build_encrypted_post(
                    path, token=self.access_token, params=params, body=body)
                resp = requests.request(method, url, data=enc_body,
                                        headers=_HEADERS, timeout=self.timeout)
        except requests.RequestException as exc:
            raise JetourApiError(f"网络错误: {exc}") from exc

        try:
            payload = resp.json()
        except ValueError as exc:
            raise JetourApiError(
                f"非 JSON 响应 HTTP {resp.status_code}: {resp.text[:120]}") from exc

        status = payload.get("status")
        message = payload.get("message") or payload.get("error") or "unknown"
        if status != 200:
            raise JetourApiError(f"[{path}] {message} (status={status})",
                                 status=status, raw=payload)
        return payload.get("data")

    # ------------------------------------------------------------------ 业务
    def sign_record(self, month: str | None = None) -> dict:
        """当月签到记录: {accountId, signRecord, month, days, monthDays}"""
        month = month or month_id()
        data = self.request("GET", "/web/task/sign/sign-record",
                            params={"taskId": self.task_id, "monthInYear": month})
        return data or {}

    def sign_page(self, task_id: str | None = None) -> dict:
        """签到页面信息(连签天数/周期奖励)。"""
        data = self.request("GET", "/web/task/sign/sign-page",
                            params={"sceneCode": self.scene_code,
                                    "taskId": task_id or self.task_id})
        return data or {}

    def task_load(self) -> dict:
        """签到任务详情, 返回 {'taskInfo': ..., 'taskEventRules': ...}"""
        data = self.request("GET", "/web/task/tasks/load-one",
                            params={"sceneCode": self.scene_code, "terminal": 4})
        return data or {}

    def do_sign(self) -> dict:
        """执行签到(幂等)。"""
        return self.request("POST", "/web/task/tasks/event-start",
                            body={"eventCode": self.event_code}) or {}

    def point_detail(self) -> dict:
        """捷途币账户。"""
        return self.request("GET", "/web/point/consumer/detail") or {}

    def member_detail(self, refresh: bool = False) -> dict:
        """会员账户(accountId / memberCardAccount / cardAccountList)。"""
        if self._member is None or refresh:
            self._member = self.request("GET", "/web/member/consumer/detail") or {}
        return self._member

    def user_detail(self) -> dict:
        """用户资料(displayName / mobile / avatarUrl ...)。"""
        return self.request("GET", "/web/user/current/details") or {}

    def account_id(self) -> str:
        md = self.member_detail()
        acc = md.get("accountId")
        if not acc:
            raise JetourApiError("member_detail 中未找到 accountId")
        return str(acc)

    def blind_box_paging(self) -> dict:
        """盲盒分页(默认首页)。"""
        return self.request("GET", "/web/rights/blind-box/user/paging") or {}

    def blind_box_count(self) -> dict:
        """盲盒统计 {totalNum, packedNum, unpackedNum}。"""
        return self.request("GET", "/web/rights/blind-box/user/count") or {}

    def blind_box_receive(self, account_box_id) -> dict:
        """领取(打包)一个盲盒。account_box_id 为盲盒记录主键 id。"""
        return self.request(
            "PUT", "/web/rights/blind-box/receive",
            body={"accountBoxId": str(account_box_id),
                  "accountId": self.account_id()}) or {}

    # ------------------------------------------------------------------ 任务中心
    def task_center_tasks(self, task_type: int = 2) -> list:
        """任务中心任务清单。type: 1=商城/一次性, 2=社区内容任务(每日)。"""
        data = self.request("GET", "/web/taskCenter/task/userTaskDetails",
                            params={"type": task_type, "terminal": 4})
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------ 每日内容任务(分享/浏览)
    def report_event(self, event_code: str, properties: dict | None = None) -> dict:
        """向事件引擎上报一次事件实例。返回网关 data(成功为 None)。"""
        data = self.request("POST", "/web/event/event-instances",
                            body={"eventCode": event_code,
                                  "properties": properties or {},
                                  "terminal": 3})
        return data or {}

    def do_share_content(self) -> dict:
        """完成任务中心『分享内容』(SJ50005, 无条件)。服务端按日幂等。"""
        return self.report_event(DAILY_SHARE_EVENT, {})

    def do_browse_content(self, content: dict | None = None) -> dict:
        """完成任务中心『浏览内容』(SJ50006, 浏览时长>=15s)。

        content 可用账号级 actions.read_content 覆盖上报内容字段。
        """
        props = dict(DEFAULT_READ_CONTENT)
        props.update(content or {})
        props["content_view_time"] = int(beijing_now().timestamp() * 1000)
        props["content_duration"] = int(props.get("content_duration")
                                        or DAILY_READ_SECONDS)
        return self.report_event(DAILY_BROWSE_EVENT, props)

    def point_flow(self, page_no: int = 1, page_size: int = 20) -> list:
        """积分流水列表(倒序), 每条含 createTime/streamPoint/businessInfo。"""
        data = self.request("GET", "/web/point/flow",
                            params={"pageNo": page_no, "pageSize": page_size})
        if isinstance(data, dict):
            return data.get("data", []) or []
        return data or []

    def today_reward_names(self) -> set:
        """今日已到账的奖励任务名集合(依据积分流水 businessName)。

        以流水为准判定入账, 规避 userTaskDetails status 在部分账号上的
        展示不一致问题(例如老账号分享入账但 status 仍为 0)。
        """
        now = beijing_now()
        day_start = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
        start_ms = int(day_start.timestamp() * 1000)
        names = set()
        for page in range(1, 6):
            rows = self.point_flow(page, 50)
            if not rows:
                break
            for row in rows:
                if int(row.get("createTime") or 0) >= start_ms:
                    bn = ((row.get("businessInfo") or {})
                          .get("businessName") or "").strip()
                    if bn:
                        names.add(bn)
            if int((rows[-1].get("createTime") or 0)) < start_ms:
                break
        return names

    # ------------------------------------------------------------------ 判定
    @staticmethod
    def parse_sign_state(sign_record: str | None, month_days: int = 31) -> dict:
        """
        解析签到记录字符串到本日状态。
        记录字符: '1'=已签到 '2'=已补签 '0'=漏签/未签 'n'=未到期
        返回 {record, today: {date, index, state}} 及本周期连续天数(days 由接口提供)。
        """
        record = sign_record or ""
        now = beijing_now()
        day = now.day
        index = day - 1
        state = "unknown"
        if 0 <= index < len(record):
            ch = record[index]
            if ch in ("1", "2"):
                state = "signed"
            elif ch == "0":
                state = "unsigned"  # 今天仍未签(或已漏签)
            elif ch == "n":
                state = "future"
        return {
            "record": record,
            "today": {"date": now.strftime("%Y-%m-%d"), "index": index, "state": state},
            "month_days": month_days,
        }

    def today_signed(self, record: dict | None = None) -> bool:
        record = record if record is not None else self.sign_record()
        return self.parse_sign_state(record.get("signRecord"))["today"]["state"] == "signed"

    def find_claimable_boxes(self, paging_data: dict) -> list:
        """
        在盲盒分页中筛出可领取(未打开、无奖、未回收)的记录。
        返回按发放时间升序(先领旧的)的列表。
        """
        items = []
        box_list = (paging_data or {}).get("data", [])
        if isinstance(box_list, dict):  # 兼容 {data:[...], total:...}
            box_list = box_list.get("data", []) or []
        for box in box_list or []:
            if (box.get("awardJson") is None
                    and box.get("open") == 0
                    and not box.get("recoveryTime")):
                items.append(box)
        items.sort(key=lambda b: b.get("grantTime") or 0)
        return items

    def claim_oldest_box(self, limit: int = 1) -> list:
        """领取最旧 limit 个可领取盲盒, 返回领取结果列表。"""
        claimed = []
        page = self.blind_box_paging()
        boxes = self.find_claimable_boxes(page)
        for box in boxes[: max(0, limit)]:
            box_id = box.get("id")
            name = box.get("boxName")
            if not box_id:
                continue
            try:
                self.blind_box_receive(box_id)
                claimed.append({"accountBoxId": str(box_id), "boxName": name, "ok": True})
            except JetourApiError as exc:
                claimed.append({"accountBoxId": str(box_id), "boxName": name,
                                "ok": False, "error": exc.message})
        return claimed

    # ------------------------------------------------------------------ 汇总
    def overview(self) -> dict:
        """一次性拉取核心数据(用于快照/展示)。"""
        sign_rec = self.sign_record()
        sign_page = self.sign_page()
        point = self.point_detail()
        try:
            member = self.member_detail()
        except JetourApiError:
            member = {}
        try:
            box_count = self.blind_box_count()
        except JetourApiError:
            box_count = {}
        try:
            user = self.user_detail()
        except JetourApiError:
            user = {}
        return {
            "signRecord": sign_rec,
            "signPage": sign_page,
            "point": point,
            "member": member,
            "user": user,
            "boxCount": box_count,
        }
