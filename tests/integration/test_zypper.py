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
"""Integration tests for Zypper package manager against openSUSE."""

import pytest
from craft_packages.zypper import Zypper

pytestmark = [pytest.mark.slow]


def test_zypper_refresh(zypper_container: Zypper) -> None:
    """Test refreshing package metadata in the container."""
    result = zypper_container.refresh.run()
    assert result.repositories_refreshed or result.repo_count > 0


def test_zypper_search(zypper_container: Zypper) -> None:
    """Test searching for packages in the container."""
    results = zypper_container.search.run("tree")
    assert "tree" in results


def test_zypper_info(zypper_container: Zypper) -> None:
    """Test displaying package info in the container."""
    info = zypper_container.info.run("tree")
    assert info.get("Name") == "tree"


def test_zypper_download(zypper_container: Zypper) -> None:
    """Test downloading package archives without installing."""
    downloaded = zypper_container.download.run(["tree"])
    assert "tree" in downloaded


def test_zypper_start(zypper_container: Zypper) -> None:
    """Test start method returns a Popen object."""
    proc = zypper_container.is_installed.start("tree")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_zypper_install_query_and_remove(zypper_container: Zypper) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    assert zypper_container.is_installed.run("tree") is False

    # Install package
    installed = zypper_container.install.run(["tree"])
    assert any(pkg.startswith("tree") for pkg in installed)

    # Verify is_installed is True
    assert zypper_container.is_installed.run("tree") is True

    # Verify package appears in list_installed
    all_installed = zypper_container.list_installed.run()
    assert any(pkg.startswith("tree=") for pkg in all_installed)

    # Remove package
    removed = zypper_container.remove.run(["tree"])
    assert "tree" in removed

    # Verify is_installed is False again
    assert zypper_container.is_installed.run("tree") is False


def test_zypper_upgrade(zypper_container: Zypper) -> None:
    """Test package upgrade in the container."""
    upgraded = zypper_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_zypper_autoremove(zypper_container: Zypper) -> None:
    """Test autoremove in the container."""
    removed = zypper_container.autoremove.run()
    assert isinstance(removed, list)


def test_zypper_clean(zypper_container: Zypper) -> None:
    """Test cleaning package cache."""
    assert zypper_container.clean.run() is None
