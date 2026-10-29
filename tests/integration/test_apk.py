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
"""Integration tests for APK package manager against Alpine Linux."""

import pytest
from craft_packages.apk import Apk

pytestmark = [pytest.mark.slow]


def test_apk_refresh(apk_container: Apk) -> None:
    """Test refreshing package indexes in the container."""
    result = apk_container.refresh.run()
    assert result.repositories_updated or result.repository_count > 0


def test_apk_search(apk_container: Apk) -> None:
    """Test searching for packages in the container."""
    results = apk_container.search.run("tree")
    assert "tree" in results


def test_apk_info(apk_container: Apk) -> None:
    """Test displaying package info in the container."""
    info = apk_container.info.run("tree")
    assert "description" in info


def test_apk_download(apk_container: Apk) -> None:
    """Test downloading package archives without installing."""
    downloaded = apk_container.download.run(["tree"], destdir="/tmp")
    assert "tree" in downloaded


def test_apk_start(apk_container: Apk) -> None:
    """Test start method returns a Popen object."""
    proc = apk_container.is_installed.start("tree")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_apk_install_query_and_remove(apk_container: Apk) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    assert apk_container.is_installed.run("tree") is False

    # Install package
    installed = apk_container.install.run(["tree"])
    assert any(pkg.startswith("tree") for pkg in installed)

    # Verify is_installed is True
    assert apk_container.is_installed.run("tree") is True

    # Verify package appears in list_installed
    all_installed = apk_container.list_installed.run()
    assert any(pkg.startswith("tree=") for pkg in all_installed)

    # Remove package
    removed = apk_container.remove.run(["tree"])
    assert "tree" in removed

    # Verify is_installed is False again
    assert apk_container.is_installed.run("tree") is False


def test_apk_upgrade(apk_container: Apk) -> None:
    """Test package upgrade in the container."""
    upgraded = apk_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_apk_autoremove(apk_container: Apk) -> None:
    """Test autoremove in the container."""
    removed = apk_container.autoremove.run()
    assert isinstance(removed, list)


def test_apk_clean(apk_container: Apk) -> None:
    """Test cleaning package cache."""
    assert apk_container.clean.run() is None
