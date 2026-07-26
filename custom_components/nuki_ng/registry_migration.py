"""One-time device registry migration to consistent identifiers.

Early versions registered devices under the identifier domains ``id`` (lock,
bridge) and ``web_id`` (Nuki Web API) instead of the integration ``DOMAIN``.
The lock and bridge were later corrected to ``(DOMAIN, id)``, but no migration
shipped with that change, so existing installations ended up with *both* rows:
an empty ``("id", x)`` device next to the populated ``(DOMAIN, x)`` one. The
Web API device was never converted at all and still points its ``via_device``
at the stale ``("id", x)`` entry, which is what keeps that entry alive.

The planning half of this module is deliberately free of Home Assistant
imports: deciding what to rename and what to merge is a data-structure problem
and is unit-tested as one. ``async_migrate_device_registry`` is the thin part
that reads the registry, asks for a plan and applies it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .constants import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Identifier domains written by older releases, mapped to how the same device
# is addressed today.
LEGACY_LOCK_DOMAIN = "id"
LEGACY_WEB_DOMAIN = "web_id"

Identifier = tuple[str, object]


def migrate_identifier(identifier: Identifier) -> Identifier:
    """Return the current-scheme identifier for a possibly legacy one."""
    domain, value = identifier
    if domain == LEGACY_LOCK_DOMAIN:
        return (DOMAIN, value)
    if domain == LEGACY_WEB_DOMAIN:
        # The Web API device shares its numeric id with the lock, so it needs a
        # prefix to stay distinct once both live in the same domain.
        return (DOMAIN, f"web_{value}")
    return identifier


def is_legacy(identifier: Identifier) -> bool:
    return identifier[0] in (LEGACY_LOCK_DOMAIN, LEGACY_WEB_DOMAIN)


@dataclass(frozen=True)
class DeviceRow:
    """The parts of a device registry entry this migration cares about."""

    device_id: str
    identifiers: frozenset[Identifier]
    via_device_id: str | None = None
    entity_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rename:
    """No device holds the new identifiers yet — rewrite them in place."""

    device_id: str
    new_identifiers: frozenset[Identifier]


@dataclass(frozen=True)
class Merge:
    """A device already holds the new identifiers — fold the legacy row into it.

    Renaming would raise, because the registry rejects duplicate identifiers.
    """

    source_device_id: str
    target_device_id: str
    move_entity_ids: tuple[str, ...] = ()
    repoint_device_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationPlan:
    renames: tuple[Rename, ...] = field(default_factory=tuple)
    merges: tuple[Merge, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.renames and not self.merges


def plan_identifier_migration(devices: list[DeviceRow]) -> MigrationPlan:
    """Work out how to bring `devices` onto the current identifier scheme.

    Returns an empty plan when there is nothing legacy left, which makes the
    migration safe to run on every startup.
    """
    owner_of: dict[Identifier, str] = {}
    for device in devices:
        for identifier in device.identifiers:
            owner_of[identifier] = device.device_id

    children_of: dict[str, list[str]] = {}
    for device in devices:
        if device.via_device_id:
            children_of.setdefault(device.via_device_id, []).append(device.device_id)

    renames: list[Rename] = []
    merges: list[Merge] = []

    for device in devices:
        legacy = {i for i in device.identifiers if is_legacy(i)}
        if not legacy:
            continue

        new_identifiers = frozenset(migrate_identifier(i) for i in device.identifiers)

        # Does some *other* device already answer to any of the new identifiers?
        target_id = next(
            (
                owner
                for i in new_identifiers
                if (owner := owner_of.get(i)) and owner != device.device_id
            ),
            None,
        )

        if target_id is None:
            renames.append(
                Rename(device_id=device.device_id, new_identifiers=new_identifiers)
            )
            continue

        merges.append(
            Merge(
                source_device_id=device.device_id,
                target_device_id=target_id,
                move_entity_ids=tuple(device.entity_ids),
                repoint_device_ids=tuple(children_of.get(device.device_id, ())),
            )
        )

    return MigrationPlan(renames=tuple(renames), merges=tuple(merges))


async def async_migrate_device_registry(hass, entry) -> MigrationPlan:
    """Apply `plan_identifier_migration` to the live registry for `entry`."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    entries = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    rows = [
        DeviceRow(
            device_id=device.id,
            identifiers=frozenset(device.identifiers),
            via_device_id=device.via_device_id,
            entity_ids=tuple(
                e.entity_id
                for e in er.async_entries_for_device(
                    entity_reg, device.id, include_disabled_entities=True
                )
            ),
        )
        for device in entries
    ]

    plan = plan_identifier_migration(rows)
    if plan.is_empty:
        return plan

    for rename in plan.renames:
        _LOGGER.info(
            "Migrating device %s to identifiers %s",
            rename.device_id,
            sorted(map(str, rename.new_identifiers)),
        )
        device_reg.async_update_device(
            rename.device_id, new_identifiers=set(rename.new_identifiers)
        )

    for merge in plan.merges:
        _LOGGER.info(
            "Merging stale device %s into %s (%d entities, %d children)",
            merge.source_device_id,
            merge.target_device_id,
            len(merge.move_entity_ids),
            len(merge.repoint_device_ids),
        )
        for entity_id in merge.move_entity_ids:
            entity_reg.async_update_entity(
                entity_id, device_id=merge.target_device_id
            )
        for child_id in merge.repoint_device_ids:
            device_reg.async_update_device(
                child_id, via_device_id=merge.target_device_id
            )
        device_reg.async_remove_device(merge.source_device_id)

    return plan
