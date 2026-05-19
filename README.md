# 🔋 Battery Manager for macOS

macOS 电池健康管理工具 — 交互式 TUI 界面，一键设置充电上限，保护电池寿命。

![macOS](https://img.shields.io/badge/macOS-10.15+-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 📊 **实时监控** — 电量、温度、健康度、循环次数、电芯电压
- 🎛️ **充电上限调节** — 按钮 +/- 调节，支持 20%-100%
- ⚡ **一键写入 SMC** — 免密写入硬件，立即生效
- 💾 **持久化** — 重启后设置不丢失
- 🎯 **四种策略** — 保守(60%) / 平衡(80%) / 性能(90%) / 满电(100%)
- 📋 **纯文本模式** — `--headless` 参数快速查看状态
- ⏰ **定时检查** — Cron Job 每天自动检查，异常时通知

---

## 📋 适用场景

### ✅ 适用

| 场景 | 说明 |
|------|------|
| MacBook 一直插电使用 | 办公室/家里固定工位，最佳使用场景 |
| 想延长电池寿命 | 避免长期 100% 充电导致电池老化 |
| 老款 Intel MacBook | 2015-2019 年款，有独立 SMC 芯片 |
| macOS 15+ 但 SIP 已关闭 | bclm 需要 Kext Signing 关闭才能写入 SMC |

### ❌ 不适用

| 场景 | 原因 |
|------|------|
| Apple Silicon Mac (macOS 26.4+) | 系统已原生支持充电限制 (80%-100%) |
| SIP 完全开启的 Mac | bclm 无法写入 SMC |
| 想设置充电下限 | bclm 只支持上限，下限由 SMC 自动管理 |
| Windows / Linux | 仅支持 macOS |

---

## 🖥️ 使用环境要求

### 硬件要求

- **MacBook** (2015 年及以后的 Intel 款)
- 需要有独立 **SMC 芯片** (所有 Intel Mac 都有)
- Apple Silicon Mac 不需要此工具 (系统已内置)

### 软件要求

| 项目 | 要求 | 检查命令 |
|------|------|----------|
| macOS | 10.15 Catalina 或更高 | `sw_vers` |
| Python | 3.9 或更高 | `python3 --version` |
| bclm | 最新版 | `bclm --version` |
| textual | 8.x | `pip3 show textual` |
| SIP 状态 | Kext Signing 或 Filesystem Protections 关闭 | `csrutil status` |

### SIP 状态说明

SIP (System Integrity Protection) 是 macOS 的安全机制。bclm 需要写入 SMC，所以需要部分关闭 SIP。

```bash
# 检查当前 SIP 状态
csrutil status
```

**需要看到以下至少一项为 disabled：**

```
Kext Signing: disabled        ← bclm 需要这个
Filesystem Protections: disabled  ← 或这个也行
```

**如果 SIP 完全开启 (全部 enabled)：**
1. 重启进入恢复模式 (开机按住 Command+R)
2. 打开终端
3. 执行 `csrutil disable --with kext --with dtrace --with nvram --without fs`
4. 重启

---

## 🚀 安装步骤

### 第一步：安装 bclm

```bash
# 添加 homebrew 源
brew tap zackelia/formulae

# 安装 bclm
brew install bclm

# 验证安装
bclm read
# 应该输出 100 (默认值)
```

### 第二步：安装 Python 依赖

```bash
pip3 install textual
```

### 第三步：下载工具

```bash
git clone https://github.com/Tanklive/battery-manager.git
cd battery-manager
```

### 第四步：首次配置

```bash
# 1. 设置充电上限 (推荐 80%)
sudo bclm write 80

# 2. 持久化 (重启后保持)
sudo bclm persist

# 3. 验证
bclm read
# 应该输出 80
```

### 第五步：配置免密 (推荐)

以后操作 bclm 不用再输入密码：

```bash
# 替换 your_username 为你的用户名
echo "your_username ALL=(root) NOPASSWD: /usr/local/bin/bclm" | sudo tee /etc/sudoers.d/bclm
sudo chmod 440 /etc/sudoers.d/bclm

# 验证
sudo -n bclm read
# 应该直接输出数字，不提示密码
```

---

## 📖 使用说明

### 启动 TUI 界面

```bash
python3 battery_tui.py
```

### 界面操作

```
┌──────────────────────────────────────────────────────┐
│ ⚡ [██████████████░░░░░░] 72% charging | 上限:80%    │  ← 状态栏
├──────────────────┬───────────────────────────────────┤
│ 📊 健康 Normal   │ 🎛️ 控制 ✅已生效                  │
│  健康度:88.7%    │  电量72% 充电到80%停止            │  ← 信息区
│  循环:118        │                                   │
│  容量:7764/8755  │  ➖10  ➖5   ➕5   ➕10            │  ← 调节按钮
│  电压:4168mV     │  📋写入  💾持久化                 │  ← 操作按钮
│                  │  60%  80%  90%  100%             │  ← 策略按钮
│                  │  🔄刷新                          │
├──────────────────┴───────────────────────────────────┤
│ 日志: 目标 → 80%                                     │  ← 日志区
└──────────────────────────────────────────────────────┘
```

### 按钮功能

| 按钮 | 功能 | 说明 |
|------|------|------|
| ➖10 / ➖5 | 降低上限 | 每次降 10% 或 5% |
| ➕5 / ➕10 | 升高上限 | 每次升 5% 或 10% |
| 📋写入 | 写入 SMC | 将目标上限写入硬件芯片，立即生效 |
| 💾持久化 | 持久化 | 将当前 SMC 设置写入永久存储，重启后保持 |
| 60% 80% 90% 100% | 快捷策略 | 一键切换到预设上限 |
| 🔄刷新 | 刷新状态 | 重新读取电池数据 |

### 操作流程

```
调节上限:
  点击 ➖/➕ 按钮 → 目标值更新 → 点击「📋写入」→ 生效
                                         ↓
                                   点击「💾持久化」→ 重启保持

切换策略:
  点击策略按钮 (如 80%) → 目标自动设为 80% → 点击「📋写入」→ 生效
```

### 纯文本模式

快速查看状态，不需要 TUI：

```bash
python3 battery_tui.py --headless
```

输出示例：
```
🔋 电池状态
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ 项目     ┃ 值            ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ 电量     │ 72%           │
│ 充电上限 │ 80%           │
│ 策略     │ balanced      │
│ 健康度   │ 88.7%         │
│ 状态     │ Normal        │
│ 容量     │ 7764/8755 mAh │
│ 循环     │ 118           │
│ 温度     │ 31.1°C        │
└──────────┴───────────────┘
```

### 健康分析

```bash
python3 battery_health.py
```

输出 JSON 格式的详细电池数据和建议。

---

## ⚙️ 配置文件

配置文件位置: `battery_config.json`

```json
{
  "strategy": "balanced",
  "charge_limit": 80,
  "temp_threshold_c": 35,
  "health_alert_pct": 80,
  "strategies": {
    "conservative": {"charge_limit": 60, "description": "保守 - 长期插电最大保护"},
    "balanced": {"charge_limit": 80, "description": "平衡 - Apple官方推荐"},
    "performance": {"charge_limit": 90, "description": "性能 - 需要较长续航"},
    "full": {"charge_limit": 100, "description": "满电 - 出行前临时使用"}
  }
}
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `strategy` | `"balanced"` | 当前使用的策略名称 |
| `charge_limit` | `80` | 充电上限百分比 (20-100) |
| `temp_threshold_c` | `35` | 温度告警阈值 (°C) |
| `health_alert_pct` | `80` | 健康度告警阈值 (%) |
| `strategies` | 见上文 | 四种预设策略 |

---

## 🔋 Apple 官方电池建议

来源: [apple.com/batteries](https://www.apple.com/batteries/maximizing-performance/)

### 充电习惯

- 锂电池在 **40%-80%** 区间工作寿命最长
- 避免长时间保持 **100%** 电量
- 避免频繁深度放电到 **0%**
- 每月做一次完整充放电 **(0% → 100%)** 校准电池

### 温度管理

| 条件 | 温度范围 |
|------|----------|
| 工作温度 | 10°C ~ 35°C |
| 理想温度 | 16°C ~ 22°C |
| 存储温度 | -20°C ~ 45°C |

- 超过 35°C 系统会自动停止充电
- 高温充电会进一步损坏电池

### 长期存放

- 充到 **50%** 再存放
- 每 **6 个月** 充电一次
- 不要满电或空电存放

---

## 🔧 工作原理

### 充电管理机制

```
bclm write 80%
    ↓
写入 SMC 芯片 (System Management Controller)
    ↓
SMC 硬件级控制充电行为：
  • 充到 80% → 停止充电
  • 电池自放电到 ~77% → 自动充回 80%
  • 循环区间: 77%~80% (约3%波动)
    ↓
bclm persist → 写入永久存储，重启后仍有效
```

### 为什么不需要设置下限？

SMC 芯片内置了**回差 (hysteresis)** 机制：

- 充到上限 → 停止
- 掉了约 3% → 自动开始充电
- 充回上限 → 停止

这个 3% 的自然波动是正常的，也是健康的。手动设下限反而会增加循环次数。

### bclm vs batt

| 特性 | bclm | batt |
|------|------|------|
| Intel Mac | ✅ 支持 | ❌ 不支持 |
| Apple Silicon | ⚠️ 仅 80/100 | ✅ 完整支持 |
| 充电下限 | ❌ 不支持 | ✅ 支持 |
| macOS 15+ | ⚠️ 需要 SIP 关闭 | ✅ 支持 |
| 安装方式 | `brew install bclm` | `brew install batt` |

---

## ⚠️ 注意事项

1. **bclm 需要 sudo 权限** — 首次使用需要输入密码
2. **macOS 大版本升级** 可能重置 SMC 设置，升级后检查一下
3. **SMC 重置** (断电/拆电池/PRAM重置) 会清除设置
4. **不支持充电下限** — SMC 自动管理，无需手动设置
5. **SIP 必须部分关闭** — 否则 bclm 无法写入 SMC

---

## 🐛 常见问题

### Q: bclm read 输出 100，但我设了 80？

A: 可能 SMC 被重置了。重新执行：
```bash
sudo bclm write 80
sudo bclm persist
```

### Q: 提示 "password required" ？

A: 需要配置免密 sudo，参考安装步骤第五步。

### Q: TUI 界面显示不全？

A: 终端窗口需要至少 80 列 x 40 行。拖拽调整窗口大小即可。

### Q: macOS 15 上 bclm 不工作？

A: macOS 15 限制了 SMC 访问。需要：
1. 检查 SIP 状态: `csrutil status`
2. 如果 Kext Signing 是 enabled，需要关闭它
3. 重启进入恢复模式执行: `csrutil disable --with kext`

### Q: 温度显示不正确？

A: ioreg 返回的温度单位是 0.01°C (如 3090 = 30.9°C)。工具已自动转换。

---

## 📁 文件结构

```
battery-manager/
├── battery_tui.py          # 交互式 TUI 界面（主程序）
├── battery_health.py       # 电池健康分析脚本
├── battery_config.json     # 策略配置文件
└── README.md               # 本文档
```

## 📄 License

MIT
