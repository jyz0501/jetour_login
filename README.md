# 捷途汽车 App API 分析与 Frida Hook

本项目用于分析捷途汽车 App 的 API 接口和加密机制。

## 快速开始

```bash
git clone git@github.com:jyz0501/jetour_login.git
cd jetour_login

# 安装 Frida
pip3 install frida-tools

# Android: 运行安装脚本
./frida/android_frida_setup.sh

# 运行 Hook
frida -U -f com.jetour.traveller -l frida/frida_complete_hook.js --no-pause
```

## 文档

- [HELP.md](HELP.md) - 详细使用教程
- [docs/API.md](docs/API.md) - API 接口文档
- [docs/ENCRYPTION.md](docs/ENCRYPTION.md) - 加密机制分析

## App 信息

- 包名: `com.jetour.traveller`
- 版本: 3.2.77

## 许可证

MIT License