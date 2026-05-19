#!/usr/bin/env python3
"""
🔋 电池上下限监控守护进程
通过轮询实现充电下限功能（bclm 只支持上限，此脚本补充下限逻辑）

原理:
  电量 ≤ 下限 → 临时提高上限让系统充电
  电量 ≥ 上限 → 恢复目标上限，停止充电

使用:
  python3 battery_daemon.py              # 前台运行
  python3 battery_daemon.py --daemon     # 后台守护
  python3 battery_daemon.py --status     # 查看状态
  python3 battery_daemon.py --stop       # 停止守护进程

配置: battery_config.json 中的 upper_limit / lower_limit
"""

import subprocess, re, json, os, sys, time, signal
from datetime import datetime

CONFIG_PATH = os.path.expanduser("~/.hermes/battery_config.json")
PID_FILE = os.path.expanduser("~/.hermes/scripts/battery_daemon.pid")
LOG_FILE = os.path.expanduser("~/.hermes/scripts/battery_daemon.log")

# 默认配置
DEFAULT_CONFIG = {
    "upper_limit": 80,      # 充电上限
    "lower_limit": 60,      # 充电下限（新功能）
    "enabled": True,        # 是否启用下限保护
    "check_interval": 120,  # 检查间隔（秒）
}


def load_config():
    """加载配置，合并默认值"""
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            user_cfg = json.load(f)
        # 合并用户配置
        for k in DEFAULT_CONFIG:
            if k in user_cfg:
                cfg[k] = user_cfg[k]
    return cfg


def save_config(cfg):
    """保存配置到文件"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            full_cfg = json.load(f)
    else:
        full_cfg = {}
    full_cfg["upper_limit"] = cfg["upper_limit"]
    full_cfg["lower_limit"] = cfg["lower_limit"]
    full_cfg["limit_enabled"] = cfg["enabled"]
    full_cfg["check_interval"] = cfg["check_interval"]
    with open(CONFIG_PATH, "w") as f:
        json.dump(full_cfg, f, ensure_ascii=False, indent=2)


def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def read_battery():
    """读取电池状态"""
    info = {}
    raw = run_cmd("bclm read")
    info["charge_limit"] = int(raw) if raw.isdigit() else None

    pmset = run_cmd("pmset -g batt")
    info["power_source"] = "AC" if "AC" in pmset else "Battery"
    info["is_charging"] = "charging" in pmset.lower() and "not charging" not in pmset.lower()
    m = re.search(r"(\d+)%;\s*(\w+)", pmset)
    if m:
        info["percentage"] = int(m.group(1))
        info["state"] = m.group(2)

    ioreg = run_cmd("ioreg -l -w0")
    for key in ["Temperature"]:
        m = re.search(rf'"{key}"\s*=\s*(\d+)', ioreg)
        if m:
            info[key.lower()] = int(m.group(1))
    if "temperature" in info:
        info["temperature_c"] = round(info["temperature"] / 100.0, 1)

    return info


def set_charge_limit(limit):
    """设置充电上限"""
    result = subprocess.run(
        f"sudo bclm write {limit}",
        shell=True, capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0


def log(msg):
    """写入日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def check_temperature(info, threshold=35):
    """温度保护"""
    temp = info.get("temperature_c", 25)
    if temp > threshold:
        log(f"⚠️ 温度过高: {temp}°C (阈值: {threshold}°C)，暂停充电")
        set_charge_limit(0)  # 设为0 = 不充电
        return True
    return False


