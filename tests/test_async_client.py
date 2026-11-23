"""Unit tests for asynchronous Ecos class."""

from datetime import datetime, timedelta
import logging

import pytest

import ecactus
from ecactus.exceptions import (
    AuthenticationError,
    HomeDoesNotExistError,
    HttpError,
    InitializationError,
    InvalidJsonError,
    ParameterVerificationFailedError,
    UnauthorizedDeviceError,
    UnauthorizedError,
)

from .conftest import LOGIN, PASSWORD  # noqa: TID251

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


@pytest.fixture(scope="session")
async def client(mock_server):
    """Return an ECOS client."""
    return ecactus.AsyncEcos(url=mock_server.url)


@pytest.fixture(scope="session")
def bad_client(mock_server):
    """Return an ECOS client with wrong authentication token."""
    return ecactus.AsyncEcos(url=mock_server.url, access_token="wrong_token")


def test_exceptions():
    """Test exceptions."""
    exc = InitializationError()
    assert str(exc) == "Initialization error"
    exc = AuthenticationError()
    assert str(exc) == "Account or password or country error"
    exc = UnauthorizedError()
    assert str(exc) == "Unauthorized"
    exc = HomeDoesNotExistError()
    assert str(exc) == "Home does not exist"
    exc = HomeDoesNotExistError("home_id")
    assert str(exc) == "Home does not exist: home_id"
    exc = UnauthorizedDeviceError()
    assert str(exc) == "Device is not authorized"
    exc = ParameterVerificationFailedError()
    assert str(exc) == "Parameter verification failed"
    exc = InvalidJsonError()
    assert str(exc) == "Invalid JSON"
    exc = HttpError(404, "Not Found")
    assert str(exc) == "HTTP error: 404 Not Found"


def test_client():
    """Test ECOS client."""
    with pytest.raises(InitializationError):
        ecactus.AsyncEcos()
    with pytest.raises(InitializationError):
        ecactus.AsyncEcos(datacenter="XX")
    client = ecactus.AsyncEcos(datacenter="EU")
    assert "weiheng-tech.com" in client.url


async def test_ensure_login(mock_server):
    """Test autologin."""
    temp_client = ecactus.AsyncEcos(url=mock_server.url)
    with pytest.raises(AuthenticationError) as excinfo:
        user = await temp_client.get_user()
    assert str(excinfo.value) == "Missing Account or Password"
    temp_client = ecactus.AsyncEcos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    user = await temp_client.get_user()
    assert user.username == LOGIN


# A client given an email and a password, but not logged in yet, must log
# in before calling any of these endpoints.
@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("get_realtime_home_data", {"home_id": 9876543210987654321}),
        ("get_realtime_device_data", {"device_id": 1234567890123456789}),
        ("get_history", {"device_id": 1234567890123456789, "period_type": 4}),
        (
            "get_insight",
            {
                "device_id": 1234567890123456789,
                "period_type": 2,
                "start_date": datetime.now(),
            },
        ),
        (
            "get_fault_events",
            {
                "device_id": 1234567890123456789,
                "start_date": datetime.now() - timedelta(days=7),
                "end_date": datetime.now(),
            },
        ),
        ("get_device_detail", {"device_id": 1234567890123456789}),
        ("get_device_settings", {"device_id": 1234567890123456789}),
        ("get_device_modes", {"home_id": 9876543210987654321}),
        ("get_power_limit", {"device_id": 1234567890123456789}),
        (
            "get_pv_forecast",
            {"home_id": 9876543210987654321, "day": datetime.now()},
        ),
        (
            "get_load_forecast",
            {"home_id": 9876543210987654321, "day": datetime.now()},
        ),
        ("get_cost_info", {"home_id": 9876543210987654321}),
        ("get_week_energy", {"home_id": 9876543210987654321}),
        (
            "get_backup_statistics",
            {
                "device_id": 1234567890123456789,
                "start_date": datetime.now() - timedelta(days=30),
                "end_date": datetime.now(),
            },
        ),
        ("get_unread_message_count", {}),
        ("get_fixed_price", {"home_id": 9876543210987654321}),
    ],
)
async def test_ensure_login_before_call(mock_server, method, kwargs):
    """Test autologin on the methods that read device or home data."""
    temp_client = ecactus.AsyncEcos(email=LOGIN, password=PASSWORD, url=mock_server.url)
    await getattr(temp_client, method)(**kwargs)
    assert temp_client.access_token == mock_server.access_token


