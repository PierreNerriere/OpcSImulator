from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest
from asyncua import Client, ua

from opc_simulator import OpcUaSimulator, config_from_dict, load_config

NS_URI = "http://test.local/sim"
ROOT = "PFC100"

TEST_CONFIG = {
    "server": {
        "application_name": "Test Sim",
        "application_uri": "urn:test:sim",
        "namespace": NS_URI,
        "root_object": ROOT,
    },
    "points": [
        {"name": "Device.SerialNumber", "datatype": "String", "value": "SN-001", "writable": False},
        {"name": "Device.Temperature", "datatype": "Float", "value": 21.5, "unit": "degC", "min": -10.0, "max": 60.0},
        {"name": "Inputs.Button", "datatype": "Boolean", "value": False},
        {"name": "Sim.Counter", "datatype": "UInt32", "value": 0,
         "simulation": {"mode": "increment", "step": 1, "interval_ms": 100, "wrap": 1000, "min": 0}},
        {"name": "Sim.Flag", "datatype": "Boolean", "value": False,
         "simulation": {"mode": "toggle", "interval_ms": 100}},
    ],
}


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
async def running():
    port = free_port()
    endpoint = f"opc.tcp://127.0.0.1:{port}"
    server_data = {**TEST_CONFIG["server"], "endpoint": endpoint}
    cfg = config_from_dict({**TEST_CONFIG, "server": server_data})
    sim = OpcUaSimulator(cfg)
    await sim.start()
    try:
        yield sim, endpoint
    finally:
        await sim.stop()


async def test_read_constant_points(running):
    _, endpoint = running
    async with Client(url=endpoint) as client:
        idx = await client.get_namespace_index(NS_URI)
        assert idx == 2
        serial = client.get_node(ua.NodeId("Device.SerialNumber", idx))
        assert await serial.read_value() == "SN-001"
        temp = client.get_node(ua.NodeId("Device.Temperature", idx))
        assert await temp.read_value() == pytest.approx(21.5)


async def test_write_writable_point(running):
    _, endpoint = running
    async with Client(url=endpoint) as client:
        idx = await client.get_namespace_index(NS_URI)
        button = client.get_node(ua.NodeId("Inputs.Button", idx))
        assert await button.read_value() is False
        await button.write_value(True)
        assert await button.read_value() is True


async def test_write_readonly_point_rejected(running):
    _, endpoint = running
    async with Client(url=endpoint) as client:
        idx = await client.get_namespace_index(NS_URI)
        serial = client.get_node(ua.NodeId("Device.SerialNumber", idx))
        with pytest.raises(ua.UaError):
            await serial.write_value("HACK")
        assert await serial.read_value() == "SN-001"


async def test_simulation_updates_values(running):
    _, endpoint = running
    async with Client(url=endpoint) as client:
        idx = await client.get_namespace_index(NS_URI)
        counter = client.get_node(ua.NodeId("Sim.Counter", idx))
        flag = client.get_node(ua.NodeId("Sim.Flag", idx))
        c0 = await counter.read_value()
        f0 = await flag.read_value()
        await asyncio.sleep(0.55)
        c1 = await counter.read_value()
        f1 = await flag.read_value()
        assert c1 > c0
        assert f1 != f0


async def test_folder_structure_and_properties(running):
    _, endpoint = running
    async with Client(url=endpoint) as client:
        idx = await client.get_namespace_index(NS_URI)
        root = client.get_node(ua.NodeId(ROOT, idx))
        device = await root.get_child([f"{idx}:Device"])
        sim = await root.get_child([f"{idx}:Sim"])
        assert device is not None and sim is not None
        temp = client.get_node(ua.NodeId("Device.Temperature", idx))
        props = {}
        for p in await temp.get_properties():
            props[(await p.read_browse_name()).Name] = await p.read_value()
        assert props["Unit"] == "degC"
        assert props["Min"] == pytest.approx(-10.0)
        assert props["Max"] == pytest.approx(60.0)


def test_load_example_config():
    path = Path(__file__).parent.parent / "config" / "points.json"
    cfg = load_config(path)
    assert cfg.root_object == "PFC100"
    assert len(cfg.points) == 12
    names = [p.name for p in cfg.points]
    assert "AnalogInputs.AI0" in names
    ai0 = next(p for p in cfg.points if p.name == "AnalogInputs.AI0")
    assert ai0.datatype == "Float"
    assert ai0.simulation.mode == "sine"


def test_config_validation_errors():
    with pytest.raises(ValueError, match="datatype inconnu"):
        config_from_dict({"points": [{"name": "A", "datatype": "Wat", "value": 1}]})
    with pytest.raises(ValueError, match="mode de simulation inconnu"):
        config_from_dict({"points": [{"name": "A", "datatype": "Int32", "value": 1,
                                      "simulation": {"mode": "boom"}}]})
    with pytest.raises(ValueError, match="'name' obligatoire"):
        config_from_dict({"points": [{"datatype": "Int32", "value": 1}]})
    with pytest.raises(ValueError, match="'points' doit etre une liste"):
        config_from_dict({"points": {"A": 1}})
    with pytest.raises(ValueError, match="cycle"):
        config_from_dict({"points": [{"name": "A", "datatype": "Int32", "value": 1,
                                      "simulation": {"mode": "cycle"}}]})


def test_datatype_inference():
    cfg = config_from_dict({"points": [
        {"name": "A", "value": True},
        {"name": "B", "value": 3},
        {"name": "C", "value": 1.5},
        {"name": "D", "value": "hi"},
    ]})
    assert [p.datatype for p in cfg.points] == ["Boolean", "Int32", "Double", "String"]
