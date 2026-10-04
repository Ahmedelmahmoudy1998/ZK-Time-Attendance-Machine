"""ZK's packed clock uses twelve 31-day slots per year, not 365 days."""
from datetime import datetime
import struct


def decode_device_time(data):
    value, = struct.unpack('<I', data)
    value, second = divmod(value, 60)
    value, minute = divmod(value, 60)
    value, hour = divmod(value, 24)
    value, day = divmod(value, 31)
    year, month = divmod(value, 12)
    return datetime(2000 + year, month + 1, day + 1, hour, minute, second)


def previous_decoded_time(data):
    """Identify old importer output only when re-reading the same device record."""
    correct = decode_device_time(data)
    value, = struct.unpack('<I', data)
    old_year = value // (86400 * 365) + 2000
    try:
        return correct.replace(year=old_year)
    except ValueError:
        return None  # The previous decoder could not import this leap day.
