#!/usr/bin/env python3
"""Client d'exemple: se connecte au simulateur, lit les points, ecrit une sortie.

Usage:
    python examples/client_example.py --url opc.tcp://127.0.0.1:4840 --namespace http://wago.com/pfc100/simulator
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from asyncua import Client, ua  # noqa: E402


async def amain() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="opc.tcp://127.0.0.1:4840")
    parser.add_argument("--namespace", default="http://wago.com/pfc100/simulator")
    args = parser.parse_args()

    async with Client(url=args.url) as client:
        idx = await client.get_namespace_index(args.namespace)
        print(f"Connecte a {args.url} (namespace {idx})")

        async def read_point(path: str):
            node = client.get_node(ua.NodeId(path, idx))
            value = await node.read_value()
            print(f"  {path} = {value!r}")
            return value

        await read_point("Device.SerialNumber")
        await read_point("DigitalInputs.DI0")
        await read_point("AnalogInputs.AI0")
        counter1 = await read_point("Process.Counter")

        do0 = client.get_node(ua.NodeId("DigitalOutputs.DO0", idx))
        await do0.write_value(True)
        print(f"  ecriture DigitalOutputs.DO0 -> {await do0.read_value()}")

        print("Attente de 2.5 s pour observer la simulation...")
        await asyncio.sleep(2.5)
        counter2 = await read_point("Process.Counter")
        print(f"Compteur: {counter1} -> {counter2}")


if __name__ == "__main__":
    asyncio.run(amain())
