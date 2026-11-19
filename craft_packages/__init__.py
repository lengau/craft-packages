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
"""Package manager abstractions and wrappers for craft tools."""

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("craft-packages")
    except PackageNotFoundError:
        __version__ = "dev"

from .actions import (
    Action,
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
from .apt import (
    Apt,
    AptAutoremove,
    AptClean,
    AptDownload,
    AptInfo,
    AptInstall,
    AptIsInstalled,
    AptListInstalled,
    AptRefresh,
    AptRefreshResult,
    AptRemove,
    AptSearch,
    AptUpgrade,
)
from .manager import BasePackageManager
from .snap import (
    Snap,
    SnapAutoremove,
    SnapClean,
    SnapDownload,
    SnapInfo,
    SnapInstall,
    SnapIsInstalled,
    SnapListInstalled,
    SnapRefresh,
    SnapRefreshResult,
    SnapRemove,
    SnapSearch,
    SnapUpgrade,
)

__all__ = [
    "Action",
    "Apt",
    "AptAutoremove",
    "AptClean",
    "AptDownload",
    "AptInfo",
    "AptInstall",
    "AptIsInstalled",
    "AptListInstalled",
    "AptRefresh",
    "AptRefreshResult",
    "AptRemove",
    "AptSearch",
    "AptUpgrade",
    "AutoremoveAction",
    "BasePackageManager",
    "CleanAction",
    "DownloadAction",
    "InfoAction",
    "InstallAction",
    "IsInstalledAction",
    "ListInstalledAction",
    "RefreshAction",
    "RemoveAction",
    "SearchAction",
    "Snap",
    "SnapAutoremove",
    "SnapClean",
    "SnapDownload",
    "SnapInfo",
    "SnapInstall",
    "SnapIsInstalled",
    "SnapListInstalled",
    "SnapRefresh",
    "SnapRefreshResult",
    "SnapRemove",
    "SnapSearch",
    "SnapUpgrade",
    "UpgradeAction",
    "__version__",
]
