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
    console.print(Panel.fit(
        "[bold cyan]Android Health & Performance Doctor (Universal ADB CLI)[/bold cyan]\n"
        "[dim]Diagnoză profundă sacadare (UI Jank), blocaje aplicații (ANR), baze de date sistem & compilare ART[/dim]",
        border_style="cyan"
    ))

    adb = AdbManager()
    if not adb.is_available():
        console.print("[bold red][!] ADB nu a fost găsit sau Android Platform Tools nu este accesibil.[/bold red]")
        sys.exit(1)

    if "--pair" in sys.argv:
        idx = sys.argv.index("--pair")
        if len(sys.argv) > idx + 2:
            res = adb.pair_wireless(sys.argv[idx + 1], sys.argv[idx + 2])
            console.print(f"[bold {'green' if res.get('success') else 'red'}]{res.get('message')}[/]")
        else:
            console.print("[yellow]Utilizare: python cli.py --pair IP:PORT_ASOCIERE COD_6_CIFRE[/yellow]")

    if "--connect" in sys.argv:
        idx = sys.argv.index("--connect")
        if len(sys.argv) > idx + 1:
            res = adb.connect_wireless(sys.argv[idx + 1])
            console.print(f"[bold {'green' if res.get('success') else 'red'}]{res.get('message')}[/]")
        else:
            console.print("[yellow]Utilizare: python cli.py --connect IP:PORT_CONECTARE[/yellow]")

    devices = adb.get_devices()
    if not devices:
        console.print("[bold yellow][!] Niciun telefon conectat (USB sau Wireless Wi-Fi).[/bold yellow]")
        console.print("[white]• Prin USB: Conectează cablul USB și activează 'Depanare USB'.[/white]")
        console.print("[white]• Fără cablu (Wi-Fi): Rulează [bold]python main.py[/bold] și apasă pe '📶 Conectare Wireless (Fără USB)' sau folosește:[/white]")
        console.print("[cyan]  python cli.py --pair IP:PORT COD_6_CIFRE --connect IP:PORT_CONECTARE[/cyan]")
        sys.exit(0)

    authorized = [d for d in devices if d["state"] == "device"]
    if not authorized:
        console.print("[bold yellow][!] Telefonul este conectat dar neautorizat.[/bold yellow]")
        console.print("[white]Deblochează ecranul Pixel-ului și apasă pe 'Permiteți' (Allow USB debugging).[/white]")
        sys.exit(0)

    target = authorized[0]
    console.print(f"[bold green][✓] Dispozitiv detectat:[/bold green] {target['model']} [dim]({target['serial']})[/dim]\n")

    diag = PhoneDiagnostics(adb, target["serial"])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Se analizează UI Jank, jurnale ANR, servicii accesibilitate, RAM, temperatură...", total=None)
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

    # 1. Overview Table
    table = Table(title=f"Rezumat Stare {dev.get('brand', '')} {dev.get('model', 'Android')}", show_header=True, header_style="bold magenta")
    table.add_column("Parametru", style="dim")
    table.add_column("Valoare")
    table.add_column("Status")

    table.add_row("Scor Sănătate", f"{eval_data['score']}/100", f"[{'green' if eval_data['score']>=80 else ('yellow' if eval_data['score']>=60 else 'red')}]{eval_data['verdict']}[/]")
    table.add_row("Versiune Android", f"{dev['model']} (Android {dev['android_version']})", "OK")
    table.add_row("Uptime (fără restart)", dev["uptime_str"], "[red]Restart recomandat[/red]" if dev["needs_reboot"] else "[green]OK[/green]")
    table.add_row("Fluență Ecran & Animații", f"{ui_fluency.get('peak_refresh_rate', 120)}Hz | Animații {ui_fluency.get('window_animation_scale', 1.0)}x", f"Jank Global: {ui_fluency.get('global_jank_percent', 0)}%")
    table.add_row("Hook-uri Accesibilitate", f"{len(sys_pressure.get('accessibility_services', []))} active", "[red]Cauză de sacadare![/red]" if sys_pressure.get("has_accessibility_hooks") else "[green]Curat[/green]")
    table.add_row("Stocare Internă", f"{storage['used_gb']} GB / {storage['total_gb']} GB ({storage['percent_used']}%)", f"[{'red' if storage['status']=='critical' else ('yellow' if storage['status']=='warning' else 'green')}]{storage['status'].upper()}[/]")
    table.add_row("Memorie RAM", f"{memory['used_mb']} MB / {memory['total_mb']} MB ({memory['ram_percent_used']}%)", f"[{'red' if memory['status']=='critical' else ('yellow' if memory['status']=='warning' else 'green')}]{memory['status'].upper()}[/]")
    table.add_row("ZRAM (Swap)", f"{memory['swap_used_mb']} MB / {memory['swap_total_mb']} MB ({memory['swap_percent_used']}%)", f"Mem Stall: {sys_pressure.get('mem_stall_percent', 0)}%")
    table.add_row("Temperatură Baterie", f"{thermals['battery_temp_c']} °C", f"[{'red' if thermals['battery_temp_c']>=41 else ('yellow' if thermals['battery_temp_c']>=38.5 else 'green')}]{thermals['thermal_status']}[/]")
    table.add_row("Evenimente ANR / Crash", f"{anrs['total_anrs']} ANRs, {anrs['total_crashes']} Crash-uri", f"[{'red' if anrs['total_anrs']>0 else 'green'}]{'Probleme detectate' if anrs['total_anrs']>0 else 'Curat'}[/]")
    table.add_row("Nivel Baterie", f"{battery['level']}% ({battery['health']})", f"Cicluri: {battery['cycles']}")

    console.print(table)
    console.print()

    # 2. ANR Culprits
    if anrs["top_culprits"]:
        anr_table = Table(title="[bold red]Aplicații cu blocaje sau crash-uri frecvente[/bold red]", header_style="bold red")
        anr_table.add_column("Pachet Aplicație")
        anr_table.add_column("Incidente (ANR / Crash)")
        for c in anrs["top_culprits"]:
            anr_table.add_row(c["package"], str(c["count"]))
        console.print(anr_table)
        console.print()

    # 3. Recommendations
    console.print("[bold yellow]Plan de acțiune și recomandări:[/bold yellow]")
    for idx, rec in enumerate(eval_data["recommendations"], 1):
        color = "red" if rec["severity"] == "urgent" else ("yellow" if rec["severity"] == "recomandat" else "cyan")
        console.print(f"[{color}]{idx}. {rec['title']}[/{color}]")
        console.print(f"   [dim]{rec['description']}[/dim]\n")

    if "--fix" in sys.argv:
        console.print("[bold magenta]⚡ Se execută Super-Optimizarea Completă...[/bold magenta]")
        opt = PhoneOptimizer(adb, target["serial"])
        culprits = [c["package"] for c in anrs.get("top_culprits", [])]
        res = opt.run_deep_boost_all(culprit_packages=culprits)
        console.print(f"[bold green][✓] {res['message']}[/bold green]")
    else:
        console.print("[dim]Pentru a aplica automat toate reparațiile din CLI, rulează: [bold]python cli.py --fix[/bold][/dim]")
        console.print("[dim]Pentru interfața grafică web completă, rulează: [bold]python main.py[/bold][/dim]")

if __name__ == "__main__":
    main()
