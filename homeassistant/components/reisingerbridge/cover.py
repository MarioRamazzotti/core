"""Platform for the reisinger bridge cover component."""
import logging

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import OpenReisingerEntity

_LOGGER = logging.getLogger(__name__)

STATES_MAP = {0: STATE_CLOSED, 1: STATE_OPEN}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the OpenReisinger covers."""
    async_add_entities(
        [OpenReisingerCover(hass.data[DOMAIN][entry.entry_id], entry.unique_id)]
    )


class OpenReisingerCover(OpenReisingerEntity, CoverEntity):
    """Representation of a OpenReisinger cover."""

    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, open_reisinger_data_coordinator, device_id):
        """Initialize the cover."""
        self._state = None
        self._state_before_move = None

        super().__init__(open_reisinger_data_coordinator, device_id)

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self._state is None:
            return None
        return self._state == STATE_CLOSED

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""
        if self._state is None:
            return None
        return self._state == STATE_CLOSING

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""
        if self._state is None:
            return None
        return self._state == STATE_OPENING

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._state in [STATE_CLOSED, STATE_CLOSING]:
            return
        self._state_before_move = self._state
        self._state = STATE_CLOSING
        await self._push_button()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._state in [STATE_OPEN, STATE_OPENING]:
            return
        self._state_before_move = self._state
        self._state = STATE_OPENING
        await self._push_button()

    @callback
    def _update_attr(self) -> None:
        """Update the state and attributes."""
        status = self.coordinator.data

        self._attr_name = f"slidingdoor_{status['serial']}"
        state = STATE_OPEN if status.get("open") else STATE_CLOSED
        if self._state_before_move is not None:
            if self._state_before_move != state:
                self._state = state
                self._state_before_move = None
        else:
            self._state = state

    async def _push_button(self):
        """Send commands to API."""
        result = await self.coordinator.open_reisinger_connection.open_door()
        if result is None:
            _LOGGER.error("Unable to connect to Reisinger drive device")
        if result == 1:
            return

        if result == 2:
            _LOGGER.error("Unable to control %s: Device key is incorrect", self.name)
        elif result > 2:
            _LOGGER.error("Unable to control %s: Error code %s", self.name, result)

        self._state = self._state_before_move
        self._state_before_move = None
