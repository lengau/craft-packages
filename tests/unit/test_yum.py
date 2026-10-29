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
"""Unit tests for Yum package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.yum import (
    Yum,
    YumAutoremove,
    YumClean,
    YumDownload,
    YumInfo,
    YumInstall,
    YumIsInstalled,
    YumListInstalled,
    YumRefresh,
    YumRefreshResult,
    YumRemove,
    YumSearch,
    YumUpgrade,
)


def test_yum_refresh():
    action = YumRefresh()
    assert action.get_command() == ["yum", "makecache"]

    output = io.StringIO(
        "CentOS Stream 9 - BaseOS                          5.4 kB/s | 5.4 kB 00:00\n"
        "Metadata cache created.\n"
    )
    result = action.interpret(output)
    assert result == YumRefreshResult(metadata_cache_created=True, repo_count=1)


def test_yum_install():
    action = YumInstall()
    assert action.get_command(["tree"]) == ["yum", "install", "-y", "tree"]
    assert action.get_command(["tree"], nodocs=True) == [
        "yum",
        "install",
        "-y",
        "--nodocs",
        "tree",
    ]

    output = io.StringIO(
        "Installed:\n"
        "  tree-1.8.0-10.el9.x86_64\n"
        "  curl-minimal.x86_64 8.5.0-1 baseos\n"
        "\n"
        "Complete!\n"
    )
    installed = action.interpret(output)
    assert installed == ["tree=1.8.0-10.el9", "curl-minimal=8.5.0-1"]


def test_yum_remove():
    action = YumRemove()
    assert action.get_command(["tree"]) == ["yum", "remove", "-y", "tree"]
    assert action.get_command(["tree"], autoremove=True) == [
        "yum",
        "remove",
        "-y",
        "--autoremove",
        "tree",
    ]

    output = io.StringIO("Removed:\n  tree.x86_64 1.8.0-10.el9\n\nComplete!\n")
    removed = action.interpret(output)
    assert removed == ["tree"]


def test_yum_upgrade():
    action = YumUpgrade()
    assert action.get_command() == ["yum", "upgrade", "-y"]
    assert action.get_command(["tree"]) == ["yum", "upgrade", "-y", "tree"]

    output = io.StringIO("Upgraded:\n  tree.x86_64 1.8.1-1.el9\n\nComplete!\n")
    upgraded = action.interpret(output)
    assert upgraded == ["tree=1.8.1-1.el9"]


def test_yum_search():
    action = YumSearch()
    assert action.get_command("tree") == ["yum", "search", "tree"]

    output = io.StringIO(
        "========================= Name & Summary Matched: tree =========================\n"
        "tree.x86_64 : File system tree viewer\n"
    )
    results = action.interpret(output)
    assert results == {"tree": "File system tree viewer"}


def test_yum_info():
    action = YumInfo()
    assert action.get_command("tree") == ["yum", "info", "tree"]

    output = io.StringIO(
        "Name         : tree\n"
        "Version      : 1.8.0\n"
        "Release      : 10.el9\n"
        "Description  : File system tree viewer\n"
    )
    info = action.interpret(output)
    assert info == {
        "Name": "tree",
        "Version": "1.8.0",
        "Release": "10.el9",
        "Description": "File system tree viewer",
    }


def test_yum_list_installed():
    action = YumListInstalled()
    assert action.get_command() == [
        "rpm",
        "-qa",
        "--qf",
        "%{NAME}=%{VERSION}-%{RELEASE}\n",
    ]

    output = io.StringIO("tree=1.8.0-10.el9\ntzdata=2026e-1.el9\n")
    assert action.interpret(output) == ["tree=1.8.0-10.el9", "tzdata=2026e-1.el9"]


def test_yum_is_installed():
    action = YumIsInstalled()
    assert action.get_command("tree") == ["rpm", "-q", "tree"]

    assert action.interpret(io.StringIO("tree-1.8.0-10.el9.x86_64\n")) is True
    assert action.interpret(io.StringIO("package tree is not installed\n")) is False
    assert action.interpret(io.StringIO("")) is False


def test_yum_download():
    action = YumDownload()
    assert action.get_command(["tree"]) == [
        "yum",
        "install",
        "-y",
        "--downloadonly",
        "tree",
    ]
    assert action.get_command(["tree"], destdir="/tmp") == [
        "yum",
        "install",
        "-y",
        "--downloadonly",
        "--destdir",
        "/tmp",
        "tree",
    ]

    output = io.StringIO(
        "Downloading Packages:\ntree-1.8.0-10.el9.x86_64.rpm  56 kB/s | 56 kB 00:00\nComplete!\n"
    )
    assert action.interpret(output) == ["tree"]


def test_yum_clean():
    action = YumClean()
    assert action.get_command() == ["yum", "clean", "all"]
    assert action.interpret(io.StringIO("")) is None


def test_yum_autoremove():
    action = YumAutoremove()
    assert action.get_command() == ["yum", "autoremove", "-y"]

    output = io.StringIO("Removed:\n  old-dep.x86_64 1.0-1\nComplete!\n")
    assert action.interpret(output) == ["old-dep"]


def test_yum_manager():
    mock_runner = mock.Mock()
    yum = Yum(runner=mock_runner)

    assert yum._runner is mock_runner
    assert yum.refresh._runner is mock_runner
    assert yum.install._runner is mock_runner
    assert yum.remove._runner is mock_runner
    assert yum.upgrade._runner is mock_runner
    assert yum.search._runner is mock_runner
    assert yum.info._runner is mock_runner
    assert yum.list_installed._runner is mock_runner
    assert yum.is_installed._runner is mock_runner
    assert yum.download._runner is mock_runner
    assert yum.clean._runner is mock_runner
    assert yum.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "Installed:\n  tree-1.8.0-10.el9.x86_64\nComplete!\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = yum.install.run(["tree"])
    assert installed == ["tree=1.8.0-10.el9"]

    mock_runner.assert_called_with(
        ["yum", "install", "-y", "tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
