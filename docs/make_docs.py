import json
import os
import shutil
import subprocess
from typing import Dict

import click
from click.exceptions import BadParameter


CWD: str = os.getcwd()
BUILD_DIR: str = "build"


def build_project(source_dir: str, output_type: str) -> str:
    if not os.path.isdir(source_dir):
        raise BadParameter("{} is not a valid directory!".format(source_dir))
    if "conf.py" not in os.listdir(source_dir):
        raise BadParameter(
            "source_dir must be the root of the documentation, not {}".format(
                source_dir
            )
        )
    build_dir = source_dir + "/" + BUILD_DIR
    try:
        if len(os.listdir(build_dir)) != 0:
            shutil.rmtree(build_dir)
    except FileNotFoundError:
        os.mkdir(build_dir)
    subprocess.run(["sphinx-build", "-b", output_type, source_dir, build_dir])
    return build_dir


# CLI functions


@click.command()
@click.option(
    "--source-dir", default=CWD, help="The source directory of the documentation."
)
@click.option("--output-file", help="The source directory of the documentation.")
def create_json(source_dir: str, output_file: str) -> None:
    pages: Dict = {"pages": []}
    build_dir = build_project(source_dir, "json")
    for file in os.listdir(build_dir):
        if file.split(".")[-1] == "fjson":
            with open(build_dir + "/" + file) as f:
                data: Dict[str, str] = json.load(f)
            try:
                if file == "index.fjson":  # Root file
                    pages["pages"].append(
                        {
                            "title": data["title"],
                            "path": "docs" + "/",
                            "body": data["body"],
                        }
                    )
                else:
                    pages["pages"].append(
                        {
                            "title": data["title"],
                            "path": ("docs" + "/" + data["title"]).lower(),
                            "body": data["body"],
                        }
                    )
            except KeyError:
                pass
    if output_file:
        output_file = output_file.split(".")[0] + ".json"
        with open(source_dir + "/" + output_file, "w") as f:
            json.dump(pages, f)
    shutil.rmtree(build_dir)
    click.echo("Completed successfully")


if __name__ == "__main__":
    create_json()
