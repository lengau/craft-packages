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
"""Unit tests for BasePackageManager class."""

import subprocess
from collections.abc import Sequence
from typing import IO, Any
from unittest import mock

import pytest
from craft_packages.actions import (
    InfoAction,
    InstallAction,
    IsInstalledAction,
    ListInstalledAction,
    RefreshAction,
    RemoveAction,
    SearchAction,
    UpgradeAction,
)
from craft_packages.manager import BasePackageManager


class DummyRefresh(RefreshAction[str]):
    def get_command(self, **kwargs: Any) -> list[str]:
        del kwargs
        return ["dummy", "refresh"]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyInstall(InstallAction[str]):
    def get_command(self, packages: Sequence[str], **kwargs: Any) -> list[str]:
        return ["dummy", "install", *packages]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyRemove(RemoveAction[str]):
    def get_command(self, packages: Sequence[str], **kwargs: Any) -> list[str]:
        return ["dummy", "remove", *packages]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyUpgrade(UpgradeAction[str]):
    def get_command(
        self, packages: Sequence[str] | None = None, **kwargs: Any
    ) -> list[str]:
        return ["dummy", "upgrade", *(packages or [])]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummySearch(SearchAction[str]):
    def get_command(self, query: str, **kwargs: Any) -> list[str]:
        return ["dummy", "search", query]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyInfo(InfoAction[str]):
    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        return ["dummy", "info", package]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyListInstalled(ListInstalledAction[str]):
    def get_command(self, **kwargs: Any) -> list[str]:
        del kwargs
        return ["dummy", "list-installed"]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class DummyIsInstalled(IsInstalledAction[str]):
    def get_command(self, package: str, **kwargs: Any) -> list[str]:
        del kwargs
        return ["dummy", "is-installed", package]

    def interpret(self, stream: IO[str]) -> str:
        return stream.read()


class ConcretePackageManager(BasePackageManager):
    @property
    def refresh(self) -> RefreshAction[str]:
        return DummyRefresh(self._runner)

    @property
    def install(self) -> InstallAction[str]:
        return DummyInstall(self._runner)

    @property
    def remove(self) -> RemoveAction[str]:
        return DummyRemove(self._runner)

    @property
    def upgrade(self) -> UpgradeAction[str]:
        return DummyUpgrade(self._runner)

    @property
    def search(self) -> SearchAction[str]:
        return DummySearch(self._runner)

    @property
    def info(self) -> InfoAction[str]:
        return DummyInfo(self._runner)

    @property
    def list_installed(self) -> ListInstalledAction[str]:
        return DummyListInstalled(self._runner)

    @property
    def is_installed(self) -> IsInstalledAction[str]:
        return DummyIsInstalled(self._runner)


def test_base_package_manager_cannot_instantiate_directly():
    with pytest.raises(TypeError):
        BasePackageManager()  # ty: ignore[call-non-callable]


def test_concrete_package_manager_default_runner():
    pm = ConcretePackageManager()
    assert pm._runner is subprocess.Popen


def test_concrete_package_manager_custom_runner():
    custom_runner = mock.Mock()
    pm = ConcretePackageManager(runner=custom_runner)
    assert pm._runner is custom_runner
    assert pm.install._runner is custom_runner


def test_unimplemented_optional_actions():
    pm = ConcretePackageManager()
    with pytest.raises(NotImplementedError, match="does not support download action"):
        _ = pm.download
    with pytest.raises(NotImplementedError, match="does not support clean action"):
        _ = pm.clean
    with pytest.raises(NotImplementedError, match="does not support autoremove action"):
        _ = pm.autoremove
