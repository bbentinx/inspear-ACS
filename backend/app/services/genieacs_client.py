"""Cliente GenieACS NBI — Connection Request, reboot, firmware."""

import json
from typing import Any, Optional
import httpx
from ..config import settings

TIMEOUT = 20.0


class GenieACSDeviceNotFound(Exception):
    pass


class GenieACSClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.genieacs_nbi_url).rstrip("/")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/devices/?limit=1")
                return r.status_code == 200
        except Exception:
            return False

    async def list_devices(self, limit: int = 1000) -> list[dict]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{self.base_url}/devices/", params={"limit": limit})
            r.raise_for_status()
            return r.json()

    async def get_device(self, device_id: str) -> Optional[dict]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"{self.base_url}/devices/",
                params={"query": json.dumps({"_id": device_id})},
            )
            r.raise_for_status()
            devices = r.json()
            return devices[0] if devices else None

    async def resolve_device_id(self, serial_or_id: str) -> Optional[str]:
        """Resolve Inspear serial → GenieACS _id (ex: SERIAL → 00259E-EG8145V5-...)."""
        doc = await self.get_device(serial_or_id)
        if doc:
            return doc["_id"]

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for query in (
                {"_deviceId._SerialNumber": serial_or_id},
                {"InternetGatewayDevice.DeviceInfo.SerialNumber": serial_or_id},
            ):
                r = await client.get(
                    f"{self.base_url}/devices/",
                    params={"query": json.dumps(query)},
                )
                r.raise_for_status()
                devices = r.json()
                if devices:
                    return devices[0]["_id"]
        return None

    async def get_device_by_serial(self, serial_or_id: str) -> Optional[dict]:
        ga_id = await self.resolve_device_id(serial_or_id)
        if not ga_id:
            return None
        return await self.get_device(ga_id)

    async def connection_request(self, device_id: str) -> dict:
        """Solicita que a ONT inicie sessão CWMP imediatamente."""
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                params={"connection_request": ""},
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def reboot(self, device_id: str) -> dict:
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                json={"name": "reboot"},
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def download_file(
        self,
        device_id: str,
        url: str,
        file_type: str,
        file_name: str,
    ) -> dict:
        """TR-069 Download genérico (firmware, vendor config, etc.)."""
        task = {
            "name": "download",
            "fileType": file_type,
            "fileName": file_name,
            "targetFileName": file_name,
            "url": url,
        }
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                json=task,
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def download_firmware(
        self,
        device_id: str,
        firmware_url: str,
        file_name: str = "firmware.bin",
    ) -> dict:
        """TR-069 Download — Firmware Upgrade Image."""
        return await self.download_file(
            device_id, firmware_url, "1 Firmware Upgrade Image", file_name
        )

    async def download_vendor_config(
        self,
        device_id: str,
        config_url: str,
        file_name: str = "inspear-default.xml",
    ) -> dict:
        """TR-069 Download — Vendor Configuration File (config padrão ISP)."""
        return await self.download_file(
            device_id, config_url, "3 Vendor Configuration File", file_name
        )

    async def set_parameter_values(
        self,
        device_id: str,
        parameter_values: list[tuple[str, Any, str]],
    ) -> dict:
        """TR-069 setParameterValues — lista de (path, value, type)."""
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        task = {
            "name": "setParameterValues",
            "parameterValues": [[p, v, t] for p, v, t in parameter_values],
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/devices/{ga_id}/tasks", json=task)
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def add_object(self, device_id: str, object_name: str) -> dict:
        """TR-069 addObject — cria instância (ex: PortMapping)."""
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                json={"name": "addObject", "objectName": object_name},
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def refresh_object(self, device_id: str, object_name: str) -> dict:
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                json={"name": "refreshObject", "objectName": object_name},
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}

    async def get_parameter_values(self, device_id: str, parameters: list[str]) -> dict:
        ga_id = await self.resolve_device_id(device_id)
        if not ga_id:
            raise GenieACSDeviceNotFound(device_id)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/devices/{ga_id}/tasks",
                json={"name": "getParameterValues", "parameterNames": parameters},
            )
            r.raise_for_status()
            return r.json() if r.content else {"status": "ok"}


genieacs_client = GenieACSClient()