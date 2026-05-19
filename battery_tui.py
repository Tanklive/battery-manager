#!/usr/bin/env python3
"""🔋 电池管理 - TUI v3 带配置面板"""

import subprocess, re, json, os, sys
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer, Static, Button, RichLog
from textual.reactive import reactive
from textual import work
from rich.table import Table
from rich.console import Console

CONFIG_PATH = os.path.expanduser("~/.hermes/battery_config.json")
STRATEGIES = {
    "conservative": {"charge_limit": 60, "desc": "保守"},
    "balanced":     {"charge_limit": 80, "desc": "平衡"},
    "performance":  {"charge_limit": 90, "desc": "性能"},
    "full":         {"charge_limit": 100, "desc": "满电"},
}

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"strategy": "balanced", "charge_limit": 80, "upper_limit": 80,
            "lower_limit": 20, "limit_enabled": True, "check_interval": 120,
            "temp_threshold_c": 35}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def read_battery():
    info = {}
    raw = run_cmd("bclm read")
    info["charge_limit"] = int(raw) if raw.isdigit() else None
    pmset = run_cmd("pmset -g batt")
    info["power_source"] = "AC" if "AC" in pmset else "Battery"
    info["is_charging"] = "charging" in pmset.lower() and "not charging" not in pmset.lower()
    m = re.search(r"(\d+)%;\s*(\w+)", pmset)
    if m:
        info["percentage"] = int(m.group(1))
        info["state"] = m.group(2)
    m = re.search(r"(\d+:\d+)\s*remaining", pmset)
    if m:
        info["remaining"] = m.group(1)
    ioreg = run_cmd("ioreg -l -w0")
    for key in ["DesignCapacity", "MaxCapacity", "CycleCount", "Temperature"]:
        m = re.search(rf'"{key}"\s*=\s*(\d+)', ioreg)
        if m:
            info[key.lower()] = int(m.group(1))
    if "temperature" in info:
        info["temperature_c"] = round(info["temperature"] / 100.0, 1)
    if "designcapacity" in info and "maxcapacity" in info:
        info["health_pct"] = round(info["maxcapacity"] / info["designcapacity"] * 100, 1)
    sp = run_cmd("system_profiler SPPowerDataType | grep 'Condition:'")
    m = re.search(r"Condition:\s*(\w+)", sp)
    if m:
        info["condition"] = m.group(1)
    return info

def get_daemon_status():
    pid_file = os.path.expanduser("~/.hermes/scripts/battery_daemon.pid")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        try:
            os.kill(int(pid), 0)
            return True, pid
        except (ProcessLookupError, ValueError):
            pass
    return False, None


