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
"""Integration test fixtures and configuration."""

import contextlib
import subprocess
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import pylxd
import pylxd.exceptions
import pytest
from craft_packages.apt import Apt


@dataclass(frozen=True)
class ImageSpec:
    """Specification of a container image for integration tests."""

    name: str
    server: str
    alias: str


IMAGE_SPECS: list[ImageSpec] = [
    # Ubuntu standard releases since 18.04
    ImageSpec("ubuntu-18.04", "https://cloud-images.ubuntu.com/releases/", "18.04"),
    ImageSpec("ubuntu-20.04", "https://cloud-images.ubuntu.com/releases/", "20.04"),
    ImageSpec("ubuntu-22.04", "https://cloud-images.ubuntu.com/releases/", "22.04"),
    ImageSpec("ubuntu-24.04", "https://cloud-images.ubuntu.com/releases/", "24.04"),
    ImageSpec("ubuntu-26.04", "https://cloud-images.ubuntu.com/releases/", "26.04"),
    # Ubuntu minimal releases since 18.04
    ImageSpec(
        "ubuntu-minimal-18.04",
        "https://cloud-images.ubuntu.com/minimal/releases/",
        "18.04",
    ),
    ImageSpec(
        "ubuntu-minimal-20.04",
        "https://cloud-images.ubuntu.com/minimal/releases/",
        "20.04",
    ),
    ImageSpec(
        "ubuntu-minimal-22.04",
        "https://cloud-images.ubuntu.com/minimal/releases/",
        "22.04",
    ),
    ImageSpec(
        "ubuntu-minimal-24.04",
        "https://cloud-images.ubuntu.com/minimal/releases/",
        "24.04",
    ),
    ImageSpec(
        "ubuntu-minimal-26.04",
        "https://cloud-images.ubuntu.com/minimal/releases/",
        "26.04",
    ),
    # Debian releases since 12
    ImageSpec("debian-12", "https://images.lxd.canonical.com", "debian/12"),
    ImageSpec("debian-13", "https://images.lxd.canonical.com", "debian/13"),
    ImageSpec("debian-14", "https://images.lxd.canonical.com", "debian/14"),
    ImageSpec("debian-sid", "https://images.lxd.canonical.com", "debian/sid"),
]


@pytest.fixture(
    scope="session",
    params=IMAGE_SPECS,
    ids=[spec.name for spec in IMAGE_SPECS],
)
def lxd_container(request: pytest.FixtureRequest) -> Generator[Any, None, None]:
    """Start an LXD container for the test session across parametrized images."""
    spec: ImageSpec = request.param
    try:
        client: Any = pylxd.Client()
        if not client.trusted:
            pytest.skip("LXD client is not trusted")  # ty: ignore[too-many-positional-arguments]
    except (
        pylxd.exceptions.ClientConnectionFailed,
        pylxd.exceptions.LXDAPIException,
    ) as exc:
        pytest.skip(f"LXD is not available: {exc}")  # ty: ignore[too-many-positional-arguments]

    name = f"test-cp-{spec.name.replace('.', '-')}-{uuid.uuid4().hex[:6]}"
    config = {
        "name": name,
        "source": {
            "type": "image",
            "mode": "pull",
            "server": spec.server,
            "protocol": "simplestreams",
            "alias": spec.alias,
        },
    }

    container: Any = client.containers.create(config, wait=True)
    container.start(wait=True)

    # Wait for cloud-init if present
    res = container.execute(["which", "cloud-init"])
    if res.exit_code == 0:
        container.execute(["cloud-init", "status", "--wait"])

    yield container

    with contextlib.suppress(pylxd.exceptions.LXDAPIException, Exception):
        container.stop(wait=True)
    with contextlib.suppress(pylxd.exceptions.LXDAPIException, Exception):
        container.delete(wait=True)


@pytest.fixture(scope="session")
def apt_container(lxd_container: Any) -> Apt:
    """Return an Apt instance whose commands execute in the LXD container."""

    def container_runner(cmd: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
        exec_cmd = ["lxc", "exec", lxd_container.name, "--", *cmd]
        return subprocess.Popen(exec_cmd, **kwargs)

    return Apt(runner=container_runner)
