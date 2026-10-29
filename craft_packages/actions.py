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
"""Base action abstractions for package manager operations."""

import abc
import io
import subprocess
from collections.abc import Callable, Sequence
from typing import IO, Any, Generic, TypeVar

T = TypeVar("T")

Runner = Callable[..., subprocess.Popen[Any]]


class Action(abc.ABC, Generic[T]):
    """Base class for an action executed by a package manager."""

    def __init__(self, runner: Runner = subprocess.Popen) -> None:
        self._runner = runner

    @abc.abstractmethod
    def get_command(self, *args: Any, **kwargs: Any) -> list[str]:
        """Return the command as a list of strings."""

    def start(
        self,
        *args: Any,
        runner_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> subprocess.Popen[Any]:
        """Start the command using the configured runner and return the Popen object."""
        cmd = self.get_command(*args, **kwargs)
        default_kwargs: dict[str, Any] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }
        if runner_kwargs:
            default_kwargs.update(runner_kwargs)
        return self._runner(cmd, **default_kwargs)

    def run(
        self,
        *args: Any,
        runner_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> T:
        """Run the command to completion and return interpreted output."""
        proc = self.start(*args, runner_kwargs=runner_kwargs, **kwargs)
        stdout, _ = proc.communicate()
        return self.interpret(io.StringIO(stdout))

    @abc.abstractmethod
    def interpret(self, stream: IO[str]) -> T:
        """Interpret the output of the command from a stream-like object."""

    def parse(self, stream: IO[str]) -> T:
        """Parse the output of the command from a stream-like object.

        Alias for interpret().
        """
        return self.interpret(stream)


class RefreshAction(Action[T], abc.ABC):
    """Abstract action for refreshing package repository metadata."""

    @abc.abstractmethod
    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the refresh command."""


class InstallAction(Action[T], abc.ABC):
    """Abstract action for installing packages."""

    @abc.abstractmethod
    def get_command(self, packages: Sequence[str], **kwargs: Any) -> list[str]:
        """Return the install command for the specified packages."""


class RemoveAction(Action[T], abc.ABC):
    """Abstract action for removing packages."""

    @abc.abstractmethod
    def get_command(self, packages: Sequence[str], **kwargs: Any) -> list[str]:
        """Return the remove command for the specified packages."""


class UpgradeAction(Action[T], abc.ABC):
    """Abstract action for upgrading packages."""

    @abc.abstractmethod
    def get_command(
        self, packages: Sequence[str] | None = None, **kwargs: Any
    ) -> list[str]:
        """Return the upgrade command."""


class SearchAction(Action[T], abc.ABC):
    """Abstract action for searching packages."""

    @abc.abstractmethod
    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        """Return the search command for the given query."""


class InfoAction(Action[T], abc.ABC):
    """Abstract action for showing package information."""

    @abc.abstractmethod
    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the info command for the given package."""


class ListInstalledAction(Action[T], abc.ABC):
    """Abstract action for listing installed packages."""

    @abc.abstractmethod
    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the list-installed command."""


class IsInstalledAction(Action[T], abc.ABC):
    """Abstract action for checking if a package is installed."""

    @abc.abstractmethod
    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        """Return the command to check if a package is installed."""


class DownloadAction(Action[T], abc.ABC):
    """Abstract action for downloading packages without installation."""

    @abc.abstractmethod
    def get_command(self, packages: Sequence[str], **kwargs: Any) -> list[str]:
        """Return the download command for the specified packages."""


class CleanAction(Action[T], abc.ABC):
    """Abstract action for cleaning package cache."""

    @abc.abstractmethod
    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the clean cache command."""


class AutoremoveAction(Action[T], abc.ABC):
    """Abstract action for removing unneeded dependency packages."""

    @abc.abstractmethod
    def get_command(self, **kwargs: Any) -> list[str]:
        """Return the autoremove command."""
