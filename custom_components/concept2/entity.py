"""Base entity for the Concept2 Logbook integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import Concept2DataUpdateCoordinator


class Concept2Entity(CoordinatorEntity[Concept2DataUpdateCoordinator]):
    """Base entity tying a Concept2 entity to its account's device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the entity and its shared device info."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="Concept2 Logbook",
            manufacturer=MANUFACTURER,
        )

    @property
    def available(self) -> bool:
        """Stay available after a failed poll so entities keep their last-known values.

        The first refresh must succeed for the entry to load, so there is always a value.
        """
        return True