async def test_login(mock_server, client):
    """Test login."""
    with pytest.raises(AuthenticationError):
        await client.login("wrong_login", "wrong_password")
    await client.login(LOGIN, PASSWORD)
    assert client.access_token == mock_server.access_token
    assert client.refresh_token == mock_server.refresh_token


async def test_get_user(client, bad_client):
    """Test get user info."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_user()
    user = await client.get_user()
    assert user.username == LOGIN


async def test_get_homes(client, bad_client):
    """Test get homes."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_homes()
    homes = await client.get_homes()
    assert homes[1].name == "My Home"


async def test_get_devices(client, bad_client):
    """Test get devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_devices(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await client.get_devices(home_id=0)
    devices = await client.get_devices(home_id=9876543210987654321)
    assert devices[0].alias == "My Device"
    assert devices[0].wifi_sn == "WIFI000000000001"
    assert devices[0].ems_software_version == "000-00000-00"
    assert devices[0].dsp1_software_version == "111-11111-11"
    assert devices[0].bms_vendor == "VENDOR"
    assert devices[0].first_install == datetime.fromtimestamp(1700000000)
    assert devices[0].safety_standard_int == 1


async def test_get_all_devices(client, bad_client):
    """Test get all devices."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_all_devices()
    devices = await client.get_all_devices()
    assert devices[0].alias == "My Device"


async def test_get_today_device_data(client, bad_client):
    """Test get current day device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_today_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_today_device_data(device_id=0)
    power_ts = await client.get_today_device_data(device_id=1234567890123456789)
    assert len(power_ts.metrics) > 0
    # get the first  timestamp
    first_timestamp = power_ts.metrics[0].timestamp
    assert power_ts.find_by_timestamp(first_timestamp, exact=False).solar is not None
    assert power_ts.find_by_timestamp(first_timestamp, exact=True).solar is not None
    # get a timestamp that does not exist
    before_timestamp = first_timestamp - timedelta(seconds=1)
    assert (
        power_ts.find_by_timestamp(before_timestamp, exact=False).solar
        == power_ts.metrics[0].solar
    )  # the nearst metric is returned
    assert (
        power_ts.find_by_timestamp(before_timestamp, exact=True) is None
    )  # exact lookup returns None
    # get a timestamp after the last one
    last_timestamp = power_ts.metrics[-1].timestamp
    after_timestamp = last_timestamp + timedelta(seconds=1)
    assert (
        power_ts.find_by_timestamp(after_timestamp, exact=False).solar
        == power_ts.metrics[-1].solar
    )  # value is 1/10th of the position
    assert power_ts.find_by_timestamp(after_timestamp, exact=True) is None
    # get a timestamp within 2 existings
    if len(power_ts.metrics) > 2:
        timestamp1 = power_ts.metrics[1].timestamp
        timestamp2 = power_ts.metrics[2].timestamp
        delta = timestamp2 - timestamp1
        if delta >= timedelta(seconds=2):
            timestamp = timestamp1 + delta / 2
            assert (
                power_ts.find_by_timestamp(timestamp, exact=False).solar
                == power_ts.metrics[1].solar
            )  # returns the value in 2nd position
            timestamp = timestamp1 + delta / 2 + timedelta(seconds=1)
            assert (
                power_ts.find_by_timestamp(timestamp, exact=False).solar
                == power_ts.metrics[2].solar
            )  # returns the value in 3rd position
    # return series between 2 dates
    between_ts = power_ts.find_between(first_timestamp, last_timestamp)
    assert len(between_ts.metrics) == len(power_ts.metrics)


async def test_get_realtime_device_data(client, bad_client):
    """Test get realtime device data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_device_data(device_id=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_realtime_device_data(device_id=0)
    power_metrics = await client.get_realtime_device_data(device_id=1234567890123456789)
    assert power_metrics.home is not None
    assert power_metrics.battery_heater_status == 0
    assert power_metrics.sys_run_mode == 0
    assert power_metrics.sys_power_config == 3


async def test_get_realtime_home_data(client, bad_client):
    """Test get realtime home data."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_realtime_home_data(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await client.get_realtime_home_data(home_id=0)
    power_metrics = await client.get_realtime_home_data(home_id=9876543210987654321)
    assert power_metrics.home is not None


async def test_get_history(client, bad_client):
    """Test get history."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_history(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_history(
            device_id=1234567890123456789, start_date=now, period_type=5
        )
    history = await client.get_history(
        device_id=1234567890123456789, start_date=now, period_type=4
    )
    assert len(history.metrics) == 1

    # TODO other period types


