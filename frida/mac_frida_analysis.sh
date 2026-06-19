#!/bin/bash
# macOS Frida 分析脚本 - 捷途 App
# 用于在 macOS 上分析 libapp.so 的加密逻辑

echo "========================================"
echo "捷途 App 加密分析 - macOS 版"
echo "========================================"

# 检查 Frida 是否安装
if ! command -v frida &> /dev/null; then
    echo "[-] Frida not installed. Installing..."
    pip3 install frida-tools
fi

echo "[+] Frida version: $(frida --version)"

# 方式1: 如果有 iOS 设备连接
echo ""
echo "[*] 检查连接的设备..."
frida-ps -U 2>/dev/null && echo "[+] iOS 设备已连接" || echo "[!] 无 iOS 设备连接"

# 方式2: 如果有 iOS 模拟器
echo ""
echo "[*] 检查 iOS 模拟器..."
frida-ps -Uai 2>/dev/null | head -10

# 方式3: 直接分析 libapp.so
echo ""
echo "[*] 分析本地 libapp.so..."
LIBAPP="/Users/alun/Downloads/开发/捷途汽车 app/output/lib/arm64-v8a/libapp.so"

if [ -f "$LIBAPP" ]; then
    echo "[+] libapp.so 存在"
    echo "    大小: $(ls -lh "$LIBAPP" | awk '{print $5}')"
    echo "    MD5: $(md5 -q "$LIBAPP")"
    
    # 提取加密相关字符串
    echo ""
    echo "[*] 提取加密相关字符串..."
    strings "$LIBAPP" | grep -iE "(encrypt|aes|key|crypto)" | head -20
    
    # 提取 JTEncrypt 相关
    echo ""
    echo "[*] JTEncrypt 相关..."
    strings "$LIBAPP" | grep -iE "JTEncrypt|passwordEncrypt|aesEncrypt" | head -10
else
    echo "[!] libapp.so 不存在"
fi

echo ""
echo "========================================"
echo "使用方法:"
echo "========================================"
echo ""
echo "1. iOS 设备 (需要越狱或 Frida-Gadget):"
echo "   frida -U -f com.jetour.traveller -l frida_complete_hook.js"
echo ""
echo "2. iOS 模拟器:"
echo "   frida -U -n '捷途汽车' -l frida_complete_hook.js"
echo ""
echo "3. macOS 应用 (如果有 macOS 版本):"
echo "   frida -n '捷途汽车' -l frida_complete_hook.js"
echo ""
echo "========================================"