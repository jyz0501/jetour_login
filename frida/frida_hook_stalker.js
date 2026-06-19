// Frida Script - 捷途 App 加密调用链分析
// 使用 Stalker 跟踪加密函数执行流程

console.log("========================================");
console.log("捷途 App 加密调用链分析 (Stalker)");
console.log("========================================\n");

var libapp = null;
varstalker = null;

// 初始化
function init() {
    libapp = Process.findModuleByName("libapp.so");
    if (libapp) {
        console.log("[+] libapp.so: " + libapp.base + " (size: 0x" + libapp.size.toString(16) + ")");
    }
    
    stalker = Stalker;
    if (stalker) {
        console.log("[+] Stalker available");
    }
}

// 查找加密函数地址
function findEncryptFuncs() {
    if (!libapp) return [];
    
    var funcs = [];
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
                console.log("[+] " + name + " @ " + addr);
                funcs.push({name: name, addr: addr});
            }
        } catch(e) {}
    });
    
    return funcs;
}

// Hook 并使用 Stalker 跟踪
function traceWithStalker(func) {
    console.log("\n[+] Tracing: " + func.name + " @ " + func.addr);
    
    Interceptor.attach(func.addr, {
        onEnter: function(args) {
            this.startTime = Date.now();
            console.log("\n=== " + func.name + " ENTER ===");
            console.log("  Time: " + this.startTime);
            
            // 打印前几个参数
            for (var i = 0; i < 4; i++) {
                try {
                    var arg = args[i];
                    if (arg && arg.toInt32() !== 0) {
                        console.log("  Arg[" + i + "]: " + arg);
                    }
                } catch(e) {}
            }
            
            // 开始 Stalker 跟踪
            if (stalker && this.context) {
                try {
                    this.coroutine = stalker.follow(this.context.pc, {
                        events: {
                            call: true,
                            ret: false,
                            exec: false
                        },
                        onReceive: function(events) {
                            console.log("  [Stalker] Calls: " + events.length + " events");
                        }
                    });
                } catch(e) {
                    console.log("  [-] Stalker error: " + e);
                }
            }
        },
        onLeave: function(retval) {
            var endTime = Date.now();
            console.log("\n=== " + func.name + " LEAVE ===");
            console.log("  Duration: " + (endTime - this.startTime) + "ms");
            console.log("  Return: " + retval);
            
            // 停止 Stalker
            if (this.coroutine) {
                try {
                    stalker.flush(this.coroutine);
                    stalker.stop(this.coroutine);
                } catch(e) {}
            }
        }
    });
}

// 主跟踪函数
function startTracing() {
    console.log("\n[+] Finding encryption functions...");
    var funcs = findEncryptFuncs();
    
    console.log("\n[+] Attaching to " + funcs.length + " functions...");
    funcs.forEach(function(f) {
        traceWithStalker(f);
    });
    
    console.log("\n[+] Tracing active. Use the app to trigger encryption...");
}

// Hook Java 层加密
function hookJavaLayer() {
    Java.perform(function() {
        console.log("\n[+] Hooking Java crypto...");
        
        try {
            var Cipher = Java.use("javax.crypto.Cipher");
            
            Cipher.doFinal.overload('[byte').implementation = function(data) {
                console.log("\n=== javax.crypto.Cipher.doFinal ===");
                console.log("Input length: " + data.length);
                console.log("Input: " + toHex(data));
                console.log("Mode: " + this.getMode());
                console.log("Algorithm: " + this.getAlgorithm());
                
                var result = this.doFinal(data);
                console.log("Output length: " + result.length);
                console.log("Output: " + toHex(result));
                return result;
            };
            
            var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
            SecretKeySpec.$init.overload('[byte', 'java.lang.String').implementation = function(key, algo) {
                console.log("\n=== SecretKeySpec.<init> ===");
                console.log("Algorithm: " + algo);
                console.log("Key: " + toHex(key));
                return this.$init(key, algo);
            };
            
            var IvParameterSpec = Java.use("javax.crypto.spec.IvParameterSpec");
            IvParameterSpec.$init.overload('[byte').implementation = function(iv) {
                console.log("\n=== IvParameterSpec.<init> ===");
                console.log("IV: " + toHex(iv));
                return this.$init(iv);
            };
            
        } catch (e) {
            console.log("[-] Java crypto hook error: " + e);
        }
    });
}

// 辅助函数
function toHex(bytes) {
    var result = "";
    for (var i = 0; i < Math.min(bytes.length, 32); i++) {
        result += bytes[i].toString(16).padStart(2, '0');
    }
    if (bytes.length > 32) result += "...";
    return result;
}

// 搜索内存中的密钥
function searchMemoryKeys() {
    console.log("\n[+] Searching memory for keys...");
    
    if (!libapp) return;
    
    // 常见模式
    var patterns = [
        "jetour",
        "JTP@ss",
        "AES256",
        "encrypt"
    ];
    
    patterns.forEach(function(p) {
        try {
            Memory.scan(libapp.base, libapp.size, p, {
                onMatch: function(addr, size) {
                    console.log("[!] Found '" + p + "' at: " + addr);
                },
                onComplete: function() {}
            });
        } catch(e) {}
    });
}

// 主函数
function main() {
    init();
    startTracing();
    hookJavaLayer();
    searchMemoryKeys();
    
    console.log("\n========================================");
    console.log("Tracing started.");
    console.log("Trigger encryption in the app.");
    console.log("========================================\n");
}

// 执行
main();

// 定时输出
setInterval(function() {
    console.log(".[ still monitoring ]");
}, 60000);
