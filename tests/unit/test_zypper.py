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
"""Unit tests for Zypper package manager and actions."""

import io
import subprocess
from unittest import mock

from craft_packages.zypper import (
    Zypper,
    ZypperAutoremove,
    ZypperClean,
    ZypperDownload,
    ZypperInfo,
    ZypperInstall,
    ZypperIsInstalled,
    ZypperListInstalled,
    ZypperRefresh,
    ZypperRefreshResult,
    ZypperRemove,
    ZypperSearch,
    ZypperUpgrade,
)


def test_zypper_refresh():
    action = ZypperRefresh()
    assert action.get_command() == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "refresh",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <progress name=\"Building repository 'repo-oss' cache\" done=\"1\"/>\n"
        "  <message type=\"info\">All repositories have been refreshed.</message>\n"
        "</stream>\n"
    )
    result = action.interpret(output)
    assert result == ZypperRefreshResult(repositories_refreshed=True, repo_count=1)


def test_zypper_install():
    action = ZypperInstall()
    assert action.get_command(["tree"]) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "install",
        "-y",
        "tree",
    ]
    assert action.get_command(["tree"], no_recommends=True) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "install",
        "-y",
        "--no-recommends",
        "tree",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-install>\n"
        "      <solvable type=\"package\" name=\"tree\" edition=\"2.2.1-160000.2.2\" arch=\"x86_64\"/>\n"
        "    </to-install>\n"
        "  </install-summary>\n"
        "</stream>\n"
    )
    installed = action.interpret(output)
    assert installed == ["tree=2.2.1-160000.2.2"]


def test_zypper_remove():
    action = ZypperRemove()
    assert action.get_command(["tree"]) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "remove",
        "-y",
        "tree",
    ]
    assert action.get_command(["tree"], clean_deps=True) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "remove",
        "-y",
        "--clean-deps",
        "tree",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-remove>\n"
        "      <solvable type=\"package\" name=\"tree\" edition=\"2.2.1-160000.2.2\" arch=\"x86_64\"/>\n"
        "    </to-remove>\n"
        "  </install-summary>\n"
        "</stream>\n"
    )
    removed = action.interpret(output)
    assert removed == ["tree"]


def test_zypper_upgrade():
    action = ZypperUpgrade()
    assert action.get_command() == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "update",
        "-y",
    ]
    assert action.get_command(dist_upgrade=True) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "dist-upgrade",
        "-y",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-upgrade>\n"
        "      <solvable type=\"package\" name=\"tree\" edition=\"2.2.1-160000.2.2\" arch=\"x86_64\"/>\n"
        "    </to-upgrade>\n"
        "  </install-summary>\n"
        "</stream>\n"
    )
    upgraded = action.interpret(output)
    assert upgraded == ["tree=2.2.1-160000.2.2"]


def test_zypper_search():
    action = ZypperSearch()
    assert action.get_command("tree") == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "search",
        "tree",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <search-result>\n"
        "    <solvable-list>\n"
        "      <solvable status=\"not-installed\" name=\"tree\" summary=\"File listing as a tree\" kind=\"package\"/>\n"
        "    </solvable-list>\n"
        "  </search-result>\n"
        "</stream>\n"
    )
    results = action.interpret(output)
    assert results == {"tree": "File listing as a tree"}


def test_zypper_info():
    action = ZypperInfo()
    assert action.get_command("tree") == [
        "zypper",
        "--non-interactive",
        "info",
        "tree",
    ]

    output = io.StringIO(
        "Name : tree\nVersion : 2.2.1\nSummary : File listing as a tree\n"
    )
    info = action.interpret(output)
    assert info == {
        "Name": "tree",
        "Version": "2.2.1",
        "Summary": "File listing as a tree",
    }


def test_zypper_list_installed():
    action = ZypperListInstalled()
    assert action.get_command() == [
        "rpm",
        "-qa",
        "--qf",
        "%{NAME}=%{VERSION}-%{RELEASE}\n",
    ]

    output = io.StringIO("tree=2.2.1-160000.2.2\n")
    assert action.interpret(output) == ["tree=2.2.1-160000.2.2"]


def test_zypper_is_installed():
    action = ZypperIsInstalled()
    assert action.get_command("tree") == ["rpm", "-q", "tree"]

    assert action.interpret(io.StringIO("tree-2.2.1-160000.2.2.x86_64\n")) is True
    assert action.interpret(io.StringIO("package tree is not installed\n")) is False


def test_zypper_download():
    action = ZypperDownload()
    assert action.get_command(["tree"]) == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "install",
        "-d",
        "-y",
        "tree",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-install>\n"
        "      <solvable type=\"package\" name=\"tree\" edition=\"2.2.1-160000.2.2\" arch=\"x86_64\"/>\n"
        "    </to-install>\n"
        "  </install-summary>\n"
        "</stream>\n"
    )
    assert action.interpret(output) == ["tree"]


def test_zypper_clean():
    action = ZypperClean()
    assert action.get_command() == [
        "zypper",
        "--non-interactive",
        "clean",
        "-a",
    ]
    assert action.interpret(io.StringIO("")) is None


def test_zypper_autoremove():
    action = ZypperAutoremove()
    assert action.get_command() == [
        "zypper",
        "--xmlout",
        "--non-interactive",
        "remove",
        "--clean-deps",
        "-y",
    ]

    output = io.StringIO(
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-remove>\n"
        "      <solvable type=\"package\" name=\"unused-pkg\" edition=\"1.0-1\" arch=\"x86_64\"/>\n"
        "    </to-remove>\n"
        "  </install-summary>\n"
        "</stream>\n"
    )
    assert action.interpret(output) == ["unused-pkg"]


def test_zypper_manager():
    mock_runner = mock.Mock()
    zypper = Zypper(runner=mock_runner)

    assert zypper._runner is mock_runner
    assert zypper.refresh._runner is mock_runner
    assert zypper.install._runner is mock_runner
    assert zypper.remove._runner is mock_runner
    assert zypper.upgrade._runner is mock_runner
    assert zypper.search._runner is mock_runner
    assert zypper.info._runner is mock_runner
    assert zypper.list_installed._runner is mock_runner
    assert zypper.is_installed._runner is mock_runner
    assert zypper.download._runner is mock_runner
    assert zypper.clean._runner is mock_runner
    assert zypper.autoremove._runner is mock_runner

    mock_proc = mock.Mock()
    mock_proc.communicate.return_value = (
        "<?xml version='1.0'?>\n"
        "<stream>\n"
        "  <install-summary>\n"
        "    <to-install>\n"
        "      <solvable type=\"package\" name=\"tree\" edition=\"2.2.1-160000.2.2\" arch=\"x86_64\"/>\n"
        "    </to-install>\n"
        "  </install-summary>\n"
        "</stream>\n",
        "",
    )
    mock_runner.return_value = mock_proc

    installed = zypper.install.run(["tree"])
    assert installed == ["tree=2.2.1-160000.2.2"]

    mock_runner.assert_called_with(
        ["zypper", "--xmlout", "--non-interactive", "install", "-y", "tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
