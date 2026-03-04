"""CLI entry point for the Knowledge Graph tool."""

from __future__ import annotations

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
from claude_conversation_kg.pipeline import IngestionPipeline
from claude_conversation_kg.visualization.renderer import GraphRenderer

app = typer.Typer(name="kg", help="Claude Conversation Knowledge Graph CLI")
console = Console()


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
    console.print(f"[green]Entities stored:[/green] {result['entities_stored']}")
    console.print(
        f"[green]Relationships stored:[/green] {result['relationships_stored']}"
    )
    if result["errors"]:
        console.print(f"[red]Errors:[/red] {result['errors']}")


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
