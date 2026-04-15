from __future__ import annotations

import typer

from drawbot_cli.commands.api import api_app
from drawbot_cli.commands.create import create_app
from drawbot_cli.commands.design import design_app
from drawbot_cli.commands.doctor import doctor
from drawbot_cli.commands.new import new
from drawbot_cli.commands.recipe import recipe_app
from drawbot_cli.commands.run import run
from drawbot_cli.commands.spec import spec_app


app = typer.Typer(
    name="drawbot",
    help="Headless, skia-native DrawBot CLI.",
    no_args_is_help=True,
)

app.command()(run)
app.command()(doctor)
app.command()(new)
app.add_typer(api_app, name="api")
app.add_typer(create_app, name="create")
app.add_typer(design_app, name="design")
app.add_typer(recipe_app, name="recipe")
app.add_typer(spec_app, name="spec")


if __name__ == "__main__":
    app()
