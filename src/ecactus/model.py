"""Data model for ECOS API."""

from bisect import bisect_left
from datetime import datetime
import re
from typing import ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Any, Self  # noqa: UP035


def _from_milliseconds(value: Any) -> Any:
    """Convert a millisecond epoch number to a naive local datetime, pass anything else through.

    Raises:
        ValueError: If the timestamp is out of range, so that pydantic reports it
            as a ValidationError.

    """
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            seconds = int(value) // 1000
        except OverflowError as err:  # json.loads accepts Infinity
            raise ValueError(f"timestamp out of range: {value}") from err
        return _from_timestamp(str(seconds))
    return value


def _from_timestamp(ts: str) -> datetime:
    """Convert a timestamp key of ECOS data to a datetime.

    Raises:
        ValueError: If the timestamp is not an integer or out of range, so that
            pydantic reports it as a ValidationError.

    """
    try:
        return datetime.fromtimestamp(int(ts))
    except (OverflowError, OSError) as err:
        raise ValueError(f"timestamp out of range: {ts}") from err


def _series(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return the `key` series of raw ECOS data, empty if it is absent or null.

    Raises:
        ValueError: If the series is neither an object nor null, so that pydantic
            reports it as a ValidationError.

    """
    series = data.get(key)
    if series is None:  # the API sends null for a whole DTO without data
        return {}
    if not isinstance(series, dict):
        # pydantic reports ValueError, not the TypeError the linter asks for
        raise ValueError(f"{key} should be an object")  # noqa: TRY004
    return series


class _EcosModel(BaseModel):
    """Base of every ECOS model.

    A ValidationError does not quote the input data, which can hold personal
    data (email, phone, location, serial numbers) and would otherwise end up in
    tracebacks that the log redaction does not cover. `errors()` still returns it.
    """

    model_config = ConfigDict(hide_input_in_errors=True)


class User(_EcosModel):
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

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.


class Home(_EcosModel):
    """Represents a home.

    Attributes:
        id: Unique identifier for the home.
        name: Name of the home (or `SHARED_DEVICES` if the home is shared from another account).
        type_int: Type number of the home.
        longitude: Longitude of the home's location, or None if not specified.
        latitude: Latitude of the home's location, or None if not specified.
        device_number: Number of devices associated with the home.
        relation_type_int: Type number of relation for the home.
        create_time: Time when the home was created.
        update_time: Time when the home was last updated.

    """

    id: str = Field(alias="homeId")
    name: str = Field(alias="homeName")
    type_int: int = Field(alias="homeType")
    # TODO: type (based on an Enum)
    longitude: float | None = None
    latitude: float | None = None
    device_number: int = Field(alias="homeDeviceNumber")
    relation_type_int: int = Field(alias="relationType")
    # TODO: relation_type (based on an Enum)
    create_time: datetime = Field(alias="createTime")
    update_time: datetime = Field(alias="updateTime")

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.

    @model_validator(mode="after")
    def _enforce_shared_device_name(self) -> Self:
        """Force the name for virtual home 'shared devices' (homeType=0)."""
        if self.type_int == 0:
            self.name = "SHARED_DEVICES"
        return self


class Device(_EcosModel):
    """Represents a device.

    Attributes:
        id: Unique identifier for the device.
        alias: Human-readable name for the device (e.g., "My Device").
        state_int: Current state number of the device.
        vpp: VPP status.
        type_int: Type number of the device.
        serial: Device serial number.
        agent_id: Unique identifier for the device's agent.
        longitude: Longitude of the device's location.
        latitude: Latitude of the device's location.
        device_type: Unknown (e.g., "XX-XXX123").
        master_int: Master status number.
        wifi_sn: WiFi dongle serial number. Only reported by get_devices, None otherwise.
        resource_series_id: Resource series ID. Only reported by get_devices, None otherwise.
        resource_type_id: Resource type ID. Only reported by get_devices, None otherwise.
        ems_software_version: EMS firmware version. Only reported by get_devices, None
            otherwise.
        dsp1_software_version: DSP1 firmware version. Only reported by get_devices, None
            otherwise.
        bms_vendor: Battery management system vendor. Only reported by get_devices, None
            otherwise.
        first_install: Date of the first installation. Only reported by get_devices, None
            otherwise.
        safety_standard_int: Grid safety standard number (1 = Germany VDE-AR-N 4105). Only
            reported by get_devices, None otherwise.

    """

    id: str = Field(alias="deviceId")
    alias: str = Field(alias="deviceAliasName")
    state_int: int = Field(alias="state")
    # TODO: state (based on an Enum)
    vpp: bool
    type_int: int = Field(alias="type")
    # TODO: type (based on an Enum)
    serial: str = Field(alias="deviceSn")
    agent_id: str = Field(alias="agentId")
    longitude: float = Field(alias="lon")
    latitude: float = Field(alias="lat")
    device_type: str | None = Field(alias="deviceType")
    master_int: int = Field(alias="master")
    # TODO: master (based on an Enum)
    wifi_sn: str | None = Field(alias="wifiSn", default=None)
    resource_series_id: int | None = Field(alias="resourceSeriesId", default=None)
    resource_type_id: int | None = Field(alias="resourceTypeId", default=None)
    ems_software_version: str | None = Field(alias="emsSoftwareVersion", default=None)
    dsp1_software_version: str | None = Field(alias="dsp1SoftwareVersion", default=None)
    bms_vendor: str | None = Field(alias="bmsVendor", default=None)
    first_install: datetime | None = Field(alias="firstInstall", default=None)
    safety_standard_int: int | None = Field(alias="safetyStandard", default=None)

    model_config = ConfigDict(
        extra="allow", populate_by_name=True
    )  # Allows additional fields. Allows to populate by field name in the model attribute, as well as the aliases.

    @field_validator("first_install", mode="before")
    @classmethod
    def _first_install_from_ms(cls, value: Any) -> Any:
        """Convert milliseconds since the epoch to the naive local time used elsewhere."""
        return _from_milliseconds(value)


# Extra fields not modelled yet:
# """
#     Attributes:
#         battery_soc: Battery state of charge.
#         battery_power: Battery power level.
#         socket_switch: Socket switch state, or None if not applicable.
#         charge_station_mode: Charge station mode, or None if not applicable.
#         weight: Weight of the device.
#         temp: Temperature of the device, or None if not specified.
#         icon: Icon associated with the device, or None if not specified.
#         category: Category of the device, or None if not specified.
#         model: Model of the device, or None if not specified.-
# """
# battery_soc: float = Field(alias="batterySoc")
# battery_power: int = Field(alias="batteryPower")
# socket_switch: bool | None = Field(alias="socketSwitch")
# charge_station_mode: str | None = Field(alias="chargeStationMode")
# weight: int
# temp: float | None
# icon: str | None
# category: str | None
# model: str | None


class PowerMetrics(_EcosModel):
    """Represents a single timestamped power data point.

    Attributes:
        timestamp: Timestamp of the data point.
        solar (float | None): Power generated by the solar panels in watts (W).
        grid: AC active power at the inverter output (W), the "Total Active Power" of the
            installer app. Not the grid meter, which is `meter`.
        battery: Power to/from the battery (W).
        meter: Power measured (Negative means export to the grid, positive means import from the grid.) (W).
        home (float | None): Power consumed by the home (W).
        eps: Power consumed by the EPS (W).
        charge: To be defined (W).
        battery_heater_status: Battery heater state (0 = off). Only reported by
            get_realtime_device_data, None otherwise.
        sys_run_mode: System run mode code (1 = grid connected). Only reported by
            get_realtime_device_data, None otherwise.
        sys_power_config: System power configuration code. Only reported by
            get_realtime_device_data, None otherwise.

    """

    timestamp: datetime = Field(default_factory=datetime.now)
    # No ge=0 constraint: the live API legitimately returns small negative
    # readings (measurement noise around zero, e.g. homePower=-2.0). Rejecting
    # them raised a ValidationError that discarded the entire surrounding
    # payload (a whole DeviceInsight / PowerTimeSeries), so a single noisy field
    # lost otherwise-valid data. strict=True is kept to avoid silent coercion.
    solar: Annotated[float | None, Field(strict=True, alias="solarPower")]
    grid: float | None = Field(alias="gridPower")
    battery: float | None = Field(alias="batteryPower")
    meter: float | None = Field(alias="meterPower")
    home: Annotated[float | None, Field(strict=True, alias="homePower")]
    eps: float | None = Field(alias="epsPower")
    charge: float | None = Field(alias="chargePower", default=None)
    # State codes of the realtime device payload. Optional: the history and
    # insight series reuse this model and never carry them.
    battery_heater_status: int | None = Field(alias="batHeaterStatus", default=None)
    sys_run_mode: int | None = Field(alias="sysRunMode", default=None)
    sys_power_config: int | None = Field(alias="sysPowerConfig", default=None)

    model_config = ConfigDict(
        extra="allow", populate_by_name=True
    )  # Allows additional fields. Allows to populate by field name in the model attribute, as well as the aliases.


# Extra fields (returned by get_realtime_home_data):
# "batterySocList": [
#     {
#         "deviceSn": "SHC000000000000001",
#         "batterySoc": 0.0,
#         "sysRunMode": 1,
#         "isExistSolar": True,
#         "sysPowerConfig": 3,
#     }
# ],
#
# Extra fields (returned by get_realtime_device_data):
#     "batterySoc": 0,
#     "isExistSolar": true,
#
# Example when all solar production is used by home:
# ``` py
# {'batterySoc': 0.0, 'batteryPower': 0, 'epsPower': 0, 'gridPower': 2479, 'homePower': 3674, 'meterPower': 1102, 'solarPower': 2572, 'sysRunMode': 1, 'isExistSolar': True, 'sysPowerConfig': 3}
# # Home 3674 (homePower)
# # PV -> Home 2572 (solarPower)
# # Grid -> Home 1102 (meterPower)
# # gridPower (could be related to operating mode with % reserved SOC for grid connection)
# ```
# Example when solar over production is injected to the grid:
# ``` py
# {'batterySoc': 0.0, 'batteryPower': 0, 'epsPower': 0, 'gridPower': 4194, 'homePower': 3798, 'meterPower': -650, 'solarPower': 4448, 'sysRunMode': 1, 'isExistSolar': True, 'sysPowerConfig': 3}
# # Home 3798
# # PV -> Home 4448
# # Home -> Grid 650
# # gridPower (could be related to operating mode with % reserved SOC for grid connection)
# ```


# class HomeMetrics(PowerMetrics):
#     """Represents a single timestamped data point for a home.

#     Attributes:
#         timestamp (datetime): Timestamp of the data point.
#         solar_power (int | None): Power generated by the solar panels in watts (W).
#         grid_power (int | None): Power exchanged with the grid (W). Negative means import, positive means export.
#         battery_power (int | None): Power flowing to/from the battery (W). Positive means charging, negative means discharging.
#         meter_power (int | None): Power measured (to be defined) (W).
#         home_power (int | None): Power consumed by the home (W).
#         eps_power (int | None): Power consumed by the EPS (W).
#         charge_power: (to be defined)
#         battery_soc: State of charge of each battery.

#     """

#     charge_power: int | None = Field(alias="chargePower")
#     battery_soc: list[Any] | None = Field(alias="batterySocList")

#     def __init__(self, **data) -> None:
#         """Initiate from Metrics class with current timestamp."""
#         data["timestamp"] = int(datetime.now().timestamp())
#         super().__init__(**data)


class PowerTimeSeries(_EcosModel):
    """Represents a series of power metrics over time.

    Attributes:
        metrics: A list of power metrics.

            During initialization it can be provided as a dictionary. Example:
            ``` py
            PowerTimeSeries( {
                "solarPowerDps":   { "1740783600":0.0, ... },
                "batteryPowerDps": { "1740783600":0.0, ... },
                "gridPowerDps":    { "1740783600":0.0, ... },
                "meterPowerDps":   { "1740783600":3152.0, ... },
                "homePowerDps":    { "1740783600":3152.0, ... },
                "epsPowerDps":     { "1740783600":0.0, ... }
            } )
            ```
            The model validator automatically transforms this raw dict into a sorted list of PowerMetrics objects.

    """

    metrics: Annotated[
        list[PowerMetrics], Field(default_factory=list)
    ]  # if instance is created without explicitly providing data, a new, independent empty list is generated as the default

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: Any) -> Any:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of PowerMetrics, or `data`
                unchanged if it is not a dict, for pydantic to reject.

        """
        if not isinstance(data, dict):
            return data

        # no tranformation if input if already a list of metrics
        if "metrics" in data:
            # a `metrics` that is not a list is left to pydantic to reject
            metrics = data["metrics"]
            if not isinstance(metrics, list) or all(
                isinstance(m, PowerMetrics) for m in metrics
            ):
                return data

        solar = _series(data, "solarPowerDps")
        battery = _series(data, "batteryPowerDps")
        grid = _series(data, "gridPowerDps")
        meter = _series(data, "meterPowerDps")
        home = _series(data, "homePowerDps")
        eps = _series(data, "epsPowerDps")

        # Assume all dicts have identical timestamp keys
        timestamps = sorted(home.keys(), key=int)
        data_points: list[dict[str, Any]] = []
        for ts in timestamps:
            ts_dt = _from_timestamp(ts)
            data_points.append(
                {
                    "timestamp": ts_dt,
                    "solar": solar.get(ts, None),
                    "battery": battery.get(ts, None),
                    "grid": grid.get(ts, None),
                    "meter": meter.get(ts, None),
                    "home": home.get(ts, None),
                    "eps": eps.get(ts, None),
                }
            )
        return {"metrics": data_points}

    def find_by_timestamp(
        self, target: datetime, exact: bool = False
    ) -> PowerMetrics | None:
        """Return the PowerMetrics instance with the timestamp nearest to the target datetime (or with the exact timestamp only).

        Args:
            target: The target datetime to find the PowerMetrics instance for.
            exact: If True, only return the PowerMetrics instance with the exact timestamp. If False, return the PowerMetrics instance with the timestamp nearest to the target datetime.

        Returns:
            A PowerMetrics instance corresponding to the target datetime.

        """
        if not self.metrics:
            return None

        if exact:
            for metric in self.metrics:
                if metric.timestamp == target:
                    return metric
            return None

        # Extract timestamps and use bisect for efficient nearest lookup.
        timestamps = [m.timestamp for m in self.metrics]
        pos = bisect_left(timestamps, target)

        if pos == 0:
            return self.metrics[0]
        if pos == len(self.metrics):
            return self.metrics[-1]

        before = self.metrics[pos - 1]
        after = self.metrics[pos]
        # Return the closer one.
        if abs(target - before.timestamp) <= abs(after.timestamp - target):
            return before
        return after

    def find_between(self, start: datetime, end: datetime) -> "PowerTimeSeries":
        """Return a list of PowerMetrics instances with timestamps between start and end (inclusive).

        Args:
            start: The start datetime of the range.
            end: The end datetime of the range.

        Returns:
            A list of PowerMetrics instances with timestamps between start and end (inclusive).

        """
        return PowerTimeSeries(
            metrics=[m for m in self.metrics if start <= m.timestamp <= end]
        )

    # def total_solar_energy(self) -> float:
    #     """Compute total solar energy generated during the day (in kWh)."""
    #     energy = 0.0
    #     for i in range(1, len(self.data_points)):
    #         dt = (self.data_points[i].timestamp - self.data_points[i-1].timestamp).total_seconds() / 3600  # Convert to hours
    #         avg_power = (self.data_points[i].solar_power + self.data_points[i-1].solar_power) / 2
    #         energy += avg_power * dt  # Power (W) * Time (h) = Energy (Wh)
    #     return energy / 1000  # Convert Wh to kWh

    # def peak_solar_power(self) -> float:
    #     """Get the highest solar power recorded during the day."""
    #     return max(dp.solar_power for dp in self.data_points)

    # def average_battery_soc(self) -> float:
    #     """Compute the average battery state of charge (SOC) for the day."""
    #     return sum(dp.battery_soc for dp in self.data_points) / len(self.data_points) if self.data_points else 0.0


class EnergyMetric(_EcosModel):
    """Represents a single energy data point.

    Attributes:
        timestamp: Timestamp of the data point.
        energy: The measured energy value at the given timestamp.

    """

    timestamp: datetime
    energy: float | None


class WeekDayEnergy(_EcosModel):
    """Represents the energy of one day in the rolling week of get_week_energy.

    Attributes:
        weekday: ISO weekday of the day (1 = Monday ... 7 = Sunday).
        solar: Solar production in kWh.
        grid: Energy imported from the grid in kWh.
        to_grid: Energy exported to the grid in kWh.
        home: Home consumption in kWh.
        self_powered: Share of the consumption covered without the grid, in percent.
        carbon_emissions: Avoided carbon emissions, or None if not reported.
        save_standard_coal: Saved standard coal, or None if not reported.

    """

    weekday: int
    solar: float | None = Field(alias="solarEnergy", default=None)
    grid: float | None = Field(alias="gridEnergy", default=None)
    to_grid: float | None = Field(alias="toGrid", default=None)
    home: float | None = Field(alias="homeEnergy", default=None)
    self_powered: float | None = Field(alias="selfPowered", default=None)
    carbon_emissions: float | None = Field(alias="carbonEmissions", default=None)
    save_standard_coal: float | None = Field(alias="saveStandardCoal", default=None)

    model_config = ConfigDict(populate_by_name=True)


class WeekEnergy(_EcosModel):
    """Represents the rolling week shown on the home screen of the ECOS app.

    The API keys the last seven days by ISO weekday: the entry of `today` is the
    current day (still running), the other six are the preceding days.

    Attributes:
        today: ISO weekday of the current day (1 = Monday ... 7 = Sunday).
        last_week_total_solar: Solar production of the last seven days in kWh.
        last_week_total_grid: Grid import of the last seven days in kWh.
        last_week_total_carbon_emissions: Avoided carbon emissions of the last seven days.
        last_week_total_save_standard_coal: Saved standard coal of the last seven days.
        days: One entry per weekday, sorted by weekday.

            During initialization it can be provided as the raw "weekEnergy",
            "carbonEmissionsWeekEnergy" and "saveStandardCoalWeekEnergy" dicts; the
            model validator merges them into a sorted list of WeekDayEnergy objects.

    """

    today: int
    last_week_total_solar: float | None = Field(
        alias="lastWeekTotalSolar", default=None
    )
    last_week_total_grid: float | None = Field(alias="lastWeekTotalGrid", default=None)
    last_week_total_carbon_emissions: float | None = Field(
        alias="lastWeekTotalCarbonEmissions", default=None
    )
    last_week_total_save_standard_coal: float | None = Field(
        alias="lastWeekTotalSaveStandardCoal", default=None
    )
    days: list[WeekDayEnergy] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _merge_week_dicts(cls, data: Any) -> Any:
        """Merge the three per-weekday dicts of the raw response into `days`.

        Args:
            data: Raw ECOS data.

        Returns:
            The data with a `days` list instead of the per-weekday dicts.

        """
        if not isinstance(data, dict) or "weekEnergy" not in data:
            return data
        keys = ("weekEnergy", "carbonEmissionsWeekEnergy", "saveStandardCoalWeekEnergy")
        merged: dict[int, dict[str, Any]] = {}
        for key in keys:
            for weekday, values in _series(data, key).items():
                if not isinstance(values, dict | None):
                    # pydantic reports ValueError, not the TypeError the linter asks for
                    raise ValueError(f"{key} values should be objects")  # noqa: TRY004
                merged.setdefault(int(weekday), {"weekday": int(weekday)}).update(
                    values or {}
                )
        data = {key: value for key, value in data.items() if key not in keys}
        data["days"] = [merged[weekday] for weekday in sorted(merged)]
        return data


class EnergyHistory(_EcosModel):
    """Represents a series of energy metrics over a period.

    Attributes:
        energy_consumption: The total energy consumption in kWh.
        solar_percent: The percentage of energy produced by solar panels.
        metrics: A list of energy measurement points.

            During initialization it can be provided as a dictionary from the "homeEnergyDps" field. Example:
                ```py
                EnergyHistory( {
                "energyConsumption": 12.3,
                "solarPercent": 45.6,
                "homeEnergyDps": {
                    "1733112000": 39.6,
                    ...
                    "1735707599": 41.3,
                    }
                } )
                ```
            The model validator automatically transforms this raw dict into a sorted list of EnergyMetric objects.

    """

    energy_consumption: float = Field(alias="energyConsumption")
    solar_percent: float = Field(alias="solarPercent")
    metrics: list[EnergyMetric] = Field(alias="homeEnergyDps")

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: Any) -> Any:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of EnergyMetric, or `data`
                unchanged if it is not a dict, for pydantic to reject.

        """
        if not isinstance(data, dict):
            return data
        home = _series(data, "homeEnergyDps")
        timestamps = sorted(home.keys(), key=int)
        data_points: list[dict[str, Any]] = []
        for ts in timestamps:
            ts_dt = _from_timestamp(ts)
            data_points.append({"timestamp": ts_dt, "energy": home.get(ts, None)})
        output: dict[str, Any] = {
            key: value for key, value in data.items() if key != "homeEnergyDps"
        }  # copy items from data excluding homeEnergyDps
        output["metrics"] = data_points
        return output


