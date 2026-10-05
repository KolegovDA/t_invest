from head_server.firewall import (
    build_manual_command,
    build_netsh_arguments,
)


RULE_NAME = (
    "ESM Head Server TCP 8200"
)


def test_netsh_arguments_order() -> None:
    arguments = (
        build_netsh_arguments(
            rule_name=RULE_NAME,
            port=8200,
        )
    )

    assert arguments == [
        "advfirewall",
        "firewall",
        "add",
        "rule",
        "name=ESM Head Server TCP 8200",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        "localport=8200",
        "profile=any",
        "enable=yes",
    ]


def test_manual_command_contains_rule_and_port() -> None:
    command = (
        build_manual_command(
            rule_name=RULE_NAME,
            port=8200,
        )
    )

    assert command.startswith(
        "netsh advfirewall "
        "firewall add rule "
    )

    assert (
        'name="ESM Head Server '
        'TCP 8200"'
        in command
    )

    assert (
        "localport=8200"
        in command
    )

    assert (
        "dir=in"
        in command
    )

    assert (
        "action=allow"
        in command
    )

    assert (
        "profile=any"
        in command
    )

    assert (
        "enable=yes"
        in command
    )
