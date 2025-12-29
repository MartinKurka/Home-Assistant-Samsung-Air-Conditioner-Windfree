import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TOKEN): cv.string,
                vol.Required(CONF_DEVICES): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(CONF_DEVICE_ID): cv.string,
                                vol.Required(CONF_NAME): cv.string,
                                vol.Required(CONF_UNIQUE_ID): cv.string,
                            }
                        )
                    ],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MySmartThings integration."""
    hass.data[DOMAIN] = config[DOMAIN]

    _LOGGER.debug("Initializing MySmartThings with devices: %s", config[DOMAIN]["devices"])

    # Load the climate platform
    await async_load_platform(hass, "climate", DOMAIN, {}, config)

    return True