class EnergyStatistics(_EcosModel):
    """Represents energy statistics.

    Attributes:
        consumption: The total energy consumption (kWh).
        from_battery: The energy consumed from battery (kWh).
        to_battery: The energy sent to battery (kWh).
        from_grid: The energy consumed from the grid (kWh).
        to_grid: The energy sent to the grid (kWh).
        from_solar: The energy produced from solar (kWh).
        eps: To be defined.

    """

    consumption: float = Field(alias="consumptionEnergy")
    from_battery: float = Field(alias="fromBattery")
    to_battery: float = Field(alias="toBattery")
    from_grid: float = Field(alias="fromGrid")
    to_grid: float = Field(alias="toGrid")
    from_solar: float = Field(alias="fromSolar")
    eps: float

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.


class ConsumptionMetrics(_EcosModel):
    """Represents a single timestamped consumption data point.

    Attributes:
        timestamp: Timestamp of the data point.
        from_battery: Energy consumed from battery (kWh).
        to_battery: Energy sent to battery (kWh).
        from_grid: Energy consumed from the grid (kWh).
        to_grid: Energy sent to the grid (kWh).
        from_solar: Energy produced from solar (kWh).
        home: Home energy consumption (kWh).
        eps: To be defined.
        self_powered: Autonomous operation (%).

    """

    timestamp: datetime = Field(default_factory=datetime.now)
    from_battery: Annotated[
        float | None, Field(strict=True, ge=0, alias="fromBatteryDps")
    ]
    to_battery: Annotated[float | None, Field(strict=True, ge=0, alias="toBatteryDps")]
    from_grid: Annotated[float | None, Field(strict=True, ge=0, alias="fromGridDps")]
    to_grid: Annotated[float | None, Field(strict=True, ge=0, alias="toGridDps")]
    from_solar: Annotated[float | None, Field(strict=True, ge=0, alias="fromSolarDps")]
    home: Annotated[float | None, Field(strict=True, ge=0, alias="homeEnergyDps")]
    eps: Annotated[float | None, Field(strict=True, ge=0, alias="epsDps")]
    self_powered: Annotated[
        float | None, Field(strict=True, ge=0, alias="selfPoweredDps")
    ]

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.


