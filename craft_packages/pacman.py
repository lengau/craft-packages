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
"""Pacman package manager implementation."""

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

_PACMAN_NVR_PARTS_COUNT = 3
_PACMAN_QUERY_PARTS_MIN = 2


@dataclass(frozen=True)
class PacmanRefreshResult:
    """Result of a pacman -Sy run."""

    databases_synchronized: bool = False
    database_count: int = 0


class PacmanRefresh(RefreshAction[PacmanRefreshResult]):
    """Refresh Pacman package databases."""

    def get_command(self, *, force: bool = False, **kwargs: Any) -> list[str]:
        """Return the pacman refresh command."""
        del kwargs
        flag = "-Syy" if force else "-Sy"
        return ["pacman", flag]

    def interpret(self, stream: IO[str]) -> PacmanRefreshResult:
        """Parse pacman -Sy output.

        Example command output::

            :: Synchronizing package databases...
             core downloading...
             extra downloading...

        Example output:
            PacmanRefreshResult(databases_synchronized=True, database_count=2)
        """
        sync_started = False
        db_count = 0
        for line in stream:
            stripped = line.strip()
            if "Synchronizing package databases" in stripped:
                sync_started = True
            elif "downloading..." in stripped:
                db_count += 1
        return PacmanRefreshResult(
            databases_synchronized=sync_started, database_count=db_count
        )


