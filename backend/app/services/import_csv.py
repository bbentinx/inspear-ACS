"""Importação CSV — clientes e equipamentos (OLT/ERP)."""

import csv
import io
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import Customer, Device


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


CUSTOMER_COLUMNS = {
    "name", "nome", "pppoe_login", "login", "phone", "telefone",
    "email", "address", "endereco", "neighborhood", "bairro",
    "pop_id", "pop", "external_code", "codigo",
}

DEVICE_COLUMNS = {
    "serial_number", "serial", "mac_wan", "mac", "manufacturer", "fabricante",
    "model", "modelo", "firmware", "pppoe_login", "login",
    "pop_id", "olt_id", "olt", "pon_id", "pon", "onu_id", "cto_id", "cto",
    "customer_name", "cliente",
}


def _normalize_row(row: dict) -> dict:
    mapping = {
        "nome": "name", "login": "pppoe_login", "telefone": "phone",
        "endereco": "address", "bairro": "neighborhood", "codigo": "external_code",
        "serial": "serial_number", "mac": "mac_wan", "fabricante": "manufacturer",
        "modelo": "model", "olt": "olt_id", "pon": "pon_id", "cto": "cto_id",
        "cliente": "customer_name", "pop": "pop_id",
    }
    out = {}
    for k, v in row.items():
        key = k.strip().lower()
        key = mapping.get(key, key)
        if v and str(v).strip():
            out[key] = str(v).strip()
    return out


async def import_customers_csv(db: AsyncSession, content: str) -> ImportResult:
    result = ImportResult()
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        result.errors.append("CSV vazio ou sem cabeçalho")
        return result

    for i, row in enumerate(reader, start=2):
        data = _normalize_row(row)
        name = data.get("name")
        if not name:
            result.errors.append(f"Linha {i}: nome obrigatório")
            result.skipped += 1
            continue

        pppoe = data.get("pppoe_login")
        existing = None
        if pppoe:
            r = await db.execute(select(Customer).where(Customer.pppoe_login == pppoe))
            existing = r.scalar_one_or_none()
        if not existing and data.get("external_code"):
            r = await db.execute(select(Customer).where(Customer.external_code == data["external_code"]))
            existing = r.scalar_one_or_none()

        pop_id = None
        if data.get("pop_id"):
            try:
                pop_id = int(data["pop_id"])
            except ValueError:
                pass

        if existing:
            existing.name = name
            existing.phone = data.get("phone") or existing.phone
            existing.address = data.get("address") or existing.address
            existing.neighborhood = data.get("neighborhood") or existing.neighborhood
            result.updated += 1
        else:
            db.add(Customer(
                name=name,
                pppoe_login=pppoe,
                phone=data.get("phone"),
                email=data.get("email"),
                address=data.get("address"),
                neighborhood=data.get("neighborhood"),
                external_code=data.get("external_code"),
                pop_id=pop_id,
            ))
            result.created += 1

    return result


async def import_devices_csv(db: AsyncSession, content: str) -> ImportResult:
    result = ImportResult()
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        result.errors.append("CSV vazio ou sem cabeçalho")
        return result

    for i, row in enumerate(reader, start=2):
        data = _normalize_row(row)
        serial = data.get("serial_number")
        if not serial:
            result.errors.append(f"Linha {i}: serial obrigatório")
            result.skipped += 1
            continue

        r = await db.execute(select(Device).where(Device.serial_number == serial))
        existing = r.scalar_one_or_none()

        customer_id = None
        pppoe = data.get("pppoe_login")
        if pppoe:
            cr = await db.execute(select(Customer).where(Customer.pppoe_login == pppoe))
            cust = cr.scalar_one_or_none()
            if cust:
                customer_id = cust.id
        elif data.get("customer_name"):
            cr = await db.execute(select(Customer).where(Customer.name == data["customer_name"]))
            cust = cr.scalar_one_or_none()
            if cust:
                customer_id = cust.id

        def _int(k):
            try:
                return int(data[k]) if data.get(k) else None
            except ValueError:
                return None

        # FK opcionais — ignora IDs inexistentes (CSV de OLT costuma usar slot/porta, não PK)
        pop_id = _int("pop_id")
        olt_id = _int("olt_id")
        pon_id = _int("pon_id")
        cto_id = _int("cto_id")

        fields = dict(
            mac_wan=data.get("mac_wan"),
            manufacturer=data.get("manufacturer", "Huawei"),
            model=data.get("model", "HG8245X6-10"),
            firmware=data.get("firmware"),
            customer_id=customer_id,
            pop_id=pop_id,
            olt_id=olt_id,
            pon_id=pon_id,
            onu_id=_int("onu_id"),
            cto_id=cto_id,
        )

        if existing:
            for k, v in fields.items():
                if v is not None:
                    setattr(existing, k, v)
            result.updated += 1
        else:
            db.add(Device(serial_number=serial, **fields))
            result.created += 1

    return result