# 电池管理开发踩坑记录

## ioreg 温度单位

**错误**：`info['temperature_c'] = info['temperature'] / 10.0`
**正确**：`info['temperature_c'] = info['temperature'] / 100.0`

ioreg 返回的 Temperature 值单位是 **0.01°C**（centidegrees）。
例如：3090 = 30.90°C，不是 309°C。

验证方法：
```bash
ioreg -l -w0 | grep '"Temperature"'
# 输出: "Temperature" = 3090
# 3090 / 100 = 30.9°C ✓
```

## Textual 开发踩坑

### self.log 命名冲突

Textual 的 `App` 类有内置 `self.log` 属性（用于调试日志）。
自定义日志方法如果也叫 `self.log`，会覆盖内置属性，导致：
```
AttributeError: 'function' object has no attribute 'system'
```
**解决**：自定义方法用 `log_msg`、`add_log` 等名称。

### @work 装饰器必须加 thread=True

Textual 的 `@work` 装饰器默认要求 async 函数。
如果函数是普通 sync 函数（如调用 subprocess），必须加 `thread=True`：
```python
# 错误
@work(exclusive=True)
def _apply_charge_limit(self, target):
    subprocess.run(...)

# 正确
@work(exclusive=True, thread=True)
def _apply_charge_limit(self, target):
    subprocess.run(...)
```

### MarkupError: 嵌套标签冲突

在 Static 组件中使用 Rich markup 时，嵌套的标签会冲突导致崩溃：
```
MarkupError: closing tag '[/green]' does not match any open tag
```

**错误写法**：
```python
f"[bold]⚙️ 配置[/bold] 守护:{dm_tag}\n"  # dm_tag 内含 [green]...[/green]
# 渲染后: [bold]⚙️ 配置[/bold] 守护:[green]运行中[/green]
# Textual 解析时 [bold] 和 [green] 嵌套冲突
```

**正确写法**：不要在 f-string 中嵌套带 markup 的变量，直接用纯文本：
```python
dm = "运行中" if running else "未运行"
return f"[bold]⚙️ 配置[/bold] 守护:{dm}\n..."  # 纯文本，无嵌套标签
```

### textual 8.x 没有 Slider 组件

textual 8.2.6 中 `from textual.widgets import Slider` 会报 ImportError。
**解决**：用按钮（➖/➕）代替滑块，或用 `ProgressBar`。

## bclm 在 macOS 15 上的行为

- bclm read：SIP 部分禁用时可用 ✓
- bclm write：需要 sudo + SIP 部分禁用。macOS 15 可能限制 SMC 写入
- 实测：MacBookPro11,5 + macOS 15.7.4 + SIP 部分禁用 → read/write 均可用
- bclm write 需要通过 osascript 打开终端执行（agent 无法输入 sudo 密码）
- **建议配置 sudoers 免密**：避免每次操作都弹终端让用户输密码

## sudo 免密配置

```bash
# 配置 bclm 免密 sudo（只需执行一次）
sudo bash -c 'echo "用户名 ALL=(root) NOPASSWD: /usr/local/bin/bclm" > /etc/sudoers.d/bclm && chmod 440 /etc/sudoers.d/bclm'

# 验证
sudo -n bclm read  # 无需密码则成功
```

**注意**：用户名替换为实际的 macOS 登录用户名。

## TUI 界面设计踩坑

### 按钮被挤出屏幕

右栏宽度有限，如果按钮文字太长（如「升高上限 ▶」），两个按钮并排会超出容器宽度，导致第二个按钮不可见。

**解决**：
- 按钮文字要短：「➖10」「➕5」「📋写入」
- CSS 用 `Horizontal > Button { width: 1fr; }` 让按钮平分空间
- 去掉不必要的描述性文字

### 可视化刻度尺不实用

曾尝试用 ▼▲ 标记的进度条显示充电上限，用户明确不喜。
**结论**：用策略按钮，不用可视化刻度尺。

### 输入框多余

用户不需要手动输入精确数值，按钮调节够用。
**结论**：去掉输入框，纯按钮操作。

### 三栏布局适配 80x40

三栏（健康+控制+配置）在 80x40 终端中可以完整显示：
- 每栏约 25-27 列宽（扣除边距和分隔）
- 按钮文字必须 ≤ 6 字符才能 2 个一行
- 垂直方向用 `height: auto` 不用固定值
- CSS 中三栏都用 `width: 1fr` 平分空间

## bclm 只设上限，不设下限

bclm write 设置的是充电上限。SMC 芯片自动管理：
- 到上限停止充电
- 电池自放电到约 77%（低于上限 3%）时自动充回
- 这个 3% 的回差（hysteresis）是 SMC 内置的，防止频繁充放电

**如需下限功能**：用 `battery_daemon.py` 守护进程，通过轮询监控实现。

## 电芯电压

ioreg 中 CellVoltage 是一个数组（每个电芯的电压）。
取平均值：
```python
m = re.search(r'"CellVoltage"=\(([\\d,]+)\\)', ioreg)
if m:
    cells = [int(x) for x in m.group(1).split(',')]
    avg = sum(cells) / len(cells)
```

正常范围：3700-4200 mV（满电约 4200，截止约 3000）。
