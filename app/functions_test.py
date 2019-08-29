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

    assert zero_pad(None) is None
    assert zero_pad("doughnut") == "doughnut"
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


def helper_test_hms_to_seconds(hms, result):
    """Runs 18+ asserts on hms_to_seconds() for various permutations of a list input."""
    hms_original = hms
    assert hms_to_seconds(hms_original) == result

    # Iterate through all 16 permutations of int & str for each value
    i = 0
    for combo in itertools.product([int, str], repeat=len(hms)):
        while i < len(hms):
            # Test each combination of input types
            hms[i] = combo[i](hms[i])
            assert hms_to_seconds(hms) == result
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
                if hms[i] in (0, '0', '00') and combo[i]:
                    hms[i] = None
                assert hms_to_seconds(hms) == result
                i += 1

            # Reset the input & index counter
            hms = hms_original
            i = 0

    # (-1 * each value) should return (-1 * value)
    i = 0
    while i < len(hms):
        hms[i] = f"-{hms[i]}"

    assert hms_to_seconds(hms) == -1 * result


def test_hms_to_seconds():
    helper_test_hms_to_seconds([0, 0, 0, 0], 0)
    helper_test_hms_to_seconds([0, 0, 0, 9], 9)
    helper_test_hms_to_seconds([0, 0, 0, 73], 73)
    helper_test_hms_to_seconds([0, 0, 0, 43767], 43767)
    helper_test_hms_to_seconds([0, 0, 1, 0], 60)
    helper_test_hms_to_seconds([0, 0, 2, 0], 120)
    helper_test_hms_to_seconds([0, 0, 2, 31], 151)
    helper_test_hms_to_seconds([0, 0, 82, 50], 4970)
    helper_test_hms_to_seconds([0, 0, 9006, 18], (9006 * 60) + 18)
    helper_test_hms_to_seconds([0, 1, 00, 0], 3600)
    helper_test_hms_to_seconds([0, 5, 56, 14], (3600 * 5) + (60 * 56) + 14)
    helper_test_hms_to_seconds([0, 10, 0, 25], 3600 * 10 + 25)
    helper_test_hms_to_seconds([0, 184, 35, 447], (3600 * 184) + (35 * 60) + 447)
    helper_test_hms_to_seconds([1, 0, 0, 0], 86400)
    helper_test_hms_to_seconds([6, 9, 14, 21], (86400 * 6) + (3600 * 9) + (60 * 14) + 21)
    helper_test_hms_to_seconds([37, 8405, 93, 61521], (86400 * 37) + (3600 * 8405) + (60 * 93) + 61521)

    # Mix in some negatives
    helper_test_hms_to_seconds([0, 1, 0, -22], 3600 + -22)
    helper_test_hms_to_seconds([0, 1, -8, 0], 3600 + (60 * -8))
    helper_test_hms_to_seconds([0, -3, 2, 31], (-3600 * 3) + 151)
    helper_test_hms_to_seconds([-2, 5, 56, 14], (86400 * -2) + (3600 * 5) + (60 * 56) + 14)
    helper_test_hms_to_seconds([2, 5, -14, -56], (86400 * 2) + (3600 * 5) + (60 * -14) + -56)
    helper_test_hms_to_seconds([-6, -9, -14, 21], (86400 * -6) + (3600 * -9) + (60 * -14) + 21)
    helper_test_hms_to_seconds([-6, -9, 14, -21], (86400 * -6) + (3600 * -9) + (60 * 14) + -21)
    helper_test_hms_to_seconds([-6, 9, -14, -21], (86400 * -6) + (3600 * 9) + (60 * 14) + -21)
    helper_test_hms_to_seconds([6, -9, -14, -21], (86400 * 6) + (3600 * -9) + (60 * -14) + -21)
    helper_test_hms_to_seconds([37, -8405, 93, 61521], (86400 * 37) + (3600 * -8405) + (60 * 93) + 61521)

    # Type checks
    with pytest.raises(TypeError, ValueError):
        hms_to_seconds("doughnut")
        hms_to_seconds(["doughnut"])
        hms_to_seconds([str, 2, 3, 4])
        hms_to_seconds([1, datetime, 3, 4])
        hms_to_seconds([1, 2, "doughnut", 4])
        hms_to_seconds([1, 2, 3, [0]])
        hms_to_seconds(73)
        hms_to_seconds(datetime)

    with pytest.raises(IndexError):
        hms_to_seconds([1])
        hms_to_seconds([1, 2])
        hms_to_seconds([1, 2, 3])
        hms_to_seconds([1, 2, 3, 4, 5])


def test_hms_to_string():
    # Type checks
    with pytest.raises(TypeError, ValueError):
        hms_to_string("doughnut")
        hms_to_string(["doughnut"])
        hms_to_string([str, 2, 3, 4])
        hms_to_string([1, datetime, 3, 4])
        hms_to_string([1, 2, "doughnut", 4])
        hms_to_string([1, 2, 3, [0]])
        hms_to_string(73)
        hms_to_string(datetime)

    with pytest.raises(IndexError):
        hms_to_string([1])
        hms_to_string([1, 2])
        hms_to_string([1, 2, 3])
        hms_to_string([1, 2, 3, 4, 5])
