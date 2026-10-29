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
"""Zypper package manager implementation."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import IO, Any

from .actions import (
    AutoremoveAction,
    CleanAction,
    DownloadAction,
    InfoAction,
    InstallAction,
    IsInstalledAction,
    ListInstalledAction,
    RefreshAction,
    RemoveAction,
    SearchAction,
    UpgradeAction,
)
from .manager import BasePackageManager

_ZYPPER_SEARCH_FIELDS_MIN = 3
_RPM_NVR_PARTS_COUNT = 3


@dataclass(frozen=True)
class ZypperRefreshResult:
    """Result of a zypper refresh run."""

    repositories_refreshed: bool = False
    repo_count: int = 0


class ZypperRefresh(RefreshAction[ZypperRefreshResult]):
    """Refresh Zypper package metadata."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the zypper refresh command."""
        del kwargs
        return ["zypper", "--non-interactive", "refresh"]

    def interpret(self, stream: IO[str]) -> ZypperRefreshResult:
        """Parse zypper refresh output.

        Example command output::

            Building repository 'repo-oss' cache [....done]
            All repositories have been refreshed.

        Example output:
            ZypperRefreshResult(repositories_refreshed=True, repo_count=1)
        """
        repos = 0
        refreshed = False
        for line in stream:
            stripped = line.strip()
            if "All repositories have been refreshed." in stripped:
                refreshed = True
            elif (
                "Building repository" in stripped or "Retrieving repository" in stripped
            ):
                repos += 1
        return ZypperRefreshResult(repositories_refreshed=refreshed, repo_count=repos)


