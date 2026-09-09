#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jetour_crypto.py
================
捷途 mobile-consumer.jetour.com.cn 网关 "encryptFlag/encryptParam" 加密协议（已逆向并实测验证）。

来源: https://h5-app.jetour.com.cn/assets/index.5f9db6c0.js (uni-app / h5-app 渠道)
原始 JS 算法(名 jr): CryptoJS.AES 加密, 密钥为 Base64.parse("vVfnp9ozfDQyonMKuqgZUWjtdV+7PtBqtMCwJqz2HKQ="),
随机 16 字节 IV, AES-256-CBC + PKCS7, 输出 = Base64(IV || 密文), 再把 '+' 替换为 '-'。

协议要点:
  * 算法: AES-256-CBC + PKCS7
  * 密钥: base64 解码 "vVfnp9ozfDQyonMKuqgZUWjtdV+7PtBqtMCwJqz2HKQ=" (32 字节)
  * 密文 = 随机16字节IV || AES密文 , 整体 base64, 并只把 '+' 替换为 '-'
  * 请求需带请求头 encryptFlag: true
  * GET:  原 query(含 access_token=...)整体加密后作为 ?encryptParam=<值>
  * POST:  URL 的 query(access_token)加密放 ?encryptParam; body 为加密后的 JSON 字符串
  * 附带请求头 Origin/Referer: https://h5-app.jetour.com.cn

