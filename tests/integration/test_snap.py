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
"""Integration tests for Snap package manager."""

import pytest
from craft_packages.snap import Snap

pytestmark = [pytest.mark.slow]


def test_snap_refresh(snap_container: Snap) -> None:
    """Test refreshing snaps in the container."""
    result = snap_container.refresh.run()
    assert result.refreshed


def test_snap_search(snap_container: Snap) -> None:
    """Test searching for snaps in the store."""
    results = snap_container.search.run("hello")
    assert "hello" in results


def test_snap_info(snap_container: Snap) -> None:
    """Test displaying snap info."""
    info = snap_container.info.run("hello")
    assert info.get("name") == "hello"


def test_snap_download(snap_container: Snap) -> None:
    """Test downloading a snap without installing."""
    downloaded = snap_container.download.run(["hello"], destdir="/tmp")
    assert "hello" in downloaded


def test_snap_start(snap_container: Snap) -> None:
    """Test start method returns a Popen object."""
    proc = snap_container.is_installed.start("hello")
    proc.wait()
    assert proc.returncode in (0, 1)


def test_snap_install_query_and_remove(snap_container: Snap) -> None:
    """Test snap install, query, list-installed, and remove lifecycle."""
    # Ensure snap is not installed initially
    assert snap_container.is_installed.run("hello") is False

    # Install snap
    installed = snap_container.install.run(["hello"])
    assert any(s.startswith("hello=") for s in installed)

    # Verify is_installed is True
    assert snap_container.is_installed.run("hello") is True

    # Verify package appears in list_installed
    all_installed = snap_container.list_installed.run()
    assert any(s.startswith("hello=") for s in all_installed)

    # Remove snap
    removed = snap_container.remove.run(["hello"])
    assert "hello" in removed

    # Verify is_installed is False again
    assert snap_container.is_installed.run("hello") is False


def test_snap_upgrade(snap_container: Snap) -> None:
    """Test snap refresh command."""
    upgraded = snap_container.upgrade.run()
    assert isinstance(upgraded, list)


def test_snap_autoremove(snap_container: Snap) -> None:
    """Test removing disabled snaps."""
    removed = snap_container.autoremove.run()
    assert isinstance(removed, list)


def test_snap_clean(snap_container: Snap) -> None:
    """Test cleaning snap cache."""
    assert snap_container.clean.run() is None
