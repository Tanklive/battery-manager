#!/usr/bin/env python3
"""电池1小时监控 - 每2分钟记录一次"""
import subprocess, re, json, time, os
from datetime import datetime

LOG = os.path.expanduser("~/.hermes/scripts/battery_1h_log.jsonl")

def read():
    info = {}
    raw = subprocess.run("bclm read", shell=True, capture_output=True, text=True, timeout=5).stdout.strip()
    info["smc"] = int(raw) if raw.isdigit() else None
    
    pmset = subprocess.run("pmset -g batt", shell=True, capture_output=True, text=True, timeout=5).stdout
    info["power"] = "AC" if "AC" in pmset else "Battery"
    info["charging"] = "charging" in pmset.lower() and "not charging" not in pmset.lower()
    m = re.search(r"(\d+)%;\s*(\w+)", pmset)
    if m:
        info["pct"] = int(m.group(1))
        info["state"] = m.group(2)
    
    ioreg = subprocess.run("ioreg -l -w0", shell=True, capture_output=True, text=True, timeout=10).stdout
    m = re.search(r'"Temperature"\s*=\s*(\d+)', ioreg)
    if m:
        info["temp"] = round(int(m.group(1)) / 100.0, 1)
    
    m = re.search(r'"IsCharging"\s*=\s*(Yes|No)', ioreg)
    if m:
        info["is_charging"] = m.group(1) == "Yes"
    
    info["ts"] = datetime.now().strftime("%H:%M:%S")
    return info

print("🔋 开始1小时电池监控 (每2分钟记录)")
print("=" * 60)

for i in range(30):  # 30次 × 2分钟 = 60分钟
    info = read()
    
    # 写入日志
    with open(LOG, "a") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    
    # 打印
    chg = "⚡充电" if info.get("is_charging") else "🔋放电"
    print(f"[{info['ts']}] {info['pct']}% {chg} | SMC:{info['smc']}% | {info['temp']}°C | {info['power']}")
    
    if i < 29:
        time.sleep(120)  # 2分钟

print("=" * 60)
print("✅ 监控完成")
