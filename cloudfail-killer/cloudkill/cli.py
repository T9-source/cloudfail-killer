"""
CloudFail-Killer CLI Entry Point

Multi-profile CLI tool for discovering origin IPs behind Cloudflare.
Supports IPv6, stealth mode, batch scanning, and multiple output formats.

Usage:
    cloudkill scan example.com --profile pentester --ipv6
    cloudkill scan example.com --profile bugbounty --output results.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cloudkill import __version__
from cloudkill.config import Config, OutputFormat, ScanProfile, StealthMode, WebhookConfig
from cloudkill.core.models import ScanReport
from cloudkill.core.runner import SourceRunner

app = typer.Typer(
    name="cloudkill",
    help="CloudFail-Killer: Discover origin IPs behind Cloudflare",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


LEGAL_BANNER = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   ██████╗ ███████╗ ██████╗     ██████╗ ██████╗  █████╗ ███╗   ██╗████████╗ ║
║  ██╔════╝ ██╔══╝██╔═══██╗    ██╔══██╗██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝ ║
║  ██║  ███╗█████╗  ██║   ██║    ██████╔╝██████╔╝███████║██╔██╗ ██║   ██║    ║
║  ██║   ██║██╔══╝  ██║   ██║    ██╔═══╝ ██╔══██╗██╔══██║██╚██╗██║   ██║    ║
║  ╚██████╔╝███████╗╚██████╔╝    ██║     ██║  ██║██║  ██║██║ ╚████║   ██║    ║
║   ╚═════╝ ╚══════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ║
║                                                                            ║
║         [bold cyan]ORIGIN IP DISCOVERY TOOL v{version}[/]                    ║
║                   [dim]Developed by smart-unknown[/dim]                     ║
║                                                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  [bold yellow]DISCLAIMER:[/] This tool is intended for [bold]AUTHORIZED[/]             ║
║  security testing and educational purposes ONLY.                              ║
║                                                                            ║
║  Unauthorized use of this tool against systems you do not own or have       ║
║  explicit permission to test is [bold red]ILLEGAL[/].                           ║
║                                                                            ║
║  The developers assume [bold]NO LIABILITY[/] for misuse of this tool.             ║
║  By proceeding, you confirm you have proper authorization.                  ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
""".format(version=__version__)


def show_banner() -> None:
    """Display the legal disclaimer banner."""
    console.print(
        Panel(
            Text.from_ansi(LEGAL_BANNER),
            border_style="bold red",
            padding=(0, 1),
        )
    )
    console.print()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
) -> None:
    """CloudKill: Advanced origin IP discovery behind Cloudflare."""
    if version:
        console.print(f"cloudkill v{__version__}")
        raise typer.Exit()


