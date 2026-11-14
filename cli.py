import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from adb_manager import AdbManager
from diagnostics import PhoneDiagnostics
from optimizer import PhoneOptimizer

console = Console()

def main():
    lang = "ro" if "--ro" in sys.argv else "en"
    ro = (lang == "ro")

    console.print(Panel.fit(
        "[bold cyan]Android Health & Performance Doctor (Universal ADB CLI)[/bold cyan]\n"
        + (
            "[dim]Diagnoză profundă sacadare (UI Jank), blocaje aplicații (ANR), baze de date sistem & compilare ART[/dim]"
            if ro else
            "[dim]Deep diagnostics for UI Jank, App Freezes (ANRs), System Databases & ART Compilation[/dim]"
        ),
        border_style="cyan"
    ))

    adb = AdbManager()
    if not adb.is_available():
        console.print(
            "[bold red][!] ADB nu a fost găsit sau Android Platform Tools nu este accesibil.[/bold red]"
            if ro else "[bold red][!] ADB binary not found. Please install Android Platform Tools.[/bold red]"
        )
        sys.exit(1)

    if "--pair" in sys.argv:
        idx = sys.argv.index("--pair")
        if len(sys.argv) > idx + 2:
            res = adb.pair_wireless(sys.argv[idx + 1], sys.argv[idx + 2], lang=lang)
            console.print(f"[bold {'green' if res.get('success') else 'red'}]{res.get('message')}[/]")
        else:
            console.print("[yellow]Usage: python cli.py --pair PAIRING_IP:PORT 6_DIGIT_CODE[/yellow]")

    if "--connect" in sys.argv:
        idx = sys.argv.index("--connect")
        if len(sys.argv) > idx + 1:
            res = adb.connect_wireless(sys.argv[idx + 1], lang=lang)
            console.print(f"[bold {'green' if res.get('success') else 'red'}]{res.get('message')}[/]")
        else:
            console.print("[yellow]Usage: python cli.py --connect CONNECT_IP:PORT[/yellow]")

    devices = adb.get_devices(lang=lang)
    if not devices:
        if ro:
            console.print("[bold yellow][!] Niciun telefon conectat (USB sau Wireless Wi-Fi).[/bold yellow]")
            console.print("[white]• Prin USB: Conectează cablul USB și activează 'Depanare USB'.[/white]")
            console.print("[white]• Fără cablu (Wi-Fi): Rulează [bold]python main.py[/bold] sau folosește:[/white]")
            console.print("[cyan]  python cli.py --pair IP:PORT COD_6_CIFRE --connect IP:PORT_CONECTARE[/cyan]")
        else:
            console.print("[bold yellow][!] No Android device connected (USB or Wireless Wi-Fi).[/bold yellow]")
            console.print("[white]• Via USB: Connect the USB cable and enable 'USB debugging'.[/white]")
            console.print("[white]• Via Wi-Fi (No Cable): Run [bold]python main.py[/bold] or use:[/white]")
            console.print("[cyan]  python cli.py --pair IP:PORT 6_DIGIT_CODE --connect IP:CONNECT_PORT[/cyan]")
        sys.exit(0)

    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        console.print(
            "[bold yellow][!] Telefonul este conectat dar neautorizat. Deblochează ecranul și apasă pe 'Allow'.[/bold yellow]"
            if ro else "[bold yellow][!] Device is connected but unauthorized. Unlock your phone screen and tap 'Allow'.[/bold yellow]"
        )
        sys.exit(0)

    target = authorized[0]
    console.print(
        f"[bold green][✓] {'Dispozitiv detectat' if ro else 'Detected device'}:[/bold green] {target['model']} [dim]({target['serial']})[/dim]\n"
    )

    diag = PhoneDiagnostics(adb, target["serial"], lang=lang)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(
            description=(
                "Se analizează UI Jank, jurnale ANR, servicii accesibilitate, RAM, temperatură..."
                if ro else "Analyzing UI Jank, ANR logs, accessibility hooks, RAM/ZRAM, and thermals..."
            ),
            total=None
        )
        report = diag.run_full_scan()

    eval_data = report["health_evaluation"]
    dev = report["device"]
    storage = report["storage"]
    memory = report["memory"]
    anrs = report["anrs_and_crashes"]
    thermals = report["thermals_and_cpu"]
    battery = report["battery"]
    ui_fluency = report.get("ui_fluency", {})
    sys_pressure = report.get("system_pressure", {})

    table_title = (
        f"Rezumat Stare {dev.get('brand', '')} {dev.get('model', 'Android')}"
        if ro else f"Health Overview: {dev.get('brand', '')} {dev.get('model', 'Android')}"
    )
    table = Table(title=table_title, show_header=True, header_style="bold magenta")
    table.add_column("Parametru" if ro else "Metric", style="dim")
    table.add_column("Valoare" if ro else "Value")
    table.add_column("Status")

    table.add_row(
        "Scor Sănătate" if ro else "Health Score",
        f"{eval_data['score']}/100",
        f"[{'green' if eval_data['score']>=80 else ('yellow' if eval_data['score']>=60 else 'red')}]{eval_data['verdict']}[/]"
    )
    table.add_row("Android / SoC", f"{dev['model']} (Android {dev['android_version']} • {dev.get('soc', 'SoC')})", "OK")
    table.add_row(
        "Uptime",
        dev["uptime_str"],
        ("[red]Restart recomandat[/red]" if ro else "[red]Reboot recommended[/red]") if dev["needs_reboot"] else "[green]OK[/green]"
    )
    table.add_row(
        "Fluență UI & Animații" if ro else "UI Fluency & Animations",
        f"{ui_fluency.get('peak_refresh_rate', 120)}Hz | {ui_fluency.get('window_animation_scale', 1.0)}x",
        f"Global Jank: {ui_fluency.get('global_jank_percent', 0)}%"
    )
    table.add_row(
        "Hook-uri Accesibilitate" if ro else "Accessibility Hooks",
        f"{len(sys_pressure.get('accessibility_services', []))} active",
        ("[red]Cauză sacadare![/red]" if ro else "[red]Lag cause![/red]") if sys_pressure.get("has_accessibility_hooks") else "[green]Clean[/green]"
    )
    table.add_row(
        "Stocare Internă" if ro else "Internal Storage",
        f"{storage['used_gb']} GB / {storage['total_gb']} GB ({storage['percent_used']}%)",
        f"[{'red' if storage['status']=='critical' else ('yellow' if storage['status']=='warning' else 'green')}]{storage['status'].upper()}[/]"
    )
    table.add_row(
        "RAM",
        f"{memory['used_mb']} MB / {memory['total_mb']} MB ({memory['ram_percent_used']}%)",
        f"[{'red' if memory['status']=='critical' else ('yellow' if memory['status']=='warning' else 'green')}]{memory['status'].upper()}[/]"
    )
    table.add_row(
        "ZRAM (Swap)",
        f"{memory['swap_used_mb']} MB / {memory['swap_total_mb']} MB ({memory['swap_percent_used']}%)",
        f"Mem Stall: {sys_pressure.get('mem_stall_percent', 0)}%"
    )
    table.add_row(
        "Temperatură Baterie" if ro else "Battery Temperature",
        f"{thermals['battery_temp_c']} °C",
        f"[{'red' if thermals['battery_temp_c']>=41 else ('yellow' if thermals['battery_temp_c']>=38.5 else 'green')}]{thermals['thermal_status']}[/]"
    )
    table.add_row(
        "ANR / Crash (24h)",
        f"{anrs['total_anrs']} ANRs, {anrs['total_crashes']} Crashes",
        f"[{'red' if anrs['total_anrs']>0 else 'green'}]{('Probleme detectate' if ro else 'Issues detected') if anrs['total_anrs']>0 else 'Clean'}[/]"
    )
    table.add_row(
        "Baterie" if ro else "Battery",
        f"{battery['level']}% ({battery['health']})",
        f"{'Cicluri' if ro else 'Cycles'}: {battery['cycles']}"
    )

    console.print(table)
    console.print()

    if anrs["top_culprits"]:
        anr_table = Table(
            title="[bold red]Aplicații cu blocaje sau crash-uri (24h)[/bold red]" if ro else "[bold red]Freezing / Crashing Packages (Last 24h)[/bold red]",
            header_style="bold red"
        )
        anr_table.add_column("Pachet" if ro else "Package")
        anr_table.add_column("Incidente" if ro else "Incidents")
        for c in anrs["top_culprits"]:
            anr_table.add_row(c["package"], str(c["count"]))
        console.print(anr_table)
        console.print()

    console.print("[bold yellow]Plan de acțiune și recomandări:[/bold yellow]" if ro else "[bold yellow]Recommended Repair Plan:[/bold yellow]")
    for idx, rec in enumerate(eval_data["recommendations"], 1):
        color = "red" if rec["severity"] == "urgent" else ("yellow" if rec["severity"] == "recomandat" else "cyan")
        console.print(f"[{color}]{idx}. {rec['title']}[/{color}]")
        console.print(f"   [dim]{rec['description']}[/dim]\n")

    if "--fix" in sys.argv:
        console.print("[bold magenta]⚡ Se execută Super-Optimizarea Completă...[/bold magenta]" if ro else "[bold magenta]⚡ Running Complete 1-Click Super-Boost...[/bold magenta]")
        opt = PhoneOptimizer(adb, target["serial"], lang=lang)
        culprits = [c["package"] for c in anrs.get("top_culprits", [])]
        res = opt.run_deep_boost_all(culprit_packages=culprits)
        console.print(f"[bold green][✓] {res['message']}[/bold green]")
    else:
        if ro:
            console.print("[dim]Pentru a aplica automat toate reparațiile din CLI: [bold]python cli.py --fix --ro[/bold][/dim]")
            console.print("[dim]Pentru interfața grafică web completă: [bold]python main.py[/bold][/dim]")
        else:
            console.print("[dim]To automatically apply all repairs from CLI: [bold]python cli.py --fix[/bold] (add [bold]--ro[/bold] for Romanian)[/dim]")
            console.print("[dim]To launch the full interactive Web Dashboard: [bold]python main.py[/bold][/dim]")

if __name__ == "__main__":
    main()
