from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from asyncua import ua

DATATYPES: dict[str, tuple[ua.VariantType, int]] = {
    "Boolean": (ua.VariantType.Boolean, ua.ObjectIds.Boolean),
    "SByte": (ua.VariantType.SByte, ua.ObjectIds.SByte),
    "Byte": (ua.VariantType.Byte, ua.ObjectIds.Byte),
    "Int16": (ua.VariantType.Int16, ua.ObjectIds.Int16),
    "UInt16": (ua.VariantType.UInt16, ua.ObjectIds.UInt16),
    "Int32": (ua.VariantType.Int32, ua.ObjectIds.Int32),
    "UInt32": (ua.VariantType.UInt32, ua.ObjectIds.UInt32),
    "Int64": (ua.VariantType.Int64, ua.ObjectIds.Int64),
    "UInt64": (ua.VariantType.UInt64, ua.ObjectIds.UInt64),
    "Float": (ua.VariantType.Float, ua.ObjectIds.Float),
    "Double": (ua.VariantType.Double, ua.ObjectIds.Double),
    "String": (ua.VariantType.String, ua.ObjectIds.String),
    "DateTime": (ua.VariantType.DateTime, ua.ObjectIds.DateTime),
}

SIMULATION_MODES = ("constant", "random", "sine", "increment", "decrement", "toggle", "cycle")


@dataclass
class SimulationConfig:
    mode: str = "constant"
    interval_ms: int = 1000
    min: Optional[float] = None
    max: Optional[float] = None
    amplitude: float = 1.0
    period_s: float = 60.0
    step: float = 1.0
    wrap: Optional[float] = None
    values: Optional[list[Any]] = None


@dataclass
class PointConfig:
    name: str
    datatype: str
    value: Any = None
    nodeid: Optional[str] = None
    writable: bool = True
    description: Optional[str] = None
    unit: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    simulation: SimulationConfig = field(default_factory=SimulationConfig)


@dataclass
class SimulatorConfig:
    endpoint: str = "opc.tcp://0.0.0.0:4840"
    application_name: str = "OPC UA Simulator"
    application_uri: str = "urn:opcua:simulator"
    namespace: str = "http://opcua.simulator.local"
    root_object: str = "Simulator"
    points: list[PointConfig] = field(default_factory=list)


def infer_datatype(value: Any) -> str:
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Int32"
    if isinstance(value, float):
        return "Double"
    return "String"


def convert_value(value: Any, datatype: str) -> Any:
    if value is None:
        return None
    if datatype == "Boolean":
        return bool(value)
    if datatype in ("SByte", "Byte", "Int16", "UInt16", "Int32", "UInt32", "Int64", "UInt64"):
        return int(value)
    if datatype in ("Float", "Double"):
        return float(value)
    if datatype == "DateTime":
        return value
    return str(value)
