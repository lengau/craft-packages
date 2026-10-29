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
"""Unit tests for Apk package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.apk import (
    Apk,
    ApkAutoremove,
    ApkClean,
    ApkDownload,
    ApkInfo,
    ApkInstall,
    ApkIsInstalled,
    ApkListInstalled,
    ApkRefresh,
    ApkRefreshResult,
    ApkRemove,
    ApkSearch,
    ApkUpgrade,
)


def test_apk_refresh():
    action = ApkRefresh()
    assert action.get_command() == ["apk", "update"]

    output = io.StringIO(
        "fetch https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz\n"
        "OK: 20710 distinct packages available\n"
    )
    result = action.interpret(output)
    assert result == ApkRefreshResult(repositories_updated=True, repository_count=1)


def test_apk_install():
    action = ApkInstall()
    assert action.get_command(["tree"]) == ["apk", "add", "tree"]
    assert action.get_command(["tree"], no_cache=True) == [
        "apk",
        "add",
        "--no-cache",
        "tree",
    ]

    output = io.StringIO(
        "(1/1) Installing tree (2.2.1-r0)\n"
        "Executing busybox-1.37.0-r20.trigger\n"
        "OK: 9 MiB in 33 packages\n"
    )
    installed = action.interpret(output)
    assert installed == ["tree=2.2.1-r0"]


def test_apk_remove():
    action = ApkRemove()
    assert action.get_command(["tree"]) == ["apk", "del", "tree"]
    assert action.get_command(["tree"], purge=True) == [
        "apk",
        "del",
        "--purge",
        "tree",
    ]
    assert action.get_command(["tree"], rdepends=True) == [
        "apk",
        "del",
        "--rdepends",
        "tree",
    ]

    output = io.StringIO(
        "(1/1) Purging tree (2.2.1-r0)\n"
        "Executing busybox-1.37.0-r20.trigger\n"
        "OK: 9 MiB in 32 packages\n"
    )
    removed = action.interpret(output)
    assert removed == ["tree"]


def test_apk_upgrade():
    action = ApkUpgrade()
    assert action.get_command() == ["apk", "upgrade"]
    assert action.get_command(available=True) == ["apk", "upgrade", "--available"]
    assert action.get_command(["tree"]) == ["apk", "upgrade", "tree"]

    output = io.StringIO("(1/1) Upgrading tree (2.2.0-r0 -> 2.2.1-r0)\n")
    upgraded = action.interpret(output)
    assert upgraded == ["tree=2.2.1-r0"]


def test_apk_search():
    action = ApkSearch()
    assert action.get_command("tree") == ["apk", "search", "-v", "tree"]
    assert action.get_command("tree", exact=True) == [
        "apk",
        "search",
        "-v",
        "-e",
        "tree",
    ]

    output = io.StringIO(
        "tree-2.2.1-r0 - Recursive directory indented listing of files\n"
    )
    results = action.interpret(output)
    assert results == {"tree": "Recursive directory indented listing of files"}


def test_apk_info():
    action = ApkInfo()
    assert action.get_command("tree") == ["apk", "info", "-a", "tree"]

    output = io.StringIO(
        "tree-2.2.1-r0 description:\n"
        "Recursive directory indented listing of files\n"
        "\n"
        "tree-2.2.1-r0 webpage:\n"
        "https://oldmanprogrammer.net/source.php?dir=projects/tree\n"
    )
    info = action.interpret(output)
    assert info == {
        "description": "Recursive directory indented listing of files",
        "webpage": "https://oldmanprogrammer.net/source.php?dir=projects/tree",
    }


def test_apk_list_installed():
    action = ApkListInstalled()
    assert action.get_command() == ["apk", "info", "-v"]

    output = io.StringIO("acl-libs-2.3.2-r1\ntree-2.2.1-r0\n")
    assert action.interpret(output) == ["acl-libs=2.3.2-r1", "tree=2.2.1-r0"]


def test_apk_is_installed():
    action = ApkIsInstalled()
    assert action.get_command("tree") == ["apk", "info", "-e", "tree"]

    assert action.interpret(io.StringIO("tree\n")) is True
    assert action.interpret(io.StringIO("")) is False


def test_apk_download():
    action = ApkDownload()
    assert action.get_command(["tree"]) == ["apk", "fetch", "tree"]
    assert action.get_command(["tree"], destdir="/tmp") == [
        "apk",
        "fetch",
        "-o",
        "/tmp",
        "tree",
    ]

    output = io.StringIO("Downloading tree-2.2.1-r0\n")
    assert action.interpret(output) == ["tree"]


def test_apk_clean():
    action = ApkClean()
    assert action.get_command() == ["apk", "cache", "clean"]
    assert action.interpret(io.StringIO("")) is None


def test_apk_autoremove():
    action = ApkAutoremove()
    assert action.get_command() == ["apk", "cache", "purge"]
    assert action.interpret(io.StringIO("")) == []


def test_apk_manager():
    mock_runner = mock.Mock()
    apk = Apk(runner=mock_runner)

    assert apk._runner is mock_runner
    assert apk.refresh._runner is mock_runner
    assert apk.install._runner is mock_runner
    assert apk.remove._runner is mock_runner
    assert apk.upgrade._runner is mock_runner
    assert apk.search._runner is mock_runner
    assert apk.info._runner is mock_runner
    assert apk.list_installed._runner is mock_runner
    assert apk.is_installed._runner is mock_runner
    assert apk.download._runner is mock_runner
    assert apk.clean._runner is mock_runner
    assert apk.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "(1/1) Installing tree (2.2.1-r0)\nOK: 9 MiB in 33 packages\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = apk.install.run(["tree"])
    assert installed == ["tree=2.2.1-r0"]

    mock_runner.assert_called_with(
        ["apk", "add", "tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
