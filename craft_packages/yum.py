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
"""YUM package manager implementation."""

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
_YUM_PARTS_MIN = 3
_NAME_VERSION_FIELDS_MIN = 2
_RPM_NVR_PARTS_COUNT = 3


@dataclass(frozen=True)
class YumRefreshResult:
    """Result of a yum makecache run."""

    metadata_cache_created: bool = False
    repo_count: int = 0


class YumRefresh(RefreshAction[YumRefreshResult]):
    """Refresh YUM package metadata cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the yum makecache command."""
        del kwargs
        return ["yum", "makecache"]

    def interpret(self, stream: IO[str]) -> YumRefreshResult:
        """Parse yum makecache output."""
        repos = 0
        cache_created = False
        for line in stream:
            stripped = line.strip()
            if (
                "Metadata cache created." in stripped
                or "Metadata Cache Created" in stripped
            ):
                cache_created = True
            elif "|" in stripped or "Metadata" in stripped:
                repos += 1
        return YumRefreshResult(metadata_cache_created=cache_created, repo_count=repos)


class YumInstall(InstallAction[list[str]]):
    """Install packages using yum."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        nodocs: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the yum install command."""
        del kwargs
        cmd = ["yum", "install", "-y"]
        if nodocs:
            cmd.append("--nodocs")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from yum output."""
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
                if len(parts) >= _YUM_PARTS_MIN and parts[1] in _COMMON_ARCHES:
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


class YumRemove(RemoveAction[list[str]]):
    """Remove packages using yum."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        autoremove: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the yum remove command."""
        del kwargs
        cmd = ["yum", "remove", "-y"]
        if autoremove:
            cmd.append("--autoremove")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from yum output."""
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


class YumUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using yum."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the yum upgrade command."""
        del kwargs
        cmd = ["yum", "upgrade", "-y"]
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from yum output."""
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
                if len(parts) >= _YUM_PARTS_MIN and parts[1] in _COMMON_ARCHES:
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


class YumSearch(SearchAction[dict[str, str]]):
    """Search packages using yum."""

    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the yum search command."""
        del kwargs
        return ["yum", "search", query]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse yum search output."""
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


class YumInfo(InfoAction[dict[str, str]]):
    """Show package details using yum."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the yum info command."""
        del kwargs
        return ["yum", "info", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse yum info key-value output."""
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


class YumListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using rpm query."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the rpm command for listing installed packages."""
        del kwargs
        return ["rpm", "-qa", "--qf", "%{NAME}=%{VERSION}-%{RELEASE}\n"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings."""
        return sorted(
            line.strip() for line in stream if line.strip() and "=" in line.strip()
        )


class YumIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using rpm."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the rpm command for checking package status."""
        del kwargs
        return ["rpm", "-q", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse rpm -q output."""
        content = stream.read().strip()
        if not content:
            return False
        return not content.startswith("package ") and "not installed" not in content


class YumDownload(DownloadAction[list[str]]):
    """Download package archives using yum download-only."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        destdir: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the yum command to download packages."""
        del kwargs
        cmd = ["yum", "install", "-y", "--downloadonly"]
        if destdir:
            cmd.extend(["--destdir", destdir])
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from yum output."""
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


class YumClean(CleanAction[None]):
    """Clean YUM package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the yum clean all command."""
        del kwargs
        return ["yum", "clean", "all"]

    def interpret(self, stream: IO[str]) -> None:
        """Return None as yum clean produces no structured output."""
        del stream


class YumAutoremove(AutoremoveAction[list[str]]):
    """Remove unused packages using yum."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the yum autoremove command."""
        del kwargs
        return ["yum", "autoremove", "-y"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from yum autoremove output."""
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


class Yum(BasePackageManager):
    """YUM package manager interface."""

    @property
    def refresh(self) -> YumRefresh:
        """Refresh repository metadata."""
        return YumRefresh(self._runner)

    @property
    def install(self) -> YumInstall:
        """Install packages."""
        return YumInstall(self._runner)

    @property
    def remove(self) -> YumRemove:
        """Remove packages."""
        return YumRemove(self._runner)

    @property
    def upgrade(self) -> YumUpgrade:
        """Upgrade packages."""
        return YumUpgrade(self._runner)

    @property
    def search(self) -> YumSearch:
        """Search packages."""
        return YumSearch(self._runner)

    @property
    def info(self) -> YumInfo:
        """Display package details."""
        return YumInfo(self._runner)

    @property
    def list_installed(self) -> YumListInstalled:
        """List installed packages."""
        return YumListInstalled(self._runner)

    @property
    def is_installed(self) -> YumIsInstalled:
        """Check if package is installed."""
        return YumIsInstalled(self._runner)

    @property
    def download(self) -> YumDownload:
        """Download packages without installation."""
        return YumDownload(self._runner)

    @property
    def clean(self) -> YumClean:
        """Clean package cache."""
        return YumClean(self._runner)

    @property
    def autoremove(self) -> YumAutoremove:
        """Remove unused dependencies."""
        return YumAutoremove(self._runner)
