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
"""Integration tests for Pacman package manager against Arch Linux."""

import pytest
from craft_packages.pacman import Pacman

pytestmark = [pytest.mark.slow]


def test_pacman_refresh(pacman_container: Pacman) -> None:
    """Test refreshing package databases in the container."""
    result = pacman_container.refresh.run()
    assert result.databases_synchronized or result.database_count > 0


def test_pacman_search(pacman_container: Pacman) -> None:
    """Test searching for packages in the container."""
    results = pacman_container.search.run("tree")
    assert "tree" in results


def test_pacman_info(pacman_container: Pacman) -> None:
    """Test displaying package info in the container."""
    info = pacman_container.info.run("tree")
    assert info.get("Name") == "tree"


def test_pacman_download(pacman_container: Pacman) -> None:
    """Test downloading package archives without installing."""
    downloaded = pacman_container.download.run(["tree"])
    assert "tree" in downloaded


def test_pacman_start(pacman_container: Pacman) -> None:
    """Test start method returns a Popen object."""
    proc = pacman_container.is_installed.start("tree")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_pacman_install_query_and_remove(pacman_container: Pacman) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    assert pacman_container.is_installed.run("tree") is False

    # Install package
    installed = pacman_container.install.run(["tree"])
    assert any(pkg.startswith("tree") for pkg in installed)

    # Verify is_installed is True
    assert pacman_container.is_installed.run("tree") is True

    # Verify package appears in list_installed
    all_installed = pacman_container.list_installed.run()
    assert any(pkg.startswith("tree=") for pkg in all_installed)

    # Remove package
    removed = pacman_container.remove.run(["tree"])
    assert "tree" in removed

    # Verify is_installed is False again
    assert pacman_container.is_installed.run("tree") is False


def test_pacman_upgrade(pacman_container: Pacman) -> None:
    """Test package upgrade in the container."""
    upgraded = pacman_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_pacman_autoremove(pacman_container: Pacman) -> None:
    """Test autoremove in the container."""
    removed = pacman_container.autoremove.run()
    assert isinstance(removed, list)


def test_pacman_clean(pacman_container: Pacman) -> None:
    """Test cleaning package cache."""
    assert pacman_container.clean.run() is None