@app.command()
def scan(
    domain: str = typer.Argument(
        ...,
        help="Target domain (e.g., example.com)",
    ),
    profile: str = typer.Option(
        "researcher",
        "--profile", "-p",
        help="Scan profile: researcher, pentester, bugbounty, enterprise, automation",
    ),
    ipv6: bool = typer.Option(
        False,
        "--ipv6", "-6",
        help="Prefer IPv6 resolution",
    ),
    active: bool = typer.Option(
        False,
        "--active",
        help="Enable light active probing (HTTP probes + port check)",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (extension determines format: .json, .csv, .txt, .md)",
    ),
    threads: int = typer.Option(
        20,
        "--threads", "-t",
        help="Number of concurrent threads (1-200)",
    ),
    stealth: bool = typer.Option(
        False,
        "--stealth",
        help="Enable stealth mode (random delays + UA rotation)",
    ),
    fmt: str = typer.Option(
        "json",
        "--format", "-f",
        help="Output format: json, csv, txt, md, pdf, nuclei",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed output including low-confidence results",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Suppress all output except final results",
    ),
    domains: Optional[str] = typer.Option(
        None,
        "--domains",
        help="File with list of domains to scan (batch mode)",
    ),
    webhook: Optional[str] = typer.Option(
        None,
        "--webhook",
        help="Generic webhook URL for notifications",
    ),
    slack_webhook: Optional[str] = typer.Option(
        None,
        "--slack-webhook",
        help="Slack webhook URL for notifications",
    ),
    discord_webhook: Optional[str] = typer.Option(
        None,
        "--discord-webhook",
        help="Discord webhook URL for notifications",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Disable SQLite result caching",
    ),
    no_enrich: bool = typer.Option(
        False,
        "--no-enrich",
        help="Disable enrichment pipeline (SSL, ASN, scoring)",
    ),
    no_banner: bool = typer.Option(
        False,
        "--no-banner",
        help="Skip the legal disclaimer banner",
    ),
) -> None:
    """Scan a domain to discover origin IPs behind Cloudflare."""
    # Show legal banner unless suppressed
    if not no_banner:
        show_banner()
        console.print()

    # Validate profile
    valid_profiles = [p.value for p in ScanProfile]
    if profile not in valid_profiles:
        console.print(f"[bold red]Error:[/] Invalid profile '{profile}'")
        console.print(f"Valid profiles: {', '.join(valid_profiles)}")
        raise typer.Exit(1)

    # Build configuration
    config_overrides = {
        "ipv6_preference": ipv6,
        "active": active,
        "threads": threads,
        "output": output,
        "verbose": verbose,
        "quiet": quiet,
    }

    # Display enrichment status
    if not no_enrich:
        console.print(f"[bold]Enrichment:[/] SSL + ASN + Scoring + FP Filter")
    else:
        console.print("[bold]Enrichment:[/] [yellow]disabled[/yellow]")

    if stealth:
        config_overrides["stealth_mode"] = StealthMode.STEALTH

    if fmt:
        try:
            config_overrides["output_format"] = OutputFormat(fmt)
        except ValueError:
            console.print(f"[bold red]Error:[/] Invalid format '{fmt}'")
            console.print(f"Valid formats: {', '.join(f.value for f in OutputFormat)}")
            raise typer.Exit(1)

    if webhook:
        config_overrides["webhook"] = WebhookConfig(url=webhook, slack_url=slack_webhook, discord_url=discord_webhook)
    elif slack_webhook or discord_webhook:
        config_overrides["webhook"] = WebhookConfig(url=webhook, slack_url=slack_webhook, discord_url=discord_webhook)

    try:
        scan_config = Config.from_profile(profile, **config_overrides)
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/] {e}")
        raise typer.Exit(1)

    # Display scan configuration
    console.print(f"[bold cyan]CloudKill[/bold cyan] v{__version__}")
    console.print(f"[bold]Target:[/] {domain}")
    console.print(f"[bold]Profile:[/] {profile}")
    console.print(f"[bold]IPv6:[/] {'enabled' if ipv6 else 'disabled'}")
    console.print(f"[bold]Active:[/] {'enabled' if active else 'disabled'}")
    console.print(f"[bold]Stealth:[/] {scan_config.stealth_mode.value}")
    console.print(f"[bold]Threads:[/] {scan_config.effective_threads}")
    if output:
        console.print(f"[bold]Output:[/] {output}")
    console.print()

    # Run the scan asynchronously
    try:
        report = asyncio.run(_run_scan(domain, scan_config, enable_enrichment=not no_enrich))
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted by user.[/yellow]")
        raise typer.Exit(130)

    # Save output if requested
    if output and report.results:
        _save_report(report, output, fmt)


async def _run_scan(domain: str, config: Config, enable_enrichment: bool = True) -> ScanReport:
    """Execute the scan using the SourceRunner."""
    from cloudkill.core.engine import AsyncEngine
    from cloudkill.core.runner import SourceRunner
    from cloudkill.sources import get_enabled_sources

    # Initialize engine first (sources may need it for HTTP requests)
    engine = AsyncEngine(config=config)
    await engine.start()

    # Get all enabled and configured source plugins
    sources = get_enabled_sources(config=config, engine=engine)

    if not sources:
        console.print("[yellow]No enabled data source plugins found.[/yellow]")
        console.print("[dim]Most sources work without API keys. Check --help for details.[/dim]")
        report = ScanReport(domain=domain, profile=config.profile.value)
        report.errors.append("No enabled sources")
        report.finalize()
        await engine.stop()
        return report

    # Show which sources will be used
    source_names = [s.name for s in sources]
    configured_count = sum(1 for s in sources if s.is_configured())
    console.print(f"  [bold]Sources enabled:[/] {len(sources)} ({configured_count} configured)")
    if config.verbose:
        for s in sources:
                status = "[green]OK[/green]" if s.is_configured() else "[yellow]no key[/yellow]"
                console.print(f"    {s.name:<20} {status}")
    console.print()

    # Run the scan
    runner = SourceRunner(config=config, engine=engine, enable_enrichment=enable_enrichment)
    try:
        report = await runner.run(domain, sources)
        return report
    finally:
        await engine.stop()


