# This file is part of craft-packages.
#
# Copyright 2026 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
# SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Unit tests for Action base classes."""

import inspect
import io
import subprocess
from typing import IO
from unittest import mock

import pytest
from craft_packages.actions import (
    Action,
    AutoremoveAction,
    CleanAction,
    DownloadAction,
    InfoAction,
    InstallAction,
    IsInstalledAction,
    ListInstalledAction,
    RefreshAction,
    RemoveAction,
    SearchAction,
    UpgradeAction,
)


class DummyAction(Action[list[str]]):
    """Concrete Action for testing."""

    def get_command(self, *packages: str, flag: bool = False) -> list[str]:
        cmd = ["dummy", "run"]
        if flag:
            cmd.append("--flag")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        return [line.strip() for line in stream if line.strip()]


def test_action_get_command():
    action = DummyAction()
    assert action.get_command("pkg-a", "pkg-b") == ["dummy", "run", "pkg-a", "pkg-b"]
    assert action.get_command("pkg-a", flag=True) == ["dummy", "run", "--flag", "pkg-a"]


def test_action_run():
    mock_runner = mock.Mock()
    action = DummyAction(runner=mock_runner)

    action.run("pkg-a", flag=True)

    mock_runner.assert_called_once_with(
        ["dummy", "run", "--flag", "pkg-a"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_action_run_custom_kwargs():
    mock_runner = mock.Mock()
    action = DummyAction(runner=mock_runner)

    action.run("pkg-a", runner_kwargs={"cwd": "/tmp", "text": False})

    mock_runner.assert_called_once_with(
        ["dummy", "run", "pkg-a"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        cwd="/tmp",
    )


def test_action_interpret_and_parse():
    action = DummyAction()
    stream = io.StringIO("line1\n\nline2\n")

    assert action.interpret(stream) == ["line1", "line2"]

    stream.seek(0)
    assert action.parse(stream) == ["line1", "line2"]


@pytest.mark.parametrize(
    "action_cls",
    [
        Action,
        RefreshAction,
        InstallAction,
        RemoveAction,
        UpgradeAction,
        SearchAction,
        InfoAction,
        ListInstalledAction,
        IsInstalledAction,
        DownloadAction,
        CleanAction,
        AutoremoveAction,
    ],
)
def test_abstract_actions_cannot_instantiate(action_cls):
    assert inspect.isabstract(action_cls)
    with pytest.raises(TypeError):
        action_cls()
