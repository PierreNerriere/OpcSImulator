from __future__ import annotations

import logging

from asyncua import Server, ua

from .config_loader import load_config
from .models import DATATYPES, SimulatorConfig, convert_value
from .simulation import PointSimulator

log = logging.getLogger("opc_simulator")


class OpcUaSimulator:
    def __init__(self, config: SimulatorConfig) -> None:
        self.config = config
        self.server = Server()
        self.namespace_index: int = 2
        self._simulators: list[PointSimulator] = []

    async def setup(self) -> None:
        cfg = self.config
        await self.server.init()
        self.server.set_server_name(cfg.application_name)
        await self.server.set_application_uri(cfg.application_uri)
        self.server.set_endpoint(cfg.endpoint)
        self.namespace_index = await self.server.register_namespace(cfg.namespace)
        objects = self.server.get_objects_node()
        root = await objects.add_object(
            ua.NodeId(cfg.root_object, self.namespace_index),
            ua.QualifiedName(cfg.root_object, self.namespace_index),
        )
        for point in cfg.points:
            await self._add_point(root, point)

    async def start(self) -> None:
        await self.setup()
        await self.server.start()
        for sim in self._simulators:
            await sim.start()
        log.info(
            "Serveur OPC UA demarre sur %s (%d points, namespace %d = %s)",
            self.config.endpoint,
            len(self.config.points),
            self.namespace_index,
            self.config.namespace,
        )

    async def stop(self) -> None:
        for sim in self._simulators:
            await sim.stop()
        await self.server.stop()
        log.info("Serveur arrete")

    async def run_forever(self) -> None:
        await self.start()
        try:
            import asyncio

            await asyncio.Event().wait()
        finally:
            await self.stop()

    async def _add_point(self, root: ua.Node, point) -> None:
        segments = point.name.split(".")
        parent = root
        for i, segment in enumerate(segments[:-1]):
            folder_path = ".".join(segments[: i + 1])
            parent = await self._get_or_create_folder(parent, segment, folder_path)
        browse_name = ua.QualifiedName(segments[-1], self.namespace_index)
        nodeid = self._resolve_nodeid(point)
        varianttype, datatype_id = DATATYPES[point.datatype]
        value = convert_value(point.value, point.datatype)
        var = await parent.add_variable(
            nodeid, browse_name, value, varianttype=varianttype, datatype=datatype_id
        )
        await var.set_writable(point.writable)
        if point.description:
            await var.write_attribute(
                ua.AttributeIds.Description,
                ua.DataValue(
                    ua.Variant(ua.LocalizedText(point.description), ua.VariantType.LocalizedText)
                ),
            )
        await self._add_properties(var, point)
        if point.simulation.mode != "constant":
            self._simulators.append(PointSimulator(var, point, value, varianttype))
        log.debug("Point ajoute: ns=%d;%s = %r (%s)", self.namespace_index, point.name, value, point.datatype)

    async def _add_properties(self, var: ua.Node, point) -> None:
        props = []
        if point.unit is not None:
            props.append(("Unit", str(point.unit)))
        if point.min is not None:
            props.append(("Min", float(point.min)))
        if point.max is not None:
            props.append(("Max", float(point.max)))
        for prop_name, prop_value in props:
            await var.add_property(
                ua.NodeId(f"{point.name}.{prop_name}", self.namespace_index),
                ua.QualifiedName(prop_name, self.namespace_index),
                prop_value,
            )

    async def _get_or_create_folder(self, parent: ua.Node, name: str, path: str) -> ua.Node:
        nodeid = ua.NodeId(path, self.namespace_index)
        qname = ua.QualifiedName(name, self.namespace_index)
        try:
            return await parent.get_child([qname])
        except ua.UaStatusCodeError:
            return await parent.add_folder(nodeid, qname)

    def _resolve_nodeid(self, point) -> ua.NodeId:
        if point.nodeid:
            if isinstance(point.nodeid, str) and point.nodeid.lower().startswith("ns="):
                return ua.NodeId.from_string(point.nodeid)
            return ua.NodeId(point.nodeid, self.namespace_index)
        return ua.NodeId(point.name, self.namespace_index)


def load_and_build(config_path: str) -> OpcUaSimulator:
    return OpcUaSimulator(load_config(config_path))
