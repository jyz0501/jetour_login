// Frida Script - macOS 本地分析 libapp.so
// 不需要运行 App，直接分析 libapp.so 文件的加密逻辑

console.log("╔════════════════════════════════════════════════════════════╗");
console.log("║     macOS 本地分析 - libapp.so 加密逻辑                      ║");
console.log("╚════════════════════════════════════════════════════════════╝\n");

// libapp.so 路径
var LIBAPP_PATH = "/Users/alun/Downloads/开发/捷途汽车 app/output/lib/arm64-v8a/libapp.so";

// 加载 libapp.so
function loadLibapp() {
    console.log("[*] Loading libapp.so...");
    
    try {
        // 尝试加载本地 SO 文件
        var libapp = Module.load(LIBAPP_PATH);
        console.log("[+] libapp.so loaded successfully");
        console.log("    Base: " + libapp.base);
        console.log("    Size: " + libapp.size);
        console.log("    Name: " + libapp.name);
        
        return libapp;
    } catch (e) {
        console.log("[-] Failed to load libapp.so: " + e);
        console.log("[!] This script needs to run in a process context.");
        console.log("[!] Use: frida -n some_process -l this_script.js");
        return null;
    }
}

// 分析导出符号
function analyzeExports(libapp) {
    if (!libapp) return;
    
    console.log("\n[*] Analyzing exported symbols...\n");
    
    var exports = libapp.enumerateExports();
    var cryptoExports = [];
    
    exports.forEach(function(exp) {
        if (exp.name.toLowerCase().indexOf("encrypt") !== -1 ||
            exp.name.toLowerCase().indexOf("aes") !== -1 ||
            exp.name.toLowerCase().indexOf("crypto") !== -1 ||
            exp.name.toLowerCase().indexOf("cipher") !== -1) {
            cryptoExports.push(exp);
            console.log("  [+] " + exp.type + " " + exp.name + " @ " + exp.address);
        }
    });
    
    console.log("\n[*] Found " + cryptoExports.length + " crypto-related exports");
    
    return cryptoExports;
}

// 分析符号表
function analyzeSymbols(libapp) {
    if (!libapp) return;
    
    console.log("\n[*] Analyzing symbols...\n");
    
    var symbols = libapp.enumerateSymbols();
    var cryptoSymbols = [];
    
    symbols.forEach(function(sym) {
        if (sym.name.indexOf("encrypt") !== -1 ||
            sym.name.indexOf("Encrypt") !== -1 ||
            sym.name.indexOf("AES") !== -1 ||
            sym.name.indexOf("aes") !== -1 ||
            sym.name.indexOf("JTEncrypt") !== -1 ||
            sym.name.indexOf("passwordEncrypt") !== -1) {
            cryptoSymbols.push(sym);
            console.log("  [+] " + sym.type + " " + sym.name);
        }
    });
    
    console.log("\n[*] Found " + cryptoSymbols.length + " crypto-related symbols");
    
    return cryptoSymbols;
}

// 搜索内存中的字符串
function searchStrings(libapp) {
    if (!libapp) return;
    
    console.log("\n[*] Searching for encryption strings...\n");
    
    var patterns = [
        "encryptParam",
        "encryptFlag",
        "riskParam",
        "volcParam",
        "JTEncrypt",
        "passwordEncrypt",
        "aesEncrypt",
        "_encryptBlock",
        "_encryptQueryParams",
        "jetour",
        "signInScene",
        "event-start"
    ];
    
    patterns.forEach(function(pattern) {
        try {
            Memory.scan(libapp.base, libapp.size, pattern, {
                onMatch: function(addr, size) {
                    console.log("  [!] Found '" + pattern + "' at: " + addr);
                    try {
                        var str = addr.readCString();
                        console.log("      Content: " + str.substring(0, 64));
                    } catch(e) {}
                },
                onComplete: function() {}
            });
        } catch (e) {
            console.log("  [-] Scan error for '" + pattern + "': " + e);
        }
    });
}

