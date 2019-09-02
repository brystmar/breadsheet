import pytest
import itertools
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

    with pytest.raises(TypeError):
        zero_pad(None)

    with pytest.raises(TypeError):
        zero_pad("doughnut")

    with pytest.raises(TypeError):
        zero_pad(datetime)


def test_seconds_to_hms():
    # Single inputs
    helper_test_seconds_to_hms(0, ['0', '0', '00', '00'])
    helper_test_seconds_to_hms(53, ['0', '0', '00', '53'])
    helper_test_seconds_to_hms(1620, ['0', '0', '27', '00'])
    helper_test_seconds_to_hms(3600 * 4, ['0', '4', '00', '00'])
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
    helper_test_seconds_to_hms(-53, ['0', '0', '00', '00'])
    helper_test_seconds_to_hms(-394, ['0', '0', '00', '00'])

    assert seconds_to_hms(-6) == ['0', '0', '00', '00']
    assert seconds_to_hms(-6.31) == ['0', '0', '00', '00']

    # Type checks
    with pytest.raises(TypeError):
        seconds_to_hms(None)

    with pytest.raises(TypeError):
        seconds_to_hms(datetime)

    with pytest.raises(TypeError):
        seconds_to_hms("doughnut")

    with pytest.raises(TypeError):
        seconds_to_hms("-6.3")


def test_hms_to_seconds():
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 0, 0], 0)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 0, 9], 9)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 0, 73], 73)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 0, 43767], 43767)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 1, 0], 60)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 2, 0], 120)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 2, 31], 151)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 82, 50], 4970)
    helper_test_hms_to_x(hms_to_seconds, [0, 0, 9006, 18], (9006 * 60) + 18)
    helper_test_hms_to_x(hms_to_seconds, [0, 1, 00, 0], 3600)
    helper_test_hms_to_x(hms_to_seconds, [0, 5, 56, 14], (3600 * 5) + (60 * 56) + 14)
    helper_test_hms_to_x(hms_to_seconds, [0, 10, 0, 25], 3600 * 10 + 25)
    helper_test_hms_to_x(hms_to_seconds, [0, 184, 35, 447], (3600 * 184) + (35 * 60) + 447)
    helper_test_hms_to_x(hms_to_seconds, [1, 0, 0, 0], 86400)
    helper_test_hms_to_x(hms_to_seconds, [6, 9, 14, 21], (86400 * 6) + (3600 * 9) + (60 * 14) + 21)
    helper_test_hms_to_x(hms_to_seconds, [37, 8405, 93, 61521], (86400 * 37) + (3600 * 8405) + (60 * 93) + 61521)

    # Mix in some negatives
    helper_test_hms_to_x(hms_to_seconds, [0, 1, 0, -22], 3600 + -22)
    helper_test_hms_to_x(hms_to_seconds, [0, 1, -8, 0], 3600 + (60 * -8))
    helper_test_hms_to_x(hms_to_seconds, [0, -3, 2, 31], (-3600 * 3) + 151)
    helper_test_hms_to_x(hms_to_seconds, [-2, 5, 56, 14], (86400 * -2) + (3600 * 5) + (60 * 56) + 14)
    helper_test_hms_to_x(hms_to_seconds, [2, 5, -14, -56], (86400 * 2) + (3600 * 5) + (60 * -14) + -56)
    helper_test_hms_to_x(hms_to_seconds, [-6, -9, -14, 21], (86400 * -6) + (3600 * -9) + (60 * -14) + 21)
    helper_test_hms_to_x(hms_to_seconds, [-6, -9, 14, -21], (86400 * -6) + (3600 * -9) + (60 * 14) + -21)
    helper_test_hms_to_x(hms_to_seconds, [-6, 9, -14, -21], (86400 * -6) + (3600 * 9) + (60 * -14) + -21)
    helper_test_hms_to_x(hms_to_seconds, [6, -9, -14, -21], (86400 * 6) + (3600 * -9) + (60 * -14) + -21)
    helper_test_hms_to_x(hms_to_seconds, [37, -8405, 93, 61521], (86400 * 37) + (3600 * -8405) + (60 * 93) + 61521)

    # Type checks
    with pytest.raises(TypeError):
        hms_to_seconds("doughnut")

    with pytest.raises(TypeError):
        hms_to_seconds([str, 2, 3, 4])

    with pytest.raises(TypeError):
        hms_to_seconds([1, datetime, 3, 4])

    with pytest.raises(TypeError):
        hms_to_seconds([1, 2, "doughnut", 4])

    with pytest.raises(TypeError):
        hms_to_seconds([1, 2, 3, [0]])

    with pytest.raises(TypeError):
        hms_to_seconds(73)

    with pytest.raises(TypeError):
        hms_to_seconds(datetime)

    with pytest.raises(TypeError):
        hms_to_seconds(datetime.utcnow())

    with pytest.raises(IndexError):
        hms_to_seconds(["doughnut"])

    with pytest.raises(IndexError):
        hms_to_seconds([1])

    with pytest.raises(IndexError):
        hms_to_seconds([1, 2])

    with pytest.raises(IndexError):
        hms_to_seconds([1, 2, 3])

    with pytest.raises(IndexError):
        hms_to_seconds([1, 2, 3, 4, 5])


