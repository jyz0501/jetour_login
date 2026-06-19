# 捷途汽车 App API 分析与 Frida Hook 详细教程

## 目录

1. [环境准备](#1-环境准备)
2. [Android 设备设置](#2-android-设备设置)
3. [iOS 设备设置](#3-ios-设备设置)
4. [Frida 脚本使用](#4-frida-脚本使用)
5. [API 接口说明](#5-api-接口说明)
6. [加密机制分析](#6-加密机制分析)
7. [常见问题](#7-常见问题)

---

## 1. 环境准备

### 1.1 安装 Frida

**macOS:**

```bash
# 使用 pip3 安装
pip3 install frida-tools

# 或使用 Python 3.12
python3.12 -m pip install frida-tools --user

# 验证安装
frida --version
# 输出: 17.14.1
```

**Windows:**

```bash
pip install frida-tools
```

**Linux:**

```bash
pip3 install frida-tools
```

### 1.2 克隆项目

```bash
git clone git@github.com:jyz0501/jetour_login.git
cd jetour_login
```

---

## 2. Android 设备设置

### 2.1 下载 Frida Server

Frida Server 版本需要与 Frida 版本匹配：

```bash
# 检查 Frida 版本
frida --version
# 输出: 17.14.1

# 下载对应版本
# https://github.com/frida/frida/releases/tag/17.14.1
# 下载: frida-server-17.14.1-android-arm64.xz
```

### 2.2 安装 Frida Server

**方式1: 使用脚本（推荐）**

```bash
chmod +x frida/android_frida_setup.sh
./frida/android_frida_setup.sh
```

**方式2: 手动安装**

```bash
# 下载并解压
curl -L -o frida-server.xz https://github.com/frida/frida/releases/download/17.14.1/frida-server-17.14.1-android-arm64.xz
xz -d frida-server.xz

# 推送到设备
adb push frida-server /data/local/tmp/frida-server

# 设置权限
adb shell chmod 755 /data/local/tmp/frida-server
```

### 2.3 启动 Frida Server

```bash
# 需要 root 权限
adb shell su -c '/data/local/tmp/frida-server &'

# 或使用前台模式（调试用）
adb shell su -c '/data/local/tmp/frida-server'
```

### 2.4 验证连接

```bash
# 检查设备连接
frida-ps -U

# 应显示进程列表
# PID  Name
# ---- ----
# 1234 com.jetour.traveller
```

### 2.5 SELinux 问题解决

如果 Frida 无法工作，可能是 SELinux 阻止：

```bash
# 临时禁用 SELinux
adb shell su -c 'setenforce 0'

# 检查 SELinux 状态
adb shell getenforce
# 输出: Permissive
```

---

## 3. iOS 设备设置

### 3.1 启用开发者模式

1. 连接 iPhone 到 Mac
2. 打开 **Xcode**
3. **Window** → **Devices and Simulators**
4. 选择你的 iPhone
5. 等待 Xcode 识别设备

然后在 iPhone 上：

1. 打开 **设置**
2. **隐私与安全** → **开发者模式**
3. **开启** 开发者模式
4. **重启** iPhone
5. 重启后点击 **启用**

### 3.2 挂载 Developer Disk Image

**方式1: 使用 Xcode（推荐）**

Xcode 会自动挂载 Developer Disk Image。

**方式2: 使用 ideviceimagemounter**

```bash
# 安装工具
brew install libimobiledevice

# 检查开发者模式状态
ideviceimagemounter devmodestatus

# 挂载（需要 Xcode 提供的镜像）
ideviceimagemounter mount /path/to/DeveloperDiskImage
```

### 3.3 验证连接

```bash
# 检查设备连接
frida-ps -Uai

# 应显示应用列表
```

---

## 4. Frida 脚本使用

### 4.1 脚本列表

| 脚本 | 说明 | 推荐场景 |
|------|------|---------|
| `frida_complete_hook.js` | 全功能整合版 | **推荐使用** |
| `frida_hook_encryption.js` | 通用加密 Hook | 初次分析 |
| `frida_hook_aes.js` | AES 深度分析 | 密钥提取 |
| `frida_hook_signin.js` | 签到 API 监控 | 签到分析 |
| `frida_hook_ios.js` | iOS 专用 | iOS 设备 |
| `mac_local_analysis.js` | macOS 本地分析 | 无设备时 |

### 4.2 运行 Hook

**Spawn 模式（启动 App）：**

```bash
# Android
frida -U -f com.jetour.traveller -l frida/frida_complete_hook.js --no-pause

# iOS
frida -U -f com.jetour.traveller -l frida/frida/frida_complete_hook.js --no-pause
```

**Attach 模式（Hook 已运行的 App）：**

```bash
# Android
frida -U -n "捷途汽车" -l frida/frida_complete_hook.js

# iOS
frida -U -n "捷途汽车" -l frida/frida_complete_hook.js
```

### 4.3 参数说明

| 参数 | 说明 |
|------|------|
| `-U` | USB 连接设备 |
| `-f` | Spawn 模式（启动 App） |
| `-n` | Attach 模式（进程名） |
| `-l` | 加载脚本 |
| `--no-pause` | 不暂停 App 启动 |

### 4.4 预期输出

Hook 成功后会输出：

```
=== AES Encryption Detected ===
  Operation: ENCRYPT
  Algorithm: AES-256
  Key Length: 32
  Key: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f ...
  IV: 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f
  Input Length: 48
  Input: {"taskId":"xxx","sceneCode":"signInScene"}
```

---

## 5. API 接口说明

详见 [docs/API.md](docs/API.md)

### 5.1 登录流程

```
1. 发送短信验证码
   POST /api/v1/common/mobile/sms
   
2. 验证码登录
   POST /api/v1/uaa/mobile/mobile-code-login
   
3. 获取 accessToken
```

### 5.2 签到流程

```
1. 获取签到任务信息
   GET /web/task/tasks/load-one
   
2. 获取签到页面信息
   GET /web/task/sign/sign-page
   
3. 执行签到（加密）
   POST /web/task/tasks/event-start
```

### 5.3 盲盒流程

```
1. 获取盲盒列表
   GET /web/rights/blind-box/user/paging
   
2. 领取盲盒（加密）
   POST /web/rights/blind-box/receive
```

---

## 6. 加密机制分析

详见 [docs/ENCRYPTION.md](docs/ENCRYPTION.md)

### 6.1 加密参数

| 参数 | 说明 |
|------|------|
| `encryptParam` | URL 加密参数 |
| `encryptFlag` | 加密标志 |
| `riskParam` | 风险参数 |
| `volcParam` | 设备参数 |

### 6.2 加密流程

```
请求参数 → AES 加密 → Base64 编码 → encryptParam
```

### 6.3 逆向方法

1. **Frida Hook** - 动态提取密钥
2. **IDA Pro** - 静态分析 libapp.so
3. **动态调试** - 跟踪加密流程

---

## 7. 常见问题

### Q1: Frida 无法连接设备？

**Android:**
- 确保 frida-server 正在运行
- 检查 SELinux 状态
- 确保设备已 root

**iOS:**
- 确保开发者模式已启用
- 确保 Developer Disk Image 已挂载
- 重新连接 USB

### Q2: App 崩溃？

- 使用 spawn 模式 `-f` 而非 attach 模式 `-n`
- 检查 Frida 版本与 frida-server 版本是否匹配
- 尝试禁用 SELinux

### Q3: 无法提取密钥？

- 确保触发了加密操作（如签到）
- 使用 `frida_complete_hook.js` 全功能脚本
- 检查 Hook 输出是否正常

### Q4: macOS 找不到 Frida 命令？

```bash
# 添加到 PATH
export PATH="$HOME/Library/Python/3.12/bin:$PATH"

# 或使用完整路径
/Users/alun/Library/Python/3.12/bin/frida
```

### Q5: iOS 26.1 无法挂载 Developer Disk Image？

- iOS 26.1 是新版本，需要最新的 Xcode beta
- 等待 Xcode 更新或使用 iOS 模拟器

---

## 附录

### A. 项目文件结构

```
jetour_login/
├── README.md
├── HELP.md
├── docs/
│   ├── API.md
│   ├── ENCRYPTION.md
│   └── FRIDA_GUIDE.md
├── frida/
│   ├── frida_complete_hook.js
│   ├── frida_hook_encryption.js
│   ├── frida_hook_aes.js
│   ├── frida_hook_signin.js
│   ├── frida_hook_ios.js
│   ├── mac_local_analysis.js
│   ├── android_frida_setup.sh
│   └── mac_frida_analysis.sh
└── api/
    └── test_api.py
```

### B. App 信息

| 属性 | 值 |
|------|-----|
| 包名 | `com.jetour.traveller` |
| 版本 | 3.2.77 (26033101) |
| 架构 | arm64-v8a |
| 平台 | Android / iOS |

### C. 相关链接

- [Frida 官网](https://frida.re/)
- [Frida GitHub](https://github.com/frida/frida)
- [Frida 文档](https://frida.re/docs/)

---

**注意**: 本项目仅供学习研究，请勿用于非法用途。