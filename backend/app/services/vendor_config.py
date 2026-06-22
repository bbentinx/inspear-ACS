"""Gera arquivo Vendor Configuration File (Huawei TR-069) a partir do perfil."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..models.entities import DeviceConfigProfile

NS = "urn:broadband-forum-org:cwmp:xml-annex-a"


def _el(parent: ET.Element, tag: str, text: str | int | bool | None) -> None:
    if text is None or text == "":
        return
    node = ET.SubElement(parent, tag)
    node.text = str(text).lower() if isinstance(text, bool) else str(text)


def build_vendor_xml(profile: DeviceConfigProfile) -> str:
    """XML TR-069 simplificado para Download tipo Vendor Configuration File."""
    root = ET.Element("InternetGatewayDevice", xmlns=NS)

    mgmt = ET.SubElement(root, "ManagementServer")
    _el(mgmt, "URL", profile.acs_url)
    _el(mgmt, "Username", profile.acs_username)
    _el(mgmt, "Password", profile.acs_password)
    _el(mgmt, "ConnectionRequestUsername", profile.cr_username)
    _el(mgmt, "ConnectionRequestPassword", profile.cr_password)
    _el(mgmt, "PeriodicInformEnable", True)
    _el(mgmt, "PeriodicInformInterval", profile.periodic_inform_interval or 300)

    wan = ET.SubElement(root, "WANDevice")
    wan1 = ET.SubElement(wan, "WANDeviceInstance")
    wcd = ET.SubElement(wan1, "WANConnectionDevice")
    wcd1 = ET.SubElement(wcd, "WANConnectionDeviceInstance")
    ppp = ET.SubElement(wcd1, "WANPPPConnection")
    ppp1 = ET.SubElement(ppp, "WANPPPConnectionInstance")
    _el(ppp1, "Enable", True)
    _el(ppp1, "Username", profile.pppoe_username)
    _el(ppp1, "Password", profile.pppoe_password)
    if profile.wan_vlan is not None:
        _el(ppp1, "X_HW_VLAN", profile.wan_vlan)

    lan = ET.SubElement(root, "LANDevice")
    lan1 = ET.SubElement(lan, "LANDeviceInstance")
    wlan = ET.SubElement(lan1, "WLANConfiguration")

    w24 = ET.SubElement(wlan, "WLANConfigurationInstance")
    w24.set("instance", "1")
    _el(w24, "Enable", True)
    _el(w24, "SSID", profile.wifi_24_ssid)
    _el(w24, "KeyPassphrase", profile.wifi_24_password)

    w5 = ET.SubElement(wlan, "WLANConfigurationInstance")
    w5.set("instance", "5")
    _el(w5, "Enable", True)
    _el(w5, "SSID", profile.wifi_5_ssid)
    _el(w5, "KeyPassphrase", profile.wifi_5_password)

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def write_vendor_file(profile: DeviceConfigProfile, base_dir: Path) -> Path:
    out_dir = base_dir / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{profile.serial_number}.xml"
    path.write_text(build_vendor_xml(profile), encoding="utf-8")
    return path