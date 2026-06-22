"""Registry de adapters — seleciona o adapter correto por fabricante."""

from .huawei import HuaweiAdapter
from .zte import ZTEAdapter
from .fiberhome import FiberHomeAdapter
from .generic import GenericTR069Adapter
from .base import BaseAdapter, NormalizedDeviceState

ADAPTERS: list[BaseAdapter] = [
    HuaweiAdapter(),
    ZTEAdapter(),
    FiberHomeAdapter(),
    GenericTR069Adapter(),
]


def get_adapter(payload: dict) -> BaseAdapter:
    for adapter in ADAPTERS:
        if adapter.can_handle(payload):
            return adapter
    return GenericTR069Adapter()


def normalize_payload(payload: dict) -> NormalizedDeviceState:
    adapter = get_adapter(payload)
    return adapter.normalize(payload)