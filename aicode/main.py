import asyncio
import click
from aicode.repl import REPL


@click.command()
def cli():
    """
    brodex - AI coding assistant powered by Groq

    Set GROQ_API_KEY environment variable.
    Get your free key at https://console.groq.com
    """
    repl = REPL()
    asyncio.run(repl.run())


if __name__ == "__main__":
    cli()
