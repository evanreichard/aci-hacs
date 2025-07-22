import pytest

from .models import DeviceMode, DeviceNotSupported, RampStatus
from .protocol import Protocol

p = Protocol()


class TestParseCharacteristicData:
    def test_parse_characteristic_data_valid(self):
        # Test data from your example
        data = bytes([0x1E, 0xFF, 0x02, 0x09, 0x03, 0x0C, 0x00, 0x00,
                      0x07, 0xE4, 0x00, 0x00, 0x00, 0x00, 0x27, 0x10, 0x00, 0x32])

        result = p.parse_status(data)

        assert result.temperature == 20.20
        assert result.fan_speed == 3
        assert result.ramp_status == RampStatus.NONE  # byte 7 = 0x00
        assert result.mode == DeviceMode.ON    # 0x32 & 0x0F = 2

    def test_nibble_parsing(self):
        base_data = bytearray([0] * 18)

        # Test packed byte 17: fan_speed=5, device_mode=3
        base_data[17] = 0x53  # 5 << 4 | 3
        result = p.parse_status(bytes(base_data))
        assert result.fan_speed == 5
        assert result.mode == DeviceMode.AUTO_TEMP

    def test_all_device_modes(self):
        base_data = bytearray([0] * 18)

        for mode in DeviceMode:
            base_data[17] = 0x70 | mode.value  # fan_speed=7, device_mode=mode
            result = p.parse_status(bytes(base_data))
            assert result.mode == mode

    def test_fan_speed_range(self):
        base_data = bytearray([0] * 18)

        for speed in range(11):  # 0-10 (0-A)
            # fan_speed=speed, device_mode=OFF
            base_data[17] = (speed << 4) | 1
            result = p.parse_status(bytes(base_data))
            assert result.fan_speed == speed

    def test_ramp_statuses(self):
        base_data = bytearray([0] * 18)

        test_cases = [
            (8, RampStatus.UP),
            (4, RampStatus.DOWN),
            (0, RampStatus.NONE)
        ]

        for value, expected in test_cases:
            base_data[7] = value
            result = p.parse_status(bytes(base_data))
            assert result.ramp_status == expected

    def test_invalid_data_length(self):
        with pytest.raises(ValueError, match="Invalid characteristic data length"):
            p.parse_status(b"short")

    def test_invalid_enum_values(self):
        base_data = bytearray([0] * 18)

        # Invalid ramp status
        base_data[7] = 99
        result = p.parse_status(bytes(base_data))
        assert result.ramp_status == RampStatus.NONE

        # Invalid device mode (lower nibble = 9)
        base_data[17] = 0x19
        result = p.parse_status(bytes(base_data))
        assert result.mode == DeviceMode.OFF


class TestParseAdvertisementData:

    def test_valid_airtap_data(self):
        # Sample data from your comment
        data = bytes([
            0xA4, 0xC1, 0x38, 0x5F, 0x42, 0x9B, 0x53, 0x34, 0x30, 0x42, 0x4D,
            0x03, 0x06, 0x00, 0x05, 0xCD, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00
        ])

        result = p.parse_advertisement(data)

        assert result.id == 'D-S40BM'
        assert result.name == 'AirTap (D-S40BM)'
        assert result.temperature == 14.85  # 05CD = 1485 / 100
        assert result.fan_speed == 4  # 0x04 & 0x0F = 4

    def test_invalid_data_length_short(self):
        data = bytes([0x00] * 26)  # 26 bytes instead of 27

        with pytest.raises(ValueError, match="Invalid advertisement data length: 26"):
            p.parse_advertisement(data)

    def test_invalid_data_length_long(self):
        data = bytes([0x00] * 28)  # 28 bytes instead of 27

        with pytest.raises(ValueError, match="Invalid advertisement data length: 28"):
            p.parse_advertisement(data)

    def test_unsupported_device_type(self):
        data = bytes([0x00] * 27)
        data = bytearray(data)
        data[12] = 99  # Invalid device type

        with pytest.raises(DeviceNotSupported, match="99"):
            p.parse_advertisement(bytes(data))

    def test_different_temperature_values(self):
        data = bytearray([0x00] * 27)
        data[12] = 6  # AIRTAP
        data[6:11] = b'TEST1'
        data[14:16] = (2000).to_bytes(2, 'big')  # 20.00°C

        result = p.parse_advertisement(bytes(data))
        assert result.temperature == 20.0

    def test_different_fan_speeds(self):
        data = bytearray([0x00] * 27)
        data[12] = 6  # AIRTAP
        data[6:11] = b'TEST2'
        data[18] = 0x0A  # Fan speed 10

        result = p.parse_advertisement(bytes(data))
        assert result.fan_speed == 10

    def test_max_fan_speed(self):
        data = bytearray([0x00] * 27)
        data[12] = 6  # AIRTAP
        data[6:11] = b'TEST3'
        data[18] = 0xFF  # Upper nibble ignored, lower = 15

        result = p.parse_advertisement(bytes(data))
        assert result.fan_speed == 15