def daemon_loop():
    """主监控循环"""
    cfg = load_config()
    upper = cfg["upper_limit"]
    lower = cfg["lower_limit"]
    interval = cfg["check_interval"]
    temp_threshold = load_config().get("temp_threshold_c", 35)

    log(f"🔋 电池守护进程启动")
    log(f"   上限: {upper}% | 下限: {lower}% | 间隔: {interval}s")
    log(f"   温度保护: {temp_threshold}°C")

    current_mode = "normal"  # normal / charging / temp_protect

    while True:
        try:
            info = read_battery()
            pct = info.get("percentage", 50)
            temp = info.get("temperature_c", 25)
            smc_limit = info.get("charge_limit", upper)
            power = info.get("power_source", "Battery")

            # 只在插电时启用下限保护
            if power != "AC":
                if current_mode != "battery":
                    log(f"🔌 未插电 ({pct}%)，下限保护暂停")
                    current_mode = "battery"
                time.sleep(interval)
                continue

            # 温度保护
            if temp > temp_threshold:
                if current_mode != "temp_protect":
                    log(f"🌡️ 温度保护启动: {temp}°C > {temp_threshold}°C")
                    set_charge_limit(0)
                    current_mode = "temp_protect"
                time.sleep(interval)
                continue

            # 温度恢复
            if current_mode == "temp_protect" and temp < temp_threshold - 2:
                log(f"🌡️ 温度恢复: {temp}°C，取消温度保护")
                set_charge_limit(upper)
                current_mode = "normal"

            # 下限保护逻辑
            if pct <= lower:
                # 电量低于下限 → 临时提高上限让系统充电
                if smc_limit != 100:
                    log(f"⬇️ 电量 {pct}% ≤ 下限 {lower}%，临时提高上限到 100% 充电")
                    set_charge_limit(100)
                    current_mode = "charging"

            elif pct >= upper:
                # 电量达到上限 → 恢复目标上限
                if smc_limit != upper:
                    log(f"⬆️ 电量 {pct}% ≥ 上限 {upper}%，恢复上限 {upper}% 停止充电")
                    set_charge_limit(upper)
                    current_mode = "normal"

            else:
                # 在上下限之间 → 保持当前状态
                if current_mode == "charging" and smc_limit == 100:
                    # 还在充电中，等充到上限
                    pass
                elif smc_limit != upper and current_mode != "temp_protect":
                    log(f"🔄 电量 {pct}% 在 {lower}%-{upper}% 之间，恢复上限 {upper}%")
                    set_charge_limit(upper)
                    current_mode = "normal"

        except Exception as e:
            log(f"❌ 错误: {e}")

        time.sleep(interval)


def show_status():
    """显示当前状态"""
    cfg = load_config()
    info = read_battery()
    pct = info.get("percentage", "?")
    temp = info.get("temperature_c", "?")
    smc = info.get("charge_limit", "?")
    power = info.get("power_source", "?")

    upper = cfg["upper_limit"]
    lower = cfg["lower_limit"]
    enabled = cfg["enabled"]

    # 检查守护进程是否运行
    pid = None
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read().strip()
        # 检查进程是否还活着
        try:
            os.kill(int(pid), 0)
            running = True
        except (ProcessLookupError, ValueError):
            running = False
            pid = None
    else:
        running = False

    print("🔋 电池守护进程状态")
    print("=" * 40)
    print(f"  电量:     {pct}%")
    print(f"  温度:     {temp}°C")
    print(f"  电源:     {power}")
    print(f"  SMC上限:  {smc}%")
    print(f"  目标上限: {upper}%")
    print(f"  下限:     {lower}%")
    print(f"  下限保护: {'✅ 启用' if enabled else '❌ 禁用'}")
    print(f"  守护进程: {'✅ 运行中 (PID: ' + pid + ')' if running else '❌ 未运行'}")

    if running:
        # 显示最近日志
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                lines = f.readlines()[-5:]
            if lines:
                print(f"\n  最近日志:")
                for line in lines:
                    print(f"    {line.rstrip()}")


def start_daemon():
    """启动守护进程"""
    # 检查是否已运行
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read().strip()
        try:
            os.kill(int(pid), 0)
            print(f"⚠️ 守护进程已在运行 (PID: {pid})")
            return
        except (ProcessLookupError, ValueError):
            os.remove(PID_FILE)

    # 写入 PID 文件
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

    log(f"🚀 守护进程启动 (PID: {pid})")

    try:
        daemon_loop()
    except KeyboardInterrupt:
        log("🛑 守护进程停止")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def stop_daemon():
    """停止守护进程"""
    if not os.path.exists(PID_FILE):
        print("❌ 守护进程未运行")
        return

    with open(PID_FILE) as f:
        pid = f.read().strip()

    try:
        os.kill(int(pid), signal.SIGTERM)
        print(f"✅ 已停止守护进程 (PID: {pid})")
        os.remove(PID_FILE)
    except ProcessLookupError:
        print(f"⚠️ 进程 {pid} 已不存在")
        os.remove(PID_FILE)
    except Exception as e:
        print(f"❌ 停止失败: {e}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    elif "--stop" in sys.argv:
        stop_daemon()
    elif "--daemon" in sys.argv:
        # 后台运行
        pid = os.fork()
        if pid > 0:
            print(f"🔋 守护进程已在后台启动 (PID: {pid})")
            sys.exit(0)
        else:
            # 子进程
            os.setsid()
            start_daemon()
    else:
        start_daemon()