// 分析函数代码
function analyzeFunction(libapp, addr, name) {
    if (!libapp || !addr) return;
    
    console.log("\n[*] Analyzing function: " + name + " @ " + addr);
    
    try {
        // 读取函数开头的指令
        var instructions = Instruction.parse(addr);
        console.log("  First instruction: " + instructions);
        
        // 尝试反汇编前几条指令
        console.log("\n  Disassembly:");
        var currentAddr = addr;
        for (var i = 0; i < 10; i++) {
            try {
                var inst = Instruction.parse(currentAddr);
                console.log("    " + currentAddr + ": " + inst.mnemonic + " " + inst.operands);
                currentAddr = currentAddr.add(inst.size);
            } catch (e) {
                break;
            }
        }
    } catch (e) {
        console.log("  [-] Disassembly error: " + e);
    }
}

// Hook 加密函数（如果可以）
function hookCryptoFunctions(libapp) {
    if (!libapp) return;
    
    console.log("\n[*] Attempting to hook crypto functions...\n");
    
    var funcs = [
        "JTEncrypt",
        "passwordEncrypt",
        "aesEncrypt",
        "_encryptBlock",
        "_encryptQueryParams"
    ];
    
    funcs.forEach(function(name) {
        try {
            var addr = Module.findExportByName(libapp.name, name);
            if (addr) {
                console.log("  [+] Hooking " + name + " @ " + addr);
                
                Interceptor.attach(addr, {
                    onEnter: function(args) {
                        console.log("\n=== " + name + " called ===");
                        console.log("  Args: " + args.length);
                        for (var i = 0; i < 4; i++) {
                            try {
                                console.log("  Arg[" + i + "]: " + args[i]);
                            } catch(e) {}
                        }
                    },
                    onLeave: function(retval) {
                        console.log("  Return: " + retval);
                    }
                });
            }
        } catch (e) {
            console.log("  [-] Hook error for " + name + ": " + e);
        }
    });
}

// 提取可能的密钥
function extractKeys(libapp) {
    if (!libapp) return;
    
    console.log("\n[*] Extracting potential keys...\n");
    
    // 搜索 16/32 字节的连续数据（可能是 AES 密钥）
    var keyPatterns = [
        // Jetour 常见模式
        "jetour2024jetour",
        "Jetour@2024#Key",
        "JTP@ssw0rd2024!",
        // 通用模式
        "0123456789abcdef",
        "abcdefghijklmnop"
    ];
    
    keyPatterns.forEach(function(pattern) {
        try {
            Memory.scan(libapp.base, libapp.size, pattern, {
                onMatch: function(addr, size) {
                    console.log("  [!] Potential key at: " + addr);
                    console.log("      Pattern: " + pattern);
                    console.log("      Data: " + hexdump(addr, {length: 32}));
                },
                onComplete: function() {}
            });
        } catch (e) {}
    });
}

// 主函数
function main() {
    console.log("Platform: " + Process.platform);
    console.log("PID: " + Process.id);
    console.log("Arch: " + Process.arch);
    
    var libapp = loadLibapp();
    
    if (libapp) {
        var exports = analyzeExports(libapp);
        var symbols = analyzeSymbols(libapp);
        searchStrings(libapp);
        extractKeys(libapp);
        hookCryptoFunctions(libapp);
        
        // 分析关键函数
        if (exports && exports.length > 0) {
            exports.forEach(function(exp) {
                analyzeFunction(libapp, exp.address, exp.name);
            });
        }
    } else {
        console.log("\n[!] 无法直接加载 libapp.so");
        console.log("[!] 需要在进程上下文中运行此脚本");
        console.log("[!] 使用方法:");
        console.log("    frida -n some_process -l mac_local_analysis.js");
        console.log("    或");
        console.log("    frida -U -f com.jetour.traveller -l mac_local_analysis.js");
    }
    
    console.log("\n========================================");
    console.log("Analysis complete.");
    console.log("========================================\n");
}

// 执行
main();