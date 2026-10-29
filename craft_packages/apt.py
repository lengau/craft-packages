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
"""Apt package manager implementation."""

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


@dataclass(frozen=True)
class AptRefreshResult:
    """Result of an apt-get update run."""

    hits: int = 0
    gets: int = 0
    ignored: int = 0
    errors: int = 0


class AptRefresh(RefreshAction[AptRefreshResult]):
    """Refresh APT package index."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apt-get update command."""
        del kwargs
        return ["apt-get", "update"]

    def interpret(self, stream: IO[str]) -> AptRefreshResult:
        """Parse apt-get update output."""
        hits = gets = ignored = errors = 0
        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Hit:"):
                hits += 1
            elif stripped.startswith("Get:"):
                gets += 1
            elif stripped.startswith("Ign:"):
                ignored += 1
            elif stripped.startswith("Err:"):
                errors += 1
        return AptRefreshResult(hits=hits, gets=gets, ignored=ignored, errors=errors)


class AptInstall(InstallAction[list[str]]):
    """Install packages using apt-get."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        no_recommends: bool = False,
        allow_downgrades: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apt-get install command."""
        del kwargs
        cmd = ["apt-get", "install", "-y"]
        if no_recommends:
            cmd.append("--no-install-recommends")
        if allow_downgrades:
            cmd.append("--allow-downgrades")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from apt-get output."""
        pattern = re.compile(r"^Setting up\s+([^\s:]+)(?::\S+)?\s+\(([^)]+)\)")
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := pattern.match(line.strip()))
        ]


class AptRemove(RemoveAction[list[str]]):
    """Remove packages using apt-get."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        purge: bool = False,
        autoremove: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apt-get remove or purge command."""
        del kwargs
        subcmd = "purge" if purge else "remove"
        cmd = ["apt-get", subcmd, "-y"]
        if autoremove:
            cmd.append("--autoremove")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from apt-get output."""
        removed: list[str] = []
        pattern = re.compile(
            r"^(?:Removing|Purging configuration files for)\s+([^\s:]+)"
        )
        for line in stream:
            if match := pattern.match(line.strip()):
                pkg = match.group(1)
                if pkg not in removed:
                    removed.append(pkg)
        return removed


class AptUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using apt-get."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        *,
        dist_upgrade: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apt-get upgrade command."""
        del kwargs
        subcmd = "dist-upgrade" if dist_upgrade else "upgrade"
        cmd = ["apt-get", subcmd, "-y"]
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from apt-get output."""
        pattern = re.compile(r"^Setting up\s+([^\s:]+)(?::\S+)?\s+\(([^)]+)\)")
        return [
            f"{match.group(1)}={match.group(2)}"
            for line in stream
            if (match := pattern.match(line.strip()))
        ]


