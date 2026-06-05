import typer

app = typer.Typer(help="OKoffice agent-native Office infra CLI")

@app.callback()
def main() -> None:
    """Open-source PDF infrastructure for AI agents."""

@app.command()
def version() -> None:
    typer.echo("agentpdf 0.0.0")

if __name__ == "__main__":
    app()
