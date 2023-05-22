import uuid

import pytest
from django.utils import timezone
from django.utils.text import slugify

from chat.services.consumer_services import ConsumerServices


def test_set_device_data(mock_redis_hset, mock_redis_expireat, mock_luascript_set_alias_device):
    assert (
        ConsumerServices.set_device_data(
            device="device_001", did=uuid.uuid4(), channel="channels_auto_generated_channel_name"
        )
        is None
    )


def test_set_alias_device(mock_luascript_set_alias_device):
    assert ConsumerServices.set_alias_device("device_001") == 1


@pytest.mark.parametrize(
    "test_alias, test_message, test_status",
    [
        ("1942", "Alias must be a mix of alphanumeric characters", False),
        ("Ade", "Alias must be between 4 to 15 characters long", False),
        ("Device_Alias_cannot", "Alias must be between 4 to 15 characters long", False),
        ("sneaky", "sneaky is not allowed", False),
        ("linq", "linq is not allowed", False),
    ],
)
def test_format_and_validate_alias_with_wrong_alias(test_alias, test_message, test_status):
    """
    Alias which do not meet the specified requirements should return
    status of False, reason why alias failed to pass and the formated alias
    """
    message, alias, status = ConsumerServices.format_and_validate_alias(test_alias)
    test_alias = slugify(str(test_alias).lower()).replace("-", "_")

    assert alias == test_alias
    assert message == test_message
    assert status == test_status


@pytest.mark.parametrize(
    "test_alias, test_message, test_status",
    [
        ("sharon1942", "Alias formated successfully", True),
        ("Mayo", "Alias formated successfully", True),
        ("Kool.Kat", "Alias formated successfully", True),
    ],
)
def test_format_and_validate_alias_with_correct_alias(test_alias, test_message, test_status):
    """
    Alias which meet the specified requirements should return
    status of True, the reason and the formated alias.
    """
    message, alias, status = ConsumerServices.format_and_validate_alias(test_alias)
    test_alias = slugify(str(test_alias).lower()).replace("-", "_")

    assert alias == test_alias
    assert message == test_message
    assert status == test_status


@pytest.mark.parametrize(
    "test_alias, test_message, test_status",
    [
        ("1942", "Alias must be a mix of alphanumeric characters", False),
        ("Ade", "Alias must be between 4 to 15 characters long", False),
        ("Device_Alias_cannot", "Alias must be between 4 to 15 characters long", False),
        ("sneaky", "sneaky is not allowed", False),
        ("linq", "linq is not allowed", False),
    ],
)
def test_format_and_verify_alias_with_wrong_alias(test_alias, test_message, test_status):
    """
    This method first passes the alias to the format_and_validate_alias
    if the returned status is true we then proceed, if not we return the
    reason, alias and status
    """
    message, alias, status = ConsumerServices.format_and_verify_alias(
        device="device:123", alias=test_alias
    )

    test_alias = slugify(str(test_alias).lower()).replace("-", "_")

    assert alias == test_alias
    assert message == test_message
    assert status == test_status


@pytest.mark.parametrize(
    "test_alias, test_message, test_status",
    [
        ("1942", "Alias must be a mix of alphanumeric characters", False),
        ("Ade", "Alias must be between 4 to 15 characters long", False),
        ("Device_Alias_cannot", "Alias must be between 4 to 15 characters long", False),
        ("sneaky", "sneaky is not allowed", False),
        ("linq", "linq is not allowed", False),
    ],
)
def test_format_and_verify_alias_with_wrong_alias(test_alias, test_message, test_status):
    """
    This method first passes the alias to the format_and_validate_alias
    if the returned status is true we then proceed, if not we return the
    reason, alias and status
    """
    message, alias, status = ConsumerServices.format_and_verify_alias(
        device="device:123", alias=test_alias
    )
    test_alias = slugify(str(test_alias).lower()).replace("-", "_")

    assert alias == test_alias
    assert message == test_message
    assert status == test_status


# @pytest.mark.parametrize(
#     "test_alias, test_message, test_status",
#     [
#         ("sharon1942", "Alias formated successfully", True),
#         ("Mayo", "Alias formated successfully", True),
#         ("Kool.Kat", "Alias formated successfully", True),
#     ],
# )
# def test_format_and_verify_alias_with_correct_alias_but_is_already_device_alias(
#     mock_redis_hset
#     test_alias,
#     test_message,
#     test_status,
# ):
#     """
#     This method first passes the alias to the format_and_validate_alias
#     if the returned status is true we then proceed, if not we return the
#     reason, alias and status
#     """
#     device: str = "device:123"

#     message, alias, status = ConsumerServices.format_and_verify_alias(
#         device=device, alias=test_alias
#     )
#     test_alias = slugify(str(test_alias).lower()).replace("-", "_")

#     # append .linq to formated alias
#     test_alias = f"{test_alias}.linq"

#     # add device alias to device_alias first
#     mock_redis_hset(name="device_alias", mapping={device: test_alias})

#     assert alias == test_alias
#     assert message == test_message
#     assert status == test_status
