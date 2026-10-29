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
"""Integration tests for Apt package manager against container instances."""

import pytest
from craft_packages.apt import Apt

pytestmark = [pytest.mark.slow]


def test_apt_refresh(apt_container: Apt) -> None:
    """Test refreshing package lists in the container."""
    result = apt_container.refresh.run()
    assert result.hits > 0 or result.gets > 0


def test_apt_search(apt_container: Apt) -> None:
    """Test searching for packages in the container."""
    results = apt_container.search.run("hello")
    assert "hello" in results


def test_apt_info(apt_container: Apt) -> None:
    """Test displaying package info in the container."""
    info = apt_container.info.run("hello")
    assert info.get("Package") == "hello"


def test_apt_download(apt_container: Apt) -> None:
    """Test downloading package archives without installing."""
    downloaded = apt_container.download.run(["hello"])
    assert "hello" in downloaded


def test_apt_clean(apt_container: Apt) -> None:
    """Test cleaning package cache."""
    assert apt_container.clean.run() is None


def test_apt_start(apt_container: Apt) -> None:
    """Test start method returns a Popen object."""
    proc = apt_container.is_installed.start("hello")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_apt_install_query_and_remove(apt_container: Apt) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    assert apt_container.is_installed.run("hello") is False

    # Install package
    installed = apt_container.install.run(["hello"])
    assert any(pkg.startswith("hello=") for pkg in installed)

    # Verify is_installed is True
    assert apt_container.is_installed.run("hello") is True

    # Verify package appears in list_installed
    all_installed = apt_container.list_installed.run()
    assert any(pkg.startswith("hello=") for pkg in all_installed)

    # Remove package
    removed = apt_container.remove.run(["hello"])
    assert "hello" in removed

    # Verify is_installed is False again
    assert apt_container.is_installed.run("hello") is False


def test_apt_upgrade(apt_container: Apt) -> None:
    """Test package upgrade in the container."""
    upgraded = apt_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_apt_autoremove(apt_container: Apt) -> None:
    """Test autoremove in the container."""
    removed = apt_container.autoremove.run()
    assert isinstance(removed, list)
