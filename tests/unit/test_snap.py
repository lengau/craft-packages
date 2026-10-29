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
"""Unit tests for Snap package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.snap import (
    Snap,
    SnapAutoremove,
    SnapClean,
    SnapDownload,
    SnapInfo,
    SnapInstall,
    SnapIsInstalled,
    SnapListInstalled,
    SnapRefresh,
    SnapRefreshResult,
    SnapRemove,
    SnapSearch,
    SnapUpgrade,
)


def test_snap_refresh():
    action = SnapRefresh()
    assert action.get_command() == [
        "snap",
        "refresh",
        "--color=never",
        "--unicode=never",
    ]
    assert action.get_command(hold="24h") == [
        "snap",
        "refresh",
        "--color=never",
        "--unicode=never",
        "--hold=24h",
    ]

    output = io.StringIO("All snaps up to date.\n")
    result = action.interpret(output)
    assert result == SnapRefreshResult(refreshed=True, snap_count=0)

    output_refreshed = io.StringIO("hello (stable) 2.10 from Canonical** refreshed\n")
    result2 = action.interpret(output_refreshed)
    assert result2 == SnapRefreshResult(refreshed=True, snap_count=1)


def test_snap_install():
    action = SnapInstall()
    assert action.get_command(["hello"]) == [
        "snap",
        "install",
        "--color=never",
        "--unicode=never",
        "hello",
    ]
    assert action.get_command(["hello"], classic=True, channel="edge") == [
        "snap",
        "install",
        "--color=never",
        "--unicode=never",
        "--classic",
        "--channel=edge",
        "hello",
    ]
    assert action.get_command(["hello"], devmode=True, dangerous=True) == [
        "snap",
        "install",
        "--color=never",
        "--unicode=never",
        "--devmode",
        "--dangerous",
        "hello",
    ]

    output = io.StringIO("hello 2.10 from Canonical** installed\n")
    installed = action.interpret(output)
    assert installed == ["hello=2.10"]


def test_snap_remove():
    action = SnapRemove()
    assert action.get_command(["hello"]) == ["snap", "remove", "hello"]
    assert action.get_command(["hello"], purge=True, revision="42") == [
        "snap",
        "remove",
        "--purge",
        "--revision=42",
        "hello",
    ]

    output = io.StringIO("hello removed (snap data snapshot saved)\n")
    removed = action.interpret(output)
    assert removed == ["hello"]


def test_snap_upgrade():
    action = SnapUpgrade()
    assert action.get_command() == [
        "snap",
        "refresh",
        "--color=never",
        "--unicode=never",
    ]
    assert action.get_command(["hello"], channel="beta", classic=True) == [
        "snap",
        "refresh",
        "--color=never",
        "--unicode=never",
        "--classic",
        "--channel=beta",
        "hello",
    ]

    output = io.StringIO("hello (stable) 2.10 from Canonical** refreshed\n")
    upgraded = action.interpret(output)
    assert upgraded == ["hello=2.10"]


def test_snap_search():
    action = SnapSearch()
    assert action.get_command("tree") == [
        "snap",
        "find",
        "--color=never",
        "--unicode=never",
        "tree",
    ]

    output = io.StringIO(
        "Name  Version  Publisher  Notes  Summary\n"
        "tree  2.1.3    brlin      -      A directory listing command\n"
    )
    results = action.interpret(output)
    assert results == {"tree": "A directory listing command"}


def test_snap_info():
    action = SnapInfo()
    assert action.get_command("hello") == [
        "snap",
        "info",
        "--color=never",
        "--unicode=never",
        "hello",
    ]

    output = io.StringIO(
        "name:      hello\n"
        "summary:   GNU Hello, the 'hello world' snap\n"
        "publisher: Canonical**\n"
    )
    info = action.interpret(output)
    assert info == {
        "name": "hello",
        "summary": "GNU Hello, the 'hello world' snap",
        "publisher": "Canonical**",
    }


def test_snap_list_installed():
    action = SnapListInstalled()
    assert action.get_command() == [
        "snap",
        "list",
        "--color=never",
        "--unicode=never",
    ]

    output = io.StringIO(
        "Name       Version  Rev   Tracking  Publisher  Notes\n"
        "astral-uv  0.13.5   1821  latest    lengau*    classic\n"
        "hello      2.10     42    latest    canonical  -\n"
    )
    assert action.interpret(output) == ["astral-uv=0.13.5", "hello=2.10"]


def test_snap_is_installed():
    action = SnapIsInstalled()
    assert action.get_command("hello") == [
        "snap",
        "list",
        "--color=never",
        "--unicode=never",
        "hello",
    ]

    output_installed = io.StringIO(
        "Name   Version  Rev  Tracking  Publisher  Notes\n"
        "hello  2.10     42   latest    canonical  -\n"
    )
    assert action.interpret(output_installed) is True

    output_not_installed = io.StringIO("error: no matching snaps installed\n")
    assert action.interpret(output_not_installed) is False


def test_snap_download():
    action = SnapDownload()
    assert action.get_command(["hello"]) == ["snap", "download", "hello"]
    assert action.get_command(["hello"], destdir="/tmp", channel="candidate") == [
        "snap",
        "download",
        "--target-directory=/tmp",
        "--channel=candidate",
        "hello",
    ]

    output = io.StringIO('Fetching snap "hello"\nFetching assertions for "hello"\n')
    assert action.interpret(output) == ["hello"]


def test_snap_clean():
    action = SnapClean()
    assert action.get_command() == [
        "sh",
        "-c",
        "rm -rf /var/lib/snapd/cache/*",
    ]
    assert action.interpret(io.StringIO("")) is None


def test_snap_autoremove():
    action = SnapAutoremove()
    assert action.get_command() == [
        "sh",
        "-c",
        'snap list --all 2>/dev/null | grep "disabled" | while read -r name ver rev rest; do snap remove "$name" --revision="$rev"; done || true',
    ]

    output = io.StringIO("hello removed\n")
    assert action.interpret(output) == ["hello"]


def test_snap_manager():
    mock_runner = mock.Mock()
    snap = Snap(runner=mock_runner)

    assert snap._runner is mock_runner
    assert snap.refresh._runner is mock_runner
    assert snap.install._runner is mock_runner
    assert snap.remove._runner is mock_runner
    assert snap.upgrade._runner is mock_runner
    assert snap.search._runner is mock_runner
    assert snap.info._runner is mock_runner
    assert snap.list_installed._runner is mock_runner
    assert snap.is_installed._runner is mock_runner
    assert snap.download._runner is mock_runner
    assert snap.clean._runner is mock_runner
    assert snap.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "hello 2.10 from Canonical** installed\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = snap.install.run(["hello"])
    assert installed == ["hello=2.10"]

    mock_runner.assert_called_with(
        ["snap", "install", "--color=never", "--unicode=never", "hello"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
