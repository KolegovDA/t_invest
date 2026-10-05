from __future__ import annotations

import pytest
import socket
import sys

from pathlib import Path


sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parents[1]
    ),
)

import run_server  # noqa: E402


@pytest.mark.parametrize("platform,expected", [("win32", "asyncio:SelectorEventLoop"), ("linux", "auto")])
def test_web_event_loop_avoids_windows_proactor_without_starting_server(monkeypatch, platform, expected):
    import asyncio
    from uvicorn import Config

    monkeypatch.setattr(run_server.sys, "platform", platform)
    selected = run_server._web_event_loop()
    assert selected == expected
    if platform == "win32":
        assert Config(app=object(), loop=selected).get_loop_factory() is asyncio.SelectorEventLoop


def _occupy_port() -> socket.socket:
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    sock.bind(
        (
            "127.0.0.1",
            0,
        )
    )

    sock.listen(1)

    return sock


def test_resolve_web_port_returns_free_requested_port() -> None:
    sock = _occupy_port()

    port = (
        sock
        .getsockname()[1]
    )

    sock.close()

    assert (
        run_server
        ._resolve_web_port(
            host="127.0.0.1",
            requested=port,
            max_port=port + 5,
        )
        == port
    )


def test_resolve_web_port_skips_busy_port() -> None:
    sock = _occupy_port()

    busy_port = (
        sock
        .getsockname()[1]
    )

    try:
        if not (
            run_server
            ._is_port_available(
                host="127.0.0.1",
                port=(
                    busy_port
                    + 1
                ),
            )
        ):
            pytest.skip(
                "Neighbor port is "
                "occupied on this "
                "machine"
            )

        assert (
            run_server
            ._resolve_web_port(
                host="127.0.0.1",
                requested=busy_port,
                max_port=(
                    busy_port
                    + 5
                ),
            )
            == (
                busy_port
                + 1
            )
        )

    finally:
        sock.close()


def test_resolve_web_port_fails_when_range_exhausted() -> None:
    sock = _occupy_port()

    busy_port = (
        sock
        .getsockname()[1]
    )

    try:
        with pytest.raises(
            RuntimeError
        ) as error:
            run_server._resolve_web_port(
                host="127.0.0.1",
                requested=busy_port,
                max_port=busy_port,
            )

        assert (
            "No free TCP port"
            in str(
                error.value
            )
        )

    finally:
        sock.close()


def test_resolve_web_port_explicit_busy_port_above_range() -> None:
    sock = _occupy_port()

    busy_port = (
        sock
        .getsockname()[1]
    )

    try:
        with pytest.raises(
            RuntimeError
        ) as error:
            run_server._resolve_web_port(
                host="127.0.0.1",
                requested=busy_port,
                max_port=(
                    busy_port
                    - 1
                ),
            )

        assert (
            "already in use"
            in str(
                error.value
            )
        )

    finally:
        sock.close()