class ZypperInstall(InstallAction[list[str]]):
    """Install packages using zypper."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        no_recommends: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the zypper install command."""
        del kwargs
        cmd = ["zypper", "--non-interactive", "install", "-y"]
        if no_recommends:
            cmd.append("--no-recommends")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from zypper output.

        Example command output::

            (1/1) Installing: tree-2.2.1-160000.2.2.x86_64 [..done]

        Example output:
            ["tree=2.2.1-160000.2.2"]
        """
        installed: list[str] = []
        pattern = re.compile(r"Installing:\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                full_pkg = match.group(1)
                without_arch = full_pkg.rsplit(".", 1)[0]
                subparts = without_arch.rsplit("-", 2)
                if len(subparts) == _RPM_NVR_PARTS_COUNT:
                    installed.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                else:
                    installed.append(without_arch)

        return installed


class ZypperRemove(RemoveAction[list[str]]):
    """Remove packages using zypper."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        clean_deps: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the zypper remove command."""
        del kwargs
        cmd = ["zypper", "--non-interactive", "remove", "-y"]
        if clean_deps:
            cmd.append("--clean-deps")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from zypper output.

        Example command output::

            (1/1) Removing: tree-2.2.1-160000.2.2.x86_64 [..done]

        Example output:
            ["tree"]
        """
        removed: list[str] = []
        pattern = re.compile(r"Removing:\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                full_pkg = match.group(1)
                without_arch = full_pkg.rsplit(".", 1)[0]
                subparts = without_arch.rsplit("-", 2)
                name = (
                    subparts[0]
                    if len(subparts) == _RPM_NVR_PARTS_COUNT
                    else without_arch
                )
                removed.append(name)

        return removed


class ZypperUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using zypper."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        *,
        dist_upgrade: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the zypper update command."""
        del kwargs
        subcmd = "dist-upgrade" if dist_upgrade else "update"
        cmd = ["zypper", "--non-interactive", subcmd, "-y"]
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from zypper output.

        Example command output::

            (1/1) Installing: tree-2.2.1-160000.2.2.x86_64 [..done]

        Example output:
            ["tree=2.2.1-160000.2.2"]
        """
        upgraded: list[str] = []
        pattern = re.compile(r"Installing:\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                full_pkg = match.group(1)
                without_arch = full_pkg.rsplit(".", 1)[0]
                subparts = without_arch.rsplit("-", 2)
                if len(subparts) == _RPM_NVR_PARTS_COUNT:
                    upgraded.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                else:
                    upgraded.append(without_arch)

        return upgraded


class ZypperSearch(SearchAction[dict[str, str]]):
    """Search packages using zypper."""

    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the zypper search command."""
        del kwargs
        return ["zypper", "--non-interactive", "search", query]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse zypper search table output.

        Example command output::

            S  | Name | Summary                | Type
            ---+------+------------------------+--------
            i+ | tree | File listing as a tree | package

        Example output:
            {"tree": "File listing as a tree"}
        """
        results: dict[str, str] = {}
        for line in stream:
            if "|" in line and not line.startswith(("-", "S  |", "Loading")):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= _ZYPPER_SEARCH_FIELDS_MIN:
                    name = parts[1]
                    summary = parts[2]
                    if name and name != "Name":
                        results[name] = summary
        return results


class ZypperInfo(InfoAction[dict[str, str]]):
    """Show package details using zypper."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the zypper info command."""
        del kwargs
        return ["zypper", "--non-interactive", "info", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse zypper info key-value output.

        Example command output::

            Name : tree
            Version : 2.2.1
            Summary : File listing as a tree

        Example output:
            {
                "Name": "tree",
                "Version": "2.2.1",
                "Summary": "File listing as a tree",
            }
        """
        info: dict[str, str] = {}
        current_key: str | None = None

        for line in stream:
            if " : " in line and not line.startswith((" ", "\t")):
                key, _, val = line.partition(" : ")
                current_key = key.strip()
                info[current_key] = val.strip()
            elif current_key and line.startswith((" ", "\t")):
                info[current_key] += "\n" + line.strip()

        return info


class ZypperListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using rpm query."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the rpm command for listing installed packages."""
        del kwargs
        return ["rpm", "-qa", "--qf", "%{NAME}=%{VERSION}-%{RELEASE}\n"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings.

        Example command output::

            tree=2.2.1-160000.2.2

        Example output:
            ["tree=2.2.1-160000.2.2"]
        """
        return sorted(
            line.strip() for line in stream if line.strip() and "=" in line.strip()
        )


class ZypperIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using rpm."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the rpm command for checking package status."""
        del kwargs
        return ["rpm", "-q", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse rpm -q output.

        Example command output::

            tree-2.2.1-160000.2.2.x86_64

        Example output:
            True
        """
        content = stream.read().strip()
        if not content:
            return False
        return not content.startswith("package ") and "not installed" not in content


class ZypperDownload(DownloadAction[list[str]]):
    """Download package archives using zypper install -d."""

    def get_command(
        self,
        packages: Sequence[str],
        **kwargs: Any,
    ) -> list[str]:
        """Return the zypper download command."""
        del kwargs
        cmd = ["zypper", "--non-interactive", "install", "-d", "-y"]
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from zypper output.

        Example command output::

            Retrieving: tree-2.2.1-160000.2.2.x86_64 (repo-oss (16.0)) (1/1),  84.2 KiB

        Example output:
            ["tree"]
        """
        downloaded: list[str] = []
        pattern = re.compile(r"Retrieving:\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                full_pkg = match.group(1)
                without_arch = full_pkg.rsplit(".", 1)[0]
                subparts = without_arch.rsplit("-", 2)
                name = (
                    subparts[0]
                    if len(subparts) == _RPM_NVR_PARTS_COUNT
                    else without_arch
                )
                downloaded.append(name)

        return downloaded


class ZypperClean(CleanAction[None]):
    """Clean Zypper package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the zypper clean command."""
        del kwargs
        return ["zypper", "--non-interactive", "clean", "-a"]

    def interpret(self, stream: IO[str]) -> None:
        """Parse clean output.

        zypper clean produces no structured output.

        Example output:
            None
        """
        del stream


class ZypperAutoremove(AutoremoveAction[list[str]]):
    """Remove unused packages using zypper."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the zypper autoremove command."""
        del kwargs
        return ["zypper", "--non-interactive", "remove", "--clean-deps", "-y"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from zypper remove output.

        Example command output::

            (1/1) Removing: unused-pkg-1.0-1.x86_64 [..done]

        Example output:
            ["unused-pkg"]
        """
        removed: list[str] = []
        pattern = re.compile(r"Removing:\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                full_pkg = match.group(1)
                without_arch = full_pkg.rsplit(".", 1)[0]
                subparts = without_arch.rsplit("-", 2)
                name = (
                    subparts[0]
                    if len(subparts) == _RPM_NVR_PARTS_COUNT
                    else without_arch
                )
                removed.append(name)

        return removed


class Zypper(BasePackageManager):
    """Zypper package manager interface."""

    @property
    def refresh(self) -> ZypperRefresh:
        """Refresh repository metadata."""
        return ZypperRefresh(self._runner)

    @property
    def install(self) -> ZypperInstall:
        """Install packages."""
        return ZypperInstall(self._runner)

    @property
    def remove(self) -> ZypperRemove:
        """Remove packages."""
        return ZypperRemove(self._runner)

    @property
    def upgrade(self) -> ZypperUpgrade:
        """Upgrade packages."""
        return ZypperUpgrade(self._runner)

    @property
    def search(self) -> ZypperSearch:
        """Search packages."""
        return ZypperSearch(self._runner)

    @property
    def info(self) -> ZypperInfo:
        """Display package details."""
        return ZypperInfo(self._runner)

    @property
    def list_installed(self) -> ZypperListInstalled:
        """List installed packages."""
        return ZypperListInstalled(self._runner)

    @property
    def is_installed(self) -> ZypperIsInstalled:
        """Check if package is installed."""
        return ZypperIsInstalled(self._runner)

    @property
    def download(self) -> ZypperDownload:
        """Download packages without installation."""
        return ZypperDownload(self._runner)

    @property
    def clean(self) -> ZypperClean:
        """Clean package cache."""
        return ZypperClean(self._runner)

    @property
    def autoremove(self) -> ZypperAutoremove:
        """Remove unused dependencies."""
        return ZypperAutoremove(self._runner)
