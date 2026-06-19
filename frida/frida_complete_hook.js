// Frida Complete Hook Script - 捷途 App 全功能加密分析
// 支持 iOS/Android，监控所有加密相关调用

console.log("╔════════════════════════════════════════════════════════════╗");
console.log("║     捷途 App 加密分析 - Complete Frida Hook v3.0            ║");
console.log("╚════════════════════════════════════════════════════════════╝\n");

var CONFIG = {
    verbose: true,
    logCalls: true,
    logMemory: true,
    logCrypto: true
};

var libapp = null;
var results = {
    aesKeys: [],
    rsaKeys: [],
    encryptParams: [],
    devTokens: []
};

// 初始化
function init() {
    console.log("[*] Initializing...");
    
    // 查找 libapp.so
    var modules = Process.enumerateModules();
    modules.forEach(function(mod) {
        if (mod.name.indexOf("app.so") !== -1 || mod.name === "libapp.so") {
            libapp = mod;
            console.log("[+] Found: " + mod.name + " @ " + mod.base);
        }
    });
    
    if (!libapp) {
        console.log("[!] Warning: libapp.so not found directly, searching...");
        modules.forEach(function(mod) {
            if (mod.name.length < 20 && mod.size > 0x1000000) {
                console.log("  Candidate: " + mod.name + " (" + mod.size + ")");
            }
        });
    }
    
    console.log("[+] Frida version: " + Frida.version);
    console.log("[+] Platform: " + Process.platform);
    console.log("[+] PID: " + Process.id + "\n");
}

// ==================== iOS Hooks ====================
function hookIOS() {
    if (Process.platform !== "darwin") return;
    
    console.log("[*] Setting up iOS hooks...\n");
    
    hookCFNetworkiOS();
    hookCommonCrypto();
    hookSecurityFramework();
}

// ==================== Android Hooks ====================
function hookAndroid() {
    if (Process.platform !== "android") return;
    
    console.log("[*] Setting up Android hooks...\n");
    
    hookAndroidCrypto();
    hookAndroidNetwork();
    hookBouncyCastle();
}

// ==================== CommonCrypto (iOS/macOS) ====================
function hookCommonCrypto() {
    console.log("[*] Hooking CommonCrypto...");
    
    var funcs = [
        {name: "CCCrypt", args: 7},
        {name: "CCCryptorCreate", args: 6},
        {name: "CCCryptorUpdate", args: 4},
        {name: "CCCryptorFinal", args: 3},
        {name: "CCCryptorGetOutputLength", args: 3}
    ];
    
    funcs.forEach(function(f) {
        var addr = Module.findExportByName("libcommonCrypto.dylib", f.name);
        if (addr) {
            console.log("  [+] " + f.name + " @ " + addr);
            
            Interceptor.attach(addr, {
                onEnter: function(args) {
                    if (!CONFIG.logCrypto) return;
                    
                    console.log("\n═══ " + f.name + " ═══");
                    
                    // CCCrypt(op, alg, opt, key, keylen, iv, dataIn, dataInLen, dataOut, dataOutAvailable, dataOutMoved)
                    if (f.args >= 5 && args[3]) {
                        console.log("  Key: " + hexdump(args[3], {length: 32}));
                    }
                    if (f.args >= 6 && args[5]) {
                        console.log("  IV: " + hexdump(args[5], {length: 16}));
                    }
                    if (f.args >= 7 && args[6]) {
                        var len = f.args >= 8 ? args[7].toInt32() : 64;
                        console.log("  Input: " + hexdump(args[6], {length: Math.min(len, 64)}));
                    }
                },
                onLeave: function(retval) {
                    console.log("  Result: " + retval + "\n");
                }
            });
        }
    });
}

// ==================== Security Framework (iOS) ====================
function hookSecurityFramework() {
    console.log("[*] Hooking Security framework...");
    
    var funcs = [
        "SecKeyCreateEncryptedData",
        "SecKeyCreateDecryptedData",
        "SecKeyCreateSignature",
        "SecKeyVerifySignature"
    ];
    
    funcs.forEach(function(name) {
        var addr = Module.findExportByName("libSecurity.dylib", name);
        if (addr) {
            console.log("  [+] " + name + " @ " + addr);
            
            Interceptor.attach(addr, {
                onEnter: function(args) {
                    console.log("\n═══ " + name + " ═══");
                    console.log("  Arg[0]: " + args[0]);
                    console.log("  Arg[1]: " + args[1]);
                    if (args[2]) {
                        console.log("  Arg[2]: " + hexdump(args[2], {length: 64}));
                    }
                },
                onLeave: function(retval) {
                    console.log("  Return: " + (retval ? retval : "null") + "\n");
                }
            });
        }
    });
}

