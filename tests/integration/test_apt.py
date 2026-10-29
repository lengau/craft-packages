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
"""Integration tests for Apt package manager against an Ubuntu 26.04 container."""

import pytest
from craft_packages.apt import Apt

pytestmark = [pytest.mark.slow]


def test_apt_refresh(apt_container: Apt) -> None:
    """Test refreshing package lists in the container."""
    proc = apt_container.refresh.run()
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    result = apt_container.refresh.interpret(proc.stdout)
    assert result.hits > 0 or result.gets > 0


def test_apt_search(apt_container: Apt) -> None:
    """Test searching for packages in the container."""
    proc = apt_container.search.run("hello")
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    results = apt_container.search.interpret(proc.stdout)
    assert "hello" in results


def test_apt_info(apt_container: Apt) -> None:
    """Test displaying package info in the container."""
    proc = apt_container.info.run("hello")
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    info = apt_container.info.interpret(proc.stdout)
    assert info.get("Package") == "hello"


def test_apt_download(apt_container: Apt) -> None:
    """Test downloading package archives without installing."""
    proc = apt_container.download.run(["hello"])
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    downloaded = apt_container.download.interpret(proc.stdout)
    assert "hello" in downloaded


def test_apt_clean(apt_container: Apt) -> None:
    """Test cleaning package cache."""
    proc = apt_container.clean.run()
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    assert apt_container.clean.interpret(proc.stdout) is None


def test_apt_install_query_and_remove(apt_container: Apt) -> None:
    """Test package install, query, list-installed, and remove lifecycle."""
    # Ensure package is not installed initially
    proc_check = apt_container.is_installed.run("hello")
    proc_check.wait()
    assert proc_check.stdout is not None
    assert apt_container.is_installed.interpret(proc_check.stdout) is False

    # Install package
    proc_install = apt_container.install.run(["hello"])
    proc_install.wait()
    assert proc_install.returncode == 0
    assert proc_install.stdout is not None
    installed = apt_container.install.interpret(proc_install.stdout)
    assert any(pkg.startswith("hello=") for pkg in installed)

    # Verify is_installed is True
    proc_check2 = apt_container.is_installed.run("hello")
    proc_check2.wait()
    assert proc_check2.stdout is not None
    assert apt_container.is_installed.interpret(proc_check2.stdout) is True

    # Verify package appears in list_installed
    proc_list = apt_container.list_installed.run()
    proc_list.wait()
    assert proc_list.returncode == 0
    assert proc_list.stdout is not None
    all_installed = apt_container.list_installed.interpret(proc_list.stdout)
    assert any(pkg.startswith("hello=") for pkg in all_installed)

    # Remove package
    proc_remove = apt_container.remove.run(["hello"])
    proc_remove.wait()
    assert proc_remove.returncode == 0
    assert proc_remove.stdout is not None
    removed = apt_container.remove.interpret(proc_remove.stdout)
    assert "hello" in removed

    # Verify is_installed is False again
    proc_check3 = apt_container.is_installed.run("hello")
    proc_check3.wait()
    assert proc_check3.stdout is not None
    assert apt_container.is_installed.interpret(proc_check3.stdout) is False


def test_apt_upgrade(apt_container: Apt) -> None:
    """Test package upgrade in the container."""
    proc = apt_container.upgrade.run()
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    upgraded = apt_container.upgrade.interpret(proc.stdout)
    assert isinstance(upgraded, list)


def test_apt_autoremove(apt_container: Apt) -> None:
    """Test autoremove in the container."""
    proc = apt_container.autoremove.run()
    proc.wait()
    assert proc.returncode == 0
    assert proc.stdout is not None
    removed = apt_container.autoremove.interpret(proc.stdout)
    assert isinstance(removed, list)
