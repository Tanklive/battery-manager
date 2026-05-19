---
name: battery-manager
description: "macOS 电池健康管理：TUI交互界面 + 后台守护进程，实现充电上下限自动管理、温度保护、健康监控。基于 bclm + SMC 芯片。"
version: 1.0.0
author: 吉量
license: MIT
metadata:
  hermes:
    tags: [battery, health, charging, power-management, macos, smc, tui]
    related_skills: []
---

# 🔋 Battery Manager — macOS 电池健康管理

macOS 电池充电上下限管理工具。通过 bclm 控制 SMC 芯片实现充电上限，守护进程轮询补充下限功能。

## Overview

锂电池在 20%-90% 区间工作寿命最长。Apple 官方建议充电上限 80%-90%。此工具实现：
- **充电上限**: bclm 写入 SMC 芯片，硬件级控制
- **充电下限**: 守护进程每 2 分钟轮询，电量低于下限时临时提高上限触发充电
- **温度保护**: 超过 35°C 自动暂停充电
- **TUI 界面**: 三栏交互界面，按钮操作，无需输入框

## When to Use

- MacBook 一直插电使用（办公室/家里固定工位）
- 想延长电池寿命，避免长期 100% 充电老化
- 老款 Intel MacBook（2015-2019）
- macOS 15+ 但 SIP 已关闭（Kext Signing: disabled）

**不适用:**
- Apple Silicon Mac（macOS 26.4+ 已原生支持充电限制）
- SIP 完全开启的 Mac（bclm 无法写入 SMC）
- Windows / Linux

## 前置条件

| 项目 | 要求 | 检查命令 |
|------|------|----------|
| macOS | 10.15+ | `sw_vers` |
| Python | 3.9+ | `python3 --version` |
| bclm | brew 安装 | `bclm --version` |
| textual | pip 安装 | `pip3 show textual` |
| SIP | Kext Signing 关闭 | `csrutil status` |

## 安装步骤

```bash
# 1. 安装 bclm
brew tap zackelia/formulae
brew install bclm

# 2. 安装 textual
pip3 install textual

# 3. 首次配置
sudo bclm write 90
sudo bclm persist

# 4. 配置免密 sudo
echo "your_username ALL=(root) NOPASSWD: /usr/local/bin/bclm" | sudo tee /etc/sudoers.d/bclm
sudo chmod 440 /etc/sudoers.d/bclm
```

## 使用方式

### TUI 交互界面

```bash
python3 scripts/battery_tui.py
```

三栏布局:
- 左栏: 电池健康（状态、健康度、容量、循环、电压）
- 中栏: 充电控制（±调节、写入SMC、持久化、策略切换）
- 右栏: 配置面板（上下限、间隔、守护进程状态）

### 后台守护进程

```bash
# 启动守护
python3 scripts/battery_daemon.py --daemon

# 查看状态
python3 scripts/battery_daemon.py --status

# 停止
python3 scripts/battery_daemon.py --stop
```

### 纯文本模式

```bash
python3 scripts/battery_tui.py --headless
```

### 健康分析

```bash
python3 scripts/battery_health.py
```

## 配置文件

`battery_config.json`:

```json
{
  "upper_limit": 90,
  "lower_limit": 20,
  "check_interval": 120,
  "temp_threshold_c": 35,
  "limit_enabled": true,
  "strategy": "performance"
}
```

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `upper_limit` | 90 | 充电上限 (20-100) |
| `lower_limit` | 20 | 充电下限 (0-80) |
| `check_interval` | 120 | 检查间隔 (秒) |
| `temp_threshold_c` | 35 | 温度保护阈值 (°C) |
| `limit_enabled` | true | 是否启用下限保护 |

## 工作原理

```
bclm write 90% → 写入 SMC 芯片
    ↓
SMC 硬件级控制:
  充到 ~93% (Intel回差+3%) → 停止充电
  掉到 ~90% → 自动充回 ~93%
    ↓
守护进程补充下限:
  电量 ≤ 20% → 临时 SMC=100% → 充电
  电量 ≥ 90% → 恢复 SMC=90% → 停止
    ↓
循环: 20% ↔ 90%
```

## 策略预设

| 策略 | 上限 | 适用场景 |
|------|------|----------|
| 🛡️ 保守 | 60% | 长期插电最大保护 |
| ⚖️ 平衡 | 80% | 日常使用（推荐）|
| ⚡ 性能 | 90% | 需要较长续航 |
| 🔋 满电 | 100% | 出行前临时使用 |

## Apple 官方电池建议

- 锂电池在 **40%-80%** 区间工作寿命最长
- 避免长时间保持 **100%** 电量
- 工作温度: **10°C ~ 35°C**
- **不需要**定期放电校准（锂电池无记忆效应）
- 长期存放充到 **50%**

## 开机自启

```bash
# 启用
launchctl load ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist

# 禁用
launchctl unload ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist
```

## Common Pitfalls

1. **bclm write 需要 sudo** — 建议配置免密 sudoers
2. **Intel Mac 回差 +3%** — 设 90% 实际停在 ~93%，如需精确 90% 设为 87%
3. **macOS 大版本升级** 可能重置 SMC，升级后检查
4. **SIP 必须部分关闭** — `csrutil status` 确认 Kext Signing: disabled
5. **守护进程只在插电时工作** — 用电池时自动暂停下限保护
6. **温度 > 35°C 自动保护** — 暂停充电，降温后自动恢复

## Verification Checklist

- [ ] `bclm read` 输出正确上限值
- [ ] `sudo -n bclm read` 免密可用
- [ ] TUI 界面三栏正常显示
- [ ] 守护进程运行中（`battery_daemon.py --status`）
- [ ] LaunchAgent 已加载（`launchctl list | grep battery`）
- [ ] 拔掉电源 → 守护进程自动暂停
- [ ] 插上电源 → 守护进程自动恢复

## GitHub

https://github.com/Tanklive/battery-manager
