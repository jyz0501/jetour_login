# 捷途汽车 App 加密机制分析

## 加密概述

捷途汽车 App 使用 AES 加密对敏感请求参数进行加密，主要涉及以下参数：

| 参数 | 说明 |
|------|------|
| `encryptParam` | URL 加密参数（Base64编码） |
| `POST Body` | 请求体加密数据 |
| `encryptFlag` | 加密标志（固定值 `true`） |
| `riskParam` | 风险参数（防水验证码相关） |
| `volcParam` | 火山引擎设备参数 |

---

## 加密数据结构

### encryptParam（63 bytes）

```
Base64: XVbMc0E0Bog0aMncZT4Fc9eBOtNc2Gr/O2TZv0bw7mjeocEZ9-cSUUfZL-f5K1ooqTokk3gHxy6LQc7gxNX8dQ==
Hex: 5d56cc73413406883468c9dc653e0573d7813ad35cd86aff3b64d9bf46f0ee68dea1c119f5c49451f64b7f92b5a28a93a24937807c72e8b41cee0c4d5fc750
```

结构推测：
- 前 47 bytes: 加密数据
- 后 16 bytes: IV 或签名

---

### POST Body（48 bytes）

```
Base64: gXH4rVw42PRhIfeubA3AaElTOzFQx6onNgBn11yuHwRPCvIIi3YL4V4aEsfB5kUq
Hex: 8171f8ad5c38d8f46121f7ae6c0dc06849533b3150c7aa27360067d75cae1f044f0af2088b760be15e1a12c7c1e6452a
```

结构：
- 前 16 bytes: IV（初始化向量）
- 后 32 bytes: AES 加密数据（2个块）

---

## 加密函数分析

从 `libapp.so` 中提取的加密相关符号：

| 函数 | 说明 |
|------|------|
| `JTEncrypt` | 捷途加密主类 |
| `passwordEncrypt` | 密码加密 |
| `aesEncrypt` | AES 加密 |
| `_encryptBlock` | 块加密（多个地址） |
| `_encryptQueryParams` | 查询参数加密 |

---

## 加密流程推测

```
1. 构造请求参数 JSON
   {
     "taskId": "3439799346990943525",
     "sceneCode": "signInScene",
     "timestamp": 1781798947823
   }

2. 使用 AES 加密
   - 密钥: 待提取（可能与 devToken 相关）
   - IV: 随机生成或固定
   - 模式: AES-CBC

3. Base64 编码
   - encryptParam = Base64(IV + ciphertext)
   - POST Body = Base64(IV + ciphertext)

4. 添加请求头
   - encryptFlag: true
   - riskParam: {...}
   - volcParam: {...}
```

---

## RSA 公钥

从 App 中提取的 RSA 公钥（用于密码加密）：

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDrZMr+UeSEfxy0Es+r0uzMeU+mDp8
ZfpKiWByUZZ1j6D2v2tFCOnxLhBSw21oR/ksk2QpnUQX9vjCyXZ6OVGKCMsbcpx+AYi
1xl7DJ4EeQqVX/AZvSsxiGvnKB7bvdSjTyBEzQfUNKOOu/YJ9PYP/ElP1Xy5Capnov
zJGt8uD3YwIDAQAB
-----END PUBLIC KEY-----
```

---

## 设备参数 (volcParam)

```json
{
  "devToken": "BMTyQJ7hc93dxRSX5hP-55lmNAejVo5WoTTwKQLmMaj9H2QSkZuJrQ4cHIPau87y2MbS71h_JHv9PIpbh7dNikbLSPNrLkCXysc46LOsqts7iNsZIz9wxPvi26EWPshAbFQtfTLUSbKnbeoX0-nrqK0OPyiHXfKhVMMtUwXJ9fsc*",
  "appVersion": "3.2.83",
  "devicePlatform": "ios",
  "deviceBrand": "iPhone17,1",
  "osVersion": "26.1"
}
```

`devToken` 可能参与 AES 密钥生成。

---

## 逆向方法

### 方法1: Frida Hook

使用 Frida Hook AES 加密函数，提取密钥：

```javascript
Interceptor.attach(Module.findExportByName("libapp.so", "aesEncrypt"), {
    onEnter: function(args) {
        console.log("Key:", hexdump(args[1], {length: 32}));
        console.log("IV:", hexdump(args[2], {length: 16}));
    }
});
```

### 方法2: IDA Pro 分析

1. 打开 `libapp.so`
2. 搜索字符串 `encryptParam`
3. 交叉引用找到 `_encryptQueryParams`
4. 分析函数逻辑，提取 AES 密钥

### 方法3: 动态调试

使用 Frida Stalker 跟踪加密流程：

```javascript
Stalker.follow(tid, {
    transform: function(iterator) {
        // 跟踪 AES 加密指令
    }
});
```

---

## 密钥候选

尝试的密钥模式：

| 模式 | 结果 |
|------|------|
| `jetour2024jetour` | 乱码 |
| `taskId` MD5 | 乱码 |
| `devToken` SHA256 | 待验证 |

---

## 结论

完全破解加密需要：

1. 动态 Hook 获取真实密钥
2. 分析密钥生成算法（可能与 devToken 相关）
3. 理解 IV 生成方式

建议使用 Frida 在真机上运行 Hook 脚本获取完整加密参数。