class PacmanInstall(InstallAction[list[str]]):
    """Install packages using pacman."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        needed: bool = False,
        nodeps: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the pacman install command."""
        del kwargs
        cmd = ["pacman", "-S", "--noconfirm"]
        if needed:
            cmd.append("--needed")
        if nodeps:
            cmd.append("--nodeps")
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages from pacman output.

        Example command output::

            resolving dependencies...
            looking for conflicting packages...

            Packages (1) tree-2.3.2-1

            Total Installed Size:  0.09 MiB

            :: Proceed with installation? [Y/n]
            installing tree...

        Example output:
            ["tree=2.3.2-1"]
        """
        installed: list[str] = []
        in_packages_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Packages ("):
                in_packages_section = True
                after_paren = stripped.partition(")")[2].strip()
                tokens = after_paren.split()
            elif in_packages_section:
                if (
                    stripped.startswith(
                        ("Total Download Size:", "Total Installed Size:", "::")
                    )
                    or not stripped
                ):
                    in_packages_section = False
                    continue
                tokens = stripped.split()
            else:
                continue

            for token in tokens:
                subparts = token.rsplit("-", 2)
                if len(subparts) == _PACMAN_NVR_PARTS_COUNT:
                    installed.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                else:
                    installed.append(token)

        return installed


class PacmanRemove(RemoveAction[list[str]]):
    """Remove packages using pacman."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        cascade: bool = False,
        recursive: bool = False,
        unneeded: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the pacman remove command."""
        del kwargs
        flags = "-R"
        if cascade:
            flags += "c"
        if recursive:
            flags += "s"
        if unneeded:
            flags += "u"
        cmd = ["pacman", flags, "--noconfirm"]
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from pacman output.

        Example command output::

            Packages (1) tree-2.3.2-1

            Total Removed Size:  0.09 MiB

            :: Do you want to remove these packages? [Y/n]
            removing tree...

        Example output:
            ["tree"]
        """
        removed: list[str] = []
        in_packages_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Packages ("):
                in_packages_section = True
                after_paren = stripped.partition(")")[2].strip()
                tokens = after_paren.split()
            elif in_packages_section:
                if stripped.startswith(("Total Removed Size:", "::")) or not stripped:
                    in_packages_section = False
                    continue
                tokens = stripped.split()
            else:
                continue

            for token in tokens:
                subparts = token.rsplit("-", 2)
                name = (
                    subparts[0] if len(subparts) == _PACMAN_NVR_PARTS_COUNT else token
                )
                removed.append(name)

        return removed


class PacmanUpgrade(UpgradeAction[list[str]]):
    """Upgrade packages using pacman."""

    def get_command(
        self,
        packages: Sequence[str] | None = None,
        *,
        enable_downgrade: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Return the pacman upgrade command."""
        del kwargs
        flags = "-Suu" if enable_downgrade else "-Su"
        cmd = ["pacman", flags, "--noconfirm"]
        if packages:
            cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse upgraded packages from pacman output.

        Example command output::

            Packages (1) tree-2.3.2-1

            Total Installed Size:  0.09 MiB

        Example output:
            ["tree=2.3.2-1"]
        """
        upgraded: list[str] = []
        in_packages_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Packages ("):
                in_packages_section = True
                after_paren = stripped.partition(")")[2].strip()
                tokens = after_paren.split()
            elif in_packages_section:
                if (
                    stripped.startswith(
                        ("Total Download Size:", "Total Installed Size:", "::")
                    )
                    or not stripped
                ):
                    in_packages_section = False
                    continue
                tokens = stripped.split()
            else:
                continue

            for token in tokens:
                subparts = token.rsplit("-", 2)
                if len(subparts) == _PACMAN_NVR_PARTS_COUNT:
                    upgraded.append(f"{subparts[0]}={subparts[1]}-{subparts[2]}")
                else:
                    upgraded.append(token)

        return upgraded


class PacmanSearch(SearchAction[dict[str, str]]):
    """Search packages using pacman."""

    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the pacman search command."""
        del kwargs
        return ["pacman", "-Ss", query]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse pacman search output.

        Example command output::

            extra/tree 2.3.2-1
                A directory listing program displaying a depth indented list of files

        Example output:
            {"tree": "A directory listing program displaying a depth indented list of files"}
        """
        results: dict[str, str] = {}
        current_pkg: str | None = None
        pkg_pattern = re.compile(r"^[a-zA-Z0-9_\-]+/([a-zA-Z0-9_\-\+]+)\s+")

        for line in stream:
            line_str = line.rstrip()
            if line_str.startswith("    ") and current_pkg:
                results[current_pkg] = line_str.strip()
                current_pkg = None
            elif match := pkg_pattern.match(line_str):
                current_pkg = match.group(1)

        return results


class PacmanInfo(InfoAction[dict[str, str]]):
    """Show package details using pacman."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the pacman info command."""
        del kwargs
        return ["pacman", "-Si", package]

    def interpret(self, stream: IO[str]) -> dict[str, str]:
        """Parse pacman info key-value output.

        Example command output::

            Repository      : extra
            Name            : tree
            Version         : 2.3.2-1
            Description     : A directory listing program

        Example output:
            {
                "Repository": "extra",
                "Name": "tree",
                "Version": "2.3.2-1",
                "Description": "A directory listing program",
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


class PacmanListInstalled(ListInstalledAction[list[str]]):
    """List installed packages using pacman query."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the pacman query command."""
        del kwargs
        return ["pacman", "-Q"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse installed packages into package=version strings.

        Example command output::

            acl 2.4.0-1
            tree 2.3.2-1

        Example output:
            ["acl=2.4.0-1", "tree=2.3.2-1"]
        """
        installed: list[str] = []
        for line in stream:
            parts = line.strip().split()
            if len(parts) >= _PACMAN_QUERY_PARTS_MIN:
                installed.append(f"{parts[0]}={parts[1]}")
        return sorted(installed)


class PacmanIsInstalled(IsInstalledAction[bool]):
    """Check if package is installed using pacman."""

    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the pacman query command."""
        del kwargs
        return ["pacman", "-Q", package]

    def interpret(self, stream: IO[str]) -> bool:
        """Parse pacman -Q output.

        Example command output::

            tree 2.3.2-1

        Example output:
            True
        """
        content = stream.read().strip()
        if not content:
            return False
        return not content.startswith("error:")


class PacmanDownload(DownloadAction[list[str]]):
    """Download package archives using pacman download-only."""

    def get_command(
        self,
        packages: Sequence[str],
        *,
        cachedir: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return the pacman download command."""
        del kwargs
        cmd = ["pacman", "-Sw", "--noconfirm"]
        if cachedir:
            cmd.extend(["--cachedir", cachedir])
        cmd.extend(packages)
        return cmd

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse downloaded package names from pacman output.

        Example command output::

            Packages (1) tree-2.3.2-1

            Total Download Size:  0.04 MiB

        Example output:
            ["tree"]
        """
        downloaded: list[str] = []
        in_packages_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Packages ("):
                in_packages_section = True
                after_paren = stripped.partition(")")[2].strip()
                tokens = after_paren.split()
            elif in_packages_section:
                if stripped.startswith(("Total Download Size:", "::")) or not stripped:
                    in_packages_section = False
                    continue
                tokens = stripped.split()
            else:
                continue

            for token in tokens:
                subparts = token.rsplit("-", 2)
                name = (
                    subparts[0] if len(subparts) == _PACMAN_NVR_PARTS_COUNT else token
                )
                downloaded.append(name)

        return downloaded


class PacmanClean(CleanAction[None]):
    """Clean Pacman package cache."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the pacman clean command."""
        del kwargs
        return ["pacman", "-Sc", "--noconfirm"]

    def interpret(self, stream: IO[str]) -> None:
        """Parse clean output.

        pacman -Sc produces no structured output.

        Example output:
            None
        """
        del stream


class PacmanAutoremove(AutoremoveAction[list[str]]):
    """Remove unused orphan packages using pacman."""

    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the command for removing orphan packages."""
        del kwargs
        return ["sh", "-c", "pacman -Qtdq | xargs -r pacman -Rns --noconfirm"]

    def interpret(self, stream: IO[str]) -> list[str]:
        """Parse removed packages from pacman autoremove output.

        Example command output::

            checking dependencies...

            Packages (1) orphan-1.0-1

            Total Removed Size:  0.03 MiB

        Example output:
            ["orphan"]
        """
        removed: list[str] = []
        in_packages_section = False

        for line in stream:
            stripped = line.strip()
            if stripped.startswith("Packages ("):
                in_packages_section = True
                after_paren = stripped.partition(")")[2].strip()
                tokens = after_paren.split()
            elif in_packages_section:
                if stripped.startswith(("Total Removed Size:", "::")) or not stripped:
                    in_packages_section = False
                    continue
                tokens = stripped.split()
            else:
                continue

            for token in tokens:
                subparts = token.rsplit("-", 2)
                name = (
                    subparts[0] if len(subparts) == _PACMAN_NVR_PARTS_COUNT else token
                )
                removed.append(name)

        return removed


class Pacman(BasePackageManager):
    """Pacman package manager interface."""

    @property
    def refresh(self) -> PacmanRefresh:
        """Refresh repository metadata."""
        return PacmanRefresh(self._runner)

    @property
    def install(self) -> PacmanInstall:
        """Install packages."""
        return PacmanInstall(self._runner)

    @property
    def remove(self) -> PacmanRemove:
        """Remove packages."""
        return PacmanRemove(self._runner)

    @property
    def upgrade(self) -> PacmanUpgrade:
        """Upgrade packages."""
        return PacmanUpgrade(self._runner)

    @property
    def search(self) -> PacmanSearch:
        """Search packages."""
        return PacmanSearch(self._runner)

    @property
    def info(self) -> PacmanInfo:
        """Display package details."""
        return PacmanInfo(self._runner)

    @property
    def list_installed(self) -> PacmanListInstalled:
        """List installed packages."""
        return PacmanListInstalled(self._runner)

    @property
    def is_installed(self) -> PacmanIsInstalled:
        """Check if package is installed."""
        return PacmanIsInstalled(self._runner)

    @property
    def download(self) -> PacmanDownload:
        """Download packages without installation."""
        return PacmanDownload(self._runner)

    @property
    def clean(self) -> PacmanClean:
        """Clean package cache."""
        return PacmanClean(self._runner)

    @property
    def autoremove(self) -> PacmanAutoremove:
        """Remove unused dependencies."""
        return PacmanAutoremove(self._runner)
