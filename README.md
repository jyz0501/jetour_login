# 捷途签到自动化 (Jetour_SignTool)

对捷途会员体系（App / 微信小程序 / H5）「每日签到 / 盲盒 / 积分 / 内容任务」的自动化脚本。
请求默认走与 App/H5 相同的加密通道（`encryptFlag/encryptParam`，AES-256-CBC，详见 `jetour_crypto.py`）。
实测小程序渠道签发的明文 `access_token` 经该加密通道同样有效，因此接入新账号无需区分渠道。
网关鉴权只看 `access_token`：OpenID 为固定值（无需配置），手机号仅作为 `config.yaml` 中的账号标签（用于区分多账号，不参与任何请求）。Web 面板直接粘贴 token 即可执行，无需手机号/OpenID。

> 仅供个人自动化使用，请遵守捷途平台规则，勿用于商业用途。

## 核心能力

- **每日自动签到**：北京时间每日定时调用签到接口（`event-start`），失败自动重查确认，天然幂等（已签则跳过）
- **自动领取盲盒**：把未领取(未开)的盲盒按发放时间从旧到新领取（数量可配）
- **每日内容任务**：账号启用 `content_task` 时自动补做任务中心「分享内容 SJ50005 / 浏览内容 SJ50006」（以当日积分流水判断是否入账，幂等）
- **多账号支持**：每个账号可独立 token / 签到任务 / 开关（token 可放环境变量或项目根 `.env`，均已被 gitignore）
- **Web 操作面板**：本地网页一键“签到 / 领盲盒 / 全部执行”，真实调用接口（原 mock 已移除）
- **历史与推送**：运行历史写入 `state/`，兼容旧面板的 `sign-data.json` 汇总，可选 webhook 推送
- **GitHub Actions 定时**：无需常驻机器，每天 00:30（北京时间）自动跑

## 项目结构

```
Jetour_SignTool/
├── jetour_crypto.py        # 加密协议 AES-256-CBC (纯 Python, 无第三方依赖)
├── jetour_client.py        # 加密 API 客户端(签到/盲盒/会员/积分)
├── automation.py           # 自动化编排 + 快照/历史/推送
├── main.py                 # CLI 入口
├── server.py               # Web 面板后端(真实执行)
├── index.html              # Web 面板页面
├── config.yaml             # 账号与开关配置(不含敏感 token)
├── requirements.txt
└── .github/workflows/jetour-sign.yml   # 每日定时签到
```

## 快速开始

```bash
cd Jetour_SignTool
pip install -r requirements.txt

# 1. 准备 token (不要提交 git; 多账号时直接在项目根 .env 写 KEY=VALUE 亦可,
#    脚本运行前自动读取, .env 已被 gitignore)
export JETOUR_ACCESS_TOKEN="抓包获取的 access_token"

# 2. 先只查不改：确认账号与 token 可用
python main.py check

# 3. 执行一次完整自动化(签到 + 领盲盒 + 写快照)
python main.py run

# 只看签到不碰盲盒
python main.py run --no-blind-box

# 4. (可选) 启动本地操作面板
python main.py web        # http://localhost:8000
```

### config.yaml 说明

每个账号可独立配置：

```yaml
accounts:
  - name: 主账号
    phone: "18663531366"             # 账号标识(区分多账号), 不参与请求
    token_env: JETOUR_ACCESS_TOKEN   # 从环境变量取 token
    task_id: "3439799346990943525"   # 签到任务 id
    event_code: "SJ50001"            # 签到事件编码
    actions:
      sign: true
      blind_box: true
      blind_box_max: 1               # 每次最多领取 1 个
```

token 解析优先级：`account.token` > `account.token_env` 环境变量（含项目根 `.env`）> `JETOUR_ACCESS_TOKEN` > `ACCESS_TOKEN`。

## 定时自动化

推送到 GitHub 仓库后配置 Secrets：

| Secret | 说明 |
|---|---|
| `JETOUR_ACCESS_TOKEN` | access_token（必备） |
| `NOTIFY_WEBHOOK` | 可选推送地址（Server酱/PushPlus/任意 JSON POST） |

每天北京时间 00:30 自动签到，产物（`sign-data.json`、`state/`）会上传为 Actions Artifact 便于排查。
也可在 Actions 页面手动 `Run workflow` 立即执行。

