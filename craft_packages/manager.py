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
"""Abstract base package manager."""

import abc
import subprocess
from typing import Any

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
    Runner,
    SearchAction,
    UpgradeAction,
)


class BasePackageManager(abc.ABC):
    """Abstract base class for all package manager implementations."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess.Popen,
    ) -> None:
        self._runner = runner

    @property
    @abc.abstractmethod
    def refresh(self) -> RefreshAction[Any]:
        """Action to refresh package repository metadata."""

    @property
    @abc.abstractmethod
    def install(self) -> InstallAction[Any]:
        """Action to install packages."""

    @property
    @abc.abstractmethod
    def remove(self) -> RemoveAction[Any]:
        """Action to remove packages."""

    @property
    @abc.abstractmethod
    def upgrade(self) -> UpgradeAction[Any]:
        """Action to upgrade packages."""

    @property
    @abc.abstractmethod
    def search(self) -> SearchAction[Any]:
        """Action to search for packages."""

    @property
    @abc.abstractmethod
    def info(self) -> InfoAction[Any]:
        """Action to display package details."""

    @property
    @abc.abstractmethod
    def list_installed(self) -> ListInstalledAction[Any]:
        """Action to list installed packages."""

    @property
    @abc.abstractmethod
    def is_installed(self) -> IsInstalledAction[Any]:
        """Action to check if a package is installed."""

    @property
    def download(self) -> DownloadAction[Any]:
        """Action to download packages without installing."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support download action"
        )

    @property
    def clean(self) -> CleanAction[Any]:
        """Action to clean package caches."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support clean action"
        )

    @property
    def autoremove(self) -> AutoremoveAction[Any]:
        """Action to remove unused dependencies."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support autoremove action"
        )
