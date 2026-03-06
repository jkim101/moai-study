"""CLI entry point for the Knowledge Graph tool."""

from __future__ import annotations

import re
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from claude_conversation_kg.config import Settings
from claude_conversation_kg.extractor.client import ExtractionClient
from claude_conversation_kg.extractor.processor import BatchProcessor
from claude_conversation_kg.graph.connection import KuzuConnection
from claude_conversation_kg.graph.queries import QueryRunner
from claude_conversation_kg.graph.schema import initialize_schema
from claude_conversation_kg.graph.store import GraphStore
from claude_conversation_kg.nlq import NaturalLanguageQuerier
from claude_conversation_kg.pipeline import IngestionPipeline
from claude_conversation_kg.visualization.renderer import GraphRenderer

app = typer.Typer(name="kg", help="Claude Conversation Knowledge Graph CLI")
console = Console()


def _print_usage_table(usage: object, title: str = "API Usage") -> None:
    """Print a token usage summary table (shared by ingest and ask commands)."""
    if not usage or getattr(usage, "api_calls", 0) == 0:
        return
    table = Table(title=title)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("API Calls", str(usage.api_calls))
    table.add_row("Input Tokens", f"{usage.input_tokens:,}")
    table.add_row("Output Tokens", f"{usage.output_tokens:,}")
    if getattr(usage, "cache_creation_input_tokens", 0):
        table.add_row("Cache Write Tokens", f"{usage.cache_creation_input_tokens:,}")
    if getattr(usage, "cache_read_input_tokens", 0):
        table.add_row("Cache Read Tokens", f"{usage.cache_read_input_tokens:,}")
    table.add_row("Estimated Cost", f"${usage.estimated_cost_usd:.4f}")
    console.print()
    console.print(table)


def _get_settings() -> Settings:
    """Load application settings."""
    return Settings()


def _build_pipeline() -> IngestionPipeline:
    """Build the full ingestion pipeline with real dependencies."""
    settings = _get_settings()
    conn = KuzuConnection(settings.db_path)
    initialize_schema(conn.conn)
    store = GraphStore(conn.conn)
    client = ExtractionClient(api_key=settings.anthropic_api_key)
    processor = BatchProcessor(client=client)
    return IngestionPipeline(store=store, processor=processor)


def _build_query_runner() -> QueryRunner:
    """Build a QueryRunner connected to the configured database."""
    settings = _get_settings()
    conn = KuzuConnection(settings.db_path)
    initialize_schema(conn.conn)
    return QueryRunner(conn.conn)


@app.command()
def ingest(
    path: Path | None = typer.Argument(None, help="Path to scan for JSONL files"),
) -> None:
    """Ingest JSONL conversation files into the knowledge graph."""
    pipeline = _build_pipeline()
    scan_path = path or Path.home() / ".claude" / "projects"

    console.print(f"[bold]Scanning:[/bold] {scan_path}")
    result = pipeline.ingest(scan_path)

    console.print(f"[green]Files processed:[/green] {result['files_processed']}")
    console.print(f"[yellow]Files skipped:[/yellow] {result['files_skipped']}")
    if result.get("sessions_skipped_short", 0):
        console.print(
            f"[yellow]Short sessions skipped:[/yellow] "
            f"{result['sessions_skipped_short']}"
        )
    console.print(f"[green]Entities stored:[/green] {result['entities_stored']}")
    console.print(
        f"[green]Relationships stored:[/green] {result['relationships_stored']}"
    )
    if result["errors"]:
        console.print(f"[red]Errors:[/red] {result['errors']}")

    _print_usage_table(result.get("usage"), title="API Usage Report")


@app.command()
def query(
    cypher: str = typer.Argument(..., help="Cypher query to execute"),
) -> None:
    """Execute a Cypher query against the knowledge graph."""
    runner = _build_query_runner()
    results = runner.execute(cypher)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table()
    columns = list(results[0].keys())
    for col in columns:
        table.add_column(col)

    for row in results:
        table.add_row(*[str(v) for v in row.values()])

    console.print(table)


