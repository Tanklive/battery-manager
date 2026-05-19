# Apple 官方电池健康建议

来源：apple.com/batteries/maximizing-performance + support.apple.com/zh-cn/102338

## 核心原则

锂电池在 **40%-80%** 区间工作寿命最长。避免长时间 100% 或 0%。

## 插电使用建议

- 设充电上限 80%（Apple 官方推荐 80%-90%）
- SMC 自动管理：到上限停，掉几个百分点自动补
- 保持「优化电池充电」开启（T2/Apple Silicon Mac）
- Intel Mac 无原生优化充电，用 bclm 实现同等效果

## 温度管理

- 工作温度：10°C ~ 35°C
- 理想温度：16°C ~ 22°C
- 超过 35°C 系统自动停止充电
- 高温充电会进一步损坏电池

## 长期存放

- 充到 50% 存放
- 每 6 个月补充充电到 50%
- 完全放电存放会导致深度放电，无法充电

## macOS 版本差异

- macOS 26.4+：原生支持充电上限（80%-100%），仅 Apple Silicon
- macOS 15：限制第三方 SMC 工具（bclm 需 SIP 部分禁用）
- macOS 13-14：优化电池充电可用，bclm 正常工作
- Intel Mac：始终需要 bclm 实现充电限制