class AptSearch(SearchAction[dict[str, str]]):
    """Search packages using apt-cache."""

    def get_command(
        self, query: str, *, names_only: bool = False, **kwargs: Any
    ) -> list[str]:
        """Return the apt-cache search command."""
        del kwargs
        cmd = ["apt-cache", "search"]
        if names_only:
            cmd.append("--names-only")
        cmd.append(query)
        return cmd

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse package search results."""
        results: dict[str, str] = {}
        for line in stream:
            line_str = line.strip()
            if " - " in line_str:
                pkg, _, desc = line_str.partition(" - ")
                results[pkg.strip()] = desc.strip()
        return results


class AptInfo(InfoAction[dict[str, str]]):
    """Show package details using apt-cache."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the apt-cache show command."""
        del kwargs
        return ["apt-cache", "show", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse RFC822 package information stanza."""
        info: dict[str, str] = {}
        current_key: str | None = None
        for line in stream:
            if line.startswith((" ", "\t")):
                if current_key:
                    info[current_key] += "\n" + line.strip()
            elif ":" in line:
                key, _, val = line.partition(":")
                current_key = key.strip()
                info[current_key] = val.strip()
        return info


_DPKG_STATUS_WORDS_COUNT = 3
_DPKG_QUERY_PARTS_COUNT = 3


def _is_dpkg_installed(status: str) -> bool:
    """Return True if dpkg status represents an installed package."""
    words = status.split()
    return (
        len(words) == _DPKG_STATUS_WORDS_COUNT
        and words[0] in ("install", "hold")
        and words[1] == "ok"
        and words[2] == "installed"
    )


class AptListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using dpkg-query."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the dpkg-query command for listing installed packages."""
        del kwargs
        return ["dpkg-query", "-W", "-f=${Package}\t${Status}\t${Version}\n"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings."""
        packages: list[str] = []
        for line in stream:
            parts = line.strip().split("\t")
            if len(parts) == _DPKG_QUERY_PARTS_COUNT and _is_dpkg_installed(parts[1]):
                packages.append(f"{parts[0]}={parts[2]}")
        return sorted(packages)


class AptIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using dpkg-query."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the dpkg-query command for checking package status."""
        del kwargs
        return ["dpkg-query", "-W", "-f=${Status}\n", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse dpkg-query status output."""
        line = stream.read().strip()
        return _is_dpkg_installed(line) if line else False


class AptDownload(DownloadAction[list[str]]):
    """Download package archives using apt-get."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        no_recommends: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the apt-get download command."""
        del kwargs
        cmd = ["apt-get", "install", "-y", "--download-only"]
        if no_recommends:
            cmd.append("--no-install-recommends")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from apt-get output."""
        pattern = re.compile(
            r"^Get:\d+\s+\S+\s+\S+\s+(?:(?:amd64|arm64|armhf|i386|all|riscv64|s390x|ppc64el)\s+)?([^\s:]+)"
        )
        return [
            match.group(1) for line in stream if (match := pattern.match(line.strip()))
        ]


class AptClean(CleanAction[None]):
    """Clean APT package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the apt-get clean command."""
        del kwargs
        return ["apt-get", "clean"]

    def interpret(self, stream: IO[str]) -> None:
        """Return None as apt-get clean produces no structured output."""
        del stream


class AptAutoremove(AutoremoveAction[list[str]]):
    """Remove unused packages using apt-get."""

    def get_command(self, *, purge: bool = False, **kwargs: Any) -> list[str]:
        """Return the apt-get autoremove command."""
        del kwargs
        cmd = ["apt-get", "autoremove", "-y"]
        if purge:
            cmd.append("--purge")
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from autoremove output."""
        removed: list[str] = []
        pattern = re.compile(
            r"^(?:Removing|Purging configuration files for)\s+([^\s:]+)"
        )
        for line in stream:
            if match := pattern.match(line.strip()):
                pkg = match.group(1)
                if pkg not in removed:
                    removed.append(pkg)
        return removed


class Apt(BasePackageManager):
    """APT package manager interface."""

    @property
    def refresh(self) -> AptRefresh:
        """Refresh repository metadata."""
        return AptRefresh(self._runner)

    @property
    def install(self) -> AptInstall:
        """Install packages."""
        return AptInstall(self._runner)

    @property
    def remove(self) -> AptRemove:
        """Remove packages."""
        return AptRemove(self._runner)

    @property
    def upgrade(self) -> AptUpgrade:
        """Upgrade packages."""
        return AptUpgrade(self._runner)

    @property
    def search(self) -> AptSearch:
        """Search packages."""
        return AptSearch(self._runner)

    @property
    def info(self) -> AptInfo:
        """Display package details."""
        return AptInfo(self._runner)

    @property
    def list_installed(self) -> AptListInstalled:
        """List installed packages."""
        return AptListInstalled(self._runner)

    @property
    def is_installed(self) -> AptIsInstalled:
        """Check if package is installed."""
        return AptIsInstalled(self._runner)

    @property
    def download(self) -> AptDownload:
        """Download packages without installation."""
        return AptDownload(self._runner)

    @property
    def clean(self) -> AptClean:
        """Clean package cache."""
        return AptClean(self._runner)

    @property
    def autoremove(self) -> AptAutoremove:
        """Remove unused dependencies."""
        return AptAutoremove(self._runner)
