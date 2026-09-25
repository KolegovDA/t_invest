from __future__ import annotations

from infrastructure.system.windows_firewall_service import (
    WindowsFirewallService,
)


def test_firewall_rule_name_contains_port() -> None:
    service = (
        WindowsFirewallService(
            port=8000,
        )
    )

    assert (
        service.rule_name
        == "ESM Trade System TCP 8000"
    )


def test_firewall_rule_name_changes_with_port() -> None:
    service = (
        WindowsFirewallService(
            port=8123,
        )
    )

    assert (
        service.rule_name
        == "ESM Trade System TCP 8123"
    )


def test_firewall_port_is_preserved() -> None:
    service = (
        WindowsFirewallService(
            port=8000,
        )
    )

    assert (
        service.port
        == 8000
    )
