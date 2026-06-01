"""Unit tests for the data models."""

from datetime import datetime, timedelta

import pytest

from ecactus.model import (
    ConsumptionMetrics,
    ConsumptionTimeSeries,
    DeviceInsight,
    EnergyHistory,
    Event,
    EventType,
    PowerMetrics,
    PowerTimeSeries,
)


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


# --- PowerTimeSeries -------------------------------------------------------
def _power_series() -> PowerTimeSeries:
    """Build a 3-point series from a raw ECOS payload."""
    return PowerTimeSeries.model_validate(
        {
            "solarPowerDps": {"1000": 10.0, "3000": 30.0, "2000": 20.0},
            "batteryPowerDps": {"1000": 0.0, "2000": 0.0, "3000": 0.0},
            "gridPowerDps": {"1000": 0.0, "2000": 0.0, "3000": 0.0},
            "meterPowerDps": {"1000": 0.0, "2000": 0.0, "3000": 0.0},
            "homePowerDps": {"1000": 10.0, "2000": 20.0, "3000": 30.0},
            "epsPowerDps": {"1000": 0.0, "2000": 0.0, "3000": 0.0},
        }
    )


def test_power_timeseries_transform_sorts_by_timestamp():
    """Raw Dps dicts are turned into a list of PowerMetrics sorted by timestamp."""
    series = _power_series()
    assert [m.solar for m in series.metrics] == [10.0, 20.0, 30.0]
    assert series.metrics == sorted(series.metrics, key=lambda m: m.timestamp)


def test_power_timeseries_passthrough_when_already_metrics():
    """A list of PowerMetrics is accepted as-is (no re-transformation)."""
    metric = _power_series().metrics[0]
    series = PowerTimeSeries(metrics=[metric])
    assert series.metrics == [metric]


def test_find_by_timestamp_exact_hit_and_miss():
    """Exact lookup returns the matching metric, or None when none matches."""
    series = _power_series()
    target = series.metrics[1].timestamp
    assert series.find_by_timestamp(target, exact=True) is series.metrics[1]
    miss = target + timedelta(seconds=1)
    assert series.find_by_timestamp(miss, exact=True) is None


def test_find_by_timestamp_nearest():
    """Non-exact lookup returns the closest metric, clamped at both ends."""
    series = _power_series()
    first, mid, last = series.metrics
    assert series.find_by_timestamp(first.timestamp - timedelta(hours=1)) is first
    assert series.find_by_timestamp(last.timestamp + timedelta(hours=1)) is last
    near_mid = mid.timestamp - timedelta(seconds=1)
    assert series.find_by_timestamp(near_mid) is mid


def test_find_by_timestamp_empty_series_returns_none():
    """Lookup on an empty series returns None."""
    assert PowerTimeSeries().find_by_timestamp(_power_series().metrics[0].timestamp) is None


def test_find_between_is_inclusive():
    """find_between returns the metrics whose timestamp falls within the range."""
    series = _power_series()
    first, mid, _last = series.metrics
    subset = series.find_between(first.timestamp, mid.timestamp)
    assert [m.solar for m in subset.metrics] == [10.0, 20.0]


# --- ConsumptionTimeSeries -------------------------------------------------
def test_consumption_timeseries_transform():
    """Raw consumption Dps dicts become a sorted list of ConsumptionMetrics."""
    series = ConsumptionTimeSeries.model_validate(
        {
            "fromBatteryDps": {"1000": 1.0, "2000": 2.0},
            "toBatteryDps": {"1000": 0.0, "2000": 0.0},
            "fromGridDps": {"1000": 0.0, "2000": 0.0},
            "toGridDps": {"1000": 0.0, "2000": 0.0},
            "fromSolarDps": {"1000": 0.0, "2000": 0.0},
            "homeEnergyDps": {"1000": 5.0, "2000": 6.0},
            "epsDps": {"1000": 0.0, "2000": 0.0},
            "selfPoweredDps": {"1000": 50.0, "2000": 60.0},
        }
    )
    assert [m.from_battery for m in series.metrics] == [1.0, 2.0]
    assert [m.home for m in series.metrics] == [5.0, 6.0]


def test_consumption_timeseries_passthrough_when_already_metrics():
    """A list of ConsumptionMetrics is accepted as-is (no re-transformation)."""
    metric = ConsumptionMetrics(
        fromBatteryDps=1.0,
        toBatteryDps=0.0,
        fromGridDps=0.0,
        toGridDps=0.0,
        fromSolarDps=0.0,
        homeEnergyDps=5.0,
        epsDps=0.0,
        selfPoweredDps=50.0,
    )
    series = ConsumptionTimeSeries(metrics=[metric])
    assert series.metrics == [metric]


# --- EnergyHistory ---------------------------------------------------------
def test_energy_history_transform():
    """The homeEnergyDps map is split into EnergyMetric points; scalars are kept."""
    history = EnergyHistory.model_validate(
        {
            "energyConsumption": 12.3,
            "solarPercent": 45.6,
            "homeEnergyDps": {"1000": 1.1, "2000": 2.2},
        }
    )
    assert history.energy_consumption == 12.3
    assert history.solar_percent == 45.6
    assert [m.energy for m in history.metrics] == [1.1, 2.2]


# --- EventType -------------------------------------------------------------
def test_eventtype_from_code_known():
    """A catalogued code resolves to its known type/description."""
    et = EventType.from_code("dsp_10")
    assert et is not None
    assert (et.type, et.type_id, et.description) == ("fault", 2, "Grid Off Fault")


def test_eventtype_from_code_unknown_returns_none():
    """An unknown code yields None."""
    assert EventType.from_code("does_not_exist") is None


def test_eventtype_from_raw_uses_catalog():
    """from_raw prefers the catalog over the raw payload values."""
    et = EventType.from_raw({"errorCode": "event_0", "eventType": "ignored"})
    assert (et.code, et.type, et.description) == ("event_0", "event", "Waiting for Grid")


def test_eventtype_from_raw_fallback_for_unknown_code():
    """An unknown code falls back to the API-provided fields (type lower-cased)."""
    et = EventType.from_raw(
        {
            "errorCode": "dsp_99",
            "eventType": "FAULT",
            "eventTypeInt": 2,
            "eventContentEn": "Some new fault",
        }
    )
    assert (et.code, et.type, et.type_id, et.description) == (
        "dsp_99",
        "fault",
        2,
        "Some new fault",
    )


def test_eventtype_from_raw_fallback_defaults_description():
    """Missing description defaults to 'Unknown'."""
    et = EventType.from_raw({"errorCode": "dsp_99", "eventType": "fault", "eventTypeInt": 2})
    assert et.description == "Unknown"


# --- Event -----------------------------------------------------------------
def test_event_transform_from_raw():
    """A raw event dict (with errorCode) is normalised into an Event."""
    event = Event.model_validate(
        {
            "errorCode": "event_1",
            "eventType": "event",
            "eventTypeInt": 0,
            "eventContentEn": "Grid Connected",
            "occurrenceTime": 946684800,
        }
    )
    assert event.event_type.code == "event_1"
    assert event.event_type.description == "Grid Connected"


def test_event_passthrough_when_already_structured():
    """Pre-built data without errorCode is passed through to normal validation."""
    et = EventType.from_code("event_0")
    event = Event(event_type=et, occurrenceTime=946684800)
    assert event.event_type is et
