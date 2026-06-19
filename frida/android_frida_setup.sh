#!/bin/bash
# Android Frida Server 安装脚本

echo "========================================"
echo "Android Frida Server 安装"
echo "========================================"

FRIDA_VERSION="17.14.1"
FRIDA_SERVER_URL="https://github.com/frida/frida/releases/download/${FRIDA_VERSION}/frida-server-${FRIDA_VERSION}-android-arm64.xz"
FRIDA_SERVER_LOCAL="/tmp/frida-server-${FRIDA_VERSION}-android-arm64"

echo "[*] Frida 版本: ${FRIDA_VERSION}"
echo "[*] 下载地址: ${FRIDA_SERVER_URL}"

# 下载 frida-server
echo ""
echo "[1] 下载 frida-server..."
curl -L -o /tmp/frida-server.xz "${FRIDA_SERVER_URL}"

# 解压
echo ""
echo "[2] 解压..."
xz -d /tmp/frida-server.xz
mv /tmp/frida-server "${FRIDA_SERVER_LOCAL}"

# 检查设备连接
echo ""
echo "[3] 检查 Android 设备连接..."
adb devices

# 推送到设备
echo ""
echo "[4] 推送 frida-server 到设备..."
adb push "${FRIDA_SERVER_LOCAL}" /data/local/tmp/frida-server

# 设置权限
echo ""
echo "[5] 设置权限..."
adb shell chmod 755 /data/local/tmp/frida-server

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "启动 frida-server:"
echo "  adb shell su -c '/data/local/tmp/frida-server &'"
echo ""
echo "验证连接:"
echo "  /Users/alun/Library/Python/3.12/bin/frida-ps -U"
echo ""
echo "运行 Hook:"
echo "  cd '/Users/alun/Downloads/开发/捷途汽车 app'"
echo "  /Users/alun/Library/Python/3.12/bin/frida -U -f com.jetour.traveller -l frida_complete_hook.js --no-pause"
echo ""