"""Data model for ECOS API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self  # noqa: UP035


class User(BaseModel):
    """Represents a user.

    Attributes:
        username: The user's username.
        nickname: The user's nickname.
        email: The user's email address.
        phone: The user's phone number.
        timezone_id: The user's time zone ID.
        timezone: The user's time zone offset (e.g., GMT-05:00).
        timezone_name: The user's time zone name (e.g., America/Toronto).
        datacenter_phonecode: The user's datacenter phone code.
        datacenter: The user's datacenter (e.g., EU).
        datacenter_host: The user's datacenter host (e.g., https://api-ecos-eu.weiheng-tech.com).

    """

    username: str
    nickname: str = ""
    email: str
    phone: str = ""
    timezone_id: str = Field(alias="timeZoneId")
    timezone: str = Field(alias="timeZone")
    timezone_name: str = Field(alias="timezoneName")
    datacenter_phonecode: int = Field(alias="datacenterPhoneCode")
    datacenter: str
    datacenter_host: str = Field(alias="datacenterHost")


class Home(BaseModel):
    """Represents a home.

    Attributes:
        id: Unique identifier for the home.
        name: Name of the home (or `SHARED_DEVICES` if the home is shared from another account).
        type: Type of the home.
        longitude: Longitude of the home's location, or None if not specified.
        latitude: Latitude of the home's location, or None if not specified.
        device_number: Number of devices associated with the home.
        relation_type: Type of relation for the home.
        create_time: Time when the home was created.
        update_time: Time when the home was last updated.

    """

    id: str = Field(alias="homeId")
    name: str = Field(alias="homeName")
    type: int = Field(alias="homeType")
    longitude: float | None = None
    latitude: float | None = None
    device_number: int = Field(alias="homeDeviceNumber")
    relation_type: int = Field(alias="relationType")
    create_time: datetime = Field(alias="createTime")
    update_time: datetime = Field(alias="updateTime")

    @model_validator(mode="after")
    def _enforce_shared_device_name(self) -> Self:
        """Force the name for virtual home 'shared devices' (homeType=0)."""
        if self.type == 0:
            self.name = "SHARED_DEVICES"
        return self


class Device(BaseModel):
    """Represents a device.

    Attributes:
        id: Unique identifier for the device.
        alias: Human-readable name for the device (e.g., "My Device").
        state: Current state of the device.
        vpp: VPP status.
        type: Type of the device.
        serial: Device serial number.
        agent_id: Unique identifier for the device's agent.
        longitude: Longitude of the device's location.
        latitude: Latitude of the device's location.
        device_type: Unknown (e.g., "XX-XXX123").
        master: Master status.

    """

    id: str = Field(alias="deviceId")
    alias: str = Field(alias="deviceAliasName")
    state: int
    vpp: bool
    type: int
    serial: str = Field(alias="deviceSn")
    agent_id: str = Field(alias="agentId")
    longitude: float = Field(alias="lon")
    latitude: float = Field(alias="lat")
    device_type: str | None = Field(alias="deviceType")
    master: int

    model_config = ConfigDict(extra="allow")  # Allows additional fields


# Not supported
# """
#     Attributes:
#         wifi_sn: WiFi serial number for the device.
#         battery_soc: Battery state of charge.
#         battery_power: Battery power level.
#         socket_switch: Socket switch state, or None if not applicable.
#         charge_station_mode: Charge station mode, or None if not applicable.
#         weight: Weight of the device.
#         temp: Temperature of the device, or None if not specified.
#         icon: Icon associated with the device, or None if not specified.
#         category: Category of the device, or None if not specified.
#         model: Model of the device, or None if not specified.-
#         resource_series_id: Resource series ID for the device.
#         resource_type_id: Resource type ID for the device.
#         ems_software_version: EMS software version.
#         dsp1_software_version: DSP1 software version.
# """
# wifi_sn: str = Field(alias="wifiSn")
# battery_soc: float = Field(alias="batterySoc")
# battery_power: int = Field(alias="batteryPower")
# socket_switch: bool | None = Field(alias="socketSwitch")
# charge_station_mode: str | None = Field(alias="chargeStationMode")
# weight: int
# temp: float | None
# icon: str | None
# category: str | None
# model: str | None
# resource_series_id: int = Field(alias="resourceSeriesId")
# resource_type_id: int = Field(alias="resourceTypeId")
# ems_software_version: str = Field(alias="emsSoftwareVersion")
# dsp1_software_version: str = Field(alias="dsp1SoftwareVersion")
