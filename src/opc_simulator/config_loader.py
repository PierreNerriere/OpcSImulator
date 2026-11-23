from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    DATATYPES,
    SIMULATION_MODES,
    PointConfig,
    SimulationConfig,
    SimulatorConfig,
    infer_datatype,
)


def load_config(path: str | Path) -> SimulatorConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return config_from_dict(data, source=str(path))


def config_from_dict(data: dict[str, Any], source: str = "<dict>") -> SimulatorConfig:
    if not isinstance(data, dict):
        raise ValueError(f"{source}: la racine du JSON doit etre un objet")
    server = data.get("server", {})
    if not isinstance(server, dict):
        raise ValueError(f"{source}: 'server' doit etre un objet")
    points_raw = data.get("points", [])
    if not isinstance(points_raw, list):
        raise ValueError(f"{source}: 'points' doit etre une liste")

    cfg = SimulatorConfig(
        endpoint=server.get("endpoint", SimulatorConfig.endpoint),
        application_name=server.get("application_name", SimulatorConfig.application_name),
        application_uri=server.get("application_uri", SimulatorConfig.application_uri),
        namespace=server.get("namespace", SimulatorConfig.namespace),
        root_object=server.get("root_object", SimulatorConfig.root_object),
    )
    seen: set[str] = set()
    for i, raw in enumerate(points_raw):
        point = _parse_point(raw, i, source)
        if point.name in seen:
            raise ValueError(f"{source}: points[{i}]: nom de point en double: {point.name!r}")
        seen.add(point.name)
        cfg.points.append(point)
    return cfg


def _parse_point(raw: Any, index: int, source: str) -> PointConfig:
    where = f"{source}: points[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: chaque point doit etre un objet")
    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise ValueError(f"{where}: champ 'name' obligatoire (ex: 'Inputs.DI0')")
    if name.startswith(".") or name.endswith(".") or ".." in name:
        raise ValueError(f"{where}: 'name' invalide: {name!r}")

    datatype = raw.get("datatype")
    value = raw.get("value")
    if datatype is None:
        if value is None:
            raise ValueError(f"{where}: 'datatype' obligatoire si 'value' est absent")
        datatype = infer_datatype(value)
    if datatype not in DATATYPES:
        raise ValueError(
            f"{where}: datatype inconnu {datatype!r}, "
            f"types supportes: {', '.join(sorted(DATATYPES))}"
        )

    sim_raw = raw.get("simulation", {})
    if not isinstance(sim_raw, dict):
        raise ValueError(f"{where}: 'simulation' doit etre un objet")
    mode = sim_raw.get("mode", "constant")
    if mode not in SIMULATION_MODES:
        raise ValueError(
            f"{where}: mode de simulation inconnu {mode!r}, "
            f"modes supportes: {', '.join(SIMULATION_MODES)}"
        )
    simulation = SimulationConfig(
        mode=mode,
        interval_ms=int(sim_raw.get("interval_ms", 1000)),
        min=sim_raw.get("min"),
        max=sim_raw.get("max"),
        amplitude=float(sim_raw.get("amplitude", 1.0)),
        period_s=float(sim_raw.get("period_s", 60.0)),
        step=float(sim_raw.get("step", 1.0)),
        wrap=sim_raw.get("wrap"),
        values=sim_raw.get("values"),
    )
    if mode == "cycle" and not simulation.values:
        raise ValueError(f"{where}: le mode 'cycle' necessite une liste 'values'")
    if simulation.interval_ms < 50:
        raise ValueError(f"{where}: 'interval_ms' doit etre >= 50")

    return PointConfig(
        name=name,
        datatype=datatype,
        value=value,
        nodeid=raw.get("nodeid"),
        writable=bool(raw.get("writable", True)),
        description=raw.get("description"),
        unit=raw.get("unit"),
        min=raw.get("min"),
        max=raw.get("max"),
        simulation=simulation,
    )