class TestHMSToString:
    """Tests for the hms_to_string() function."""
    def test_hms_to_string_lists(self):
        helper_test_hms_to_x(hms_to_string, [0, 0, 0, 0], "")
        helper_test_hms_to_x(hms_to_string, [0, 0, 0, 4], "")
        helper_test_hms_to_x(hms_to_string, [0, 0, 0, 59], "")
        helper_test_hms_to_x(hms_to_string, [0, 0, 0, 101], "1 min")
        helper_test_hms_to_x(hms_to_string, [0, 0, 1, 0], "1 min")
        helper_test_hms_to_x(hms_to_string, [0, 0, 1, 59], "1 min")
        helper_test_hms_to_x(hms_to_string, [0, 0, 1, 77], "2 min")
        helper_test_hms_to_x(hms_to_string, [0, 1, 0, 0], "1 hr")
        helper_test_hms_to_x(hms_to_string, [0, 1, 8, 17], "1 hr, 8 min")
        helper_test_hms_to_x(hms_to_string, [0, 3, 38, 17], "3 hrs, 38 min")
        helper_test_hms_to_x(hms_to_string, [0, 3, 65, 17], "4 hrs, 5 min")
        helper_test_hms_to_x(hms_to_string, [0, 3, 65, 93], "4 hrs, 6 min")
        helper_test_hms_to_x(hms_to_string, [0, 19, 0, 42], "19 hrs")
        helper_test_hms_to_x(hms_to_string, [1, 0, 0, 49], "1 day")
        helper_test_hms_to_x(hms_to_string, [2, 0, 1, 49], "2 days, 1 min")
        helper_test_hms_to_x(hms_to_string, [2, 1, 0, 0], "2 days, 1 hr")
        helper_test_hms_to_x(hms_to_string, [270, 5, 0, 0], "270 days, 5 hrs")
        helper_test_hms_to_x(hms_to_string, [270, 5, 34, 55], "270 days, 5 hrs, 34 min")
        helper_test_hms_to_x(hms_to_string, [16, 16, 44, 8], "16 days, 16 hrs, 44 min")

        # TypeErrors
        with pytest.raises(TypeError):
            hms_to_string({1, 2, 3, 4})

        with pytest.raises(TypeError):
            hms_to_string([1, 2, "doughnut", 4])

        with pytest.raises(TypeError):
            hms_to_string([1, 2, 3, [0]])

        with pytest.raises(TypeError):
            hms_to_string([str, 2, 3, 4])

        with pytest.raises(TypeError):
            hms_to_string([datetime, 2, 3, 4])

        with pytest.raises(TypeError):
            hms_to_string([1, datetime, 3, 4])

        with pytest.raises(TypeError):
            hms_to_string([1, 2, datetime, 4])

        with pytest.raises(TypeError):
            hms_to_string([1, 2, 3, datetime])

        # IndexErrors
        with pytest.raises(IndexError):
            hms_to_string([])

        with pytest.raises(IndexError):
            hms_to_string([1])

        with pytest.raises(IndexError):
            hms_to_string([1, 2])

        with pytest.raises(IndexError):
            hms_to_string([1, 2, 3])

        with pytest.raises(IndexError):
            hms_to_string([1, 2, 3, 4, 5])

        with pytest.raises(IndexError):
            hms_to_string(["doughnut"])

    def test_hms_to_string_strings(self):
        assert hms_to_string("1:2:3") == "1 hr, 2 min"
        assert hms_to_string("1:02:3") == "1 hr, 2 min"
        assert hms_to_string("1:2:03") == "1 hr, 2 min"
        assert hms_to_string("1:02:03") == "1 hr, 2 min"
        assert hms_to_string("01:2:3") == "1 hr, 2 min"
        assert hms_to_string("01:02:3") == "1 hr, 2 min"
        assert hms_to_string("01:2:03") == "1 hr, 2 min"
        assert hms_to_string("01:02:03") == "1 hr, 2 min"

        assert hms_to_string("21:2:3") == "21 hrs, 2 min"
        assert hms_to_string("21:02:3") == "21 hrs, 2 min"
        assert hms_to_string("21:2:03") == "21 hrs, 2 min"
        assert hms_to_string("21:02:03") == "21 hrs, 2 min"

        assert hms_to_string("0 day 1:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 day 1:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 day 1:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 day 1:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 day 01:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 day 01:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 day 01:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 day 01:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 day 21:2:3") == "21 hrs, 2 min"
        assert hms_to_string("0 day 21:02:3") == "21 hrs, 2 min"
        assert hms_to_string("0 day 21:2:03") == "21 hrs, 2 min"
        assert hms_to_string("0 day 21:02:03") == "21 hrs, 2 min"

        assert hms_to_string("0 day, 1:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 day, 1:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 day, 1:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 day, 1:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 day, 01:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 day, 01:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 day, 01:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 day, 01:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 day, 21:2:3") == "21 hrs, 2 min"
        assert hms_to_string("0 day, 21:02:3") == "21 hrs, 2 min"
        assert hms_to_string("0 day, 21:2:03") == "21 hrs, 2 min"
        assert hms_to_string("0 day, 21:02:03") == "21 hrs, 2 min"

        assert hms_to_string("0 days 1:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 days 1:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 days 1:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 days 1:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 days 01:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 days 01:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 days 01:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 days 01:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 days 21:2:3") == "21 hrs, 2 min"
        assert hms_to_string("0 days 21:02:3") == "21 hrs, 2 min"
        assert hms_to_string("0 days 21:2:03") == "21 hrs, 2 min"
        assert hms_to_string("0 days 21:02:03") == "21 hrs, 2 min"

        assert hms_to_string("0 days, 1:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 days, 1:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 days, 1:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 days, 1:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 days, 01:2:3") == "1 hr, 2 min"
        assert hms_to_string("0 days, 01:02:3") == "1 hr, 2 min"
        assert hms_to_string("0 days, 01:2:03") == "1 hr, 2 min"
        assert hms_to_string("0 days, 01:02:03") == "1 hr, 2 min"
        assert hms_to_string("0 days, 21:2:3") == "21 hrs, 2 min"
        assert hms_to_string("0 days, 21:02:3") == "21 hrs, 2 min"
        assert hms_to_string("0 days, 21:2:03") == "21 hrs, 2 min"
        assert hms_to_string("0 days, 21:02:03") == "21 hrs, 2 min"

        assert hms_to_string("1 day 1:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 1:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 1:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 1:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 01:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 01:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 01:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 01:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day 21:2:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day 21:02:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day 21:2:03") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day 21:02:03") == "1 day, 21 hrs, 2 min"

        assert hms_to_string("1 day, 1:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 1:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 1:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 1:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 01:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 01:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 01:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 01:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 day, 21:2:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day, 21:02:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day, 21:2:03") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 day, 21:02:03") == "1 day, 21 hrs, 2 min"

        assert hms_to_string("1 days 1:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 1:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 1:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 1:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 01:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 01:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 01:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 01:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days 21:2:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days 21:02:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days 21:2:03") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days 21:02:03") == "1 day, 21 hrs, 2 min"

        assert hms_to_string("1 days, 1:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 1:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 1:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 1:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 01:2:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 01:02:3") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 01:2:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 01:02:03") == "1 day, 1 hr, 2 min"
        assert hms_to_string("1 days, 21:2:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days, 21:02:3") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days, 21:2:03") == "1 day, 21 hrs, 2 min"
        assert hms_to_string("1 days, 21:02:03") == "1 day, 21 hrs, 2 min"

        assert hms_to_string("76 day 1:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 1:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 1:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 1:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 01:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 01:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 01:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 01:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day 21:2:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day 21:02:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day 21:2:03") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day 21:02:03") == "76 days, 21 hrs, 2 min"

        assert hms_to_string("76 day, 1:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 1:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 1:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 1:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 01:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 01:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 01:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 01:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 day, 21:2:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day, 21:02:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day, 21:2:03") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 day, 21:02:03") == "76 days, 21 hrs, 2 min"

        assert hms_to_string("76 days 1:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 1:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 1:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 1:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 01:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 01:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 01:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 01:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days 21:2:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days 21:02:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days 21:2:03") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days 21:02:03") == "76 days, 21 hrs, 2 min"

        assert hms_to_string("76 days, 1:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 1:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 1:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 1:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 01:2:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 01:02:3") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 01:2:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 01:02:03") == "76 days, 1 hr, 2 min"
        assert hms_to_string("76 days, 21:2:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days, 21:02:3") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days, 21:2:03") == "76 days, 21 hrs, 2 min"
        assert hms_to_string("76 days, 21:02:03") == "76 days, 21 hrs, 2 min"

        with pytest.raises(ValueError):
            hms_to_string("1 day 24:3:4")

        with pytest.raises(ValueError):
            hms_to_string("1 day, 1:60:3")

        with pytest.raises(ValueError):
            hms_to_string("1 day, 1:0:63")

        with pytest.raises(ValueError):
            hms_to_string("1 day, 1:00:63")

        with pytest.raises(ValueError):
            hms_to_string("1 week 2:3:4")

        with pytest.raises(ValueError):
            hms_to_string("")

        with pytest.raises(ValueError):
            hms_to_string(" ")

        with pytest.raises(ValueError):
            hms_to_string("\n")

        with pytest.raises(ValueError):
            hms_to_string("tacos")

        with pytest.raises(ValueError):
            hms_to_string("15")

        with pytest.raises(ValueError):
            hms_to_string("15.8947")

        with pytest.raises(ValueError):
            hms_to_string("-15")

        with pytest.raises(ValueError):
            hms_to_string("-15.8947")

    def test_hms_to_string_timedelta(self):
        assert hms_to_string(timedelta()) == ""
        assert hms_to_string(timedelta(seconds=0)) == ""
        assert hms_to_string(timedelta(seconds=-0)) == ""
        assert hms_to_string(timedelta(seconds=46)) == ""
        assert hms_to_string(timedelta(seconds=468)) == "7 min"
        assert hms_to_string(timedelta(minutes=7)) == "7 min"
        assert hms_to_string(timedelta(minutes=7, seconds=48)) == "7 min"
        assert hms_to_string(timedelta(minutes=7, seconds=-48)) == "6 min"
        assert hms_to_string(timedelta(hours=1, minutes=8)) == "1 hr, 8 min"
        assert hms_to_string(timedelta(hours=4, minutes=8)) == "4 hrs, 8 min"
        assert hms_to_string(timedelta(hours=4, minutes=8, seconds=59)) == "4 hrs, 8 min"
        assert hms_to_string(timedelta(days=5, hours=16, minutes=8, seconds=59)) == "5 days, 16 hrs, 8 min"
        assert hms_to_string(timedelta(hours=13, minutes=58)) == "13 hrs, 58 min"
        assert hms_to_string(timedelta(hours=137, minutes=58)) == "5 days, 17 hrs, 58 min"
        assert hms_to_string(timedelta(days=1, hours=7)) == "1 day, 7 hrs"
        assert hms_to_string(timedelta(days=2, hours=7)) == "2 days, 7 hrs"
        assert hms_to_string(timedelta(days=1, minutes=7)) == "1 day, 7 min"
        assert hms_to_string(timedelta(days=2, minutes=7)) == "2 days, 7 min"
        assert hms_to_string(timedelta(days=1, seconds=7)) == "1 day"
        assert hms_to_string(timedelta(days=2, seconds=7)) == "2 days"
        assert hms_to_string(timedelta(days=42, seconds=7)) == "42 days"
        assert hms_to_string(timedelta(days=42, seconds=-7)) == "41 days, 23 hrs, 59 min"

        with pytest.raises(ValueError):
            hms_to_string(timedelta(seconds=-3))

        with pytest.raises(ValueError):
            hms_to_string(timedelta(minutes=-2, seconds=77))

    def test_hms_to_string_type_checks(self):
        with pytest.raises(TypeError):
            hms_to_string(15)

        with pytest.raises(TypeError):
            hms_to_string(-15)

        with pytest.raises(TypeError):
            hms_to_string(73)

        with pytest.raises(TypeError):
            hms_to_string(-73)

        with pytest.raises(TypeError):
            hms_to_string(2.145)

        with pytest.raises(TypeError):
            hms_to_string(-2.145)

        with pytest.raises(TypeError):
            hms_to_string({})

        with pytest.raises(TypeError):
            hms_to_string(datetime)

        with pytest.raises(TypeError):
            hms_to_string(datetime.utcnow())

        with pytest.raises(TypeError):
            hms_to_string(timedelta)


