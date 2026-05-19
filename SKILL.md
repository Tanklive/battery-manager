---
name: battery-manager
description: "macOS 电池健康管理：充电限制、放电控制、健康监控、温度保护、交互式 TUI。基于 bclm + pmset + ioreg 实现。"
version: 1.2.0
author: 吉量
license: MIT
metadata:
  hermes:
    tags: [battery, health, charging, power-management, macos, tui]
  platform: [macos]
  requires:
    commands: [bclm, pmset, ioreg, system_profiler]
    brew: [bclm]
    pip: [textual]
---

# 电池健康管理技能

macOS 电池充放电管理、健康监控、温度保护、交互式 TUI。适用于 Intel MacBook（有 SMC 芯片）。

## 文件清单

| 文件 | 用途 |
|------|------|
| `scripts/battery_health.py` | 电池健康分析脚本（JSON 输出） |
| `scripts/battery_tui.py` | 交互式 TUI 界面（Textual 框架，适配 80x40） |
| `scripts/battery_cron_check.py` | Cron 定时检查（无告警时静默） |
| `references/pitfalls.md` | 开发踩坑记录 |
| `references/desktop-shortcut.md` | macOS .command 桌面快捷方式模板 |
| `references/tui-layout-80x40.md` | TUI 80x40 终端布局经验 |
| `references/passwordless-sudo.md` | bclm 免密 sudo 配置 |

## 前置条件

- **bclm** 必须已安装：`brew tap zackelia/formulae && brew install bclm`
- **textual** 必须已安装（TUI 需要）：`pip3 install textual`
- **SIP 状态**：bclm 需要 Kext Signing 关闭或 SIP 部分禁用才能写入 SMC
  - 检查：`csrutil status`
  - macOS 15 + SIP 完全开启 → bclm 不可用
  - macOS 15 + SIP 部分禁用（Kext Signing: disabled）→ bclm 可用
- **sudo 权限**：bclm write/persist 需要 sudo（建议配置免密，见下方）

### 配置 bclm 免密 sudo

为避免每次操作都输入密码，配置 sudoers：

```bash
# 在终端中执行（需要输入一次密码）
sudo bash -c 'echo "用户名 ALL=(root) NOPASSWD: /usr/local/bin/bclm" > /etc/sudoers.d/bclm && chmod 440 /etc/sudoers.d/bclm'
```

验证：`sudo -n bclm read`（无需密码则成功）

### bclm 工作原理（重要）

**bclm 只设上限，不设下限。** SMC 芯片自动管理充电行为：

```
bclm write 80 之后：
  充到 80% → 停止充电
  电池自放电到 ~77% → 自动充回 80%
  循环区间：约 77%~80%（3% 自然波动，周期 1~3 天）
```

不需要手动设下限，SMC 内置回差（hysteresis）机制防止频繁充放电。

### Apple 官方电池健康建议

来源：apple.com/batteries + support.apple.com/zh-cn/102338

- 锂电池在 **40%-80%** 区间工作寿命最长
- 避免长时间保持 100% 电量（加速老化）
- 保持「优化电池充电」开启（T2/Apple Silicon Mac）
- 工作温度：10°C ~ 35°C（超过 35°C 系统自动停止充电）
- 长期存放充到 50%
- 完全放电到 0% 会损坏电池
- macOS 26.4+ 原生支持充电上限（80%-100%），Intel Mac 需用 bclm

## 工具链

| 工具 | 用途 | 需要 sudo |
|------|------|-----------|
| `bclm read` | 读取当前充电上限 (%) | 否 |
| `bclm write <N>` | 设置充电上限 (20-100) | 是 |
| `bclm persist` | 持久化设置（重启后生效） | 是 |
| `bclm unpersist` | 取消持久化 | 是 |
| `pmset -g batt` | 查看电池状态和剩余时间 | 否 |
| `ioreg -l -w0` | 读取电池详细数据（容量、温度、电压） | 否 |
| `system_profiler SPPowerDataType` | 电池健康信息（循环次数、状态） | 否 |

## 使用方式

### 1. 交互式 TUI（推荐）

```bash
python3 ~/.hermes/scripts/battery_tui.py
```

功能：
- 实时电量条 + 温度 + 电源状态（每30秒自动刷新）
- 电池健康信息面板（左栏）
- 充电控制面板（右栏）：输入框 + 策略按钮 + 写入SMC/持久化
- 导出 Markdown 报告
- Q 键退出

界面设计原则：
- 使用输入框 + 按钮，不用可视化刻度尺（用户偏好）
- 按钮紧凑排列，确保在标准终端窗口中全部可见
- 右栏宽度有限，按钮文字要短（如「➖10」「📋写入SMC」）

### 2. 命令行快速查看

```bash
python3 ~/.hermes/scripts/battery_tui.py --headless
```

### 3. 健康分析脚本

```bash
python3 ~/.hermes/scripts/battery_health.py
```

输出 JSON 格式的电池状态 + 告警 + 建议。

