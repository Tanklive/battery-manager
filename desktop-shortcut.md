# macOS 桌面快捷方式 (.command 文件)

## 创建方法

macOS 的 `.command` 文件是可执行的 shell 脚本，双击即可在 Terminal 中运行。

```bash
# 创建桌面快捷方式
cat > ~/Desktop/应用名称.command << 'EOF'
#!/bin/bash
cd ~
clear
echo "正在启动..."
python3 ~/.hermes/scripts/some_script.py
EOF

chmod +x ~/Desktop/应用名称.command
```

## 带依赖检查的模板

```bash
#!/bin/bash
cd ~
clear

# 检查依赖
if ! command -v bclm &>/dev/null; then
    echo "❌ 依赖未安装，正在安装..."
    brew install bclm
fi

python3 ~/.hermes/scripts/battery_tui.py
```

## 注意事项

- 文件必须 `chmod +x` 才能双击运行
- 文件名中的 emoji 在 Finder 中可能显示异常，但不影响运行
- .command 文件会在当前 Terminal 窗口执行，不会打开新窗口
- 如果脚本需要交互（如 TUI），会直接在双击打开的 Terminal 中渲染