class ConsumptionTimeSeries(_EcosModel):
    """Represents energy time series.

    Attributes:
        metrics: A list of consumption metrics.

            During initialization it can be provided as a dictionary. Example:
            ``` py
            ConsumptionTimeSeries( {
                "fromBatteryDps": {
                    "1733976000": 0.0,
                    "1733889600": 0.0,
                    ...
                    "1734062400": 0.0,
                },
                "toBatteryDps": {...},
                "fromGridDps": {...},
                "toGridDps": {...},
                "fromSolarDps": {...},
                "homeEnergyDps": {...},
                "epsDps": {...},
                "selfPoweredDps": {...},
            } )
            ```
            The model validator automatically transforms this raw dict into a sorted list of ConsumptionMetrics objects.

    """

    metrics: Annotated[
        list[ConsumptionMetrics], Field(default_factory=list)
    ]  # if instance is created without explicitly providing data, a new, independent empty list is generated as the default

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: Any) -> Any:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of ConsumptionMetrics, or
                `data` unchanged if it is not a dict, for pydantic to reject.

        """
        if not isinstance(data, dict):
            return data
        # no tranformation if input if already a list of metrics
        if "metrics" in data:
            # a `metrics` that is not a list is left to pydantic to reject
            metrics = data["metrics"]
            if not isinstance(metrics, list) or all(
                isinstance(m, ConsumptionMetrics) for m in metrics
            ):
                return data

        from_battery = _series(data, "fromBatteryDps")
        to_battery = _series(data, "toBatteryDps")
        from_grid = _series(data, "fromGridDps")
        to_grid = _series(data, "toGridDps")
        from_solar = _series(data, "fromSolarDps")
        home = _series(data, "homeEnergyDps")
        eps = _series(data, "epsDps")
        self_powered = _series(data, "selfPoweredDps")

        # Assume all dicts have identical timestamp keys
        timestamps = sorted(home.keys(), key=int)
        data_points: list[dict[str, Any]] = []
        for ts in timestamps:
            ts_dt = _from_timestamp(ts)
            data_points.append(
                {
                    "timestamp": ts_dt,
                    "from_battery": from_battery.get(ts, None),
                    "to_battery": to_battery.get(ts, None),
                    "from_grid": from_grid.get(ts, None),
                    "to_grid": to_grid.get(ts, None),
                    "from_solar": from_solar.get(ts, None),
                    "home": home.get(ts, None),
                    "eps": eps.get(ts, None),
                    "self_powered": self_powered.get(ts, None),
                }
            )
        return {"metrics": data_points}


class DeviceInsight(_EcosModel):
    """Represents various statistics and metrics.

    Attributes:
        self_powered: Autonomous operation (%).
        power_timeseries: A list of power metrics.
        energy_statistics: Statistics of energy usage.
        energy_timeseries: A list of energy consumption metrics.

    """

    self_powered: int = Field(alias="selfPowered")
    power_timeseries: PowerTimeSeries | None = Field(alias="deviceRealtimeDto")
    energy_statistics: EnergyStatistics | None = Field(alias="deviceStatisticsDto")
    energy_timeseries: ConsumptionTimeSeries | None = Field(
        alias="insightConsumptionDataDto"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows to populate by field name in the model attribute, as well as the aliases.


class EventType(_EcosModel):
    """Event type with a catalog and a generic fallback.

    Attributes:
        code: The event code (e.g., "event_0", "dsp_10").
        type: The type string (`"event"`, `"alarm"`, `"fault"`).
        type_id: The type integer (0 = event, 1 = alarm, 2 = fault).
        description: English description of the event.

    """

    # Public fields (kept to mirror API attribute names)
    code: str = Field(validation_alias="errorCode")
    type: str = Field(validation_alias="eventType")
    type_id: int | None = Field(validation_alias="eventTypeInt")
    description: str = Field(validation_alias="eventContentEn")

    # Known catalog (code -> (type, type_id, message))
    _CATALOG: ClassVar[dict[str, tuple[str, int, str]]] = {
        "event_0": ("event", 0, "Waiting for Grid"),
        "event_1": ("event", 0, "Grid Connected"),
        "event_5": ("event", 0, "Checking"),
        "dsp_10": ("fault", 2, "Grid Off Fault"),
        "dsp_11": ("fault", 2, "Grid Voltage Undertrip/Overtrip Fault"),
        # Add more known entries here
    }

    model_config = ConfigDict(populate_by_name=True)

    # @property
    # def is_fault(self) -> bool:
    #     return self.type == "fault"

    # @property
    # def is_event(self) -> bool:
    #     return self.type == "event"

    @classmethod
    def from_code(cls, code: str) -> "EventType | None":
        """Return a cataloged EventType if code is known, else None."""
        known_event_type = cls._CATALOG.get(code)
        if not known_event_type:
            return None
        type_str, type_id, description = known_event_type
        return cls(code=code, type=type_str, type_id=type_id, description=description)

    @classmethod
    def from_raw(cls, data: dict[str, Any]) -> "EventType":
        """Build from ECOS API raw data item, using catalog when known, else a generic fallback.

        Example:
            ``` py
            event_type = model.EventType.from_raw(
                {
                    "errorCode": "event_0",
                    "eventType": "event",
                    "eventTypeInt": 0,
                    "eventContentEn": "Waiting for Grid",
                }
            )
            ```

        """
        code = data.get("errorCode") or ""
        # Try catalog first; a code that is not a string is left to pydantic to reject
        known_event_type = (
            cls.from_code(code) if isinstance(code, str) and code else None
        )
        if known_event_type is not None:
            return known_event_type

        # Fallback uses API-provided values when available
        type_str = data.get("eventType") or ""
        if isinstance(type_str, str):
            type_str = type_str.lower().strip()
        type_id = data.get("eventTypeInt")
        description = data.get("eventContentEn") or "Unknown"

        return cls(
            code=code,
            type=type_str,
            type_id=type_id,
            description=description,
        )


class Event(_EcosModel):
    """Represents a single event occurrence.

    Attributes:
        event_type: The normalized event type (cataloged or generic).
        occurrence_time: When the event occurred.
        action_int: Whether the state begins or ends: `0` = begins, `1` = ends, None if
            not reported. Each state change of the device is a pair at the same second,
            the old state ending (`1`) and the new one beginning (`0`); an alarm has a
            `0` when it is raised and a `1` when it clears.

    """

    event_type: EventType
    occurrence_time: datetime = Field(alias="occurrenceTime")
    action_int: int | None = Field(alias="eventAction", default=None)

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: Any) -> dict[str, Any]:
        """Transform API response into EventItem structure.

        Uses catalog lookup; if not found, builds a generic EventType from API fields.
        """
        if isinstance(data, dict) and "errorCode" in data:
            typed_data = cast("dict[str, Any]", data)
            return {
                "event_type": EventType.from_raw(typed_data),
                "occurrenceTime": typed_data.get("occurrenceTime"),
                "eventAction": typed_data.get("eventAction"),
            }
        return cast("dict[str, Any]", data)


def _number_prefix(value: str | None) -> float | None:
    """Return the leading number of a string such as "13000W" or "9.98", else None."""
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


class DeviceDetail(_EcosModel):
    """Represents the details of a three-phase device (`/v2/device/three/device/detail`).

    The response also lists the accounts bound to the device (`accountList`).
    That personal data is intentionally not modelled; it stays in `model_extra`.

    Attributes:
        alias: Human-readable name of the device, or None if not reported.
        serial: Device serial number, or None if not reported.
        wifi_sn: WiFi dongle serial number, or None if not reported.
        model: Device model (e.g., "TIA133"), or None if not reported.
        master_int: Master status number, or None if not reported.
        type_int: Type number of the device, or None if not reported.
        ems_software_version: EMS firmware version, or None if not reported.
        dsp1_software_version: DSP1 firmware version, or None if not reported.
        resource_series_id: Resource series ID, or None if not reported.
        resource_type_id: Resource type ID, or None if not reported.
        first_install: Date of the first installation, or None if not reported.
        rated_power: Rated power as sent by the API (e.g., "13000W").
        battery_capacity: Battery capacity in kWh as sent by the API (e.g., "9.98").
        safety_standard_int: Grid safety standard number (1 = Germany VDE-AR-N 4105), or
            None if not reported.

    """

    alias: str | None = Field(alias="name", default=None)
    serial: str | None = Field(alias="deviceSn", default=None)
    wifi_sn: str | None = Field(alias="wifiSn", default=None)
    model: str | None = Field(alias="deviceModel", default=None)
    master_int: int | None = Field(alias="master", default=None)
    type_int: int | None = Field(alias="type", default=None)
    ems_software_version: str | None = Field(alias="emsSoftwareVersion", default=None)
    dsp1_software_version: str | None = Field(alias="dsp1SoftwareVersion", default=None)
    resource_series_id: int | None = Field(alias="resourceSeriesId", default=None)
    resource_type_id: int | None = Field(alias="resourceTypeId", default=None)
    first_install: datetime | None = Field(alias="firstInstall", default=None)
    rated_power: str | None = Field(alias="ratedPower", default=None)
    battery_capacity: str | None = Field(alias="batteryCapacity", default=None)
    safety_standard_int: int | None = Field(alias="safetyStandard", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("first_install", mode="before")
    @classmethod
    def _first_install_from_ms(cls, value: Any) -> Any:
        """Convert milliseconds since the epoch to the naive local time used elsewhere."""
        return _from_milliseconds(value)

    @property
    def rated_power_w(self) -> float | None:
        """Rated power in watts, parsed from `rated_power`."""
        return _number_prefix(self.rated_power)

    @property
    def battery_capacity_kwh(self) -> float | None:
        """Battery capacity in kWh, parsed from `battery_capacity`."""
        return _number_prefix(self.battery_capacity)


class DeviceSettings(_EcosModel):
    """Represents the operating settings of a device (`/customize/info`).

    The meaning of the codes is not documented by the API; the descriptions below
    follow the ECOS app. Fields not listed here stay available in `model_extra`.

    Attributes:
        min_capacity: Minimum battery level in percent.
        charge_use_mode_int: Charge use mode number.
        strategy_mode_int: Operating mode number (0 = self-consumption, "self-generate and use"
            in the ECOS app). The self_* fields belong to this mode.
        max_feed_in: Feed-in limit in percent of the inverter's rated power (e.g. 31 on a
            13 kW inverter = 4030 W, used for a 60 % grid export cap on 6.675 kWp of PV).
        feed_in_prohibition: Feed-in prohibition flag.
        discharge_to_grid_flag: Discharge-to-grid flag.
        eps_battery_min: Battery level reserved for off-grid (EPS) operation, in percent
            ("reserved SOC in island mode" in the app).
        self_soc: Battery level reserved for backup in self-consumption mode, in percent; the
            battery stops discharging there while on grid ("reserved SOC for backup").
        self_eps_bat: EPS reserve in self-consumption mode, in percent.
        self_feed_in: Feed-in setting in self-consumption mode.
        regular_soc: Minimum battery level in regular mode, in percent.
        regular_eps_bat: EPS reserve in regular mode, in percent.
        regular_feed_in: Feed-in setting in regular mode.
        backup_soc: Minimum battery level in backup mode (-1 = not set).
        backup_eps_bat: EPS reserve in backup mode (-1 = not set).
        backup_feed_in: Feed-in setting in backup mode (-1 = not set).
        def_charge_power: Default charge power in watts.
        def_discharge_power: Default discharge power in watts.
        rated_power: Rated power as sent by the API (e.g., "13000W").
        ems_software_version: EMS firmware version.
        dsp1_software_version: DSP1 firmware version.
        bms_software_version: BMS firmware version.
        auto_strategy: Automatic strategy flag.
        charging_list: Scheduled charging windows (raw).
        discharging_list: Scheduled discharging windows (raw).

    """

    min_capacity: int | None = Field(alias="minCapacity", default=None)
    charge_use_mode_int: int | None = Field(alias="chargeUseMode", default=None)
    strategy_mode_int: int | None = Field(alias="strategyMode", default=None)
    max_feed_in: int | None = Field(alias="maxFeedIn", default=None)
    feed_in_prohibition: int | None = Field(alias="feedInProhibition", default=None)
    discharge_to_grid_flag: int | None = Field(
        alias="dischargeToGridFlag", default=None
    )
    eps_battery_min: int | None = Field(alias="epsBatteryMin", default=None)
    self_soc: int | None = Field(alias="selfSoc", default=None)
    self_eps_bat: int | None = Field(alias="selfEpsBat", default=None)
    self_feed_in: int | None = Field(alias="selfFeedIn", default=None)
    regular_soc: int | None = Field(alias="regularSoc", default=None)
    regular_eps_bat: int | None = Field(alias="regularEpsBat", default=None)
    regular_feed_in: int | None = Field(alias="regularFeedIn", default=None)
    backup_soc: int | None = Field(alias="backupSoc", default=None)
    backup_eps_bat: int | None = Field(alias="backupEpsBat", default=None)
    backup_feed_in: int | None = Field(alias="backupFeedIn", default=None)
    def_charge_power: int | None = Field(alias="defChargePower", default=None)
    def_discharge_power: int | None = Field(alias="defDischargePower", default=None)
    rated_power: str | None = Field(alias="ratedPower", default=None)
    ems_software_version: str | None = Field(alias="emsSoftwareVersion", default=None)
    dsp1_software_version: str | None = Field(alias="dsp1SoftwareVersion", default=None)
    bms_software_version: str | None = Field(alias="bmsSoftwareVersion", default=None)
    auto_strategy: int | None = Field(alias="autoStrategy", default=None)
    charging_list: list[Any] = Field(alias="chargingList", default_factory=list)
    discharging_list: list[Any] = Field(alias="dischargingList", default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DeviceMode(_EcosModel):
    """Represents the operating mode of one device of a home (`/v2/home/device/mode`).

    Attributes:
        device_name: Human-readable name of the device, or None if not reported.
        charge_use_mode_int: Charge use mode number, or None if not reported.
        strategy_mode_int: Strategy mode number, or None if not reported.
        is_main: Main device flag, or None if not reported.

    """

    device_name: str | None = Field(alias="deviceName", default=None)
    charge_use_mode_int: int | None = Field(alias="chargeUseMode", default=None)
    strategy_mode_int: int | None = Field(alias="strategyMode", default=None)
    is_main: int | None = Field(alias="isMain", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ForecastPoint(_EcosModel):
    """Represents one 15-minute point of a forecast.

    Attributes:
        timestamp: Start of the 15-minute slot.
        power: Forecast power in watts, or None if not reported.

    """

    timestamp: datetime
    power: float | None


class Forecast(_EcosModel):
    """Represents a PV or load forecast for one calendar day, in 15-minute points.

    Attributes:
        metrics: Forecast points sorted by timestamp.

            During initialization it can be provided as the raw dict of the API,
            `{"pvForecastDps": {"1795388400": 0.0, ...}}` or
            `{"loadForecastDps": {...}}`. The model validator transforms it into
            a sorted list of ForecastPoint objects.

    """

    metrics: list[ForecastPoint] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: Any) -> Any:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of ForecastPoint.

        """
        if not isinstance(data, dict) or "metrics" in data:
            return data
        series = _series(data, "pvForecastDps") or _series(data, "loadForecastDps")
        return {
            "metrics": [
                {"timestamp": _from_timestamp(ts), "power": series[ts]}
                for ts in sorted(series, key=int)
            ]
        }