### 4. 桌面快捷方式（双击启动）

双击 `~/Desktop/🔋电池管理.command` 即可启动 TUI。
创建方法见 `references/desktop-shortcut.md`。

### 5. 手动设置充电上限

```bash
sudo bclm write 80    # 设置充电上限 80%
sudo bclm persist      # 持久化（重启后生效）
```

**注意**：sudo 命令必须在用户终端中执行。Agent 可通过 osascript 打开终端窗口执行。

## 充电策略

| 策略 | 上限 | 适用场景 |
|------|------|----------|
| conservative | 60% | 长期插电，最大保护 |
| balanced | 80% | 日常使用，40-80 法则（推荐） |
| performance | 90% | 需要较长续航 |
| full | 100% | 出行前充满 |

配置文件：`~/.hermes/battery_config.json`

## 定时检查

Cron Job `5fc4a6f63778`：每天 08:00 运行 `battery_cron_check.py`
- 有告警（温度过高、健康度下降）→ 三平台通知
- 无告警 → 静默

## 最佳实践（Apple 官方 + 40-80 法则）

1. **一直插电**：设充电上限 80%（Apple 推荐 80%-90%），不用管，SMC 自动管理
2. **出行前**：临时设 100%，充满带走，回来后恢复 80%
3. **每月校准**：做一次 0%-100% 完整充放电循环
4. **温度**：避免 > 35°C 环境，不要边充边跑高负载任务
5. **长期存放**：充到 50%，每 6 个月补电
6. **不要完全放电**：0% 会损坏电池

## Pitfalls

- **配置免密 sudo**：首次使用 bclm write 前，应配置 sudoers 免密。否则每次操作都要用户输入密码，体验很差。配置方法见「前置条件」章节
- **SIP 完全开启时 bclm 不可用**：`csrutil status` 检查，Kext Signing enabled 则无法写入 SMC
- **macOS 15 安全限制**：bclm read 能工作不代表 write 也能工作，首次设置需验证
- **重启后设置丢失**：必须执行 `sudo bclm persist`
- **ioreg 温度单位是 0.01°C**：如 3090 = 30.9°C，不是 0.1°C。常见错误是除以 10 得到 309°C
- **BatteryData MaxCapacity vs system_profiler Full Charge Capacity**：两者可能略有差异，以 system_profiler 为准
- **Textual self.log 冲突**：Textual App 类有内置 `self.log` 属性，自定义日志方法必须用其他名称（如 `log_msg`），否则 `AttributeError: 'function' object has no attribute 'system'`
- **Textual @work 装饰器**：非 async 函数必须加 `thread=True`，否则 `WorkerDeclarationError`
- **bclm 值 vs 显示百分比**：Intel Mac 上 bclm write 77 实际显示约 80%，因为 SMC 值和 UI 显示有偏移
- **bclm 只设上限**：不要试图设下限。SMC 芯片有内置回差机制，自动管理充电区间
- **TUI 按钮布局**：右栏宽度有限，按钮文字要短。曾因按钮过宽导致「升高上限」按钮被挤出屏幕。用 `width: 1fr` + 短标签解决
- **TUI 适配 80x40 终端**：默认终端窗口是 80x40。按钮必须 2 个一行（右栏约 40 字符宽），不能 4 个一行。去掉不必要元素（输入框、可视化刻度尺）节省垂直空间。CSS 用 `height: auto` 不用固定值
- **不要用可视化刻度尺**：用户明确不喜，去掉后更清爽
- **不要用输入框**：用户明确不要，按钮够用。去掉输入框后垂直空间大幅节省
- **用户偏好：精简 UI**：宁可少一个功能，也不要多一个占空间的控件。每次加 UI 元素前先问「这个值得占一行吗？」

## 命令速查

| 操作 | 命令 |
|------|------|
| 启动 TUI | `python3 ~/.hermes/scripts/battery_tui.py` |
| 纯文本查看 | `python3 ~/.hermes/scripts/battery_tui.py --headless` |
| 健康分析 | `python3 ~/.hermes/scripts/battery_health.py` |
| 读取上限 | `bclm read` |
| 设置上限 | `sudo -n bclm write 80`（免密） |
| 持久化 | `sudo -n bclm persist`（免密） |
| 取消持久化 | `sudo -n bclm unpersist`（免密） |
| 配置免密 | `sudo bash -c 'echo "用户名 ALL=(root) NOPASSWD: /usr/local/bin/bclm" > /etc/sudoers.d/bclm && chmod 440 /etc/sudoers.d/bclm'` |
| 电池状态 | `pmset -g batt` |
| 电池健康 | `system_profiler SPPowerDataType \| grep -E "Cycle Count\|Condition"` |
| 电池温度 | `ioreg -l -w0 \| grep '"Temperature"'` |
| 电池容量 | `ioreg -l -w0 \| grep -E '"(DesignCapacity\|MaxCapacity)"'` |
| SIP 状态 | `csrutil status` |
