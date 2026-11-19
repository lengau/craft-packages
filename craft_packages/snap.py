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
"""Snap package manager implementation."""

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

_SNAP_FIND_FIELDS_MIN = 5
_SNAP_LIST_FIELDS_MIN = 2


@dataclass(frozen=True)
class SnapRefreshResult:
    """Result of a snap refresh run."""

    refreshed: bool = False
    snap_count: int = 0


class SnapRefresh(RefreshAction[SnapRefreshResult]):
    """Refresh snap packages."""

    def get_command(
        self,
        *,
        hold: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the snap refresh command."""
        del kwargs
        cmd = ["snap", "refresh", "--color=never", "--unicode=never"]
        if hold:
            cmd.append(f"--hold={hold}")
        return cmd

    def interpret(self, stream: IO[str]) -> SnapRefreshResult:
        """Parse snap refresh output.

        Example command output::

            All snaps up to date.

        Example output:
            SnapRefreshResult(refreshed=True, snap_count=0)
        """
        refreshed = False
        snap_count = 0
        pattern = re.compile(r"^\S+\s+(?:\([^)]+\)\s+)?\S+\s+from\s+.*?refreshed")

        for line in stream:
            stripped = line.strip()
            if "All snaps up to date." in stripped:
                refreshed = True
            elif pattern.match(stripped):
                refreshed = True
                snap_count += 1

        return SnapRefreshResult(refreshed=refreshed, snap_count=snap_count)


class SnapInstall(InstallAction[list[str]]):
    """Install snaps."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        classic: bool = False,
        devmode: bool = False,
        dangerous: bool = False,
        channel: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the snap install command."""
        del kwargs
        cmd = ["snap", "install", "--color=never", "--unicode=never"]
        if classic:
            cmd.append("--classic")
        if devmode:
            cmd.append("--devmode")
        if dangerous:
            cmd.append("--dangerous")
        if channel:
            cmd.append(f"--channel={channel}")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed snaps from snap output.

        Example command output::

            hello 2.10 from Canonical** installed

        Example output:
            ["hello=2.10"]
        """
        pattern = re.compile(r"^(\S+)\s+(\S+)\s+from\s+.*?installed")
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := pattern.match(line.strip()))
        ]


class SnapRemove(RemoveAction[list[str]]):
    """Remove snaps."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        purge: bool = False,
        revision: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the snap remove command."""
        del kwargs
        cmd = ["snap", "remove"]
        if purge:
            cmd.append("--purge")
        if revision:
            cmd.append(f"--revision={revision}")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed snaps from snap output.

        Example command output::

            hello removed (snap data snapshot saved)

        Example output:
            ["hello"]
        """
        pattern = re.compile(r"^(\S+)\s+removed")
        return [
            match.group(1) for line in stream if (match := pattern.match(line.strip()))
        ]


class SnapUpgrade(UpgradeAction[list[str]]):
    """Upgrade/refresh specific snaps."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        *,
        channel: str | None = None,
        classic: bool = False,
        devmode: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the snap refresh command for specific snaps."""
        del kwargs
        cmd = ["snap", "refresh", "--color=never", "--unicode=never"]
        if classic:
            cmd.append("--classic")
        if devmode:
            cmd.append("--devmode")
        if channel:
            cmd.append(f"--channel={channel}")
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse refreshed snaps from snap output.

        Example command output::

            hello (stable) 2.10 from Canonical** refreshed

        Example output:
            ["hello=2.10"]
        """
        pattern = re.compile(r"^(\S+)\s+(?:\([^)]+\)\s+)?(\S+)\s+from\s+.*?refreshed")
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := pattern.match(line.strip()))
        ]


class SnapSearch(SearchAction[dict[str, str]]):
    """Search snaps using snap find."""

    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the snap find command."""
        del kwargs
        return ["snap", "find", "--color=never", "--unicode=never", query]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse snap find table output.

        Example command output::

            Name  Version  Publisher  Notes  Summary
            tree  2.1.3    brlin      -      A directory listing command

        Example output:
            {"tree": "A directory listing command"}
        """
        results: dict[str, str] = {}
        header_seen = False

        for line in stream:
            stripped = line.strip()
            if not header_seen:
                if stripped.startswith("Name"):
                    header_seen = True
                continue
            parts = stripped.split(None, 4)
            if len(parts) >= _SNAP_FIND_FIELDS_MIN:
                results[parts[0]] = parts[4]
            elif len(parts) >= _SNAP_LIST_FIELDS_MIN:
                results[parts[0]] = parts[-1]

        return results


