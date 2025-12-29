from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.components.climate.const import FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH

from homeassistant.components.climate.const import SWING_HORIZONTAL, SWING_VERTICAL

from .const import DOMAIN
from pysmartthings import SmartThings, DeviceEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import logging
import asyncio

_LOGGER = logging.getLogger(__name__)
FAN_MODES = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
SWING_MODES = [SWING_VERTICAL, SWING_HORIZONTAL, "all", "fixed"]

# HVACMode.AUTO is removed, not possible to switch from AUTO to other
HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY]

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    conf = hass.data[DOMAIN]
    token = conf["token"]
    devices_conf = conf["devices"]
    _LOGGER.warning(conf)

    session = async_get_clientsession(hass)
    api = SmartThings(session, token)

    devices = await api.devices()

    entities = []
    for dev_conf in devices_conf:
        device = next((d for d in devices if d.device_id == dev_conf["device_id"]), None)
        if device:
            _LOGGER.warning(device)
            entities.append(SmartThingsClimate(device, dev_conf["name"], dev_conf["unique_id"]))
            _LOGGER.warning(f"device: {device}, name: {dev_conf["name"]}, unique_id: {dev_conf["unique_id"]}")
        else:
            _LOGGER.warning(f"SmartThings device not found: {dev_conf['device_id']}")

    async_add_entities(entities, True)

