// Frida Hook Script - 捷途 App AES 加密分析 v2
// 专门用于提取 encryptParam 和 POST body 的加密密钥

console.log("========================================");
console.log("捷途 App AES 加密深度分析");
console.log("========================================\n");

var libapp = null;

// 初始化
function init() {
    try {
        libapp = Process.findModuleByName("libapp.so");
        if (libapp) {
            console.log("[+] libapp.so: " + libapp.base + " (size: " + libapp.size + ")");
        } else {
            console.log("[-] libapp.so not found, trying arm64-v8a...");
            var libs = Process.enumerateModules();
            libs.forEach(function(lib) {
                if (lib.name.indexOf("libapp") !== -1) {
                    console.log("[+] Found: " + lib.name + " at " + lib.base);
                    libapp = lib;
                }
            });
        }
    } catch (e) {
        console.log("Error: " + e);
    }
}

// 扫描字符串并获取地址
function findString(str) {
    if (!libapp) return null;
    
    var target = Memory.allocUtf8String(str);
    var results = [];
    
    Memory.scan(libapp.base, libapp.size, target, {
        onMatch: function(address, size) {
            results.push(address);
            console.log("[+] Found string '" + str + "' at: " + address);
        },
        onComplete: function() {}
    });
    
    return results;
}

// 扫描 AES 密钥候选
function scanAesKeys() {
    console.log("\n[+] Scanning for AES key candidates...");
    
    // 常见的 Jetour 相关密钥模式
    var patterns = [
        "jetour2024", "jetour2023", "jetour@", "jetour#",
        "JTP@ssw0rd", "JTEncrypt", "JetourAES"
    ];
    
    patterns.forEach(function(pattern) {
        findString(pattern);
    });
}

// Hook AES 加密 (CCCrypt)
function hookCCCrypt() {
    console.log("\n[+] Hooking CCCrypt (CommonCrypto AES)...");
    
    var cc = Module.findExportByName("libcommonCrypto.dylib", "CCCrypt");
    if (!cc) {
        // Android
        cc = Module.findExportByName("libcrypto.so", "EVP_EncryptInit_ex");
    }
    
    if (cc) {
        console.log("[+] Found CCCrypt/EVP at: " + cc);
        Interceptor.attach(cc, {
            onEnter: function(args) {
                this.args = {
                    op: args[0].toInt32(),
                    alg: args[1].toInt32(),
                    key: args[3],
                    keylen: args[4].toInt32(),
                    iv: args[5],
                    input: args[6],
                    inlen: args[7].toInt32()
                };
                
                console.log("\n=== AES Encryption Detected ===");
                console.log("  Operation: " + (this.args.op === 0 ? "ENCRYPT" : "DECRYPT"));
                console.log("  Algorithm: AES-" + (this.args.alg === 28 ? "256" : this.args.alg === 30 ? "128" : "?"));
                console.log("  Key Length: " + this.args.keylen);
                console.log("  Key: " + hexdump(this.args.key, {length: Math.min(this.args.keylen, 32)}));
                if (this.args.iv) {
                    console.log("  IV: " + hexdump(this.args.iv, {length: 16}));
                }
                console.log("  Input Length: " + this.args.inlen);
                if (this.args.input && this.args.inlen > 0) {
                    console.log("  Input: " + hexdump(this.args.input, {length: Math.min(this.args.inlen, 64)}));
                }
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) {
                    console.log("  [SUCCESS]");
                } else {
                    console.log("  [FAILED: " + retval + "]");
                }
            }
        });
    } else {
        console.log("[-] CCCrypt not found");
    }
}

// Hook libapp.so 内部加密函数
function hookLibappCrypto() {
    console.log("\n[+] Hooking libapp.so internal crypto...");
    
    if (!libapp) {
        console.log("[-] libapp.so not available");
        return;
    }
    
    // 查找 _encryptBlock 相关符号
    var symbols = [
        "_encryptBlock",
        "_decryptBlock", 
        "JTEncrypt",
        "passwordEncrypt",
        "aesEncrypt"
    ];
    
    symbols.forEach(function(sym) {
        try {
            var addr = Module.findExportByName(libapp.name, sym);
            if (addr) {
                console.log("[+] Found " + sym + " at: " + addr);
                
                Interceptor.attach(addr, {
                    onEnter: function(args) {
                        console.log("\n=== " + sym + " called ===");
                        for (var i = 0; i < 6; i++) {
                            var arg = args[i];
                            if (arg && !arg.isNull()) {
                                try {
                                    console.log("  Arg[" + i + "]: " + hexdump(arg, {length: 32}));
                                } catch(e) {
                                    console.log("  Arg[" + i + "]: [无法读取]");
                                }
                            }
                        }
                    },
                    onLeave: function(retval) {
                        if (retval && !retval.isNull()) {
                            console.log("  Return: " + hexdump(retval, {length: 32}));
                        }
                    }
                });
            }
        } catch(e) {}
    });
    
    // 扫描加密相关字符串
    console.log("\n[+] Scanning for encryption strings...");
    var strings = [
        "encryptParam",
        "encryptFlag", 
        "riskParam",
        "volcParam",
        "passwordEncrypt",
        "aesEncrypt"
    ];
    
    strings.forEach(function(s) {
        findString(s);
    });
}

// 搜索内存中的密钥候选
function searchKeyInMemory() {
    console.log("\n[+] Searching for key candidates in memory...");
    
    // Jetour 常见密钥模式
    var keyPatterns = [
        [0x6a, 0x65, 0x74, 0x6f, 0x75, 0x72], // "jetour"
        [0x4a, 0x54, 0x40, 0x70, 0x61, 0x73, 0x73], // "JT@pass"
    ];
    
    if (libapp) {
        // 在 libapp.so 中搜索
        console.log("[+] Scanning libapp.so memory...");
        
        Memory.scan(libapp.base, libapp.size, "jetour2024", {
            onMatch: function(addr, size) {
                console.log("[!] Possible key at: " + addr);
                console.log("    Content: " + hexdump(addr, {length: 32}));
            },
            onComplete: function() {
                console.log("[+] Scan complete");
            }
        });
    }
}

// 主函数
function main() {
    console.log("Initializing...\n");
    init();
    
    hookCCCrypt();
    hookLibappCrypto();
    searchKeyInMemory();
    
    console.log("\n========================================");
    console.log("Hooks installed. Perform actions in app.");
    console.log("Press Ctrl+C to stop.");
    console.log("========================================\n");
}

// 执行
main();

// 定期输出状态
setInterval(function() {
    console.log(".[ monitoring ]");
}, 30000);
