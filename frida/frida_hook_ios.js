// Frida Script - 捷途 App iOS/微信小程序 Hook
// 专门用于监控 iOS 端的加密请求

console.log("========================================");
console.log("捷途 App iOS 加密监控");
console.log("========================================\n");

// Hook CFNetwork
function hookCFNetwork() {
    console.log("[+] Hooking CFNetwork...");
    
    var types = [
        "NSURLSession",
        "NSURLConnection", 
        "NSMutableURLRequest",
        "NSHTTPURLResponse"
    ];
    
    types.forEach(function(t) {
        try {
            var cls = ObjC.classes[t];
            if (cls) {
                console.log("[+] Found: " + t);
            }
        } catch(e) {}
    });
}

// Hook NSURLSession
function hookNSURLSession() {
    try {
        var NSURLSession = ObjC.classes.NSURLSession;
        if (!NSURLSession) {
            console.log("[-] NSURLSession not found");
            return;
        }
        
        console.log("[+] Hooking NSURLSession...");
        
        // Hook sharedSession
        var originalShared = NSURLSession.sharedSession;
        NSURLSession.sharedSession.implementation = function() {
            console.log("\n=== NSURLSession.sharedSession ===");
            return this.sharedSession();
        };
        
    } catch (e) {
        console.log("[-] NSURLSession hook error: " + e);
    }
}

// Hook NSURLRequest
function hookNSURLRequest() {
    try {
        var NSMutableURLRequest = ObjC.classes.NSMutableURLRequest;
        if (!NSMutableURLRequest) return;
        
        console.log("[+] Hooking NSMutableURLRequest...");
        
        // Hook setValue:forHTTPHeaderField:
        NSMutableURLRequest["- setValue:forHTTPHeaderField:"].implementation = function(value, field) {
            if (field && value) {
                var fieldStr = field.toString();
                var valueStr = value.toString();
                
                // 只打印重要的 header
                if (fieldStr === "encryptFlag" || 
                    fieldStr === "encryptParam" ||
                    fieldStr === "riskParam" ||
                    fieldStr === "volcParam" ||
                    fieldStr === "Content-Type") {
                    console.log("\n=== HTTP Header ===");
                    console.log("  " + fieldStr + ": " + valueStr);
                }
            }
            return this.setValue_forHTTPHeaderField_(value, field);
        };
        
    } catch (e) {
        console.log("[-] NSMutableURLRequest hook error: " + e);
    }
}

// Hook NSURLConnection
function hookNSURLConnection() {
    try {
        var NSURLConnection = ObjC.classes.NSURLConnection;
        if (!NSURLConnection) return;
        
        console.log("[+] Hooking NSURLConnection...");
        
        // Hook sendSynchronousRequest
        NSURLConnection["+ sendSynchronousRequest:returningResponse:error:"].implementation = function(request, response, error) {
            console.log("\n=== NSURLConnection.sendSynchronousRequest ===");
            console.log("  URL: " + request.URL().absoluteString());
            console.log("  Method: " + request.HTTPMethod());
            
            var result = this.sendSynchronousRequest_returningResponse_error_(request, response, error);
            
            if (result) {
                console.log("  Response received: " + result.length + " bytes");
            }
            
            return result;
        };
        
    } catch (e) {
        console.log("[-] NSURLConnection hook error: " + e);
    }
}

// Hook NSURLSessionTask
function hookNSURLSessionTask() {
    try {
        var NSURLSessionTask = ObjC.classes.NSURLSessionTask;
        if (!NSURLSessionTask) return;
        
        console.log("[+] Hooking NSURLSessionTask...");
        
        // Hook resume
        NSURLSessionTask["- resume"].implementation = function() {
            console.log("\n=== NSURLSessionTask.resume ===");
            console.log("  Task: " + this.taskDescription());
            console.log("  State: " + this.state());
            
            // 获取当前请求
            try {
                var currReq = this.currentRequest();
                if (currReq) {
                    console.log("  URL: " + currReq.URL().absoluteString());
                    console.log("  Method: " + currReq.HTTPMethod());
                }
            } catch(e) {}
            
            return this.resume();
        };
        
    } catch (e) {
        console.log("[-] NSURLSessionTask hook error: " + e);
    }
}

