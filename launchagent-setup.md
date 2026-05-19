# LaunchAgent 开机自启配置

## 概述

macOS LaunchAgent 可以让守护进程在用户登录时自动启动，崩溃后自动重启。

## 文件位置

```
~/Library/LaunchAgents/com.yangzs.battery-daemon.plist
```

## Plist 模板

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yangzs.battery-daemon</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/yangzs/.hermes/scripts/battery_daemon.py</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/yangzs/.hermes/scripts/battery_daemon_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/yangzs/.hermes/scripts/battery_daemon_stderr.log</string>

    <key>WorkingDirectory</key>
    <string>/Users/yangzs/.hermes/scripts</string>
</dict>
</plist>
```

## 管理命令

```bash
# 启用（加载）
launchctl load ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist

# 禁用（卸载）
launchctl unload ~/Library/LaunchAgents/com.yangzs.battery-daemon.plist

# 检查状态
launchctl list | grep battery

# 查看日志
tail -f ~/.hermes/scripts/battery_daemon.log
```

## 关键配置说明

| 键 | 值 | 说明 |
|----|-----|------|
| `RunAtLoad` | `true` | 用户登录时自动启动 |
| `KeepAlive` | `true` | 进程退出后自动重启 |
| `StandardOutPath` | 日志路径 | stdout 输出到文件 |
| `StandardErrorPath` | 日志路径 | stderr 输出到文件 |

## 前提条件

- 守护进程需要 `sudo bclm write` 权限
- 必须先配置 bclm 免密 sudo（/etc/sudoers.d/bclm）
- Python 路径必须正确（`/usr/bin/python3` 或 brew 路径）

## 注意事项

- LaunchAgent 只在**用户登录**后运行，不是开机即运行
- 如需开机运行（无需登录），使用 LaunchDaemon（/Library/LaunchDaemons/）
- KeepAlive=true 会让进程永远运行，退出后立即重启
- 日志文件会持续增长，建议定期清理
