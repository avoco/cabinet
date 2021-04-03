import os
from tempfile import TemporaryDirectory

import pytest

from click.testing import CliRunner
from docs.make_docs import create_json


@pytest.fixture()
def docs_directory(request):
    return str(request.fspath.join("../..") + "/docs/")


@pytest.fixture
def directory():
    with TemporaryDirectory() as tempdir:
        yield tempdir


def test_create_json(docs_directory):
    runner = CliRunner()
    result = runner.invoke(create_json, ["--source-dir={}".format(docs_directory)])
    assert result.exit_code == 0
    assert "Completed successfully" in result.output


def test_create_json_output(docs_directory):
    runner = CliRunner()
    result = runner.invoke(
        create_json, ["--source-dir={}".format(docs_directory), "--output-file=test"]
    )
    assert result.exit_code == 0
    assert "Completed successfully" in result.output
    os.remove(docs_directory + "/test.json")


def test_create_json_bad_directory(docs_directory):
    runner = CliRunner()
    bad_dir = docs_directory + docs_directory
    result = runner.invoke(create_json, ["--source-dir={}".format(bad_dir)])
    assert result.exit_code == 2
    assert "is not a valid directory" in result.output


def test_create_json_no_conf(directory):
    runner = CliRunner()
    result = runner.invoke(create_json, ["--source-dir={}".format(directory)])
    assert result.exit_code == 2
    assert "source_dir must be the root of the documentation" in result.output
