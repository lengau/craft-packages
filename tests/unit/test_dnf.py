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
"""Unit tests for Dnf package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.dnf import (
    Dnf,
    DnfAutoremove,
    DnfClean,
    DnfDownload,
    DnfInfo,
    DnfInstall,
    DnfIsInstalled,
    DnfListInstalled,
    DnfRefresh,
    DnfRefreshResult,
    DnfRemove,
    DnfSearch,
    DnfUpgrade,
)


def test_dnf_refresh():
    action = DnfRefresh()
    assert action.get_command() == ["dnf", "makecache"]

    output = io.StringIO(
        "Fedora 43 - x86_64                                5.4 kB/s | 5.4 kB 00:00\n"
        "Fedora 43 - AppStream                             5.5 kB/s | 5.5 kB 00:00\n"
        "Metadata cache created.\n"
    )
    result = action.interpret(output)
    assert result == DnfRefreshResult(metadata_cache_created=True, repo_count=2)


def test_dnf_install():
    action = DnfInstall()
    assert action.get_command(["tree"]) == ["dnf", "install", "-y", "tree"]
    assert action.get_command(["tree"], nodocs=True) == [
        "dnf",
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


def test_dnf_remove():
    action = DnfRemove()
    assert action.get_command(["tree"]) == ["dnf", "remove", "-y", "tree"]
    assert action.get_command(["tree"], autoremove=True) == [
        "dnf",
        "remove",
        "-y",
        "--autoremove",
        "tree",
    ]

    output = io.StringIO("Removed:\n  tree.x86_64 1.8.0-10.el9\n\nComplete!\n")
    removed = action.interpret(output)
    assert removed == ["tree"]


def test_dnf_upgrade():
    action = DnfUpgrade()
    assert action.get_command() == ["dnf", "upgrade", "-y"]
    assert action.get_command(["tree"]) == ["dnf", "upgrade", "-y", "tree"]

    output = io.StringIO("Upgraded:\n  tree.x86_64 1.8.1-1.el9\n\nComplete!\n")
    upgraded = action.interpret(output)
    assert upgraded == ["tree=1.8.1-1.el9"]


def test_dnf_search():
    action = DnfSearch()
    assert action.get_command("tree") == ["dnf", "search", "tree"]

    output = io.StringIO(
        "========================= Name & Summary Matched: tree =========================\n"
        "tree.x86_64 : File system tree viewer\n"
        "git-subtree.noarch : Git tools to merge and split repositories\n"
    )
    results = action.interpret(output)
    assert results == {
        "tree": "File system tree viewer",
        "git-subtree": "Git tools to merge and split repositories",
    }


def test_dnf_info():
    action = DnfInfo()
    assert action.get_command("tree") == ["dnf", "info", "tree"]

    output = io.StringIO(
        "Name         : tree\n"
        "Version      : 1.8.0\n"
        "Release      : 10.el9\n"
        "Description  : The tree utility recursively displays\n"
        "             : in a tree-like format.\n"
    )
    info = action.interpret(output)
    assert info == {
        "Name": "tree",
        "Version": "1.8.0",
        "Release": "10.el9",
        "Description": "The tree utility recursively displays\nin a tree-like format.",
    }


def test_dnf_list_installed():
    action = DnfListInstalled()
    assert action.get_command() == [
        "rpm",
        "-qa",
        "--qf",
        "%{NAME}=%{VERSION}-%{RELEASE}\n",
    ]

    output = io.StringIO("tzdata=2026e-1.el9\ntree=1.8.0-10.el9\n")
    assert action.interpret(output) == ["tree=1.8.0-10.el9", "tzdata=2026e-1.el9"]


def test_dnf_is_installed():
    action = DnfIsInstalled()
    assert action.get_command("tree") == ["rpm", "-q", "tree"]

    assert action.interpret(io.StringIO("tree-1.8.0-10.el9.x86_64\n")) is True
    assert action.interpret(io.StringIO("package tree is not installed\n")) is False
    assert action.interpret(io.StringIO("")) is False


def test_dnf_download():
    action = DnfDownload()
    assert action.get_command(["tree"]) == [
        "dnf",
        "install",
        "-y",
        "--downloadonly",
        "tree",
    ]
    assert action.get_command(["tree"], destdir="/tmp") == [
        "dnf",
        "install",
        "-y",
        "--downloadonly",
        "--destdir",
        "/tmp",
        "tree",
    ]

    output = io.StringIO(
        "Downloading Packages:\n"
        "tree-1.8.0-10.el9.x86_64.rpm  56 kB/s | 56 kB 00:00\n"
        "Complete!\n"
    )
    assert action.interpret(output) == ["tree"]


def test_dnf_clean():
    action = DnfClean()
    assert action.get_command() == ["dnf", "clean", "all"]
    assert action.interpret(io.StringIO("")) is None


def test_dnf_autoremove():
    action = DnfAutoremove()
    assert action.get_command() == ["dnf", "autoremove", "-y"]

    output = io.StringIO("Removed:\n  old-dep.x86_64 1.0-1\nComplete!\n")
    assert action.interpret(output) == ["old-dep"]


def test_dnf_manager():
    mock_runner = mock.Mock()
    dnf = Dnf(runner=mock_runner)

    assert dnf._runner is mock_runner
    assert dnf.refresh._runner is mock_runner
    assert dnf.install._runner is mock_runner
    assert dnf.remove._runner is mock_runner
    assert dnf.upgrade._runner is mock_runner
    assert dnf.search._runner is mock_runner
    assert dnf.info._runner is mock_runner
    assert dnf.list_installed._runner is mock_runner
    assert dnf.is_installed._runner is mock_runner
    assert dnf.download._runner is mock_runner
    assert dnf.clean._runner is mock_runner
    assert dnf.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "Installed:\n  tree-1.8.0-10.el9.x86_64\nComplete!\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = dnf.install.run(["tree"])
    assert installed == ["tree=1.8.0-10.el9"]

    mock_runner.assert_called_with(
        ["dnf", "install", "-y", "tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
