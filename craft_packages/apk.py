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
"""APK package manager implementation."""

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

_APK_NVR_PARTS_COUNT = 3


@dataclass(frozen=True)
class ApkRefreshResult:
    """Result of an apk update run."""

    repositories_updated: bool = False
    repository_count: int = 0


class ApkRefresh(RefreshAction[ApkRefreshResult]):
    """Refresh APK package repository indexes."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apk update command."""
        del kwargs
        return ["apk", "update"]

    def interpret(self, stream: IO[str]) -> ApkRefreshResult:
        """Parse apk update output.

        Example command output::

            fetch https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz
            fetch https://dl-cdn.alpinelinux.org/alpine/v3.22/community/x86_64/APKINDEX.tar.gz
            v3.22.7-13-gf17baf46742 [https://dl-cdn.alpinelinux.org/alpine/v3.22/community]
            OK: 20710 distinct packages available

        Example output:
            ApkRefreshResult(repositories_updated=True, repository_count=2)
        """
        repos = 0
        updated = False
        for line in stream:
            stripped = line.strip()
            if stripped.startswith("fetch "):
                repos += 1
            elif "distinct packages available" in stripped or "OK:" in stripped:
                updated = True
        return ApkRefreshResult(repositories_updated=updated, repository_count=repos)


class ApkInstall(InstallAction[list[str]]):
    """Install packages using apk."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        no_cache: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apk add command."""
        del kwargs
        cmd = ["apk", "add"]
        if no_cache:
            cmd.append("--no-cache")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from apk output.

        Example command output::

            (1/1) Installing tree (2.2.1-r0)
            Executing busybox-1.37.0-r20.trigger
            OK: 9 MiB in 33 packages

        Example output:
            ["tree=2.2.1-r0"]
        """
        pattern = re.compile(r"Installing\s+(\S+)\s+\(([^)]+)\)")
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := pattern.search(line))
        ]


class ApkRemove(RemoveAction[list[str]]):
    """Remove packages using apk."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        purge: bool = False,
        rdepends: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apk del command."""
        del kwargs
        cmd = ["apk", "del"]
        if purge:
            cmd.append("--purge")
        if rdepends:
            cmd.append("--rdepends")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from apk output.

        Example command output::

            (1/1) Purging tree (2.2.1-r0)
            Executing busybox-1.37.0-r20.trigger
            OK: 9 MiB in 32 packages

        Example output:
            ["tree"]
        """
        pattern = re.compile(r"(?:Purging|Erasing)\s+(\S+)")
        return [match.group(1) for line in stream if (match := pattern.search(line))]


class ApkUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using apk."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        *,
        available: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apk upgrade command."""
        del kwargs
        cmd = ["apk", "upgrade"]
        if available:
            cmd.append("--available")
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from apk output.

        Example command output::

            (1/1) Upgrading tree (2.2.0-r0 -> 2.2.1-r0)
            OK: 9 MiB in 33 packages

        Example output:
            ["tree=2.2.1-r0"]
        """
        upgrade_pattern = re.compile(
            r"(?:Upgrading|Installing)\s+(\S+)\s+\((?:.*?->\s*)?([^)]+)\)"
        )
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := upgrade_pattern.search(line))
        ]