class DailySavings(_EcosModel):
    """Represents the costs and savings of one day (`/v2/home/cost/info`).

    Attributes:
        day: The day.
        load_cost: Cost of the home consumption at the grid price.
        grid_cost: Cost of the energy imported from the grid.
        feed_earnings: Earnings from the energy exported to the grid.
        day_savings: Savings of the day.

    """

    day: datetime
    load_cost: float | None = Field(alias="loadCost", default=None)
    grid_cost: float | None = Field(alias="gridCost", default=None)
    feed_earnings: float | None = Field(alias="feedEarnings", default=None)
    day_savings: float | None = Field(alias="daySavings", default=None)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("day", mode="before")
    @classmethod
    def _day_from_ms(cls, value: Any) -> Any:
        """Convert milliseconds since the epoch to the naive local time used elsewhere."""
        return _from_milliseconds(value)


class CostInfo(_EcosModel):
    """Represents the costs and savings of a home as computed by the ECOS cloud.

    Amounts are in the currency configured for the home.

    Attributes:
        today_savings: Savings of the current day.
        weekly_savings: Costs and savings of the last days.
        month_savings: Savings of the current month.
        month_load_cost: Cost of the home consumption of the current month.
        month_grid_cost: Cost of the grid import of the current month.
        month_feed_earnings: Feed-in earnings of the current month.

    """

    today_savings: float | None = Field(alias="todaySavings", default=None)
    weekly_savings: list[DailySavings] = Field(
        alias="weeklySavings", default_factory=list
    )
    month_savings: float | None = Field(alias="monthSavings", default=None)
    month_load_cost: float | None = Field(alias="monthLoadCost", default=None)
    month_grid_cost: float | None = Field(alias="monthGridCost", default=None)
    month_feed_earnings: float | None = Field(alias="monthFeedEarnings", default=None)

    model_config = ConfigDict(populate_by_name=True)