@app.command()
def visualize(
    output: Path = typer.Argument(Path("graph.html"), help="Output HTML file path"),
) -> None:
    """Generate an interactive HTML visualization of the graph."""
    runner = _build_query_runner()
    renderer = GraphRenderer()
    renderer.render(runner, output)
    console.print(f"[green]Visualization saved to:[/green] {output}")


@app.command()
def audit(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of top entities"),
) -> None:
    """Show top entities by mention frequency and graph health insights."""
    runner = _build_query_runner()
    data = runner.get_audit(limit=limit)

    if data["total_entities"] == 0:
        console.print("[yellow]Graph is empty. Run 'kg ingest' first.[/yellow]")
        return

    table = Table(title=f"Top {limit} Most Mentioned Entities")
    table.add_column("#", style="dim", width=4)
    table.add_column("Entity", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Mentions", justify="right", style="green")

    for i, entity in enumerate(data["top_entities"], 1):
        table.add_row(
            str(i),
            entity["name"],
            entity["type"],
            str(entity["mention_count"]),
        )

    console.print(table)
    console.print(f"\n[dim]Total entities in graph: {data['total_entities']}[/dim]")


def _parse_period(period: str) -> int:
    """Parse a period string like '7d' into number of days.

    Raises:
        typer.BadParameter: If the period format is invalid.
    """
    match = re.fullmatch(r"(\d+)d", period)
    if not match:
        raise typer.BadParameter(
            f"Invalid period '{period}'. Use format like '7d', '30d'."
        )
    return int(match.group(1))


@app.command()
def recent(
    period: str = typer.Argument(..., help="Time period, e.g. '7d', '30d'"),
    entity_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by entity type"
    ),
) -> None:
    """Show entities first seen within a recent time period."""
    days = _parse_period(period)
    runner = _build_query_runner()
    results = runner.get_recent_entities(days=days, entity_type=entity_type)

    if not results:
        console.print("[yellow]No entities found in that period.[/yellow]")
        return

    table = Table(title=f"Entities first seen in last {days} day(s)")
    table.add_column("Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Mentions", justify="right", style="green")
    table.add_column("First Seen", style="dim")

    for row in results:
        table.add_row(
            row["name"],
            row["type"],
            str(row["mention_count"]),
            str(row["first_seen"]),
        )

    console.print(table)
    console.print(f"\n[dim]{len(results)} entities found.[/dim]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Natural language question"),
) -> None:
    """Ask a natural language question about the knowledge graph."""
    settings = _get_settings()
    if not settings.anthropic_api_key:
        console.print(
            "[red]ANTHROPIC_API_KEY is required for the ask command.[/red]"
        )
        raise typer.Exit(code=1)

    conn = KuzuConnection(settings.db_path)
    initialize_schema(conn.conn)

    querier = NaturalLanguageQuerier(
        api_key=settings.anthropic_api_key, conn=conn.conn
    )

    try:
        cypher, answer = querier.ask(question)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e

    console.print(f"[dim]Cypher: {cypher}[/dim]\n")
    console.print(answer)

    _print_usage_table(querier.usage)


@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Do not open browser automatically"
    ),
) -> None:
    """Start the KG Dashboard web server."""
    import uvicorn

    from claude_conversation_kg.dashboard.server import app as dashboard_app

    if not no_browser:
        webbrowser.open(f"http://{host}:{port}")

    uvicorn.run(dashboard_app, host=host, port=port)


@app.command()
def stats() -> None:
    """Display knowledge graph statistics."""
    runner = _build_query_runner()
    graph_stats = runner.get_stats()

    table = Table(title="Knowledge Graph Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total Entities", str(graph_stats["total_entities"]))
    table.add_row("Total Relationships", str(graph_stats["total_relationships"]))

    for etype, count in graph_stats.get("entities_by_type", {}).items():
        table.add_row(f"  {etype}", str(count))

    for rtype, count in graph_stats.get("relationships_by_type", {}).items():
        table.add_row(f"  {rtype}", str(count))

    console.print(table)


