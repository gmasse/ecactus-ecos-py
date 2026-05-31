"""Unit tests for the data models."""

from datetime import datetime

import pytest

from ecactus.model import ConsumptionMetrics, DeviceInsight, PowerMetrics


def test_power_metrics_timestamp_uses_default_factory():
    """The default timestamp must be evaluated per instance, not once at import.

    With ``Field(default=datetime.now())`` the default is frozen at class
    definition time, so every instance shares the import-time timestamp. A
    ``default_factory`` evaluates ``datetime.now`` at instantiation instead.
    """
    before = datetime.now()
    metric = PowerMetrics(
        solarPower=0,
        gridPower=0,
        batteryPower=0,
        meterPower=0,
        homePower=0,
        epsPower=0,
    )
    assert metric.timestamp >= before


def test_consumption_metrics_timestamp_uses_default_factory():
    """Same default_factory guarantee for ConsumptionMetrics."""
    before = datetime.now()
    metric = ConsumptionMetrics(
        fromBatteryDps=0,
        toBatteryDps=0,
        fromGridDps=0,
        toGridDps=0,
        fromSolarDps=0,
        homeEnergyDps=0,
        epsDps=0,
        selfPoweredDps=0,
    )
    assert metric.timestamp >= before


def test_power_metrics_accepts_small_negative_values():
    """The live API returns small negative power readings (noise around zero).

    These must not raise: a single out-of-range field previously aborted the
    whole nested parse (DeviceInsight / PowerTimeSeries) and discarded valid
    data alongside it.
    """
    metric = PowerMetrics(
        solarPower=0,
        gridPower=0,
        batteryPower=0,
        meterPower=0,
        homePower=-2.0,
        epsPower=0,
    )
    assert metric.home == -2.0
    assert metric.solar == 0


def test_power_metrics_still_rejects_wrong_type():
    """strict=True is kept: a non-numeric value is still rejected."""
    with pytest.raises(ValueError):  # noqa: PT011
        PowerMetrics(
            solarPower="not-a-number",
            gridPower=0,
            batteryPower=0,
            meterPower=0,
            homePower=0,
            epsPower=0,
        )


def test_device_insight_survives_negative_realtime_value():
    """A negative realtime homePower must not break the surrounding DeviceInsight parse."""
    insight = DeviceInsight.model_validate(
        {
            "selfPowered": 42,
            "deviceRealtimeDto": {
                "solarPowerDps": {"1740783600": 0.0},
                "batteryPowerDps": {"1740783600": 0.0},
                "gridPowerDps": {"1740783600": 0.0},
                "meterPowerDps": {"1740783600": 0.0},
                "homePowerDps": {"1740783600": -2.0},
                "epsPowerDps": {"1740783600": 0.0},
            },
            "deviceStatisticsDto": {
                "consumptionEnergy": 12.3,
                "fromBattery": 1.0,
                "toBattery": 2.0,
                "fromGrid": 3.0,
                "toGrid": 4.0,
                "fromSolar": 5.0,
                "eps": 0.0,
            },
            "insightConsumptionDataDto": None,
        }
    )
    assert insight.self_powered == 42
    assert insight.energy_statistics is not None
    assert insight.energy_statistics.consumption == 12.3
    assert insight.power_timeseries is not None
    assert insight.power_timeseries.metrics[0].home == -2.0