2026-09-09 已通过线上接口实测验证(HTTP 200 返回真实数据)。
实现为纯 Python(内置 AES), 无第三方依赖。
"""

import base64
import os

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
AES_KEY_B64 = "vVfnp9ozfDQyonMKuqgZUWjtdV+7PtBqtMCwJqz2HKQ="
AES_KEY = base64.b64decode(AES_KEY_B64)  # 32 字节

_HOST = "https://mobile-consumer.jetour.com.cn"

# ---------------------------------------------------------------------------
# 纯 Python AES-256 (单块/ECB 内核) + CBC + PKCS7
# ---------------------------------------------------------------------------
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i

_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]


def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF


def _key_expansion(key):
    nk = len(key) // 4
    nr = {4: 10, 6: 12, 8: 14}[nk]
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        temp = w[i - 1][:]
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[x] for x in temp]
            temp[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            temp = [_SBOX[x] for x in temp]
        w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
    # 每轮 4 个 word(列), 返回 nr+1 轮密钥块
    return [w[4 * i:4 * i + 4] for i in range(nr + 1)]


def _add_round_key(state, rk):
    for r in range(4):
        for c in range(4):
            state[r][c] ^= rk[c][r]


def _sub_bytes(state):
    for r in range(4):
        for c in range(4):
            state[r][c] = _SBOX[state[r][c]]


def _inv_sub_bytes(state):
    for r in range(4):
        for c in range(4):
            state[r][c] = _INV_SBOX[state[r][c]]


def _shift_rows(state):
    for r in range(1, 4):
        state[r] = state[r][r:] + state[r][:r]


def _inv_shift_rows(state):
    for r in range(1, 4):
        state[r] = state[r][-r:] + state[r][:-r]


def _mix_columns(state):
    for c in range(4):
        s0, s1, s2, s3 = (state[r][c] for r in range(4))
        state[0][c] = _xtime(s0) ^ (_xtime(s1) ^ s1) ^ s2 ^ s3
        state[1][c] = s0 ^ _xtime(s1) ^ (_xtime(s2) ^ s2) ^ s3
        state[2][c] = s0 ^ s1 ^ _xtime(s2) ^ (_xtime(s3) ^ s3)
        state[3][c] = (_xtime(s0) ^ s0) ^ s1 ^ s2 ^ _xtime(s3)


def _inv_mix_columns(state):
    # 逆列混合: 每列乘 14 11 13 09 / 09 14 11 13 / 13 09 14 11 / 11 13 09 14
    for c in range(4):
        s = [state[r][c] for r in range(4)]
        x2 = [_xtime(v) for v in s]
        x4 = [_xtime(v) for v in x2]
        x8 = [_xtime(v) for v in x4]
        v9 = [x8[i] ^ s[i] for i in range(4)]
        v11 = [x8[i] ^ x2[i] ^ s[i] for i in range(4)]
        v13 = [x8[i] ^ x4[i] ^ s[i] for i in range(4)]
        v14 = [x8[i] ^ x4[i] ^ x2[i] for i in range(4)]
        state[0][c] = v14[0] ^ v11[1] ^ v13[2] ^ v9[3]
        state[1][c] = v9[0] ^ v14[1] ^ v11[2] ^ v13[3]
        state[2][c] = v13[0] ^ v9[1] ^ v14[2] ^ v11[3]
        state[3][c] = v11[0] ^ v13[1] ^ v9[2] ^ v14[3]


def _encrypt_block(block, round_keys):
    state = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(state, round_keys[0])
    for rnd in range(1, len(round_keys) - 1):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[rnd])
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[-1])
    return bytes(state[r][c] for c in range(4) for r in range(4))


def _decrypt_block(block, round_keys):
    state = [[block[4 * c + r] for c in range(4)] for r in range(4)]
    _add_round_key(state, round_keys[-1])
    for rnd in range(len(round_keys) - 2, 0, -1):
        _inv_shift_rows(state)
        _inv_sub_bytes(state)
        _add_round_key(state, round_keys[rnd])
        _inv_mix_columns(state)
    _inv_shift_rows(state)
    _inv_sub_bytes(state)
    _add_round_key(state, round_keys[0])
    return bytes(state[r][c] for c in range(4) for r in range(4))


def _aes_cbc(key, data, iv, decrypt=False):
    rk = _key_expansion(key)
    prev = iv
    out = bytearray()
    for off in range(0, len(data), 16):
        blk = data[off:off + 16]
        if decrypt:
            raw = _decrypt_block(blk, rk)
            out += bytes(x ^ y for x, y in zip(raw, prev))
            prev = blk
        else:
            xored = bytes(x ^ y for x, y in zip(blk, prev))
            out += _encrypt_block(xored, rk)
            prev = out[-16:]
    return bytes(out)


def _pad_pkcs7(data):
    pad = 16 - (len(data) % 16)
    return data + bytes([pad]) * pad


def _unpad_pkcs7(data):
    pad = data[-1]
    if pad < 1 or pad > 16 or data[-pad:] != bytes([pad]) * pad:
        raise ValueError("PKCS7 padding 校验失败")
    return data[:-pad]


# ---------------------------------------------------------------------------
# 对外接口 (与 JS 保持一致)
# ---------------------------------------------------------------------------
def encrypt(plaintext):
    """
    加密任意字符串 -> encryptParam 值
    (随机16字节IV || AES密文) base64, 并将 '+' 替换为 '-'
    """
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    iv = os.urandom(16)
    ct = _aes_cbc(AES_KEY, _pad_pkcs7(plaintext), iv, decrypt=False)
    return base64.b64encode(iv + ct).decode().replace("+", "-")


def decrypt(encrypted):
    """
    encryptParam 值 -> 明文
    """
    b = base64.b64decode(encrypted.replace("-", "+"))
    iv, ct = b[:16], b[16:]
    raw = _aes_cbc(AES_KEY, ct, iv, decrypt=True)
    return _unpad_pkcs7(raw).decode("utf-8")


def build_encrypted_get_url(path, token=None, params=None):
    """
    构造 GET 请求 URL。
    params 为普通参数字典(如 taskId / monthInYear / sceneCode), 会自动追加 access_token。
    返回完整 https 地址(已带 ?encryptParam=...) 与所需请求头。
    """
    qs = []
    if params:
        for k, v in params.items():
            if v is not None:
                qs.append(f"{k}={v}")
    if token:
        qs.append(f"access_token={token}")
    plaintext = "&".join(qs)
    url = f"{_HOST}{path}?encryptParam={encrypt(plaintext)}"
    return url, _HEADERS


def build_encrypted_post(path, token=None, body=None, params=None):
    """
    构造 POST 请求 URL + 加密 body。
    body 为 dict -> JSON 加密串; token 加密放 URL query。
    """
    qs = [f"access_token={token}"] if token else []
    if params:
        qs += [f"{k}={v}" for k, v in params.items() if v is not None]
    url = f"{_HOST}{path}"
    if qs:
        url += f"?encryptParam={encrypt('&'.join(qs))}"
    data = encrypt(json_dumps(body)) if body is not None else None
    return url, data, _HEADERS


_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://h5-app.jetour.com.cn",
    "Referer": "https://h5-app.jetour.com.cn/",
    "encryptFlag": "true",
    "User-Agent": "NetworkingExtension/8624.2.5.10.8 Network/5812.122.1 iOS/26.5.2",
}


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    # 自检: 与 openssl 交叉验证 + 线上接口实测
    import json
    import random
    import string
    import subprocess

    for _ in range(5):
        plain = "".join(random.choice(string.ascii_letters + "中文字符&=+/?%") for _ in range(random.randint(1, 96)))
        mine = encrypt(plain)
        raw = base64.b64decode(mine.replace("-", "+"))
        iv, ct = raw[:16], raw[16:]
        o = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-K", AES_KEY.hex(), "-iv", iv.hex()],
            input=ct, capture_output=True,
        )
        assert o.returncode == 0 and o.stdout == plain.encode("utf-8"), "openssl 解密结果不一致"
        assert decrypt(mine) == plain, "roundtrip 失败"
    print("[自检] openssl 交叉解密一致, decrypt roundtrip 通过")

    import requests

    TOKEN = "6sbx0i7TRwpUFBe5iAIAaQAAAAAAAAAE"
    url, headers = build_encrypted_get_url(
        "/web/task/sign/sign-record",
        token=TOKEN,
        params={"taskId": "3439799346990943525", "monthInYear": "202609"},
    )
    r = requests.get(url, headers=headers, timeout=30)
    j = r.json()
    print("[实测] sign-record HTTP", r.status_code, json.dumps(j.get("data"), ensure_ascii=False)[:220])
