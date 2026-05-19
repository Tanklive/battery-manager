#!/usr/bin/env python3
"""电池健康分析 - 读取并报告电池状态"""
import subprocess, re, json, os
from datetime import datetime

CONFIG_PATH = os.path.expanduser("~/.hermes/battery_config.json")

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "charge_limit": 80,
        "temp_threshold_c": 35,
        "health_alert_pct": 80,
        "strategy": "balanced",
        "strategies": {
            "conservative": {"charge_limit": 60, "description": "长期插电，最大电池保护"},
            "balanced": {"charge_limit": 80, "description": "日常使用，40-80 法则"},
            "performance": {"charge_limit": 90, "description": "需要较长续航时"},
            "full": {"charge_limit": 100, "description": "出行前充满"}
        }
    }

def get_battery_info():
    info = {}

    # bclm 充电上限
    try:
        info['charge_limit'] = int(run('bclm read') or 100)
    except:
        info['charge_limit'] = None

    # pmset 状态
    pmset = run('pmset -g batt')
    if 'AC' in pmset or 'AC attached' in pmset:
        info['power_source'] = 'AC'
    else:
        info['power_source'] = 'Battery'
    info['is_charging'] = 'charging' in pmset.lower() and 'not charging' not in pmset.lower()
    m = re.search(r'(\d+)%;\s*(\w+)', pmset)
    if m:
        info['percentage'] = int(m.group(1))
        info['state'] = m.group(2)
    # extract remaining time
    m = re.search(r'(\d+:\d+)\s*remaining', pmset)
    if m:
        info['remaining'] = m.group(1)

    # ioreg 详细数据
    ioreg = run('ioreg -l -w0')
    for key in ['DesignCapacity', 'MaxCapacity', 'CycleCount', 'Temperature', 'Voltage']:
        m = re.search(rf'"{key}"\s*=\s*(\d+)', ioreg)
        if m:
            info[key.lower()] = int(m.group(1))

    # 温度转换 (ioreg 返回的是 0.01°C 单位, 如 3090 = 30.90°C)
    if 'temperature' in info:
        info['temperature_c'] = round(info['temperature'] / 100.0, 1)

    # 健康度
    if 'designcapacity' in info and 'maxcapacity' in info:
        info['health_pct'] = round(info['maxcapacity'] / info['designcapacity'] * 100, 1)

    # system_profiler
    sp = run("system_profiler SPPowerDataType | grep 'Condition:'")
    m = re.search(r'Condition:\s*(\w+)', sp)
    if m:
        info['condition'] = m.group(1)

    # 电芯电压
    m = re.search(r'"CellVoltage"=\(([\d,]+)\)', ioreg)
    if m:
        cells = [int(x) for x in m.group(1).split(',')]
        info['cell_voltage_mv'] = cells
        info['cell_voltage_avg'] = round(sum(cells) / len(cells))

    return info

def analyze(info, config):
    alerts = []
    recommendations = []

    pct = info.get('percentage', 0)
    health = info.get('health_pct', 100)
    temp = info.get('temperature_c', 25)
    limit = info.get('charge_limit', 100)
    cycles = info.get('cyclecount', 0)
    strategy = config.get('strategy', 'balanced')

    # === 告警 ===
    if temp > 40:
        alerts.append(f"🔴 电池温度过高: {temp}°C，建议立即停止充电并降温")
    elif temp > 35:
        alerts.append(f"⚠️ 电池温度偏高: {temp}°C（建议 < 35°C）")

    if health < 70:
        alerts.append(f"🔴 电池健康度严重偏低: {health}%，强烈建议更换电池")
    elif health < 80:
        alerts.append(f"⚠️ 电池健康度偏低: {health}%，考虑更换电池")

    if info.get('condition') == 'Service Battery':
        alerts.append("🔴 电池状态: Service Battery，需要维修/更换")

    # === 建议 ===
    target_limit = config.get('strategies', {}).get(strategy, {}).get('charge_limit', 80)

    if limit is not None and limit != target_limit:
        recommendations.append(
            f"💡 当前充电上限 {limit}%，"
            f"策略「{strategy}」建议 {target_limit}%"
        )

    if pct > 90 and info.get('is_charging'):
        recommendations.append("💡 电量超过 90%，建议拔掉电源或降低充电上限")
    if pct < 20 and info.get('power_source') == 'Battery':
        recommendations.append("💡 电量低于 20%，建议连接电源")

    if cycles > 800:
        recommendations.append(f"ℹ️ 循环次数: {cycles}，接近 1000 次设计寿命")
    elif cycles > 500:
        recommendations.append(f"ℹ️ 循环次数: {cycles}，关注电池老化趋势")

    if not recommendations and not alerts:
        recommendations.append("✅ 电池状态良好，无需操作")

    return alerts, recommendations

def format_report(info, alerts, recommendations, config):
    lines = []
    lines.append("📊 电池健康报告")
    lines.append("=" * 40)

    # 基本状态
    lines.append(f"电量: {info.get('percentage', '?')}% ({info.get('state', 'unknown')})")
    lines.append(f"电源: {info.get('power_source', 'unknown')}")
    if info.get('remaining'):
        lines.append(f"剩余: {info['remaining']}")

    # 充电上限
    if info.get('charge_limit') is not None:
        lines.append(f"充电上限: {info['charge_limit']}%")
    else:
        lines.append("充电上限: 无法读取（bclm 未安装或 SIP 限制）")

    lines.append("")

    # 健康信息
    lines.append("── 健康信息 ──")
    if info.get('health_pct'):
        lines.append(f"健康度: {info['health_pct']}% ({info.get('condition', 'unknown')})")
    if info.get('designcapacity') and info.get('maxcapacity'):
        lines.append(f"设计容量: {info['designcapacity']} mAh")
        lines.append(f"当前容量: {info['maxcapacity']} mAh")
    if info.get('cyclecount') is not None:
        lines.append(f"循环次数: {info['cyclecount']}")
    if info.get('temperature_c') is not None:
        lines.append(f"温度: {info['temperature_c']}°C")
    if info.get('cell_voltage_avg'):
        lines.append(f"电芯电压: {info['cell_voltage_avg']}mV (avg)")

    lines.append("")

    # 当前策略
    strategy = config.get('strategy', 'balanced')
    lines.append(f"当前策略: {strategy}")

    # 告警
    if alerts:
        lines.append("")
        lines.append("── 告警 ──")
        for a in alerts:
            lines.append(a)

    # 建议
    if recommendations:
        lines.append("")
        lines.append("── 建议 ──")
        for r in recommendations:
            lines.append(r)

    return "\n".join(lines)

if __name__ == '__main__':
    config = load_config()
    info = get_battery_info()
    alerts, recommendations = analyze(info, config)

    report = format_report(info, alerts, recommendations, config)
    print(report)

    # Also output JSON for programmatic use
    result = {
        'info': info,
        'alerts': alerts,
        'recommendations': recommendations,
        'config': {'strategy': config.get('strategy'), 'charge_limit': config.get('charge_limit')},
        'timestamp': datetime.now().isoformat()
    }
    # Write JSON to temp file for cron job consumption
    json_path = os.path.expanduser("~/.hermes/scripts/battery_latest.json")
    with open(json_path, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
