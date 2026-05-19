# 🔋 Battery Manager for macOS

macOS 电池健康管理工具 — 交互式 TUI + 后台守护进程，实现充电上下限自动管理。

![macOS](https://img.shields.io/badge/macOS-10.15+-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 📊 **实时监控** — 电量、温度、健康度、循环次数、电芯电压
- 🎛️ **TUI 交互界面** — 按钮调节充电上限，一键写入 SMC
- 🔄 **后台守护进程** — 开机自启，自动管理充电上下限
- 🌡️ **温度保护** — 超过 35°C 自动暂停充电
- 💾 **持久化** — 重启后设置不丢失
- 🎯 **四种策略** — 保守 / 平衡 / 性能 / 满电
- ⏰ **定时检查** — Cron Job 每天自动检查电池健康

---

## 🔋 核心原理

### bclm + 守护进程 = 完整的上下限管理

bclm 只能设置充电**上限**（写入 SMC 芯片）。守护进程通过**轮询监控**补充了**下限**功能：

```
┌─────────────────────────────────────────────────┐
│                  充电循环示意                     │
│                                                 │
│  100% ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│                                                 │
│   90% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │  ← 上限 (SMC 停止充电)
│        ↑                        ↓               │
│   80%  │   正常使用区间         │               │
│        │                        │               │
│   70%  │                        │               │
│        │                        │               │
│   60%  │                        │               │
│        │                        │               │
│   50%  │                        │               │
│        │                        ↓               │
│   40%  │                        │               │
│        │                        │               │
│   30%  │                        │               │
│        │                        │               │
│   20% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │  ← 下限 (守护进程临时提高上限到100%)
│        ↑                        ↓               │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 工作流程

```
启动守护进程
    ↓
每 120 秒检查一次电量
    ↓
┌─ 电量 ≤ 20%? → 临时 SMC=100% → 开始充电
├─ 电量 ≥ 90%? → 恢复 SMC=90%  → 停止充电
├─ 20% < 电量 < 90%? → 保持当前状态
└─ 温度 > 35°C? → SMC=0 → 暂停充电（温度保护）
    ↓
循环: 20% ↔ 90%
```

### 为什么这样设计？

| 问题 | 解决方案 |
|------|----------|
| bclm 只有上限 | 守护进程轮询补充下限 |
| SMC 自带回差 (约3%) | 利用这个自然波动，减少充放电次数 |
| 长期100%伤电池 | 上限90%避免满电存放 |
| 完全放电也伤电池 | 下限20%避免深度放电 |
| 高温充电危险 | 温度保护自动暂停 |

---

## 📋 适用场景

### ✅ 适用

| 场景 | 说明 |
|------|------|
| MacBook 一直插电 | 办公室/家里，最佳场景 |
| 想延长电池寿命 | 避免长期 100% 老化 |
| 老款 Intel MacBook | 2015-2019 年款 |
| macOS 15+ 但 SIP 已关闭 | bclm 需要 Kext Signing 关闭 |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| Apple Silicon (macOS 26.4+) | 系统已原生支持 |
| SIP 完全开启 | bclm 无法写入 SMC |

---

## 🖥️ 使用环境要求

### 硬件

- MacBook (2015 年及以后 Intel 款)
- 需要 SMC 芯片 (所有 Intel Mac 都有)

### 软件

| 项目 | 要求 | 检查命令 |
|------|------|----------|
| macOS | 10.15+ | `sw_vers` |
| Python | 3.9+ | `python3 --version` |
| bclm | 最新版 | `bclm --version` |
| textual | 8.x | `pip3 show textual` |
| SIP | Kext Signing 关闭 | `csrutil status` |

### SIP 状态检查

```bash
csrutil status
```

需要看到：
```
Kext Signing: disabled        ← bclm 需要这个
```

---

## 🚀 安装步骤

### 第一步：安装依赖

```bash
# bclm (SMC 充电控制)
brew tap zackelia/formulae
brew install bclm

# textual (TUI 框架)
pip3 install textual
```

### 第二步：下载工具

```bash
git clone https://github.com/Tanklive/battery-manager.git
cd battery-manager
```

### 第三步：首次配置

```bash
# 设置充电上限 90%
sudo bclm write 90

# 持久化
sudo bclm persist
```

### 第四步：配置免密 sudo

```bash
# 替换 your_username 为你的用户名
echo "your_username ALL=(root) NOPASSWD: /usr/local/bin/bclm" | sudo tee /etc/sudoers.d/bclm
sudo chmod 440 /etc/sudoers.d/bclm
```

### 第五步：启动守护进程

```bash
# 前台运行（看日志）
python3 battery_daemon.py

# 后台守护
python3 battery_daemon.py --daemon
```

---

## 📖 使用说明

### TUI 交互界面

```bash
python3 battery_tui.py
```

```
┌──────────────────────────────────────────────────────┐
│ ⚡ [██████████████░░░░░░] 89% charging | 上限:90%    │
├──────────────────┬───────────────────────────────────┤
│ 📊 健康 Normal   │ 🎛️ 控制 ✅已生效                  │
│  健康度:88.7%    │  电量89% 充电到90%停止            │
│  循环:118        │  ➖10  ➖5   ➕5   ➕10            │
│  容量:7764/8755  │  📋写入  💾持久化                 │
│  电压:4168mV     │  60%  80%  90%  100%             │
│                  │  🔄刷新                          │
├──────────────────┴───────────────────────────────────┤
│ SMC=芯片，写入即生效但重启丢 | 持久化=重启保持       │
└──────────────────────────────────────────────────────┘
```

### 按钮功能

| 按钮 | 功能 |
|------|------|
| ➖10 / ➖5 | 降低充电上限 |
| ➕5 / ➕10 | 升高充电上限 |
| 📋写入 | 将上限写入 SMC 芯片，立即生效 |
| 💾持久化 | 重启后保持设置 |
| 60% 80% 90% 100% | 一键切换策略 |

### 后台守护进程

```bash
# 查看状态
python3 battery_daemon.py --status

# 启动
python3 battery_daemon.py --daemon

# 停止
python3 battery_daemon.py --stop
```

输出：
```
🔋 电池守护进程状态
========================================
  电量:     89%
  温度:     31.1°C
  电源:     AC
  SMC上限:  90%
  目标上限: 90%
  下限:     20%
  下限保护: ✅ 启用
  守护进程: ✅ 运行中 (PID: 12715)
```

### 开机自启

守护进程通过 macOS LaunchAgent 实现开机自启：

```bash
# 启用
launchctl load ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist

# 禁用
launchctl unload ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist
```

### 纯文本模式

```bash
python3 battery_tui.py --headless
```

---

## ⚙️ 配置文件

`battery_config.json`

```json
{
  "strategy": "performance",
  "charge_limit": 90,
  "upper_limit": 90,
  "lower_limit": 20,
  "limit_enabled": true,
  "check_interval": 120,
  "temp_threshold_c": 35,
  "health_alert_pct": 80
}
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `strategy` | `"balanced"` | 策略名称 |
| `upper_limit` | `90` | 充电上限 (20-100) |
| `lower_limit` | `20` | 充电下限 (0-80) |
| `limit_enabled` | `true` | 是否启用下限保护 |
| `check_interval` | `120` | 检查间隔 (秒) |
| `temp_threshold_c` | `35` | 温度保护阈值 (°C) |
| `health_alert_pct` | `80` | 健康度告警阈值 (%) |

### 策略预设

| 策略 | 上限 | 下限 | 适用场景 |
|------|------|------|----------|
| 🛡️ 保守 | 60% | 20% | 长期插电最大保护 |
| ⚖️ 平衡 | 80% | 20% | 日常使用（推荐）|
| ⚡ 性能 | 90% | 20% | 需要较长续航 |
| 🔋 满电 | 100% | - | 出行前临时使用 |

---

## 🔋 Apple 官方电池建议

来源: [apple.com/batteries](https://www.apple.com/batteries/maximizing-performance/)

- 锂电池在 **40%-80%** 区间工作寿命最长
- 避免长时间保持 **100%** 电量
- 避免频繁深度放电到 **0%**
- 工作温度: **10°C ~ 35°C**
- 每月做一次完整充放电校准

---

## ⚠️ 注意事项

1. **bclm 需要 sudo 权限** — 建议配置免密
2. **macOS 大版本升级** 可能重置 SMC，升级后检查
3. **守护进程只在插电时工作** — 用电池时自动暂停
4. **温度 > 35°C 自动保护** — 暂停充电，降温后恢复
5. **SIP 必须部分关闭** — 否则 bclm 无法写入

---

## 🐛 常见问题

### Q: bclm read 输出 100？

A: SMC 可能被重置了。重新执行：
```bash
sudo bclm write 90
sudo bclm persist
```

### Q: 守护进程没启动？

A: 检查 LaunchAgent：
```bash
launchctl list | grep battery
# 如果没有，重新加载
launchctl load ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist
```

### Q: 想改上下限？

A: 编辑 `battery_config.json`：
```json
{
  "upper_limit": 80,
  "lower_limit": 30
}
```
然后重启守护进程。

### Q: TUI 显示不全？

A: 终端窗口需要至少 80 列 x 40 行。

---

## 📁 文件结构

```
battery-manager/
├── battery_tui.py                    # TUI 交互界面
├── battery_health.py                 # 健康分析脚本
├── battery_daemon.py                 # 后台守护进程（上下限管理）
├── battery_config.json               # 策略配置
└── README.md                         # 本文档

安装后生成的文件:
~/.hermes/scripts/
├── battery_tui.py                    # TUI
├── battery_health.py                 # 分析
├── battery_daemon.py                 # 守护进程
├── battery_daemon.log                # 守护进程日志
└── battery_config.json               # 配置

~/Library/LaunchAgents/
└── com.yangzs.battery-daemon.plist   # 开机自启配置

~/Desktop/
└── 🔋电池管理.command                # 桌面快捷方式
```

## 📄 License

MIT
