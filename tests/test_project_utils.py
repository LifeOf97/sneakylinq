import uuid

import pytest

from src.utils import convert_array_to_dict, is_valid_uuid


@pytest.mark.parametrize(
    "test_uuid, expected",
    [
        (uuid.uuid1(), True),
        (uuid.uuid3(uuid.NAMESPACE_URL, "http://localhost"), True),
        (uuid.uuid4(), True),
        (uuid.uuid5(uuid.NAMESPACE_URL, "http://127.0.0.1"), True),
    ],
)
def test_is_valid_uuid_is_true_with_true_uuids(test_uuid, expected):
    assert is_valid_uuid(test_uuid) == expected


@pytest.mark.parametrize(
    "test_uuid, expected",
    [
        ("this-is-not-a-valid-uuid", False),
        ("4369ac28-f588-33cb-865a-056dfde1013", False),
        ("4369ac28-f588-33cb-865a", False),
        ("865a-056dfde1013e", False),
    ],
)
def test_is_valid_uuid_is_false_with_false_uuids(test_uuid, expected):
    assert is_valid_uuid(test_uuid) == False


@pytest.mark.parametrize(
    "data",
    [
        {"one", "two", "three", "four"},
        {1: "one", 2: "two", 3: "three"},
    ],
)
def test_convert_array_to_dict_raises_typeerror_if_type_not_list_or_tuple(data):
    with pytest.raises(TypeError):
        _ = convert_array_to_dict(data)


@pytest.mark.parametrize(
    "data",
    [
        [1, "one", 2, "two", 3],
        ("values", "in", "the", "array", "should", "be", "even"),
    ],
)
def test_convert_array_to_dict_raises_indexerror_if_elements_in_array_is_not_even(data):
    with pytest.raises(IndexError):
        _ = convert_array_to_dict(data)


@pytest.mark.parametrize(
    "array, expected",
    [
        [
            ("values", "in", "this", "array", "are", "even"),
            {"values": "in", "this": "array", "are": "even"},
        ],
        [
            [1, "one", 2, "two", 3, "three"],
            {1: "one", 2: "two", 3: "three"},
        ],
    ],
)
def test_convert_array_to_dict_should_do_what_it_says(array, expected):
    assert convert_array_to_dict(array) == expected