class SnapInfo(InfoAction[dict[str, str]]):
    """Show snap details using snap info."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the snap info command."""
        del kwargs
        return ["snap", "info", "--color=never", "--unicode=never", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        r"""Parse snap info key-value output.

        Example command output::

            name:      hello
            summary:   GNU Hello, the "hello world" snap
            publisher: Canonical**
            store-url: https://snapcraft.io/hello

        Example output:
            {
                "name": "hello",
                "summary": "GNU Hello, the \"hello world\" snap",
                "publisher": "Canonical**",
                "store-url": "https://snapcraft.io/hello",
            }
        """
        info: dict[str, str] = {}
        current_key: str | None = None

        for line in stream:
            if ":" in line and not line.startswith((" ", "\t")):
                key, _, val = line.partition(":")
                current_key = key.strip()
                info[current_key] = val.strip()
            elif current_key and line.startswith((" ", "\t")):
                info[current_key] += "\n" + line.strip()

        return info


class SnapListInstalled(ListInstalledAction[list[str]]):
    """List installed snaps using snap list."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the snap list command."""
        del kwargs
        return ["snap", "list", "--color=never", "--unicode=never"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed snaps into package=version strings.

        Example command output::

            Name       Version  Rev   Tracking  Publisher  Notes
            astral-uv  0.13.5   1821  latest    lengau*    classic
            hello      2.10     42    latest    canonical  -

        Example output:
            ["astral-uv=0.13.5", "hello=2.10"]
        """
        installed: list[str] = []
        header_seen = False

        for line in stream:
            stripped = line.strip()
            if not header_seen:
                if stripped.startswith("Name"):
                    header_seen = True
                continue
            parts = stripped.split()
            if len(parts) >= _SNAP_LIST_FIELDS_MIN:
                installed.append(f"{parts[0]}={parts[1]}")

        return sorted(installed)


class SnapIsInstalled(IsInstalledAction[bool]):
    """Check if snap is installed using snap list."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the snap list command for a specific snap."""
        del kwargs
        return ["snap", "list", "--color=never", "--unicode=never", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse snap list output.

        Example command output::

            Name   Version  Rev  Tracking  Publisher  Notes
            hello  2.10     42   latest    canonical  -

        Example output:
            True
        """
        header_seen = False
        for line in stream:
            stripped = line.strip()
            if not header_seen:
                if stripped.startswith("Name"):
                    header_seen = True
                continue
            if stripped and not stripped.startswith("error:"):
                return True
        return False


class SnapDownload(DownloadAction[list[str]]):
    """Download snaps using snap download."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        destdir: str | None = None,
        channel: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the snap download command."""
        del kwargs
        cmd = ["snap", "download"]
        if destdir:
            cmd.append(f"--target-directory={destdir}")
        if channel:
            cmd.append(f"--channel={channel}")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded snap names from snap output.

        Example command output::

            Fetching snap "hello"
            Fetching assertions for "hello"

        Example output:
            ["hello"]
        """
        pattern = re.compile(r'Fetching snap "([^"]+)"')
        return [match.group(1) for line in stream if (match := pattern.search(line))]


class SnapClean(CleanAction[None]):
    """Clean snap temporary download cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the snap cache clean command."""
        del kwargs
        return ["sh", "-c", "rm -rf /var/lib/snapd/cache/*"]

    def interpret(self, stream: IO[str]) -> None:
        """Parse clean output.

        Snap cache clean produces no structured output.

        Example output:
            None
        """
        del stream


class SnapAutoremove(AutoremoveAction[list[str]]):
    """Remove disabled snap revisions."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the command for removing disabled snaps."""
        del kwargs
        return [
            "sh",
            "-c",
            'snap list --all 2>/dev/null | grep "disabled" | while read -r name ver rev rest; do snap remove "$name" --revision="$rev"; done || true',
        ]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed snaps from snap remove output.

        Example command output::

            hello removed

        Example output:
            ["hello"]
        """
        pattern = re.compile(r"^(\S+)\s+removed")
        return [
            match.group(1) for line in stream if (match := pattern.match(line.strip()))
        ]


class Snap(BasePackageManager):
    """Snap package manager interface."""

    @property
    def refresh(self) -> SnapRefresh:
        """Refresh repository metadata."""
        return SnapRefresh(self._runner)

    @property
    def install(self) -> SnapInstall:
        """Install packages."""
        return SnapInstall(self._runner)

    @property
    def remove(self) -> SnapRemove:
        """Remove packages."""
        return SnapRemove(self._runner)

    @property
    def upgrade(self) -> SnapUpgrade:
        """Upgrade packages."""
        return SnapUpgrade(self._runner)

    @property
    def search(self) -> SnapSearch:
        """Search packages."""
        return SnapSearch(self._runner)

    @property
    def info(self) -> SnapInfo:
        """Display package details."""
        return SnapInfo(self._runner)

    @property
    def list_installed(self) -> SnapListInstalled:
        """List installed packages."""
        return SnapListInstalled(self._runner)

    @property
    def is_installed(self) -> SnapIsInstalled:
        """Check if package is installed."""
        return SnapIsInstalled(self._runner)

    @property
    def download(self) -> SnapDownload:
        """Download packages without installation."""
        return SnapDownload(self._runner)

    @property
    def clean(self) -> SnapClean:
        """Clean package cache."""
        return SnapClean(self._runner)

    @property
    def autoremove(self) -> SnapAutoremove:
        """Remove unused dependencies."""
        return SnapAutoremove(self._runner)