class ApkSearch(SearchAction[dict[str, str]]):
    """Search packages using apk."""

    def get_command(
        self,
        query: str,
        *,
        exact: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apk search command."""
        del kwargs
        cmd = ["apk", "search", "-v"]
        if exact:
            cmd.append("-e")
        cmd.append(query)
        return cmd

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse apk search output.

        Example command output::

            tree-2.2.1-r0 - Recursive directory indented listing of files

        Example output:
            {"tree": "Recursive directory indented listing of files"}
        """
        results: dict[str, str] = {}
        for line in stream:
            line_str = line.strip()
            if " - " in line_str:
                pkg_ver, _, desc = line_str.partition(" - ")
                subparts = pkg_ver.rsplit("-", 2)
                name = subparts[0] if len(subparts) == _APK_NVR_PARTS_COUNT else pkg_ver
                results[name] = desc.strip()
        return results


class ApkInfo(InfoAction[dict[str, str]]):
    """Show package details using apk."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the apk info command."""
        del kwargs
        return ["apk", "info", "-a", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse apk info key-value output.

        Example command output::

            tree-2.2.1-r0 description:
            Recursive directory indented listing of files

            tree-2.2.1-r0 webpage:
            https://oldmanprogrammer.net/source.php?dir=projects/tree

        Example output:
            {
                "description": "Recursive directory indented listing of files",
                "webpage": "https://oldmanprogrammer.net/source.php?dir=projects/tree",
            }
        """
        info: dict[str, str] = {}
        current_key: str | None = None
        header_pattern = re.compile(r"^\S+\s+([^:]+):$")

        for line in stream:
            stripped = line.strip()
            if match := header_pattern.match(stripped):
                current_key = match.group(1).strip()
                info[current_key] = ""
            elif current_key and stripped:
                if info[current_key]:
                    info[current_key] += "\n" + stripped
                else:
                    info[current_key] = stripped

        return info


class ApkListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using apk info."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apk info -v command."""
        del kwargs
        return ["apk", "info", "-v"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings.

        Example command output::

            acl-libs-2.3.2-r1
            tree-2.2.1-r0

        Example output:
            ["acl-libs=2.3.2-r1", "tree=2.2.1-r0"]
        """
        installed: list[str] = []
        for line in stream:
            stripped = line.strip()
            if stripped:
                subparts = stripped.rsplit("-", 2)
                if len(subparts) == _APK_NVR_PARTS_COUNT:
                    installed.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                else:
                    installed.append(stripped)
        return sorted(installed)


class ApkIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using apk."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the apk info -e command."""
        del kwargs
        return ["apk", "info", "-e", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse apk info -e output.

        Example command output::

            tree

        Example output:
            True
        """
        content = stream.read().strip()
        return bool(content)


class ApkDownload(DownloadAction[list[str]]):
    """Download package archives using apk fetch."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        destdir: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apk fetch command."""
        del kwargs
        cmd = ["apk", "fetch"]
        if destdir:
            cmd.extend(["-o", destdir])
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from apk output.

        Example command output::

            Downloading tree-2.2.1-r0

        Example output:
            ["tree"]
        """
        downloaded: list[str] = []
        pattern = re.compile(r"Downloading\s+(\S+)")

        for line in stream:
            if match := pattern.search(line):
                pkg_ver = match.group(1)
                subparts = pkg_ver.rsplit("-", 2)
                name = subparts[0] if len(subparts) == _APK_NVR_PARTS_COUNT else pkg_ver
                downloaded.append(name)

        return downloaded


class ApkClean(CleanAction[None]):
    """Clean APK package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apk cache clean command."""
        del kwargs
        return ["apk", "cache", "clean"]

    def interpret(self, stream: IO[str]) -> None:
        """Parse clean output.

        apk cache clean produces no structured output.

        Example output:
            None
        """
        del stream


class ApkAutoremove(AutoremoveAction[list[str]]):
    """Purge unused cached packages using apk."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apk cache purge command."""
        del kwargs
        return ["apk", "cache", "purge"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from apk output.

        apk cache purge produces no structured package removal list.

        Example output:
            []
        """
        del stream
        return []


class Apk(BasePackageManager):
    """APK package manager interface."""

    @property
    def refresh(self) -> ApkRefresh:
        """Refresh repository metadata."""
        return ApkRefresh(self._runner)

    @property
    def install(self) -> ApkInstall:
        """Install packages."""
        return ApkInstall(self._runner)

    @property
    def remove(self) -> ApkRemove:
        """Remove packages."""
        return ApkRemove(self._runner)

    @property
    def upgrade(self) -> ApkUpgrade:
        """Upgrade packages."""
        return ApkUpgrade(self._runner)

    @property
    def search(self) -> ApkSearch:
        """Search packages."""
        return ApkSearch(self._runner)

    @property
    def info(self) -> ApkInfo:
        """Display package details."""
        return ApkInfo(self._runner)

    @property
    def list_installed(self) -> ApkListInstalled:
        """List installed packages."""
        return ApkListInstalled(self._runner)

    @property
    def is_installed(self) -> ApkIsInstalled:
        """Check if package is installed."""
        return ApkIsInstalled(self._runner)

    @property
    def download(self) -> ApkDownload:
        """Download packages without installation."""
        return ApkDownload(self._runner)

    @property
    def clean(self) -> ApkClean:
        """Clean package cache."""
        return ApkClean(self._runner)

    @property
    def autoremove(self) -> ApkAutoremove:
        """Remove unused dependencies."""
        return ApkAutoremove(self._runner)