async def test_get_insight(client, bad_client):
    """Test get insight."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_insight(device_id=0, start_date=now, period_type=0)
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_insight(
            device_id=1234567890123456789, start_date=now, period_type=1
        )
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_insight(device_id=1234567890123456789, period_type=1)
    insight = await client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=0
    )
    assert len(insight.power_timeseries.metrics) > 1
    insight = await client.get_insight(
        device_id=1234567890123456789, start_date=now, period_type=2
    )
    assert len(insight.energy_timeseries.metrics) > 1


async def test_get_fault_events(client, bad_client):
    """Test get fault events."""
    end = datetime.now()
    start = end - timedelta(days=7)
    with pytest.raises(UnauthorizedError):
        await bad_client.get_fault_events(device_id=0, start_date=start, end_date=end)
    with pytest.raises(UnauthorizedDeviceError):
        await client.get_fault_events(device_id=0, start_date=start, end_date=end)
    events = await client.get_fault_events(
        device_id=1234567890123456789, start_date=start, end_date=end
    )
    # By default every type comes back
    assert {e.event_type.type for e in events} == {"event", "fault", "alarm"}
    for wanted in ("fault", "alarm", "event"):
        filtered = await client.get_fault_events(
            device_id=1234567890123456789,
            start_date=start,
            end_date=end,
            event_type=wanted,
        )
        assert filtered
        assert {e.event_type.type for e in filtered} == {wanted}


async def test_get_device_detail(client, bad_client):
    """Test get device detail."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_device_detail(device_id=0)
    detail = await client.get_device_detail(device_id=1234567890123456789)
    assert detail.model == "XX-XXX123"
    assert detail.rated_power_w == 10000
    assert detail.battery_capacity_kwh == 9.98
    assert detail.first_install == datetime.fromtimestamp(1700000000)
    # the bound accounts are personal data and not modelled
    assert not hasattr(detail, "account_list")


async def test_get_device_settings(client, bad_client):
    """Test get device settings."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_device_settings(device_id=0)
    settings = await client.get_device_settings(device_id=1234567890123456789)
    assert settings.self_soc == 15
    assert settings.eps_battery_min == 10
    assert settings.bms_software_version == "222-22222-22"
    assert settings.charging_list == []


async def test_get_device_modes(client, bad_client):
    """Test get device modes."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_device_modes(home_id=0)
    modes = await client.get_device_modes(home_id=9876543210987654321)
    assert modes[0].charge_use_mode_int == 0
    assert modes[0].is_main is None


