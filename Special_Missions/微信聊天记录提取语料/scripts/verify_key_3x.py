#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证微信 3.x（SQLCipher，PBKDF2-HMAC-SHA1 / 64000 迭代）数据库密钥是否正确。

用法:
    python verify_key_3x.py <key_hex> <db_path> [db_path ...]

    key_hex : 64 位十六进制密钥（wxdump info 输出的 key）
    db_path : 一个或多个 .db 文件路径

退出码:
    0 = 所有库均匹配
    1 = 存在不匹配的库（或文件不存在）

说明:
    微信 3.x 的密钥校验必须用「页尾 HMAC 比对」，不能靠「AES 解密第一页看 SQLite 头」
    （后者会误判为不匹配）。本脚本实现了正确的 HMAC 校验：
        pk   = PBKDF2-HMAC-SHA1(key, salt, 64000, 32)
        salt2= salt 逐字节 XOR 0x3A (58)
        pk2  = PBKDF2-HMAC-SHA1(pk, salt2, 2, 32)
        比对 HMAC-SHA1(pk2, first[:-32] + b'\\x01\\x00\\x00\\x00') == first[-32:-12]
"""

import hashlib
import hmac
import sys


def verify_3x_key(db_path: str, key_hex: str) -> bool:
    key = bytes.fromhex(key_hex.strip())
    if len(key) != 32:
        raise ValueError(f"密钥长度应为 32 字节（64 位 hex），实际 {len(key)} 字节")

    with open(db_path, "rb") as f:
        blist = f.read(5000)

    if len(blist) < 4096:
        raise ValueError(f"{db_path}: 文件过小（{len(blist)} 字节），无法读取完整第一页")

    salt = blist[:16]
    pk = hashlib.pbkdf2_hmac("sha1", key, salt, 64000, 32)
    first = blist[16:4096]

    # 关键：mac salt = salt 逐字节 XOR 0x3A (58)
    mac_salt = bytes([(b ^ 58) for b in salt])
    pk2 = hashlib.pbkdf2_hmac("sha1", pk, mac_salt, 2, 32)

    h = hmac.new(pk2, first[:-32], hashlib.sha1)
    h.update(b"\x01\x00\x00\x00")
    return h.digest() == first[-32:-12]


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    key_hex = sys.argv[1]
    paths = sys.argv[2:]

    all_ok = True
    for p in paths:
        try:
            ok = verify_3x_key(p, key_hex)
            print(f"{'匹配' if ok else '不匹配'}\t{p}")
            all_ok = all_ok and ok
        except FileNotFoundError:
            print(f"文件不存在\t{p}")
            all_ok = False
        except Exception as e:
            print(f"错误\t{p}: {e}")
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
