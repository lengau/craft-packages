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
"""Unit tests for Apt package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.apt import (
    Apt,
    AptAutoremove,
    AptClean,
    AptDownload,
    AptInfo,
    AptInstall,
    AptIsInstalled,
    AptListInstalled,
    AptRefresh,
    AptRefreshResult,
    AptRemove,
    AptSearch,
    AptUpgrade,
)


def test_apt_refresh():
    action = AptRefresh()
    assert action.get_command() == ["apt-get", "update"]

    output = io.StringIO(
        "Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease\n"
        "Get:2 http://security.ubuntu.com/ubuntu jammy-security InRelease\n"
        "Ign:3 http://archive.ubuntu.com/ubuntu jammy-updates InRelease\n"
        "Err:4 http://ppa.launchpad.net/unknown InRelease\n"
    )
    result = action.interpret(output)
    assert result == AptRefreshResult(hits=1, gets=1, ignored=1, errors=1)


def test_apt_install():
    action = AptInstall()
    assert action.get_command(["curl", "git"]) == [
        "apt-get",
        "install",
        "-y",
        "curl",
        "git",
    ]
    assert action.get_command(["curl"], no_recommends=True, allow_downgrades=True) == [
        "apt-get",
        "install",
        "-y",
        "--no-install-recommends",
        "--allow-downgrades",
        "curl",
    ]

    output = io.StringIO(
        "Reading package lists...\n"
        "Building dependency tree...\n"
        "Unpacking curl (7.81.0-1ubuntu1.16) ...\n"
        "Setting up libcurl4:amd64 (7.81.0-1ubuntu1.16) ...\n"
        "Setting up curl (7.81.0-1ubuntu1.16) ...\n"
        "Processing triggers for man-db ...\n"
    )
    installed = action.interpret(output)
    assert installed == [
        "libcurl4=7.81.0-1ubuntu1.16",
        "curl=7.81.0-1ubuntu1.16",
    ]


def test_apt_remove():
    action = AptRemove()
    assert action.get_command(["curl"]) == ["apt-get", "remove", "-y", "curl"]
    assert action.get_command(["curl"], purge=True, autoremove=True) == [
        "apt-get",
        "purge",
        "-y",
        "--autoremove",
        "curl",
    ]

    output = io.StringIO(
        "Removing curl (7.81.0-1ubuntu1.16) ...\n"
        "Purging configuration files for curl (7.81.0-1ubuntu1.16) ...\n"
    )
    removed = action.interpret(output)
    assert removed == ["curl"]


def test_apt_upgrade():
    action = AptUpgrade()
    assert action.get_command() == ["apt-get", "upgrade", "-y"]
    assert action.get_command(dist_upgrade=True) == [
        "apt-get",
        "dist-upgrade",
        "-y",
    ]
    assert action.get_command(["curl"]) == [
        "apt-get",
        "upgrade",
        "-y",
        "curl",
    ]

    output = io.StringIO("Setting up curl (7.81.0-2) ...\n")
    assert action.interpret(output) == ["curl=7.81.0-2"]


def test_apt_search():
    action = AptSearch()
    assert action.get_command("python") == ["apt-cache", "search", "python"]
    assert action.get_command("python", names_only=True) == [
        "apt-cache",
        "search",
        "--names-only",
        "python",
    ]

    output = io.StringIO(
        "python3 - interactive high-level object-oriented language\n"
        "python3-dev - header files and a static library for Python\n"
    )
    results = action.interpret(output)
    assert results == {
        "python3": "interactive high-level object-oriented language",
        "python3-dev": "header files and a static library for Python",
    }


def test_apt_info():
    action = AptInfo()
    assert action.get_command("curl") == ["apt-cache", "show", "curl"]

    output = io.StringIO(
        "Package: curl\n"
        "Version: 7.81.0-1\n"
        "Description: command line tool\n"
        " for transferring data with URL syntax\n"
    )
    info = action.interpret(output)
    assert info == {
        "Package": "curl",
        "Version": "7.81.0-1",
        "Description": "command line tool\nfor transferring data with URL syntax",
    }


def test_apt_list_installed():
    action = AptListInstalled()
    assert action.get_command() == [
        "dpkg-query",
        "-W",
        "-f=${Package}\t${Status}\t${Version}\n",
    ]

    output = io.StringIO(
        "curl\tinstall ok installed\t7.81.0-1\n"
        "git\thold ok installed\t2.34.1-1\n"
        "nano\tdeinstall ok config-files\t6.2-1\n"
    )
    packages = action.interpret(output)
    assert packages == ["curl=7.81.0-1", "git=2.34.1-1"]


def test_apt_is_installed():
    action = AptIsInstalled()
    assert action.get_command("curl") == [
        "dpkg-query",
        "-W",
        "-f=${Status}\n",
        "curl",
    ]

    assert action.interpret(io.StringIO("install ok installed\n")) is True
    assert action.interpret(io.StringIO("hold ok installed\n")) is True
    assert action.interpret(io.StringIO("deinstall ok config-files\n")) is False
    assert action.interpret(io.StringIO("")) is False


def test_apt_download():
    action = AptDownload()
    assert action.get_command(["curl"]) == [
        "apt-get",
        "install",
        "-y",
        "--download-only",
        "curl",
    ]
    assert action.get_command(["curl"], no_recommends=True) == [
        "apt-get",
        "install",
        "-y",
        "--download-only",
        "--no-install-recommends",
        "curl",
    ]

    output = io.StringIO(
        "Get:1 http://archive.ubuntu.com/ubuntu jammy/main amd64 curl amd64 7.81.0-1 [194 kB]\n"
    )
    assert action.interpret(output) == ["curl"]


def test_apt_clean():
    action = AptClean()
    assert action.get_command() == ["apt-get", "clean"]
    assert action.interpret(io.StringIO("")) is None


def test_apt_autoremove():
    action = AptAutoremove()
    assert action.get_command() == ["apt-get", "autoremove", "-y"]
    assert action.get_command(purge=True) == [
        "apt-get",
        "autoremove",
        "-y",
        "--purge",
    ]

    output = io.StringIO("Removing unused-pkg (1.0) ...\n")
    assert action.interpret(output) == ["unused-pkg"]


def test_apt_manager():
    mock_runner = mock.Mock()
    apt = Apt(runner=mock_runner)

    assert apt._runner is mock_runner
    assert apt.refresh._runner is mock_runner
    assert apt.install._runner is mock_runner
    assert apt.remove._runner is mock_runner
    assert apt.upgrade._runner is mock_runner
    assert apt.search._runner is mock_runner
    assert apt.info._runner is mock_runner
    assert apt.list_installed._runner is mock_runner
    assert apt.is_installed._runner is mock_runner
    assert apt.download._runner is mock_runner
    assert apt.clean._runner is mock_runner
    assert apt.autoremove._runner is mock_runner

    apt.install.run(["curl"])
    mock_runner.assert_called_once_with(
        ["apt-get", "install", "-y", "curl"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