async def test_get_power_limit(client, bad_client):
    """Test get power limit."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_power_limit(device_id=0)
    assert await client.get_power_limit(device_id=1234567890123456789) == 0


async def test_get_pv_and_load_forecast(client, bad_client):
    """Test get PV and load forecasts, plain and realtime."""
    now = datetime.now()
    with pytest.raises(UnauthorizedError):
        await bad_client.get_pv_forecast(home_id=0, day=now)
    pv = await client.get_pv_forecast(home_id=9876543210987654321, day=now)
    assert [p.power for p in pv.metrics] == [0.0, 100.0, 200.0, 300.0]
    assert pv.metrics[0].timestamp < pv.metrics[1].timestamp
    load = await client.get_load_forecast(
        home_id=9876543210987654321, day=now - timedelta(hours=1), realtime=True
    )
    assert len(load.metrics) == 4
    with pytest.raises(ParameterVerificationFailedError):
        await client.get_pv_forecast(
            home_id=9876543210987654321, day=now + timedelta(days=1), realtime=True
        )


async def test_get_cost_info(client, bad_client):
    """Test get cost info."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_cost_info(home_id=0)
    cost = await client.get_cost_info(home_id=9876543210987654321)
    assert cost.today_savings == 0.99
    assert cost.weekly_savings[0].day == datetime.fromtimestamp(1700000000)
    assert cost.weekly_savings[0].day_savings == 0.6


async def test_get_week_energy(client, bad_client):
    """Test get week energy."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_week_energy(home_id=0)
    with pytest.raises(HomeDoesNotExistError):
        await client.get_week_energy(home_id=0)
    week = await client.get_week_energy(home_id=9876543210987654321)
    assert week.today == 1
    assert [d.weekday for d in week.days] == [1, 2]
    assert week.days[0].solar == 6.4
    assert week.days[0].carbon_emissions == 6.4
    assert week.days[1].save_standard_coal == 0.8


async def test_get_backup_statistics(client, bad_client):
    """Test get backup statistics."""
    end = datetime.now()
    start = end - timedelta(days=30)
    with pytest.raises(UnauthorizedError):
        await bad_client.get_backup_statistics(
            device_id=0, start_date=start, end_date=end
        )
    stats = await client.get_backup_statistics(
        device_id=1234567890123456789, start_date=start, end_date=end
    )
    assert (stats.count, stats.energy, stats.duration) == (2, 1.5, 3.25)


async def test_get_unread_message_count(client, bad_client):
    """Test get unread message count."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_unread_message_count()
    count = await client.get_unread_message_count()
    assert (count.device, count.official) == (1, 0)


async def test_get_fixed_price(client, bad_client):
    """Test get fixed price."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_fixed_price(home_id=0)
    price = await client.get_fixed_price(home_id=9876543210987654321)
    assert price is not None
    assert (price.purchase_price, price.feed_in_price) == (0.32, 0.08)
    assert await client.get_fixed_price(home_id=1) is None


# TODO test 404
# TODO test bad method (ex GET in place of POST)


async def test_get_weather_now(client, bad_client):
    """Test the current weather."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_weather_now(longitude=1, latitude=2)
    weather = await client.get_weather_now(longitude=1, latitude=2)
    assert weather.temperature == 2.0
    assert weather.feels_like == -1.0
    assert weather.cloud == 26.0
    assert weather.wind_scale == "2"
    assert weather.observation_time is not None
    # Swapped coordinates: the weather service knows nothing, every value is None
    swapped = await client.get_weather_now(longitude=2, latitude=1)
    assert swapped.temperature is None
    assert swapped.observation_time is None


async def test_get_weather_hourly(client, bad_client):
    """Test the hourly weather forecast."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_weather_hourly(longitude=1, latitude=2)
    hours = await client.get_weather_hourly(longitude=1, latitude=2)
    assert [h.temperature for h in hours] == [0.0, -1.0, -2.0]
    assert hours[0].cloud is None  # empty string from the API
    assert hours[0].probability_of_precipitation == 0.0
    assert await client.get_weather_hourly(longitude=2, latitude=1) == []


async def test_get_weather_daily(client, bad_client):
    """Test the daily weather forecast."""
    with pytest.raises(UnauthorizedError):
        await bad_client.get_weather_daily(longitude=1, latitude=2)
    days = await client.get_weather_daily(longitude=1, latitude=2)
    assert days[0].day is not None
    assert (days[0].temperature_min, days[0].temperature_max) == (-6.0, 4.0)
    assert days[0].uv_index == 2.0
    assert days[0].sunrise == "07:49"
