import pytest

import sporkfish.uci_client as uci_client


@pytest.fixture
def init_client() -> uci_client.UCIClient:
    return uci_client.UCIClient(uci_client.UCIClient.UCIProtocol.ResponseMode.RETURN)


def test_uci_client_init(init_client):
    _ = init_client


def test_uci_client_go(init_client):
    client = init_client
    response = client.send_command("go")
    assert "bestmove" in response


def test_uci_client_time_inc(init_client):
    client = init_client
    response = client.send_command("go wtime 1 winc 0")
    assert "bestmove" in response
