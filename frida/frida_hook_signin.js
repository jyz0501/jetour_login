// Frida Script - 捷途 App 签到 API 监控
// 专门用于监控签到请求的加密/解密过程

console.log("========================================");
console.log("捷途 App 签到 API Hook");
console.log("========================================\n");

// 目标: 提取 event-start API 的加密参数

var BASE_URL = "mobile-consumer.jetour.com.cn";
var SIGN_API = "/web/task/tasks/event-start";

// Hook NSURLSession / CFNetwork
function hookNetwork() {
    console.log("[+] Hooking network layer...");
    
    var sessionQueue = ObjC.classes.NSObject.methods;
    
    // Hook NSURLSession 委托
    var NSURLSessionTask = ObjC.classes.NSURLSessionTask;
    var NSURLSession = ObjC.classes.NSURLSession;
    
    if (NSURLSession) {
        console.log("[+] NSURLSession available");
    }
}

// Android: Hook HttpURLConnection
function hookAndroidNetwork() {
    Java.perform(function() {
        console.log("[+] Hooking Java HttpURLConnection...");
        
        var HttpURLConnection = Java.use("java.net.HttpURLConnection");
        
        HttpURLConnection.setRequestMethod.overload('java.lang.String').implementation = function(method) {
            console.log("\n=== HTTP Request ===");
            console.log("Method: " + method);
            return this.setRequestMethod(method);
        };
        
        HttpURLConnection.setRequestProperty.overload('java.lang.String', 'java.lang.String').implementation = function(key, value) {
            if (key === "encryptFlag" || key === "riskParam" || key === "volcParam") {
                console.log("Header: " + key + " = " + value);
            }
            return this.setRequestProperty(key, value);
        };
        
        HttpURLConnection.getOutputStream.implementation = function() {
            console.log("[+] Getting OutputStream...");
            var os = this.getOutputStream();
            return os;
        };
    });
}

// Hook OkHttp (常见 Android HTTP 库)
function hookOkHttp() {
    Java.perform(function() {
        try {
            var OkHttpClient = Java.use("okhttp3.OkHttpClient");
            var RealConnection = Java.use("okhttp3.internal.connection.RealConnection");
            var Request = Java.use("okhttp3.Request");
            var Response = Java.use("okhttp3.Response");
            
            console.log("[+] OkHttp found, hooking...");
            
            // Hook connect
            RealConnection.connect.implementation = function(stackTrace) {
                console.log("\n=== OkHttp Connect ===");
                return this.connect(stackTrace);
            };
            
        } catch (e) {
            console.log("[-] OkHttp not found: " + e);
        }
    });
}

// Hook Flutter 引擎
function hookFlutter() {
    console.log("\n[+] Hooking Flutter engine...");
    
    var libflutter = Process.findModuleByName("libflutter.so");
    if (libflutter) {
        console.log("[+] libflutter.so: " + libflutter.base);
        
        // 搜索 event-start 字符串
        try {
            Memory.scan(libflutter.base, libflutter.size, "event-start", {
                onMatch: function(addr, size) {
                    console.log("[!] Found 'event-start' at: " + addr);
                },
                onComplete: function() {}
            });
        } catch(e) {
            console.log("[-] Scan error: " + e);
        }
    }
    
    // 搜索 signInScene
    var libapp = Process.findModuleByName("libapp.so");
    if (libapp) {
        console.log("[+] libapp.so: " + libapp.base);
        
        try {
            Memory.scan(libapp.base, libapp.size, "signInScene", {
                onMatch: function(addr, size) {
                    console.log("[!] Found 'signInScene' at: " + addr);
                },
                onComplete: function() {}
            });
        } catch(e) {}
    }
}

// Hook Java 层加密
function hookJavaCrypto() {
    Java.perform(function() {
        console.log("[+] Hooking javax.crypto...");
        
        try {
            // Hook Cipher
            var Cipher = Java.use("javax.crypto.Cipher");
            
            Cipher.doFinal.overload('[byte').implementation = function(input) {
                console.log("\n=== Cipher.doFinal ===");
                console.log("Input: " + toHexString(input));
                var output = this.doFinal(input);
                console.log("Output: " + toHexString(output));
                return output;
            };
            
            Cipher.doFinal.overload('[byte', 'int').implementation = function(input, offset) {
                console.log("\n=== Cipher.doFinal (with offset) ===");
                console.log("Input: " + toHexString(input));
                var output = this.doFinal(input, offset);
                console.log("Output: " + toHexString(output));
                return output;
            };
            
            // Hook SecretKeySpec
            var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
            SecretKeySpec.$init.overload('[byte', 'java.lang.String').implementation = function(keyBytes, algorithm) {
                console.log("\n=== SecretKeySpec.init ===");
                console.log("Algorithm: " + algorithm);
                console.log("Key: " + toHexString(keyBytes));
                return this.$init(keyBytes, algorithm);
            };
            
        } catch (e) {
            console.log("[-] Crypto hook error: " + e);
        }
    });
}

// 辅助函数: byte array to hex
function toHexString(bytes) {
    var result = "";
    for (var i = 0; i < Math.min(bytes.length, 64); i++) {
        result += bytes[i].toString(16).padStart(2, '0') + " ";
        if ((i+1) % 16 === 0) result += "\n";
    }
    return result;
}

// 内存搜索 - 查找 devToken
function searchDevToken() {
    console.log("\n[+] Searching for devToken in memory...");
    
    var libapp = Process.findModuleByName("libapp.so");
    if (libapp) {
        // 搜索 BMTyQJ7hc93dxRSX5hP
        try {
            Memory.scan(libapp.base, libapp.size, "BMTyQJ7hc93dxRSX", {
                onMatch: function(addr, size) {
                    console.log("[!] Found devToken pattern at: " + addr);
                    console.log("    Content: " + hexdump(addr, {length: 64}));
                },
                onComplete: function() {}
            });
        } catch(e) {}
    }
}

// 搜索 encryptParam 加密结果
function searchEncryptParam() {
    console.log("\n[+] Searching for encryptParam value...");
    
    // 已知值: XVbMc0E0Bog0aMncZT4Fc9eBOtNc2Gr/O2TZv0bw7mjeocEZ9-cSUUfZL-f5K1ooqTokk3gHxy6LQc7gxNX8dQ==
    var known_encrypted = "XVbMc0E0Bog0aMncZT4Fc9eBOtNc2Gr";
    
    var libapp = Process.findModuleByName("libapp.so");
    if (libapp) {
        try {
            Memory.scan(libapp.base, libapp.size, known_encrypted, {
                onMatch: function(addr, size) {
                    console.log("[!] Found encrypted data at: " + addr);
                },
                onComplete: function() {}
            });
        } catch(e) {}
    }
}

// 主函数
function main() {
    console.log("Initializing sign-in API monitor...\n");
    
    if (Process.platform === 'android') {
        hookAndroidNetwork();
        hookOkHttp();
        hookJavaCrypto();
    } else if (Process.platform === 'ios') {
        hookNetwork();
    }
    
    hookFlutter();
    searchDevToken();
    searchEncryptParam();
    
    console.log("\n========================================");
    console.log("Monitoring started. Trigger sign-in action.");
    console.log("========================================\n");
}

// 执行
main();

// 保持运行
setInterval(function() {}, 1000);
