"""Connection ownership boundaries."""

from swbt.gamepad import connection
from swbt.gamepad.runtime import ControllerRuntime
from swbt.transport.base import HidDeviceTransport


def test_runtime_owns_connection_workflow_and_transport_exposes_single_peer() -> None:
    assert not hasattr(connection, "ConnectionWorkflow")
    assert not hasattr(connection, "EnsureOpen")
    assert not hasattr(HidDeviceTransport, "list_bonded_peers")
    assert hasattr(HidDeviceTransport, "bonded_peer_address")
    for helper_name in (
        "_connection_transport",
        "_close_neutral_for_connection_workflow",
        "_pair_for_connection_workflow",
        "_set_connection_state",
        "_wait_for_reconnect_connected_for_workflow",
    ):
        assert not hasattr(ControllerRuntime, helper_name)
