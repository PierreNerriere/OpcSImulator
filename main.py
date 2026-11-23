#!/usr/bin/env python3
"""Simulateur de serveur OPC UA piloté par une liste de points en JSON.

Usage:
    python main.py --config config/points.json
    python main.py --config config/points.json --endpoint opc.tcp://127.0.0.1:4840
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from opc_simulator import load_and_build  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulateur de serveur OPC UA (config JSON)")
    parser.add_argument("--config", required=True, help="Chemin du fichier JSON de points")
    parser.add_argument("--endpoint", default=None, help="Override de l'endpoint (ex: opc.tcp://0.0.0.0:4840)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs DEBUG")
    return parser.parse_args()


async def amain() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    simulator = load_and_build(args.config)
    if args.endpoint:
        simulator.config.endpoint = args.endpoint
    try:
        await simulator.run_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        await simulator.stop()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(amain()))