class BackupStatistics(_EcosModel):
    """Represents the backup (EPS) statistics of a device over a period.

    Attributes:
        count: Number of backup events.
        energy: Energy supplied in backup mode.
        duration: Duration in backup mode.

    """

    count: int | None = Field(alias="backupCount", default=None)
    energy: float | None = Field(alias="backupEnergy", default=None)
    duration: float | None = Field(alias="backupDuration", default=None)

    model_config = ConfigDict(populate_by_name=True)


class MessageCount(_EcosModel):
    """Represents the number of unread messages of the account.

    Attributes:
        device: Unread device messages.
        official: Unread official messages.

    """

    device: int = Field(alias="deviceMessageCount", default=0)
    official: int = Field(alias="officialMessageCount", default=0)

    model_config = ConfigDict(populate_by_name=True)


class FixedPrice(_EcosModel):
    """Represents the fixed electricity price configured for a home.

    Attributes:
        purchase_price: Price of imported energy per kWh.
        purchase_tax: Tax on imported energy.
        feed_in_price: Price paid for exported energy per kWh.

    """

    purchase_price: float | None = Field(alias="purchasePrice", default=None)
    purchase_tax: float | None = Field(alias="purchaseTax", default=None)
    feed_in_price: float | None = Field(alias="feedInPrice", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)
