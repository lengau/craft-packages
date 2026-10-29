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
"""DNF package manager implementation."""

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

_COMMON_ARCHES = {
    "x86_64",
    "aarch64",
    "noarch",
    "i686",
    "armv7hl",
    "ppc64le",
    "s390x",
}
_DNF5_PARTS_MIN = 3
_NAME_VERSION_FIELDS_MIN = 2
_RPM_NVR_PARTS_COUNT = 3


@dataclass(frozen=True)
class DnfRefreshResult:
    """Result of a dnf makecache run."""

    metadata_cache_created: bool = False
    repo_count: int = 0


class DnfRefresh(RefreshAction[DnfRefreshResult]):
    """Refresh DNF package metadata cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the dnf makecache command."""
        del kwargs
        return ["dnf", "makecache"]

    def interpret(self, stream: IO[str]) -> DnfRefreshResult:
        """Parse dnf makecache output.

        Example command output::

            CentOS Stream 9 - BaseOS                          5.4 kB/s | 5.4 kB 00:00
            Metadata cache created.

        Example output:
            DnfRefreshResult(metadata_cache_created=True, repo_count=1)
        """
        repos = 0
        cache_created = False
        for line in stream:
            stripped = line.strip()
            if "Metadata cache created." in stripped:
                cache_created = True
            elif "|" in stripped or "Metadata" in stripped:
                repos += 1
        return DnfRefreshResult(metadata_cache_created=cache_created, repo_count=repos)


