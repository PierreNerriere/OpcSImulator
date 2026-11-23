from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from typing import Any, Optional

from asyncua import ua

from .models import PointConfig

log = logging.getLogger("opc_simulator.simulation")


class PointSimulator:
    """Anime la valeur d'une variable OPC UA selon le mode defini dans la config."""

    def __init__(self, node: Any, cfg: PointConfig, current: Any, varianttype: ua.VariantType) -> None:
        self._node = node
        self._cfg = cfg
        self._current = current
        self._varianttype = varianttype
        self._cycle_index = 0
        self._start = time.monotonic()
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._cfg.simulation.mode == "constant":
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                log.exception("Erreur dans la simulation du point %s", self._cfg.name)
            self._task = None

    async def _run(self) -> None:
        interval = self._cfg.simulation.interval_ms / 1000.0
        while True:
            await asyncio.sleep(interval)
            value = self._next_value()
            if value is not None:
                self._current = value
                await self._node.set_value(value, self._varianttype)

    def _next_value(self) -> Any:
        sim = self._cfg.simulation
        mode = sim.mode
        if mode == "random":
            return self._random_value()
        if mode == "sine":
            base = float(self._cfg.value) if isinstance(self._cfg.value, (int, float)) else 0.0
            t = time.monotonic() - self._start
            value = base + sim.amplitude * math.sin(2.0 * math.pi * t / max(sim.period_s, 0.001))
            return self._cast(value)
        if mode in ("increment", "decrement"):
            step = sim.step if mode == "increment" else -sim.step
            value = float(self._current) + step
            if sim.wrap is not None and value > sim.wrap:
                lo = sim.min if sim.min is not None else 0.0
                value = lo
            if sim.wrap is not None and value < (sim.min if sim.min is not None else 0.0):
                value = sim.wrap
            return self._cast(value)
        if mode == "toggle":
            return not bool(self._current)
        if mode == "cycle":
            values = sim.values or []
            value = values[self._cycle_index % len(values)]
            self._cycle_index += 1
            return value
        return None

    def _random_value(self) -> Any:
        sim = self._cfg.simulation
        lo = sim.min if sim.min is not None else self._cfg.min
        hi = sim.max if sim.max is not None else self._cfg.max
        if self._cfg.datatype == "Boolean":
            return random.choice([True, False])
        if self._cfg.datatype in ("SByte", "Byte", "Int16", "UInt16", "Int32", "UInt32", "Int64", "UInt64"):
            lo_i = int(lo) if lo is not None else 0
            hi_i = int(hi) if hi is not None else 100
            return random.randint(min(lo_i, hi_i), max(lo_i, hi_i))
        lo_f = float(lo) if lo is not None else 0.0
        hi_f = float(hi) if hi is not None else 1.0
        return self._cast(random.uniform(min(lo_f, hi_f), max(lo_f, hi_f)))

    def _cast(self, value: Any) -> Any:
        if self._cfg.datatype == "Boolean":
            return bool(value)
        if self._cfg.datatype in ("SByte", "Byte", "Int16", "UInt16", "Int32", "UInt32", "Int64", "UInt64"):
            return int(value)
        if self._cfg.datatype in ("Float", "Double"):
            return float(value)
        return value