## 抓包 token 获取提示

access_token 需从「捷途 App / 微信小程序 / h5-app.jetour.com.cn」请求中抓取（例如查积分或签到记录的请求头/参数），
会话失效时（接口返回 401/601 或 status 非 200）更新环境变量后重新运行即可。

## 常用接口（均已加密实测）

| 功能 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 签到记录 | GET | /web/task/sign/sign-record | 按月 `signRecord` 字符串 |
| 签到页 | GET | /web/task/sign/sign-page | 连签/周期奖励 |
| 执行签到 | POST | /web/task/tasks/event-start | body `{eventCode}` |
| 捷途币 | GET | /web/point/consumer/detail | `payableBalance` |
| 会员资料 | GET | /web/member/consumer/detail | accountId 等 |
| 盲盒列表/统计 | GET | /web/rights/blind-box/user/paging · count | |
| 领取盲盒 | PUT | /web/rights/blind-box/receive | body `{accountBoxId, accountId}` |
| 任务中心 | GET | /web/taskCenter/task/userTaskDetails | `type=2` 每日任务/`type=1` 商城类; `terminal=4` |
| 事件上报 | POST | /web/event/event-instances | body `{eventCode, properties, terminal:3}`（SJ50005/SJ50006） |
| 积分流水 | GET | /web/point/flow | 按 `businessName` 核对任务入账 |

## TODO：每日首帖（发帖类任务，暂未自动化）

> 2026-09-09 实测归档。任务中心判定规则会下发到各账号，以下为 token 实测的原始定义。

**任务**：每日首帖 `taskId=4435392523053584752` / `taskCode=meirishoutieutxo`，奖励 **捷途币 +8/天**，跳转页 `ContentPostPage`。
发帖类任务是全自动化目前**唯一缺口**：`python main.py run` 只能自动完成 签到/分享/浏览（见上表与 config `content_task`）。

**完成判定**（由任务中心 `taskEventRules` 下发，任一满足且**动态审核通过**即 +8）：

| 判定事件 | 条件（properties 表达式） | 达标要求 |
|---|---|---|
| `SJ20008` 动态审核通过 | `content_num>=30 && pic_num>=1` | 图文帖：≥30 字 + ≥1 张图 |
| `SJ20030` 动态审核通过(附加) | `content_num>=15 && video_duration>=10` | 视频帖：≥15 字 + ≥10 秒视频 |
| `SJ000027` | 无规则（占位/附加事件，未触发过） | — |

**阻塞原因**：
1. 触发的是「**动态审核通过**」事件——必须先有一条**真实存在且过审**的动态，再等审核流把 `SJ20008/SJ20030` 推进到任务引擎；脚本没有真实内容，伪造 `event-instances` 上报无意义（无动态可审）。
2. 9-09 曾手动发过一条「简单快乐爱唠嗑」，**字数不足 30 → 未达 `SJ20008` 条件**，status 仍 0（不是没发，是内容不达标）。
3. 「发帖」真实接口（App/H5 ContentPostPage 背后接口）**尚未逆向**，日志中暂无其上报模板。

**待办**：
- [ ] 手动发一条合规动态：≥30 字 + ≥1 图（或 ≥15 字 + ≥10 s 视频），验证次日/过审后 +8 币入账
- [ ] 抓包 ContentPostPage 的发布接口与图片上传接口，评估能否半自动发合规内容
- [ ] 观察 `SJ20030` 视频路径是否同样依赖人工过审（预计是）

**同族发帖/运营任务（勿伪造上报，无真实行为不会入账）**：发布优质帖 +30（`SJ50004 content_type=优质帖`）、发布精品帖 +300（`jingping1`）、发布精华帖 +2000（`jinghua1`）、内容官方推荐（`SJ20011` 动态被加精）、设为精选评论（`SJ50018` 评论被置顶）。以上均为内容运营人工项，不在自动化范围。

## 说明与限制

- `signRecord` 字符含义：`1` 已签到，`2` 补签，`0` 漏/未签，`n` 未到期
- 加密协议说明与密钥不在此 README 展开，见 `jetour_crypto.py` 文件头
- 旧的 `jetour_configuration.yaml`、`extract_jetour_sign_info.py` 等为历史明文/模拟版本，保留备用，新功能统一走 `main.py`