class DnfInstall(InstallAction[list[str]]):
    """Install packages using dnf."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        nodocs: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the dnf install command."""
        del kwargs
        cmd = ["dnf", "install", "-y"]
        if nodocs:
            cmd.append("--nodocs")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from dnf output.

        Example command output::

            Installed:
              tree-1.8.0-10.el9.x86_64
            Complete!

        Example output:
            ["tree=1.8.0-10.el9"]
        """
        installed: list[str] = []
        in_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith(("Installed:", "Installing:")):
                in_section = True
                continue
            if in_section:
                if (
                    stripped.startswith(
                        (
                            "Complete!",
                            "Transaction Summary:",
                            "Upgrading:",
                            "Removing:",
                        )
                    )
                    or not stripped
                ):
                    in_section = False
                    continue
                parts = stripped.split()
                if not parts:
                    continue
                if len(parts) >= _DNF5_PARTS_MIN and parts[1] in _COMMON_ARCHES:
                    installed.append(f"{parts[0]}={parts[2]}")
                elif len(parts) >= _NAME_VERSION_FIELDS_MIN:
                    name = parts[0].rsplit(".", 1)[0]
                    installed.append(f"{name}={parts[1]}")
                else:
                    without_arch = parts[0].rsplit(".", 1)[0]
                    subparts = without_arch.rsplit("-", 2)
                    if len(subparts) == _RPM_NVR_PARTS_COUNT:
                        installed.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                    else:
                        installed.append(without_arch)

        return installed


class DnfRemove(RemoveAction[list[str]]):
    """Remove packages using dnf."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        autoremove: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the dnf remove command."""
        del kwargs
        cmd = ["dnf", "remove", "-y"]
        if autoremove:
            cmd.append("--autoremove")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from dnf output.

        Example command output::

            Removed:
              tree.x86_64 1.8.0-10.el9
            Complete!

        Example output:
            ["tree"]
        """
        removed: list[str] = []
        in_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith(("Removed:", "Removing:")):
                in_section = True
                continue
            if in_section:
                if (
                    stripped.startswith(("Complete!", "Transaction Summary:"))
                    or not stripped
                ):
                    in_section = False
                    continue
                parts = stripped.split()
                if parts:
                    name_arch = parts[0]
                    name = name_arch.rsplit(".", 1)[0]
                    subparts = name.rsplit("-", 2)
                    if len(subparts) == _RPM_NVR_PARTS_COUNT:
                        name = subparts[0]
                    removed.append(name)

        return removed


class DnfUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using dnf."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the dnf upgrade command."""
        del kwargs
        cmd = ["dnf", "upgrade", "-y"]
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from dnf output.

        Example command output::

            Upgraded:
              tree.x86_64 1.8.1-1.el9
            Complete!

        Example output:
            ["tree=1.8.1-1.el9"]
        """
        upgraded: list[str] = []
        in_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith(("Upgraded:", "Upgrading:")):
                in_section = True
                continue
            if in_section:
                if (
                    stripped.startswith(("Complete!", "Transaction Summary:"))
                    or not stripped
                ):
                    in_section = False
                    continue
                parts = stripped.split()
                if not parts:
                    continue
                if len(parts) >= _DNF5_PARTS_MIN and parts[1] in _COMMON_ARCHES:
                    upgraded.append(f"{parts[0]}={parts[2]}")
                elif len(parts) >= _NAME_VERSION_FIELDS_MIN:
                    name = parts[0].rsplit(".", 1)[0]
                    upgraded.append(f"{name}={parts[1]}")
                else:
                    without_arch = parts[0].rsplit(".", 1)[0]
                    subparts = without_arch.rsplit("-", 2)
                    if len(subparts) == _RPM_NVR_PARTS_COUNT:
                        upgraded.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                    else:
                        upgraded.append(without_arch)

        return upgraded


class DnfSearch(SearchAction[dict[str, str]]):
    """Search packages using dnf."""

    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the dnf search command."""
        del kwargs
        return ["dnf", "search", query]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse dnf search output.

        Example command output::

            tree.x86_64 : File system tree viewer

        Example output:
            {"tree": "File system tree viewer"}
        """
        results: dict[str, str] = {}
        for line in stream:
            stripped = line.strip()
            if "\t" in stripped and not stripped.startswith("="):
                pkg_arch, _, desc = stripped.partition("\t")
                pkg = pkg_arch.rsplit(".", 1)[0].strip()
                results[pkg] = desc.strip()
            elif " : " in stripped and not stripped.startswith("="):
                pkg_arch, _, desc = stripped.partition(" : ")
                pkg = pkg_arch.rsplit(".", 1)[0].strip()
                results[pkg] = desc.strip()
        return results


class DnfInfo(InfoAction[dict[str, str]]):
    """Show package details using dnf."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the dnf info command."""
        del kwargs
        return ["dnf", "info", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse dnf info key-value output.

        Example command output::

            Name         : tree
            Version      : 1.8.0
            Release      : 10.el9
            Description  : File system tree viewer

        Example output:
            {
                "Name": "tree",
                "Version": "1.8.0",
                "Release": "10.el9",
                "Description": "File system tree viewer",
            }
        """
        info: dict[str, str] = {}
        current_key: str | None = None

        for line in stream:
            if " : " in line and not line.startswith((" ", "\t")):
                key, _, val = line.partition(" : ")
                current_key = key.strip()
                info[current_key] = val.strip()
            elif current_key and line.startswith((" ", "\t")) and ":" in line:
                _, _, val = line.partition(":")
                info[current_key] += "\n" + val.strip()

        return info


class DnfListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using rpm query."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the rpm command for listing installed packages."""
        del kwargs
        return ["rpm", "-qa", "--qf", "%{NAME}=%{VERSION}-%{RELEASE}\n"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings.

        Example command output::

            tree=1.8.0-10.el9
            tzdata=2024a-1.el9

        Example output:
            ["tree=1.8.0-10.el9", "tzdata=2024a-1.el9"]
        """
        return sorted(
            line.strip() for line in stream if line.strip() and "=" in line.strip()
        )


class DnfIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using rpm."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the rpm command for checking package status."""
        del kwargs
        return ["rpm", "-q", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse rpm -q output.

        Example command output::

            tree-1.8.0-10.el9.x86_64

        Example output:
            True
        """
        content = stream.read().strip()
        if not content:
            return False
        return not content.startswith("package ") and "not installed" not in content


class DnfDownload(DownloadAction[list[str]]):
    """Download package archives using dnf download-only."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        destdir: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the dnf command to download packages."""
        del kwargs
        cmd = ["dnf", "install", "-y", "--downloadonly"]
        if destdir:
            cmd.extend(["--destdir", destdir])
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from dnf output.

        Example command output::

            Downloading Packages:
            tree-1.8.0-10.el9.x86_64.rpm  56 kB/s | 56 kB 00:00
            Complete!

        Example output:
            ["tree"]
        """
        downloaded: list[str] = []
        in_section = False
        rpm_pattern = re.compile(r"^\s*(\S+)\.rpm")

        for line in stream:
            stripped = line.strip()
            if match := rpm_pattern.match(stripped):
                rpm_name = match.group(1)
                parts = rpm_name.rsplit("-", 2)
                downloaded.append(parts[0] if parts else rpm_name)
            elif stripped.startswith("Installing:"):
                in_section = True
                continue
            elif in_section:
                if (
                    stripped.startswith(("Transaction Summary:", "Complete!"))
                    or not stripped
                ):
                    in_section = False
                    continue
                parts = stripped.split()
                if parts:
                    downloaded.append(parts[0].rsplit(".", 1)[0])

        return downloaded


class DnfClean(CleanAction[None]):
    """Clean DNF package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the dnf clean all command."""
        del kwargs
        return ["dnf", "clean", "all"]

    def interpret(self, stream: IO[str]) -> None:
        """Parse dnf clean output.

        dnf clean produces no structured output.

        Example output:
            None
        """
        del stream


class DnfAutoremove(AutoremoveAction[list[str]]):
    """Remove unused packages using dnf."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the dnf autoremove command."""
        del kwargs
        return ["dnf", "autoremove", "-y"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from dnf autoremove output.

        Example command output::

            Removed:
              old-dep.x86_64 1.0-1
            Complete!

        Example output:
            ["old-dep"]
        """
        removed: list[str] = []
        in_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith(("Removed:", "Removing:")):
                in_section = True
                continue
            if in_section:
                if (
                    stripped.startswith(("Complete!", "Transaction Summary:"))
                    or not stripped
                ):
                    in_section = False
                    continue
                parts = stripped.split()
                if parts:
                    name_arch = parts[0]
                    name = name_arch.rsplit(".", 1)[0]
                    subparts = name.rsplit("-", 2)
                    if len(subparts) == _RPM_NVR_PARTS_COUNT:
                        name = subparts[0]
                    removed.append(name)

        return removed


class Dnf(BasePackageManager):
    """DNF package manager interface."""

    @property
    def refresh(self) -> DnfRefresh:
        """Refresh repository metadata."""
        return DnfRefresh(self._runner)

    @property
    def install(self) -> DnfInstall:
        """Install packages."""
        return DnfInstall(self._runner)

    @property
    def remove(self) -> DnfRemove:
        """Remove packages."""
        return DnfRemove(self._runner)

    @property
    def upgrade(self) -> DnfUpgrade:
        """Upgrade packages."""
        return DnfUpgrade(self._runner)

    @property
    def search(self) -> DnfSearch:
        """Search packages."""
        return DnfSearch(self._runner)

    @property
    def info(self) -> DnfInfo:
        """Display package details."""
        return DnfInfo(self._runner)

    @property
    def list_installed(self) -> DnfListInstalled:
        """List installed packages."""
        return DnfListInstalled(self._runner)

    @property
    def is_installed(self) -> DnfIsInstalled:
        """Check if package is installed."""
        return DnfIsInstalled(self._runner)

    @property
    def download(self) -> DnfDownload:
        """Download packages without installation."""
        return DnfDownload(self._runner)

    @property
    def clean(self) -> DnfClean:
        """Clean package cache."""
        return DnfClean(self._runner)

    @property
    def autoremove(self) -> DnfAutoremove:
        """Remove unused dependencies."""
        return DnfAutoremove(self._runner)
