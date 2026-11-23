"""ValidationError messages must not quote the data received from the API."""

from typing import Any

from pydantic import BaseModel, ValidationError
import pytest

from ecactus.model import DeviceInsight, Event, PowerTimeSeries, User

EMAIL = "john.doe@example.invalid"
PHONE = "+15550100123"
NICKNAME = "johnny-nick"
BAD_POWER = "bad-power-value"
BAD_TYPE_ID = "bad-type-id"


@pytest.mark.parametrize(
    ("model", "data", "values"),
    [
        pytest.param(
            User,
            {"username": EMAIL, "nickname": NICKNAME, "email": EMAIL, "phone": PHONE},
            [EMAIL, PHONE, NICKNAME],
            id="own-config",
        ),
        pytest.param(
            PowerTimeSeries,
            {"homePowerDps": {"1740783600": BAD_POWER}},
            [BAD_POWER],
            id="no-own-config",
        ),
        pytest.param(
            DeviceInsight,
            {
                "selfPowered": 0,
                "deviceRealtimeDto": {"homePowerDps": {"1740783600": BAD_POWER}},
                "deviceStatisticsDto": None,
                "insightConsumptionDataDto": None,
            },
            [BAD_POWER],
            id="nested-model",
        ),
        pytest.param(
            Event,
            {
                "errorCode": "unknown_code",
                "eventType": "event",
                "eventTypeInt": BAD_TYPE_ID,
                "eventContentEn": "Unknown",
                "occurrenceTime": 946684800,
            },
            [BAD_TYPE_ID],
            id="nested-model-built-in-validator",
        ),
    ],
)
def test_validation_error_hides_input(
    model: type[BaseModel], data: dict[str, Any], values: list[str]
) -> None:
    """The message names the failing fields without quoting any input value."""
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(data)
    message = str(exc_info.value)
    assert "input_value" not in message
    for value in values:
        assert value not in message
