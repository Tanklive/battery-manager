# TUI 80x40 终端布局经验

## 约束

macOS Terminal 默认窗口 80 列 x 40 行。TUI 必须在此尺寸下完整显示。

## 布局方案

### 方案 A：两栏（v1/v2）

```
┌──────────────────┬──────────────────┐
│ 📊 健康          │ 🎛️ 控制          │
│ 左栏 40列        │ 右栏 40列        │
└──────────────────┴──────────────────┘
```

### 方案 B：三栏（v3，当前）

```
┌──────────────┬──────────────────┬──────────────────┐
│ 📊 健康      │ 🎛️ 控制          │ ⚙️ 配置          │
│ 左栏 ~27列   │ 中栏 ~27列       │ 右栏 ~26列       │
└──────────────┴──────────────────┴──────────────────┘
```

三栏方案在 80x40 中可行，但每栏更窄，按钮文字必须更短。

## 垂直空间预算（40 行）

```
Header:              1 行
Status bar:          2 行（1 内容 + 1 空行）
Mid row (三栏):      ~12 行（取最高栏）
Log panel:           ~6 行
Footer:              1 行
Buffer:              剩余
```

## 水平空间预算（80 列）

三栏各占 1fr → 每栏约 26-27 列（扣除边距）。

### 按钮排列规则（三栏）

- 每栏约 27 列 → 每行最多 2 个按钮（每个 ~13 列含边框）
- 按钮文字必须 ≤ 6 字符
- 4 个调节按钮分 2 行：➖10 ➖5 一行，➕5 ➕10 一行
- 策略按钮 4 个分 2 行：60%/80% 一行，90%/100% 一行

## CSS 要点

```css
Screen { layout: vertical; }
#status_panel { height: auto; margin: 0 1; }
#mid_row { layout: horizontal; height: auto; margin: 0 1; }
#health_panel { width: 1fr; }
#control_panel { width: 1fr; }
#config_panel { width: 1fr; }
#log_panel { height: 1fr; margin: 0 1; }
Button { margin: 0; min-width: 8; }
Horizontal { height: auto; layout: horizontal; }
Horizontal > Button { width: 1fr; }
```

关键：`height: auto`（不用固定值），`width: 1fr`（平分空间）。

## 已验证的元素取舍

| 元素 | 保留? | 原因 |
|------|-------|------|
| 电量进度条 | ✅ | 一行搞定，信息密度高 |
| 健康信息 | ✅ | 核心数据，4 行够用 |
| 状态说明 | ✅ | 用户需要知道 SMC 是否已生效 |
| 调节按钮 | ✅ | 核心操作 |
| 策略按钮 | ✅ | 一键切换 |
| 写入/持久化 | ✅ | 必要操作 |
| 配置面板 | ✅ | 上下限/间隔可在TUI中调节 |
| 输入框 | ❌ | 用户不要，按钮够用 |
| 可视化刻度尺 | ❌ | 占 5 行空间，用户不要 |
| 日志面板 | ✅ | 保留但缩小到 6 行 |

## Textual 版本注意

- textual 8.2.6 没有 Slider 组件，不要 import
- `self.log` 是 Textual 内置属性，自定义日志用 `log_msg`
- `@work` 装饰器在非 async 函数上必须加 `thread=True`
- Rich markup 嵌套标签会冲突，变量中不要含 markup 标签
