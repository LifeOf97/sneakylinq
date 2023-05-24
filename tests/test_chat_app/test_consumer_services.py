import uuid

import pytest
from django.utils.text import slugify

from chat.services.consumer_services import ConsumerServices


class TestConsumerServices:
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
    def test_format_and_validate_alias_with_wrong_alias(
        self, test_alias, test_message, test_status
    ):
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
    def test_format_and_validate_alias_with_correct_alias(
        self, test_alias, test_message, test_status
    ):
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
    def test_format_and_verify_alias_with_wrong_alias(self, test_alias, test_message, test_status):
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
        "test_device, test_alias, test_message, test_status",
        [
            (
                "device:001",
                "testalias_001",
                "testalias_001.linq is already your device alias",
                False,
            ),
            ("device:002", "testalias_001", "Alias already taken", False),
            ("device:003", "testalias_001", "Alias already taken", False),
            (
                "device:002",
                "testalias_002",
                "testalias_002.linq is already your device alias",
                False,
            ),
        ],
    )
    def test_format_and_verify_alias_with_correct_alias_but_already_device_alias_or_alias_taken(
        self,
        test_device,
        test_alias,
        test_message,
        test_status,
        mock_redis_hget,
        mock_redis_hvals,
        mock_redis_hset,
    ):
        """
        This method first passes the alias to the format_and_validate_alias method.
        If the returned status is true we then proceed, if not, we stop.
        """
        message, alias, status = ConsumerServices.format_and_verify_alias(
            device=test_device, alias=test_alias
        )
        test_alias = slugify(str(test_alias).lower()).replace("-", "_")

        # append .linq to formated alias
        test_alias = f"{test_alias}.linq"

        assert status is test_status
        assert alias == test_alias
        assert message == test_message

    def test_set_device_data_sets_device_data_in_redis_store(
        self,
        mock_redis_hset,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
    ):
        assert (
            ConsumerServices.set_device_data(
                device="device_001",
                did=uuid.uuid4(),
                channel="channels_auto_generated_channel_name",
            )
            is None
        )

    def test_set_device_alias_saves_alias_in_redis_store(
        self, mock_redis_hset, mock_redis_expireat
    ):
        """NOTE: This method assumes the alias provided has already been validated and verified"""
        assert (
            ConsumerServices.set_device_alias(
                device="device:001",
                alias="testuser",
                device_alias="device:alias",
                alias_device="alias:device",
            )
            is None
        )

    def test_get_device_data(self, mock_luascript_get_device_data):
        data = ConsumerServices.get_device_data(device="device:005")

        assert type(data) is dict
        assert "did" in data.keys()
        assert "channel" in data.keys()
        assert "ttl" in data.keys()
        assert "alias" in data.keys()

    def test_set_alias_device(self, mock_luascript_set_alias_device):
        assert ConsumerServices.set_alias_device("device:005") == 1
