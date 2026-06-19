// Frida Hook Script for 捷途 App Encryption Analysis
// 用于提取 AES 加密密钥和加密参数

console.log("=== 捷途 App 加密 Hook 脚本 ===");

// 1. Hook libapp.so 中的加密函数
function hook_encryption() {
    console.log("\n[1] Hooking encryption functions in libapp.so...");
    
    // 查找 libapp.so 基地址
    var libapp = Process.findModuleByName("libapp.so");
    if (libapp) {
        console.log("[+] Found libapp.so at: " + libapp.base);
    } else {
        console.log("[-] libapp.so not found");
        return;
    }
    
    // Hook passwordEncrypt 函数
    var passwordEncrypt = Module.findExportByName("libapp.so", "passwordEncrypt");
    if (passwordEncrypt) {
        console.log("[+] Found passwordEncrypt at: " + passwordEncrypt);
        Interceptor.attach(passwordEncrypt, {
            onEnter: function(args) {
                console.log("\n=== passwordEncrypt called ===");
                console.log("Arg[0] (input): " + (args[0] ? args[0].readCString() : "null"));
                console.log("Arg[1] (key?): " + (args[1] ? args[1].readCString() : "null"));
            },
            onLeave: function(retval) {
                console.log("Return: " + (retval ? retval.readCString() : "null"));
            }
        });
    } else {
        console.log("[-] passwordEncrypt not found");
    }
    
    // Hook aesEncrypt 函数
    var aesEncrypt = Module.findExportByName("libapp.so", "aesEncrypt");
    if (aesEncrypt) {
        console.log("[+] Found aesEncrypt at: " + aesEncrypt);
        Interceptor.attach(aesEncrypt, {
            onEnter: function(args) {
                console.log("\n=== aesEncrypt called ===");
                console.log("Arg[0] (plaintext): " + (args[0] ? hexdump(args[0], {length: 64}) : "null"));
                console.log("Arg[1] (key?): " + (args[1] ? hexdump(args[1], {length: 32}) : "null"));
                console.log("Arg[2] (iv?): " + (args[2] ? hexdump(args[2], {length: 16}) : "null"));
            },
            onLeave: function(retval) {
                console.log("Return (encrypted): " + (retval ? hexdump(retval, {length: 64}) : "null"));
            }
        });
    } else {
        console.log("[-] aesEncrypt not found");
    }
}

// 2. Hook 系统加密函数
function hook_system_crypto() {
    console.log("\n[2] Hooking system crypto functions...");
    
    // Hook CommonCrypt AES
    var aesFuncs = [
        "CCCrypt",
        "CCCryptorCreate",
        "CCCryptorUpdate"
    ];
    
    aesFuncs.forEach(function(funcName) {
        var func = Module.findExportByName("libcommonCrypto.dylib", funcName);
        if (func) {
            console.log("[+] Found " + funcName + " at: " + func);
            Interceptor.attach(func, {
                onEnter: function(args) {
                    console.log("\n=== " + funcName + " called ===");
                    // CCCrypt(op, alg, opt, key, keylen, iv, dataIn, dataInLen, dataOut, dataOutAvailable, dataOutMoved)
                    console.log("  op: " + args[0]);
                    console.log("  alg: " + args[1]);
                    console.log("  key: " + (args[3] ? hexdump(args[3], {length: 32}) : "null"));
                    console.log("  iv: " + (args[5] ? hexdump(args[5], {length: 16}) : "null"));
                    if (args[6] && args[7]) {
                        console.log("  input: " + hexdump(args[6], {length: Math.min(args[7].toInt32(), 64)}));
                    }
                },
                onLeave: function(retval) {
                    console.log("  return: " + retval);
                }
            });
        }
    });
}

// 3. Hook Java crypto (for Android)
function hook_java_crypto() {
    console.log("\n[3] Hooking Java crypto functions...");
    
    Java.perform(function() {
        var SecretKeySpec = Java.use('javax.crypto.spec.SecretKeySpec');
        SecretKeySpec.$init.overload('[byte', 'java.lang.String').implementation = function(key, algorithm) {
            console.log("\n=== SecretKeySpec.init ===");
            console.log("  Algorithm: " + algorithm);
            console.log("  Key: " + hexdump(key));
            return this.$init(key, algorithm);
        };
        
        var Cipher = Java.use('javax.crypto.Cipher');
        Cipher.doFinal.overload('[byte').implementation = function(input) {
            console.log("\n=== Cipher.doFinal ===");
            console.log("  Input: " + hexdump(input));
            var result = this.doFinal(input);
            console.log("  Output: " + hexdump(result));
            return result;
        };
    });
}

// 4. Hook Flutter 特定加密
function hook_flutter_encryption() {
    console.log("\n[4] Hooking Flutter dart:aesencrypt...");
    
    // Hook Dart _encryptBlock (通过 MethodChannel)
    var channel = Java.perform(function() {
        var Flutter = Java.use('io.flutter.embedding.engine.FlutterEngine');
        // Hook FlutterEngine 
    });
    
    // 尝试 Hook libflutter.so 中的加密相关函数
    var libflutter = Process.findModuleByName("libflutter.so");
    if (libflutter) {
        console.log("[+] Found libflutter.so at: " + libflutter.base);
        
        // 搜索字符串
        var encrypt_str = Memory.allocUtf8String("encryptParam");
        var result = Memory.scan(libflutter.base, libflutter.size, encrypt_str, {
            onMatch: function(address, size) {
                console.log("[+] Found 'encryptParam' string at: " + address);
            },
            onComplete: function() {
                console.log("[+] Scan complete");
            }
        });
    }
}

// 5. 监控网络请求加密
function hook_network_encryption() {
    console.log("\n[5] Hooking network encryption...");
    
    // Hook URLSession/NSURLConnection
    var NSURLSession = ObjC.classes.NSURLSession;
    if (NSURLSession) {
        console.log("[+] Found NSURLSession");
        
        Interceptor.attach(NSURLSession["- dataTaskWithRequest:completionHandler:"].implementation, {
            onEnter: function(args) {
                console.log("\n=== NSURLSession request ===");
                var request = ObjC.Object(args[2]);
                console.log("  URL: " + request.URL().absoluteString());
                console.log("  HTTPMethod: " + request.HTTPMethod());
                console.log("  AllHTTPHeaderFields: " + request.allHTTPHeaderFields());
            }
        });
    }
}

// 6. 通用 Hook 框架
function start_hooks() {
    console.log("\n========================================");
    console.log("捷途 App 加密分析 - Frida Hook");
    console.log("========================================");
    console.log("PID: " + Process.id);
    console.log("Platform: " + Process.platform);
    console.log("========================================");
    
    hook_encryption();
    hook_system_crypto();
    
    if (Process.platform === 'android') {
        hook_java_crypto();
    }
    
    hook_flutter_encryption();
    
    console.log("\n[+] Hooks installed. Trigger encryption in the app...");
}

// 执行
start_hooks();

// 保持脚本运行
setTimeout(function() {
    console.log("\n[.] Still monitoring... Press Ctrl+C to stop");
}, 10000);