def _save_report(report: ScanReport, output_path: str, fmt: str) -> None:
    """Save scan report to file using exporters."""
    path = Path(output_path)

    try:
        if fmt == "json" or path.suffix == ".json":
            from cloudkill.exporters.json_export import export_json
            saved = export_json(report, path)
            console.print(f"\n[green]Results saved to [bold]{saved}[/bold][/green]")

        elif fmt == "csv" or path.suffix == ".csv":
            from cloudkill.exporters.csv_export import export_csv
            saved = export_csv(report, path)
            console.print(f"\n[green]Results saved to [bold]{saved}[/bold][/green]")

        elif fmt == "txt" or path.suffix == ".txt":
            from cloudkill.exporters.csv_export import export_ip_list
            saved = export_ip_list(report, path)
            console.print(f"\n[green]IP list saved to [bold]{saved}[/bold][/green]")

        elif fmt == "md" or path.suffix == ".md":
            from cloudkill.exporters.markdown_export import export_markdown
            saved = export_markdown(report, path)
            console.print(f"\n[green]Markdown report saved to [bold]{saved}[/bold][/green]")

        elif fmt == "pdf" or path.suffix == ".pdf":
            from cloudkill.exporters.pdf_export import export_pdf
            saved = export_pdf(report, path)
            console.print(f"\n[green]PDF report saved to [bold]{saved}[/bold][/green]")

        elif fmt == "nuclei" or path.suffix == ".yaml" or path.suffix == ".yml":
            from cloudkill.exporters.nuclei import export_nuclei_template
            saved = export_nuclei_template(report, path)
            console.print(f"\n[green]Nuclei template saved to [bold]{saved}[/bold][/green]")

        else:
            # Default: JSON
            from cloudkill.exporters.json_export import export_json
            saved = export_json(report, path)
            console.print(f"\n[green]Results saved to [bold]{saved}[/bold][/green]")

    except Exception as e:
        console.print(f"[bold red]Error saving results:[/] {e}")


@app.command()
def profiles() -> None:
    """List available scan profiles with descriptions."""
    console.print("[bold]Available Scan Profiles:[/]\n")
    profiles_data = [
        ("researcher", "Comprehensive data collection with high accuracy", "JSON + CSV", "Multi-source, historical, smart scoring"),
        ("pentester", "Fast actionable results", "CLI Table + Nuclei", "Active probing, port check, Nuclei export"),
        ("bugbounty", "Discover hidden origins", "Markdown + Slack", "JS Recon, GitHub Dorking, Wayback leaks"),
        ("enterprise", "Infrastructure monitoring", "Dashboard + PDF", "Scheduled scans, alerting, SQLite history"),
        ("automation", "CI/CD integration", "JSON + Stdout", "API mode, Docker, clean exit codes"),
    ]
    for name, goal, output, features in profiles_data:
        console.print(f"  [bold cyan]{name}[/]")
        console.print(f"    Goal:     {goal}")
        console.print(f"    Output:   {output}")
        console.print(f"    Features: {features}")
        console.print()


@app.command()
def sources(verbose_list: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed source information"
)) -> None:
    """List available data sources and their status."""
    from cloudkill.sources import get_source_info

    source_info = get_source_info()

    console.print("[bold]Available Data Sources:[/]")
    console.print(f"  Total registered: {len(source_info)}\n")

    # Static priority mapping for display
    priority_map = {
        "favicon_hash": "CRITICAL",
        "otx": "HIGH",
        "wayback": "HIGH",
        "spf_dkim": "HIGH",
        "crtsh": "HIGH",
        "urlscan": "MEDIUM",
        "anubisdb": "MEDIUM",
        "github_dork": "MEDIUM",
        "hackertarget": "LOW",
        "dnsdumpster": "LOW",
        "whoisxml": "LOW",
        "certspotter": "LOW",
        "acme_check": "REFERENCE",
    }

    if verbose_list:
        for info in source_info:
            name = info["name"]
            priority = priority_map.get(name, "MEDIUM")
            api_req = info["requires_api_key"]
            ipv6 = info["supports_ipv6"]
            enabled = info["default_enabled"]
            console.print(f"  [bold cyan]{name}[/]")
            console.print(f"    Description:     {info['description']}")
            console.print(f"    Priority:        {priority}")
            console.print(f"    API Key:         {'Required' if api_req == 'True' else 'Not required'}")
            console.print(f"    IPv6:            {'Yes' if ipv6 == 'True' else 'No'}")
            console.print(f"    Default Enabled: {'Yes' if enabled == 'True' else 'No'}")
            console.print()
    else:
        console.print(f"  {'Source':<20} {'Priority':<12} {'API Key':<12} {'IPv6':<6} {'Enabled':<8}")
        console.print(f"  {'─'*20} {'─'*12} {'─'*12} {'─'*6} {'─'*8}")
        for info in source_info:
            name = info["name"]
            priority = priority_map.get(name, "MEDIUM")
            console.print(
                f"  {name:<20} {priority:<12} "
                f"{'Yes' if info['requires_api_key'] == 'True' else 'No':<12} "
                f"{'Yes' if info['supports_ipv6'] == 'True' else 'No':<6} "
                f"{'Yes' if info['default_enabled'] == 'True' else 'No':<8}"
            )


if __name__ == "__main__":
    app()