class SmartThingsClimate(ClimateEntity):
    def __init__(self, device, name, unique_id):
        self._device = device
        self._name = name
        self._unique_id = unique_id
        self._temperature = None
        self._target_temperature = None
        self._current_temperature = None
        self._current_humidity = None
        self._hvac_mode = HVACMode.OFF
        self._fan_mode = FAN_LOW
        self._swing_mode = "fixed"
        self._target_temperature_step = 1
        self._pending_update = False
        self._attributes: dict

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.SWING_MODE

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return HVAC_MODES

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return FAN_MODES

    @property
    def swing_mode(self):
        """Return the swing setting."""
        return self._swing_mode

    @property
    def swing_modes(self):
        """Return the list of available Swings modes."""
        return SWING_MODES

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return self._attributes

    @property
    def current_humidity(self):
        """Return the current temperature."""
        if self._current_humidity is not None:
            return int(round(self._current_humidity))  # Ensure it's an integer

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if self._current_temperature is not None:
            return int(round(self._current_temperature))  # Ensure it's an integer

    @property
    def target_temperature_step(self):
        """Return the supported step size for target temperature."""
        return self._target_temperature_step  # Set step size to 1 for whole numbers

    @property
    def min_temperature(self):
        """Return the minimum temperature."""
        return 16

    @property
    def max_temperature(self):
        """Return the maximum temperature."""
        return 30

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            _LOGGER.warning(f"device: {self._name}, new target temp: {temperature}")
            self._target_temperature = temperature
            self._pending_update = True
            await  self._device.set_cooling_setpoint(temperature)
            await asyncio.sleep(1)
            self._pending_update = False            
            self.async_write_ha_state()
    
    async def async_turn_on(self):
        self._pending_update = True
        if self._hvac_mode == HVACMode.OFF:
            self._pending_update = False
            return
        else:
            await self._device.command("main", "switch", "on")
            await asyncio.sleep(0.5)
            self._pending_update = False            
            self.async_write_ha_state()
                
    async def async_turn_off(self):
        self._pending_update = True
        if self._hvac_mode != HVACMode.OFF:
            await self._device.command("main", "switch", "off")
            await asyncio.sleep(0.5)
            self._pending_update = False            
            self.async_write_ha_state()
        else:
            self._pending_update = False
            return

    async def async_set_hvac_mode(self, hvac_mode):
        self._pending_update = True
        self._hvac_mode = hvac_mode
        _LOGGER.warning(f"device: {self._name}, set_hvac_mode: {hvac_mode}")
        # You may need to send different capabilities based on hvac_mode

        if self._hvac_mode == HVACMode.OFF:
            await self._device.command("main", "switch", "off")

        elif self._hvac_mode == HVACMode.COOL:
            await self._device.command("main", "switch", "on")
            await self._device.set_air_conditioner_mode(self._hvac_mode)
            await self._device.set_fan_mode(self._fan_mode)
            await self._device.set_fan_oscillation_mode(self._swing_mode)
            await asyncio.sleep(0.5)

        elif self._hvac_mode == HVACMode.HEAT:
            await self._device.command("main", "switch", "on")
            await self._device.set_air_conditioner_mode(self._hvac_mode)
            await self._device.set_fan_mode(self._fan_mode)
            await self._device.set_fan_oscillation_mode(self._swing_mode)
            await asyncio.sleep(0.5)

        elif self._hvac_mode == HVACMode.FAN_ONLY:
            await self._device.command("main", "switch", "on")
            await self._device.set_air_conditioner_mode("wind")
            await self._device.set_fan_mode(self._fan_mode)
            await self._device.set_fan_oscillation_mode(self._swing_mode)
            await asyncio.sleep(0.5)

        elif self._hvac_mode == HVACMode.AUTO:
            await self._device.command("main", "switch", "on")
            await self._device.set_air_conditioner_mode(self._hvac_mode)
            await self._device.set_fan_mode(self._fan_mode)
            await self._device.set_fan_oscillation_mode(self._swing_mode)
            await asyncio.sleep(0.5)

        elif self._hvac_mode == HVACMode.DRY:
            await self._device.command("main", "switch", "on")
            await self._device.set_air_conditioner_mode(self._hvac_mode)
            await self._device.set_fan_mode(self._fan_mode)
            await self._device.set_fan_oscillation_mode(self._swing_mode)
            await asyncio.sleep(0.5)
        else:
            pass
        
        await asyncio.sleep(0.5)
        self._pending_update = False
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._pending_update = True
        self._fan_mode = fan_mode
        await self._device.set_fan_mode(self._fan_mode)
        # await self._device.set_air_conditioner_mode(self._hvac_mode)
        # await self._device.set_fan_oscillation_mode(self._swing_mode)

        await asyncio.sleep(0.5)
        self._pending_update = False
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        self._pending_update = True
        self._swing_mode = swing_mode
        await self._device.set_fan_oscillation_mode(self._swing_mode)
        # await self._device.set_air_conditioner_mode(self._hvac_mode)
        # await self._device.set_fan_mode(self._fan_mode)

        await asyncio.sleep(0.5)
        self._pending_update = False
        self.async_write_ha_state()

    async def async_update(self):
        if self._pending_update:
            return

        await self._device.status.refresh()
        self._current_temperature = self._device.status.values["temperature"]
        self._current_humidity = self._device.status.values["humidity"]
        self._target_temperature = self._device.status.values["coolingSetpoint"]
        self._fan_mode = self._device.status.values["fanMode"]
        self._swing_mode = self._device.status.values["fanOscillationMode"]
        self._attributes = {
            "dustFilterStatus": self._device.status.values["dustFilterStatus"],
            "status": self._device.status.values["status"],
            "supportedActions": self._device.status.values["supportedActions"],
            "P_energy": self._device.status.values["powerConsumption"],
            # "P_deltaEnergy": self._device.status.values["powerConsumption"]["deltaEnergy"],
            # "P_power": self._device.status.values["powerConsumption"]["power"],
            # "P_powerEnergy": self._device.status.values["powerConsumption"]["powerEnergy"],
            # "P_persistedEnergy": self._device.status.values["powerConsumption"]["persistedEnergy"],
            # "P_energySaved": self._device.status.values["powerConsumption"]["energySaved"],
            "name": self._device.name,
            "label": self._device.label
        }
        # _LOGGER.warning(f"label: {_label}: temp: {self._current_temperature}")