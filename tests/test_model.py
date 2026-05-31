"""Unit tests for the data models."""

from datetime import datetime

from ecactus.model import ConsumptionMetrics, PowerMetrics


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