@app.command()
def context(
    top: int = typer.Option(10, "--top", "-n", help="Number of top entities to show"),
    days: int = typer.Option(7, "--days", "-d", help="Recent activity window in days"),
    plain: bool = typer.Option(
        False, "--plain", "-p", help="Plain text output (for hooks/scripts)"
    ),
) -> None:
    """Generate a project context summary from the knowledge graph.

    Outputs top entities, relationships, and recent activity.
    Use --plain for machine-readable output suitable for session hooks.
    """
    runner = _build_query_runner()
    graph_stats = runner.get_stats()

    if graph_stats["total_entities"] == 0:
        if plain:
            print("Knowledge graph is empty. Run 'kg ingest' first.")
        else:
            console.print("[yellow]Graph is empty. Run 'kg ingest' first.[/yellow]")
        return

    audit_data = runner.get_audit(limit=top)
    recent_entities = runner.get_recent_entities(days=days)

    if plain:
        _print_context_plain(graph_stats, audit_data, recent_entities, top, days)
    else:
        _print_context_rich(graph_stats, audit_data, recent_entities, top, days)


def _print_context_plain(
    graph_stats: dict,
    audit_data: dict,
    recent_entities: list[dict],
    top: int,
    days: int,
) -> None:
    """Print context summary as plain text for hooks/scripts."""
    lines = [
        "# Knowledge Graph Context",
        f"Entities: {graph_stats['total_entities']} | "
        f"Relationships: {graph_stats['total_relationships']}",
        "",
        "## Type Distribution",
    ]
    for etype, count in graph_stats.get("entities_by_type", {}).items():
        lines.append(f"- {etype}: {count}")

    lines.append("")
    lines.append(f"## Top {top} Entities")
    for entity in audit_data.get("top_entities", []):
        lines.append(
            f"- {entity['name']} ({entity['type']}) — {entity['mention_count']}x"
        )

    if recent_entities:
        lines.append("")
        lines.append(f"## Recent Activity (last {days}d)")
        for entity in recent_entities[:10]:
            lines.append(
                f"- {entity['name']} ({entity['type']}) — "
                f"first seen {entity['first_seen']}"
            )

    print("\n".join(lines))


def _print_context_rich(
    graph_stats: dict,
    audit_data: dict,
    recent_entities: list[dict],
    top: int,
    days: int,
) -> None:
    """Print context summary with rich formatting."""
    console.print(
        f"[bold]Knowledge Graph:[/bold] "
        f"{graph_stats['total_entities']:,} entities, "
        f"{graph_stats['total_relationships']:,} relationships\n"
    )

    # Type distribution
    type_table = Table(title="Type Distribution")
    type_table.add_column("Type", style="cyan")
    type_table.add_column("Count", justify="right")
    for etype, count in graph_stats.get("entities_by_type", {}).items():
        type_table.add_row(etype, str(count))
    console.print(type_table)

    # Top entities
    console.print()
    top_table = Table(title=f"Top {top} Entities")
    top_table.add_column("#", style="dim", width=4)
    top_table.add_column("Entity", style="bold")
    top_table.add_column("Type", style="cyan")
    top_table.add_column("Mentions", justify="right", style="green")
    for i, entity in enumerate(audit_data.get("top_entities", []), 1):
        top_table.add_row(
            str(i), entity["name"], entity["type"], str(entity["mention_count"])
        )
    console.print(top_table)

    # Recent activity
    if recent_entities:
        console.print()
        recent_table = Table(title=f"Recent Activity (last {days}d)")
        recent_table.add_column("Entity", style="bold")
        recent_table.add_column("Type", style="cyan")
        recent_table.add_column("First Seen", style="dim")
        for entity in recent_entities[:10]:
            recent_table.add_row(
                entity["name"], entity["type"], str(entity["first_seen"])
            )
        console.print(recent_table)
    else:
        console.print(f"\n[dim]No new entities in the last {days} day(s).[/dim]")
