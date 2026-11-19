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
"""Unit tests for Pacman package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.pacman import (
    Pacman,
    PacmanAutoremove,
    PacmanClean,
    PacmanDownload,
    PacmanInfo,
    PacmanInstall,
    PacmanIsInstalled,
    PacmanListInstalled,
    PacmanRefresh,
    PacmanRefreshResult,
    PacmanRemove,
    PacmanSearch,
    PacmanUpgrade,
)


def test_pacman_refresh():
    action = PacmanRefresh()
    assert action.get_command() == ["pacman", "-Sy"]
    assert action.get_command(force=True) == ["pacman", "-Syy"]

    output = io.StringIO(
        ":: Synchronizing package databases...\n"
        " core downloading...\n"
        " extra downloading...\n"
    )
    result = action.interpret(output)
    assert result == PacmanRefreshResult(databases_synchronized=True, database_count=2)


def test_pacman_install():
    action = PacmanInstall()
    assert action.get_command(["tree"]) == ["pacman", "-S", "--noconfirm", "tree"]
    assert action.get_command(["tree"], needed=True) == [
        "pacman",
        "-S",
        "--noconfirm",
        "--needed",
        "tree",
    ]
    assert action.get_command(["tree"], nodeps=True) == [
        "pacman",
        "-S",
        "--noconfirm",
        "--nodeps",
        "tree",
    ]

    output = io.StringIO(
        "resolving dependencies...\n"
        "looking for conflicting packages...\n"
        "\n"
        "Packages (1) tree-2.3.2-1\n"
        "\n"
        "Total Installed Size:  0.09 MiB\n"
        "\n"
        ":: Proceed with installation? [Y/n] \n"
        "installing tree...\n"
    )
    installed = action.interpret(output)
    assert installed == ["tree=2.3.2-1"]


def test_pacman_remove():
    action = PacmanRemove()
    assert action.get_command(["tree"]) == ["pacman", "-R", "--noconfirm", "tree"]
    assert action.get_command(["tree"], recursive=True) == [
        "pacman",
        "-Rs",
        "--noconfirm",
        "tree",
    ]
    assert action.get_command(["tree"], cascade=True) == [
        "pacman",
        "-Rc",
        "--noconfirm",
        "tree",
    ]
    assert action.get_command(["tree"], unneeded=True) == [
        "pacman",
        "-Ru",
        "--noconfirm",
        "tree",
    ]

    output = io.StringIO(
        "checking dependencies...\n"
        "\n"
        "Packages (1) tree-2.3.2-1\n"
        "\n"
        "Total Removed Size:  0.09 MiB\n"
        "\n"
        ":: Do you want to remove these packages? [Y/n] \n"
        "removing tree...\n"
    )
    removed = action.interpret(output)
    assert removed == ["tree"]


def test_pacman_upgrade():
    action = PacmanUpgrade()
    assert action.get_command() == ["pacman", "-Su", "--noconfirm"]
    assert action.get_command(enable_downgrade=True) == [
        "pacman",
        "-Suu",
        "--noconfirm",
    ]

    output = io.StringIO(
        "Packages (1) tree-2.3.2-1\n\nTotal Installed Size:  0.09 MiB\n"
    )
    upgraded = action.interpret(output)
    assert upgraded == ["tree=2.3.2-1"]


def test_pacman_search():
    action = PacmanSearch()
    assert action.get_command("tree") == ["pacman", "-Ss", "tree"]

    output = io.StringIO(
        "extra/tree 2.3.2-1\n"
        "    A directory listing program displaying a depth indented list of files\n"
    )
    results = action.interpret(output)
    assert results == {
        "tree": "A directory listing program displaying a depth indented list of files"
    }


def test_pacman_info():
    action = PacmanInfo()
    assert action.get_command("tree") == ["pacman", "-Si", "tree"]

    output = io.StringIO(
        "Repository      : extra\n"
        "Name            : tree\n"
        "Version         : 2.3.2-1\n"
        "Description     : A directory listing program\n"
    )
    info = action.interpret(output)
    assert info == {
        "Repository": "extra",
        "Name": "tree",
        "Version": "2.3.2-1",
        "Description": "A directory listing program",
    }


def test_pacman_list_installed():
    action = PacmanListInstalled()
    assert action.get_command() == ["pacman", "-Q"]

    output = io.StringIO("acl 2.4.0-1\ntree 2.3.2-1\n")
    assert action.interpret(output) == ["acl=2.4.0-1", "tree=2.3.2-1"]


def test_pacman_is_installed():
    action = PacmanIsInstalled()
    assert action.get_command("tree") == ["pacman", "-Q", "tree"]

    assert action.interpret(io.StringIO("tree 2.3.2-1\n")) is True
    assert (
        action.interpret(io.StringIO("error: package 'tree' was not found\n")) is False
    )
    assert action.interpret(io.StringIO("")) is False


def test_pacman_download():
    action = PacmanDownload()
    assert action.get_command(["tree"]) == [
        "pacman",
        "-Sw",
        "--noconfirm",
        "tree",
    ]
    assert action.get_command(["tree"], cachedir="/tmp/cache") == [
        "pacman",
        "-Sw",
        "--noconfirm",
        "--cachedir",
        "/tmp/cache",
        "tree",
    ]

    output = io.StringIO(
        "Packages (1) tree-2.3.2-1\n\nTotal Download Size:  0.04 MiB\n"
    )
    assert action.interpret(output) == ["tree"]


def test_pacman_clean():
    action = PacmanClean()
    assert action.get_command() == ["pacman", "-Sc", "--noconfirm"]
    assert action.interpret(io.StringIO("")) is None


def test_pacman_autoremove():
    action = PacmanAutoremove()
    assert action.get_command() == [
        "sh",
        "-c",
        "pacman -Qtdq | xargs -r pacman -Rns --noconfirm",
    ]

    output = io.StringIO("Packages (1) orphan-1.0-1\n\nTotal Removed Size:  0.03 MiB\n")
    assert action.interpret(output) == ["orphan"]


def test_pacman_manager():
    mock_runner = mock.Mock()
    pacman = Pacman(runner=mock_runner)

    assert pacman._runner is mock_runner
    assert pacman.refresh._runner is mock_runner
    assert pacman.install._runner is mock_runner
    assert pacman.remove._runner is mock_runner
    assert pacman.upgrade._runner is mock_runner
    assert pacman.search._runner is mock_runner
    assert pacman.info._runner is mock_runner
    assert pacman.list_installed._runner is mock_runner
    assert pacman.is_installed._runner is mock_runner
    assert pacman.download._runner is mock_runner
    assert pacman.clean._runner is mock_runner
    assert pacman.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "Packages (1) tree-2.3.2-1\n\nTotal Installed Size:  0.09 MiB\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = pacman.install.run(["tree"])
    assert installed == ["tree=2.3.2-1"]

    mock_runner.assert_called_with(
        ["pacman", "-S", "--noconfirm", "tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
