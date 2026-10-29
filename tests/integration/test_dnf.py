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
"""Integration tests for DNF package manager against Fedora/CentOS/Rocky/Alma."""

import pytest
from craft_packages.dnf import Dnf

pytestmark = [pytest.mark.slow]


def test_dnf_refresh(dnf_container: Dnf) -> None:
    """Test refreshing package metadata in the container."""
    result = dnf_container.refresh.run()
    assert result.metadata_cache_created or result.repo_count > 0


def test_dnf_search(dnf_container: Dnf) -> None:
    """Test searching for packages in the container."""
    results = dnf_container.search.run("tree")
    assert "tree" in results


def test_dnf_info(dnf_container: Dnf) -> None:
    """Test displaying package info in the container."""
    info = dnf_container.info.run("tree")
    assert info.get("Name") == "tree"


def test_dnf_download(dnf_container: Dnf) -> None:
    """Test downloading package archives without installing."""
    downloaded = dnf_container.download.run(["tree"])
    assert "tree" in downloaded


def test_dnf_start(dnf_container: Dnf) -> None:
    """Test start method returns a Popen object."""
    proc = dnf_container.is_installed.start("tree")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_dnf_install_query_and_remove(dnf_container: Dnf) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    assert dnf_container.is_installed.run("tree") is False

    # Install package
    installed = dnf_container.install.run(["tree"])
    assert any(pkg.startswith("tree") for pkg in installed)

    # Verify is_installed is True
    assert dnf_container.is_installed.run("tree") is True

    # Verify package appears in list_installed
    all_installed = dnf_container.list_installed.run()
    assert any(pkg.startswith("tree=") for pkg in all_installed)

    # Remove package
    removed = dnf_container.remove.run(["tree"])
    assert "tree" in removed

    # Verify is_installed is False again
    assert dnf_container.is_installed.run("tree") is False


def test_dnf_upgrade(dnf_container: Dnf) -> None:
    """Test package upgrade in the container."""
    upgraded = dnf_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_dnf_autoremove(dnf_container: Dnf) -> None:
    """Test autoremove in the container."""
    removed = dnf_container.autoremove.run()
    assert isinstance(removed, list)


def test_dnf_clean(dnf_container: Dnf) -> None:
    """Test cleaning package cache."""
    assert dnf_container.clean.run() is None