def helper_test_seconds_to_hms(data, result):
    """Runs up to 9 asserts on seconds_to_hms() for various flavors of a numerical input."""
    assert seconds_to_hms(int(data)) == result
    assert seconds_to_hms(float(data)) == result
    assert seconds_to_hms(Decimal(data)) == result
    assert seconds_to_hms(str(data)) == result

    # Negative decimals throw an error (tested in the main function)
    if data >= 0:
        # Any negative integer should return zeroes
        assert seconds_to_hms(-data) == ['0', '0', '00', '00']

        # Throw some decimals in there
        if round(data, 0) == data:
            assert seconds_to_hms(data + .1) == result
            assert seconds_to_hms(data + .123456789) == result
            assert seconds_to_hms(data + .8) == result
            assert seconds_to_hms(data + .894094714) == result


def helper_test_hms_to_x(fn, hms, result, use_negatives=True):
    """Runs asserts on a given function for various permutations of hms, a 4-length list input."""
    hms_original = hms
    assert fn(hms_original) == result

    # Only applies to hms_to_seconds tests where all inputs are > 0
    if fn != hms_to_seconds:
        use_negatives = False
    else:
        # Determine if any of the inputs are < 0
        for h in hms:
            if int(h) < 0:
                use_negatives = False

    # Iterate through all 16 permutations of casting int & str for each value
    i = 0
    for combo in itertools.product([int, str], repeat=len(hms)):
        while i < len(hms):
            # Test each combination of input types
            hms[i] = combo[i](hms[i])
            assert fn(hms) == result
            i += 1

        # Reset the input & index counter
        hms = hms_original
        i = 0

    # Replace values of zero with None using the same permutations
    i = 0
    if 0 in hms or '0' in hms or '00' in hms:
        for combo in itertools.product([True, False], repeat=len(hms)):
            while i < len(hms):
                # When the value is zero and combo is True, replace that zero with None
                if combo[i] and hms[i] and int(hms[i]) == 0:
                    hms[i] = None
                assert fn(hms) == result
                i += 1

            # Reset the input & index counter
            hms = hms_original
            i = 0

    # Test with negatives?
    if use_negatives:
        # (-1 * each value) should return (-1 * value)
        i = 0
        while i < len(hms):
            # Skip if the value is None
            if hms[i]:
                # Don't add another negative sign if it's already < 0
                if int(hms[i]) >= 0:
                    hms[i] = f"-{hms[i]}"
            i += 1
        assert fn(hms) == -1 * result
