import pytest
from app.functions import generate_new_id, seconds_to_hms, hms_to_seconds, hms_to_string, zero_pad
from datetime import datetime, timedelta
from decimal import Decimal


def test_generate_new_id():
    # Run this 100 times to ensure it always returns a 17-character string
    for i in range(100):
        test_id = generate_new_id()
        assert isinstance(test_id, str)
        assert len(test_id) == 17

    # Ensure timestamps are created in UTC
    test_id = generate_new_id()
    now = float(datetime.utcnow().timestamp())
    assert now - 1 <= float(test_id) <= now + 1


def test_zero_pad():
    assert zero_pad(0) == "00"
    assert zero_pad(00) == "00"
    assert zero_pad("0") == "00"
    assert zero_pad("00") == "00"

    assert zero_pad(-1) == "-1"
    assert zero_pad("-1") == "-1"
    assert zero_pad("-01") == "-1"

    assert zero_pad(1) == "01"
    assert zero_pad("1") == "01"
    assert zero_pad("01") == "01"

    assert zero_pad(9) == "09"
    assert zero_pad("9") == "09"
    assert zero_pad("09") == "09"

    assert zero_pad(10) == "10"
    assert zero_pad("10") == "10"
    assert zero_pad("010") == "10"

    assert zero_pad(344) == "344"
    assert zero_pad("344") == "344"
    assert zero_pad("0344") == "344"

    assert zero_pad(None) is None
    assert zero_pad(datetime) == datetime


def helper_test_seconds_to_hms(data, result):
    """Runs up to 9 asserts on seconds_to_hms() for various flavors of a numerical input."""
    assert seconds_to_hms(int(data)) == result
    assert seconds_to_hms(float(data)) == result
    assert seconds_to_hms(Decimal(data)) == result
    assert seconds_to_hms(str(data)) == result

    if data >= 0:
        # Any negative value should return zeroes
        assert seconds_to_hms(-data) == ['0', '0', '00', '00']

        # Throw some decimals in there
        if round(data, 0) == data:
            assert seconds_to_hms(data + .1) == result
            assert seconds_to_hms(data + .123456789) == result
            assert seconds_to_hms(data + .8) == result
            assert seconds_to_hms(data + .894094714) == result


def test_seconds_to_hms():
    # Type checks
    with pytest.raises(TypeError):
        seconds_to_hms(None)
        seconds_to_hms(datetime)

    with pytest.raises(ValueError):
        seconds_to_hms("-1.8")
        seconds_to_hms("doughnut")

    # Zero
    helper_test_seconds_to_hms(0, ['0', '0', '00', '00'])
    # Only seconds
    helper_test_seconds_to_hms(53, ['0', '0', '00', '53'])
    # Whole minutes
    helper_test_seconds_to_hms(1620, ['0', '0', '27', '00'])
    # Whole hours
    helper_test_seconds_to_hms(3600 * 4, ['0', '4', '00', '00'])
    # Whole days
    helper_test_seconds_to_hms(3600 * 24 * 91, ['91', '0', '00', '00'])

    # Complex inputs
    helper_test_seconds_to_hms(3612, ['0', '1', '00', '12'])
    helper_test_seconds_to_hms(49106, ['0', '13', '38', '26'])
    helper_test_seconds_to_hms(93784, ['1', '2', '03', '04'])
    helper_test_seconds_to_hms(162421, ['1', '21', '07', '01'])
    helper_test_seconds_to_hms(501728, ['5', '19', '22', '08'])
    helper_test_seconds_to_hms(4356409, ['50', '10', '06', '49'])

    # Negative numbers
    helper_test_seconds_to_hms(-1, ['0', '0', '00', '00'])
    helper_test_seconds_to_hms(-4, ['0', '0', '00', '00'])
    helper_test_seconds_to_hms(-394, ['0', '0', '00', '00'])
