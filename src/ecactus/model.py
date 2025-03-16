"""Data model for ECOS API."""

from bisect import bisect_left
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Annotated, Any, Self  # noqa: UP035


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

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.


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

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.

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

    model_config = ConfigDict(extra="allow", populate_by_name=True)  # Allows additional fields. Allows to populate by field name in the model attribute, as well as the aliases.
# Extra fields :
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


class PowerMetrics(BaseModel):
    """Represents a single timestamped power data point.

    Attributes:
        timestamp: Timestamp of the data point.
        solar_power (float | None): Power generated by the solar panels in watts (W).
        grid_power: To be defined (W).
        battery_power: Power to/from the battery (W).
        meter_power: Power measured (Negative means export to the grid, positive means import from the grid.) (W).
        home_power (float | None): Power consumed by the home (W).
        eps_power: Power consumed by the EPS (W).
        charge_power: To be defined (W).

    """

    timestamp: datetime = Field(default=datetime.now())
    solar: Annotated[float | None, Field(strict=True, ge=0, alias="solarPower")]
    grid: float | None = Field(alias="gridPower")
    battery: float | None = Field(alias="batteryPower")
    meter: float | None = Field(alias="meterPower")
    home: Annotated[float | None, Field(strict=True, ge=0, alias="homePower")]
    eps: float | None = Field(alias="epsPower")
    charge: float | None = Field(alias="chargePower", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)  # Allows additional fields. Allows to populate by field name in the model attribute, as well as the aliases.
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
#     "sysRunMode": 0,
#     "isExistSolar": true,
#     "sysPowerConfig": 3,
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


class PowerTimeSeries(BaseModel):
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

    metrics: list[PowerMetrics] = Field(default_factory=list) # if instance is created without explicitly providing data, a new, independent empty list is generated as the default

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: dict[str, Any]) -> dict[str, list[Any]]:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of PowerMetrics.

        """

        # no tranformation if input if already a list of metrics
        if 'metrics' in data:
            if all(isinstance(m, PowerMetrics) for m in data['metrics']):
                return data

        solar = data.get("solarPowerDps", {})
        battery = data.get("batteryPowerDps", {})
        grid = data.get("gridPowerDps", {})
        meter = data.get("meterPowerDps", {})
        home = data.get("homePowerDps", {})
        eps = data.get("epsPowerDps", {})

        # Assume all dicts have identical timestamp keys
        timestamps = sorted(home.keys(), key=lambda ts: int(ts))
        data_points = []
        for ts in timestamps:
            ts_dt = datetime.fromtimestamp(int(ts))
            data_points.append({
                "timestamp": ts_dt,
                "solar": solar.get(ts, None),
                "battery": battery.get(ts, None),
                "grid": grid.get(ts, None),
                "meter": meter.get(ts, None),
                "home": home.get(ts, None),
                "eps": eps.get(ts, None),
            })
        return {"metrics": data_points}

    def find_by_timestamp(self, target: datetime, exact: bool = False) -> PowerMetrics | None:
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

    def find_between(self, start: datetime, end: datetime) -> 'PowerTimeSeries':
        """Return a list of PowerMetrics instances with timestamps between start and end (inclusive).

        Args:
            start: The start datetime of the range.
            end: The end datetime of the range.

        Returns:
            A list of PowerMetrics instances with timestamps between start and end (inclusive).

        """
        return PowerTimeSeries(metrics=[m for m in self.metrics if start <= m.timestamp <= end])

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


class EnergyMetric(BaseModel):
    """Represents a single energy data point.

    Attributes:
        timestamp: Timestamp of the data point.
        energy: The measured energy value at the given timestamp.

    """

    timestamp: datetime
    energy: float | None


class EnergyHistory(BaseModel):
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

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: dict[str, Any]) -> dict[str, list[Any]]:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of EnergyMetric.

        """
        home = data.get("homeEnergyDps", {})
        timestamps = sorted(home.keys(), key=lambda ts: int(ts))
        data_points: list[dict[str, Any]] = []
        for ts in timestamps:
            ts_dt = datetime.fromtimestamp(int(ts))
            data_points.append({
                "timestamp": ts_dt,
                "energy": home.get(ts, None)
            })
        output: dict[str, Any] = {key: value for key, value in data.items() if key != "homeEnergyDps"} # copy items from data excluding homeEnergyDps
        output["metrics"] = data_points
        return output


class EnergyStatistics(BaseModel):
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

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.


class ConsumptionMetrics(BaseModel):
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

    timestamp: datetime = Field(default=datetime.now())
    from_battery: Annotated[float | None, Field(strict=True, ge=0, alias="fromBatteryDps")]
    to_battery: Annotated[float | None, Field(strict=True, ge=0, alias="toBatteryDps")]
    from_grid: Annotated[float | None, Field(strict=True, ge=0, alias="fromGridDps")]
    to_grid: Annotated[float | None, Field(strict=True, ge=0, alias="toGridDps")]
    from_solar: Annotated[float | None, Field(strict=True, ge=0, alias="fromSolarDps")]
    home: Annotated[float | None, Field(strict=True, ge=0, alias="homeEnergyDps")]
    eps: Annotated[float | None, Field(strict=True, ge=0, alias="epsDps")]
    self_powered: Annotated[float | None, Field(strict=True, ge=0, alias="selfPoweredDps")]

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.


class ConsumptionTimeSeries(BaseModel):
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

    metrics: list[ConsumptionMetrics] = Field(default_factory=list) # if instance is created without explicitly providing data, a new, independent empty list is generated as the default

    @model_validator(mode="before")
    @classmethod
    def _transform_raw_data(cls, data: dict[str, Any]) -> dict[str, list[Any]]:
        """Extract points from raw ECOS data.

        Args:
            data: Raw ECOS data.

        Returns:
            Formatted data compatible with a list of ConsumptionMetrics.

        """
        # no tranformation if input if already a list of metrics
        if 'metrics' in data:
            if all(isinstance(m, ConsumptionMetrics) for m in data['metrics']):
                return data

        from_battery = data.get("fromBatteryDps", {})
        to_battery = data.get("toBatteryDps", {})
        from_grid = data.get("fromGridDps", {})
        to_grid = data.get("toGridDps", {})
        from_solar = data.get("fromSolarDps", {})
        home = data.get("homeEnergyDps", {})
        eps = data.get("epsDps", {})
        self_powered = data.get("selfPoweredDps", {})


        # Assume all dicts have identical timestamp keys
        timestamps = sorted(home.keys(), key=lambda ts: int(ts))
        data_points = []
        for ts in timestamps:
            ts_dt = datetime.fromtimestamp(int(ts))
            data_points.append({
                "timestamp": ts_dt,
                "from_battery": from_battery.get(ts, None),
                "to_battery": to_battery.get(ts, None),
                "from_grid": from_grid.get(ts, None),
                "to_grid": to_grid.get(ts, None),
                "from_solar": from_solar.get(ts, None),
                "home": home.get(ts, None),
                "eps": eps.get(ts, None),
                "self_powered": self_powered.get(ts, None)
            })
        return {"metrics": data_points}


class DeviceInsight(BaseModel):
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
    energy_timeseries: ConsumptionTimeSeries | None = Field(alias="insightConsumptionDataDto")

    model_config = ConfigDict(populate_by_name=True)  # Allows to populate by field name in the model attribute, as well as the aliases.