class BatteryTUI(App):
    CSS = """
    Screen { layout: vertical; }
    #status_panel { height: auto; margin: 0 1; }
    #mid_row { layout: horizontal; height: auto; margin: 0 1; }
    #health_panel { width: 1fr; }
    #control_panel { width: 1fr; }
    #config_panel { width: 1fr; }
    #log_panel { height: 1fr; margin: 0 1; }
    Button { margin: 0 0 0 0; min-width: 8; }
    Horizontal { height: auto; layout: horizontal; }
    Horizontal > Button { width: 1fr; }
    """

    TITLE = "🔋 电池管理"
    battery_data = reactive(dict, init=False)
    config = reactive(dict, init=False)

    def compose(self):
        self.config = load_config()
        self.battery_data = read_battery()
        yield Header()
        with Container(id="status_panel"):
            yield Static(self._render_status(), id="status_display")
        with Container(id="mid_row"):
            with Container(id="health_panel"):
                yield Static(self._render_health(), id="health_display")
            with Container(id="control_panel"):
                yield Static(self._render_control(), id="control_display")
                with Horizontal():
                    yield Button("➖10", id="btn_down10")
                    yield Button("➖5", id="btn_down5")
                    yield Button("➕5", id="btn_up5")
                    yield Button("➕10", id="btn_up10")
                with Horizontal():
                    yield Button("📋写入", id="btn_apply", variant="primary")
                    yield Button("💾持久化", id="btn_persist", variant="success")
                with Horizontal():
                    yield Button("60%", id="strat_conservative")
                    yield Button("80%", id="strat_balanced", variant="primary")
                with Horizontal():
                    yield Button("90%", id="strat_performance")
                    yield Button("100%", id="strat_full", variant="warning")
            with Container(id="config_panel"):
                yield Static(self._render_config(), id="config_display")
                with Horizontal():
                    yield Button("上限➖5", id="cfg_upper_down")
                    yield Button("上限➕5", id="cfg_upper_up")
                with Horizontal():
                    yield Button("下限➖5", id="cfg_lower_down")
                    yield Button("下限➕5", id="cfg_lower_up")
                with Horizontal():
                    yield Button("⏱️➖60s", id="cfg_interval_down")
                    yield Button("⏱️➕60s", id="cfg_interval_up")
                with Horizontal():
                    yield Button("🔄刷新", id="btn_refresh")
                    yield Button("🚀守护", id="btn_daemon")
        with Container(id="log_panel"):
            yield RichLog(id="log", highlight=True, markup=True)
            yield Static("[dim]配置: 上下限→守护进程 | 写入/持久化→SMC芯片[/dim]")
        yield Footer()

    def _render_status(self):
        d = self.battery_data
        cfg = self.config
        pct = d.get("percentage", "?")
        state = d.get("state", "?")
        src = d.get("power_source", "?")
        limit = d.get("charge_limit", "?")
        temp = d.get("temperature_c", "?")
        rem = d.get("remaining", "--:--")
        icon = "⚡" if d.get("is_charging") else ("🔌" if src == "AC" else "🔋")
        bar = f"[{'█'*(pct//5)}{'░'*(20-pct//5)}]" if isinstance(pct, int) else "[░░░░░░░░░░░░░░░░░░░░]"
        tc = "green" if isinstance(temp,(int,float)) and temp<=30 else ("yellow" if isinstance(temp,(int,float)) and temp<=35 else "red")
        return f" {icon} {bar} {pct}% {state} {rem} | 上限:{limit}% 策略:{cfg.get('strategy','?')} {src} [ {tc}]{temp}°C[/{tc}]"

    def _render_health(self):
        d = self.battery_data
        h = d.get("health_pct", "?")
        hc = "green" if isinstance(h,(int,float)) and h>=90 else ("yellow" if isinstance(h,(int,float)) and h>=80 else "red")
        return (
            f"[bold]📊 健康[/bold] {d.get('condition','?')}\n"
            f" 健康度:[{hc}]{h}%[/{hc}] 循环:{d.get('cyclecount','?')}\n"
            f" 容量:{d.get('maxcapacity','?')}/{d.get('designcapacity','?')}mAh\n"
            f" 电压:{d.get('cell_voltage_avg','?')}mV"
        )

    def _render_control(self):
        d = self.battery_data
        cfg = self.config
        limit = d.get("charge_limit", 0) or 0
        target = cfg.get("charge_limit", cfg.get("upper_limit", 80))
        pct = d.get("percentage", 0) or 0
        if limit == target:
            s = "[green]✅已生效[/green]"
        else:
            s = f"[yellow]SMC={limit}%→{target}%[/yellow]"
        note = f"{'停止充电' if pct>=target else f'充电到{target}%停止'}"
        return f"[bold]🎛️ 控制[/bold] {s}\n 电量{pct}% {note}"

    def _render_config(self):
        cfg = self.config
        upper = cfg.get("upper_limit", 90)
        lower = cfg.get("lower_limit", 20)
        interval = cfg.get("check_interval", 120)
        running, pid = get_daemon_status()
        dm = "运行中" if running else "未运行"
        return (
            f"[bold]⚙️ 配置[/bold] 守护:{dm}\n"
            f" 上限:{upper}% 下限:{lower}%\n"
            f" 间隔:{interval}s 温度:{cfg.get('temp_threshold_c',35)}°C"
        )

    def on_mount(self):
        self.set_interval(30, self.auto_refresh)

    def auto_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        self.battery_data = read_battery()
        self.config = load_config()
        self.query_one("#status_display").update(self._render_status())
        self.query_one("#health_display").update(self._render_health())
        self.query_one("#control_display").update(self._render_control())
        self.query_one("#config_display").update(self._render_config())

    def log_msg(self, msg):
        self.query_one("#log").write(msg)

    def on_button_pressed(self, event):
        btn = event.button.id
        cfg = self.config
        current = cfg.get("charge_limit", cfg.get("upper_limit", 80))

        # ── SMC 上限调节 ──
        if btn == "btn_down10": self._set_upper(max(20, current - 10))
        elif btn == "btn_down5": self._set_upper(max(20, current - 5))
        elif btn == "btn_up5": self._set_upper(min(100, current + 5))
        elif btn == "btn_up10": self._set_upper(min(100, current + 10))

        # ── 写入/持久化 ──
        elif btn == "btn_apply":
            target = cfg.get("upper_limit", 90)
            self.log_msg(f"[yellow]📋 写入SMC: {target}%[/yellow]")
            self._run_sudo(f"sudo bclm write {target}", f"✅ SMC={target}%")
        elif btn == "btn_persist":
            self.log_msg("[green]💾 持久化...[/green]")
            self._run_sudo("sudo bclm persist", "✅ 持久化成功")

        # ── 策略 ──
        elif btn.startswith("strat_"):
            s = btn.replace("strat_", "")
            if s in STRATEGIES:
                cfg["strategy"] = s
                cfg["charge_limit"] = STRATEGIES[s]["charge_limit"]
                cfg["upper_limit"] = STRATEGIES[s]["charge_limit"]
                save_config(cfg)
                self.config = cfg
                self.log_msg(f"[cyan]🎛️ {STRATEGIES[s]['desc']} → {cfg['upper_limit']}%[/cyan]")
                self.refresh_data()

        # ── 配置: 上限 ──
        elif btn == "cfg_upper_down":
            new = max(20, cfg.get("upper_limit", 90) - 5)
            cfg["upper_limit"] = new
            cfg["charge_limit"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]上限 → {new}%[/dim]")
            self.refresh_data()
        elif btn == "cfg_upper_up":
            new = min(100, cfg.get("upper_limit", 90) + 5)
            cfg["upper_limit"] = new
            cfg["charge_limit"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]上限 → {new}%[/dim]")
            self.refresh_data()

        # ── 配置: 下限 ──
        elif btn == "cfg_lower_down":
            new = max(0, cfg.get("lower_limit", 20) - 5)
            cfg["lower_limit"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]下限 → {new}%[/dim]")
            self.refresh_data()
        elif btn == "cfg_lower_up":
            new = min(80, cfg.get("lower_limit", 20) + 5)
            cfg["lower_limit"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]下限 → {new}%[/dim]")
            self.refresh_data()

        # ── 配置: 间隔 ──
        elif btn == "cfg_interval_down":
            new = max(30, cfg.get("check_interval", 120) - 60)
            cfg["check_interval"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]间隔 → {new}s[/dim]")
            self.refresh_data()
        elif btn == "cfg_interval_up":
            new = min(600, cfg.get("check_interval", 120) + 60)
            cfg["check_interval"] = new
            save_config(cfg)
            self.config = cfg
            self.log_msg(f"[dim]间隔 → {new}s[/dim]")
            self.refresh_data()

        # ── 刷新 ──
        elif btn == "btn_refresh":
            self.refresh_data()
            self.log_msg("[green]✅ 已刷新[/green]")

        # ── 守护进程 ──
        elif btn == "btn_daemon":
            running, pid = get_daemon_status()
            if running:
                self.log_msg("[yellow]🚀 守护进程已在运行[/yellow]")
            else:
                self.log_msg("[green]🚀 启动守护进程...[/green]")
                self._start_daemon()

    def _set_upper(self, limit):
        cfg = self.config
        for name, s in STRATEGIES.items():
            if s["charge_limit"] == limit:
                cfg["strategy"] = name
                break
        else:
            cfg["strategy"] = "custom"
        cfg["charge_limit"] = limit
        cfg["upper_limit"] = limit
        save_config(cfg)
        self.config = cfg
        self.log_msg(f"[dim]目标上限 → {limit}%[/dim]")
        self.refresh_data()

    @work(exclusive=True, thread=True)
    def _run_sudo(self, cmd, ok_msg):
        script = (
            'tell application "Terminal" to activate\n'
            'tell application "Terminal" to do script '
            f'"{cmd} && echo \\"{ok_msg}\\" || echo \\"❌ 失败\\""\n'
        )
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        self.log_msg(f"[dim]执行: {cmd}[/dim]")

    @work(exclusive=True, thread=True)
    def _start_daemon(self):
        script = (
            'tell application "Terminal" to activate\n'
            'tell application "Terminal" to do script '
            '"python3 ~/.hermes/scripts/battery_daemon.py --daemon"\n'
        )
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        self.log_msg("[dim]已在Terminal启动守护进程[/dim]")

    def key_q(self):
        self.exit()


def headless_mode():
    info = read_battery()
    cfg = load_config()
    console = Console()
    table = Table(title="🔋 电池状态", show_header=True, header_style="bold cyan")
    table.add_column("项目", style="bold")
    table.add_column("值")
    table.add_row("电量", f"{info.get('percentage', '?')}%")
    table.add_row("充电上限", f"{info.get('charge_limit', '?')}%")
    table.add_row("上限", f"{cfg.get('upper_limit', '?')}%")
    table.add_row("下限", f"{cfg.get('lower_limit', '?')}%")
    table.add_row("健康度", f"{info.get('health_pct', '?')}%")
    table.add_row("容量", f"{info.get('maxcapacity', '?')}/{info.get('designcapacity', '?')} mAh")
    table.add_row("温度", f"{info.get('temperature_c', '?')}°C")
    console.print(table)

if __name__ == "__main__":
    if "--headless" in sys.argv:
        headless_mode()
    else:
        BatteryTUI().run()
