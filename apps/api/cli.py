"""CLI for biblical-evals management tasks."""

import typer

from src.loaders.config_loader import load_app_config
from src.loaders.question_loader import load_all_questions

app = typer.Typer(
    name="biblical-evals",
    help="Biblical LLM Evaluation Framework CLI",
)


@app.command()
def questions():
    """List all loaded questions."""
    qs = load_all_questions()
    typer.echo(f"Loaded {len(qs)} questions:\n")
    for q in qs:
        typer.echo(f"  [{q.id}] ({q.type}/{q.difficulty}) {q.text[:80]}")


@app.command()
def config():
    """Show loaded configuration."""
    cfg = load_app_config()
    typer.echo(f"Models ({len(cfg.models)}):")
    for m in cfg.models:
        typer.echo(f"  - {m.name} ({m.provider})")
    typer.echo(f"\nPerspectives ({len(cfg.perspectives)}):")
    for p in cfg.perspectives:
        typer.echo(f"  - {p.id}: {p.name}")
    typer.echo(f"\nScoring Dimensions ({len(cfg.dimensions)}):")
    for d in cfg.dimensions:
        typer.echo(f"  - {d.name}: {d.label}")
    typer.echo(f"\nPrompt Templates ({len(cfg.templates)}):")
    for t in cfg.templates:
        typer.echo(f"  - {t.id}: {t.name} (v{t.version})")


@app.command()
def serve(
    host: str = "0.0.0.0",  # noqa: S104
    port: int = 8000,
    reload: bool = True,
):
    """Run the development server."""
    import uvicorn

    uvicorn.run("src.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