// Hook NSJSONSerialization
function hookJSONSerialization() {
    try {
        var NSJSONSerialization = ObjC.classes.NSJSONSerialization;
        if (!NSJSONSerialization) return;
        
        console.log("[+] Hooking NSJSONSerialization...");
        
        // Hook dataWithJSONObject
        NSJSONSerialization["+ dataWithJSONObject:options:error:"].implementation = function(obj, opts, err) {
            console.log("\n=== NSJSONSerialization.dataWithJSONObject ===");
            console.log("  Object: " + obj.toString());
            
            var result = this.dataWithJSONObject_options_error_(obj, opts, err);
            console.log("  Result length: " + (result ? result.length() : 0));
            
            return result;
        };
        
        // Hook JSONObjectWithData
        NSJSONSerialization["+ JSONObjectWithData:options:error:"].implementation = function(data, opts, err) {
            console.log("\n=== NSJSONSerialization.JSONObjectWithData ===");
            console.log("  Data length: " + data.length());
            
            var result = this.JSONObjectWithData_options_error_(data, opts, err);
            if (result) {
                console.log("  Parsed: " + result.toString().substring(0, 100));
            }
            
            return result;
        };
        
    } catch (e) {
        console.log("[-] NSJSONSerialization hook error: " + e);
    }
}

// Hook CryptoKit (iOS 13+)
function hookCryptoKit() {
    try {
        var AES = ObjC.classes.CryptoKit.SymmetricKey; // 这可能不存在
        
        console.log("[+] Checking CryptoKit...");
        
        // 尝试查找 AES 加密相关符号
        var lib = Process.findModuleByName("libsystem_crypto.dylib");
        if (lib) {
            console.log("[+] Found libsystem_crypto.dylib");
        }
        
    } catch (e) {
        console.log("[-] CryptoKit check: " + e);
    }
}

// Hook CommonCrypto
function hookCommonCrypto() {
    console.log("\n[+] Hooking CommonCrypto...");
    
    var funcs = [
        "CCCrypt",
        "CCCryptorCreate",
        "CCCryptorUpdate",
        "CCCryptorFinal"
    ];
    
    funcs.forEach(function(name) {
        try {
            var addr = Module.findExportByName("libcommonCrypto.dylib", name);
            if (addr) {
                console.log("[+] " + name + " @ " + addr);
                
                Interceptor.attach(addr, {
                    onEnter: function(args) {
                        console.log("\n=== " + name + " ===");
                        // 打印关键参数
                        for (var i = 0; i < 6; i++) {
                            try {
                                console.log("  Arg[" + i + "]: " + args[i]);
                            } catch(e) {}
                        }
                    }
                });
            }
        } catch(e) {}
    });
}

// Hook libcipher (iOS Keychain)
function hookKeychain() {
    console.log("\n[+] Hooking Security framework...");
    
    try {
        var SecKey = Module.findExportByName("libSecurity.dylib", "SecKeyCreateEncryptedData");
        if (SecKey) {
            console.log("[+] SecKeyCreateEncryptedData @ " + SecKey);
            
            Interceptor.attach(SecKey, {
                onEnter: function(args) {
                    console.log("\n=== SecKeyCreateEncryptedData ===");
                    console.log("  Algorithm: " + args[0]);
                    console.log("  Key: " + args[1]);
                    console.log("  Data: " + args[2]);
                }
            });
        }
    } catch (e) {
        console.log("[-] Keychain hook error: " + e);
    }
}

// 主函数
function main() {
    console.log("Platform: " + Process.platform);
    console.log("SDK: " + ObjC.available ? "ObjC available" : "ObjC not available");
    
    if (ObjC.available) {
        hookCFNetwork();
        hookNSURLSession();
        hookNSURLRequest();
        hookNSURLConnection();
        hookNSURLSessionTask();
        hookJSONSerialization();
    }
    
    hookCommonCrypto();
    hookKeychain();
    
    console.log("\n========================================");
    console.log("iOS monitoring started.");
    console.log("Trigger encryption in the app.");
    console.log("========================================\n");
}

// 执行
main();

// 保持运行
setInterval(function() {}, 1000);
