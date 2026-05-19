# bclm 免密 sudo 配置

## 背景

bclm write 和 bclm persist 需要 sudo 权限（写入 SMC 芯片）。每次操作都输密码体验很差。

## 配置方法

```bash
# 替换 <用户名> 为实际用户名
sudo bash -c 'echo "yangzs ALL=(root) NOPASSWD: /usr/local/bin/bclm" > /etc/sudoers.d/bclm && chmod 440 /etc/sudoers.d/bclm'
```

只需输入一次密码。

## 验证

```bash
sudo -n bclm read    # -n = non-interactive，无需密码
# 返回数字 = 成功
# 报错 password required = 配置未生效
```

## 原理

- `/etc/sudoers.d/bclm` 是独立的 sudoers 配置文件
- `440` 权限 = 只读，安全
- 仅允许 bclm 命令免密，其他 sudo 操作仍需密码
- `sudo -n` 表示非交互模式，不弹密码提示

## Agent 使用

配置免密后，agent 可直接执行：
```bash
sudo -n bclm write 80
sudo -n bclm persist
```
无需打开新终端窗口，无需用户手动输入密码。