// ==================== CFNetwork (iOS) ====================
function hookCFNetworkiOS() {
    console.log("[*] Hooking CFNetwork...");
    
    try {
        // NSURLSession Hook
        var NSURLSession = ObjC.classes.NSURLSession;
        if (NSURLSession) {
            console.log("  [+] NSURLSession available");
            
            // Hook dataTaskWithRequest
            var dataTask = NSURLSession["- dataTaskWithRequest:completionHandler:"];
            if (dataTask) {
                Interceptor.attach(dataTask.implementation, {
                    onEnter: function(args) {
                        var request = ObjC.Object(args[2]);
                        console.log("\n═══ NSURLSession Request ═══");
                        console.log("  URL: " + request.URL().absoluteString());
                        console.log("  Method: " + request.HTTPMethod());
                        
                        var headers = request.allHTTPHeaderFields();
                        if (headers) {
                            var keys = headers.allKeys();
                            for (var i = 0; i < keys.count; i++) {
                                var key = keys.objectAtIndex_(i);
                                var value = headers.objectForKey_(key);
                                if (key.toString().toLowerCase().indexOf("encrypt") !== -1 ||
                                    key.toString().toLowerCase().indexOf("risk") !== -1 ||
                                    key.toString().toLowerCase().indexOf("volc") !== -1) {
                                    console.log("  " + key + ": " + value);
                                }
                            }
                        }
                    }
                });
            }
        }
    } catch (e) {
        console.log("  [-] CFNetwork hook error: " + e);
    }
}

// ==================== Android Crypto ====================
function hookAndroidCrypto() {
    Java.perform(function() {
        console.log("[*] Hooking Android Java crypto...");
        
        try {
            // javax.crypto.Cipher
            var Cipher = Java.use("javax.crypto.Cipher");
            
            Cipher.doFinal.overload('[byte').implementation = function(data) {
                if (CONFIG.logCrypto) {
                    console.log("\n═══ javax.crypto.Cipher.doFinal ═══");
                    console.log("  Algorithm: " + this.getAlgorithm());
                    console.log("  Mode: " + this.getMode());
                    console.log("  Input: " + toHex(data));
                }
                var result = this.doFinal(data);
                if (CONFIG.logCrypto) {
                    console.log("  Output: " + toHex(result));
                }
                return result;
            };
            
            Cipher.doFinal.overload('[byte', 'int').implementation = function(data, offset) {
                if (CONFIG.logCrypto) {
                    console.log("\n═══ javax.crypto.Cipher.doFinal (offset) ═══");
                    console.log("  Input: " + toHex(data));
                }
                var result = this.doFinal(data, offset);
                if (CONFIG.logCrypto) {
                    console.log("  Output: " + toHex(result));
                }
                return result;
            };
            
            // SecretKeySpec
            var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
            SecretKeySpec.$init.overload('[byte', 'java.lang.String').implementation = function(key, algo) {
                if (CONFIG.verbose && algo.toLowerCase().indexOf("aes") !== -1) {
                    console.log("\n═══ SecretKeySpec.<init> ═══");
                    console.log("  Algorithm: " + algo);
                    console.log("  Key: " + toHex(key));
                    results.aesKeys.push({algo: algo, key: toHex(key)});
                }
                return this.$init(key, algo);
            };
            
            // IvParameterSpec
            var IvParameterSpec = Java.use("javax.crypto.spec.IvParameterSpec");
            IvParameterSpec.$init.overload('[byte').implementation = function(iv) {
                if (CONFIG.verbose) {
                    console.log("\n═══ IvParameterSpec.<init> ═══");
                    console.log("  IV: " + toHex(iv));
                }
                return this.$init(iv);
            };
            
            console.log("  [+] javax.crypto hooks installed");
            
        } catch (e) {
            console.log("  [-] Java crypto hook error: " + e);
        }
    });
}

// ==================== Android Network ====================
function hookAndroidNetwork() {
    Java.perform(function() {
        console.log("[*] Hooking Android network...");
        
        try {
            var HttpURLConnection = Java.use("java.net.HttpURLConnection");
            
            HttpURLConnection.setRequestProperty.overload('java.lang.String', 'java.lang.String').implementation = function(key, value) {
                if (key && value) {
                    var k = key.toString();
                    var v = value.toString();
                    if (k.toLowerCase().indexOf("encrypt") !== -1 ||
                        k.toLowerCase().indexOf("risk") !== -1 ||
                        k.toLowerCase().indexOf("volc") !== -1) {
                        console.log("\n═══ HTTP Header ═══");
                        console.log("  " + k + ": " + v);
                        results.encryptParams.push({key: k, value: v});
                    }
                }
                return this.setRequestProperty(key, value);
            };
            
            console.log("  [+] HttpURLConnection hooks installed");
            
        } catch (e) {
            console.log("  [-] Network hook error: " + e);
        }
    });
}

// ==================== BouncyCastle (Android) ====================
function hookBouncyCastle() {
    Java.perform(function() {
        try {
            var BC = Java.use("org.bouncycastle.crypto.engines.AESEngine");
            console.log("  [+] BouncyCastle AESEngine found");
        } catch (e) {}
    });
}

// ==================== Memory Scanning ====================
function scanMemory() {
    if (!libapp) {
        console.log("[-] libapp.so not available for scanning");
        return;
    }
    
    console.log("\n[*] Scanning memory for patterns...\n");
    
    // 已知模式
    var patterns = [
        {name: "devToken", pattern: "BMTyQJ7hc93dxRSX"},
        {name: "encryptParam", pattern: "XVbMc0E0Bog0aMnc"},
        {name: "jetour", pattern: "jetour"},
        {name: "AESKey", pattern: "AES256"}
    ];
    
    patterns.forEach(function(p) {
        try {
            Memory.scan(libapp.base, libapp.size, p.pattern, {
                onMatch: function(addr, size) {
                    console.log("  [!] " + p.name + " found at: " + addr);
                    console.log("      " + hexdump(addr, {length: 48}));
                    if (p.name === "devToken") {
                        results.devTokens.push(addr.toString());
                    }
                },
                onComplete: function() {}
            });
        } catch (e) {
            console.log("  [-] Scan error for " + p.name + ": " + e);
        }
    });
}

// ==================== libapp.so Internal Hooks ====================
function hookLibappInternal() {
    if (!libapp) return;
    
    console.log("\n[*] Hooking libapp.so internal functions...\n");
    
    var symbols = [
        "_encryptBlock",
        "JTEncrypt",
        "passwordEncrypt", 
        "aesEncrypt",
        "_encryptQueryParams"
    ];
    
    symbols.forEach(function(name) {
        try {
            var addr = Module.findExportByName(libapp.name, name);
            if (addr) {
                console.log("  [+] " + name + " @ " + addr);
                
                Interceptor.attach(addr, {
                    onEnter: function(args) {
                        console.log("\n═══ " + name + " ENTER ═══");
                        console.log("  PC: " + this.context.pc);
                        for (var i = 0; i < 6; i++) {
                            try {
                                console.log("  R[" + i + "]: " + args[i]);
                            } catch(e) {}
                        }
                    },
                    onLeave: function(retval) {
                        console.log("═══ " + name + " LEAVE ═══");
                        console.log("  Return: " + retval + "\n");
                    }
                });
            }
        } catch (e) {
            console.log("  [-] " + name + ": " + e);
        }
    });
}

// ==================== Print Summary ====================
function printSummary() {
    console.log("\n╔════════════════════════════════════════════════════════════╗");
    console.log("║                    Analysis Summary                          ║");
    console.log("╚════════════════════════════════════════════════════════════╝");
    
    console.log("\n[*] AES Keys Found: " + results.aesKeys.length);
    results.aesKeys.forEach(function(k, i) {
        console.log("  [" + i + "] " + k.algo + ": " + k.key);
    });
    
    console.log("\n[*] Encrypt Params Found: " + results.encryptParams.length);
    results.encryptParams.forEach(function(p, i) {
        console.log("  [" + i + "] " + p.key + ": " + p.value.substring(0, 64) + "...");
    });
    
    console.log("\n[*] Dev Tokens Found: " + results.devTokens.length);
    results.devTokens.forEach(function(t, i) {
        console.log("  [" + i + "] " + t);
    });
}

// ==================== Main ====================
function main() {
    init();
    
    if (Process.platform === "darwin") {
        hookIOS();
    } else if (Process.platform === "android") {
        hookAndroid();
    }
    
    hookLibappInternal();
    scanMemory();
    
    console.log("\n[*] All hooks installed. Trigger encryption in app...\n");
    
    // 定期打印摘要
    setInterval(function() {
        if (CONFIG.verbose) {
            console.log(".[ monitoring - " + new Date().toISOString() + " ]");
        }
    }, 30000);
}

// 执行
main();

// 打印摘要 (按 Ctrl+C 退出时)
process.on('SIGINT', function() {
    printSummary();
    process.exit(0);
});

// 10分钟后打印摘要
setTimeout(function() {
    printSummary();
}, 600000);
