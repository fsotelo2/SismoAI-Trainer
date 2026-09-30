"""Binary layout constants for DATASET BIN v2 (ESP32, little-endian).

All multi-byte integers and floats are read explicitly as little-endian;
host struct alignment is never relied upon. See
Reference/Especificacion_Dataset.md sections 3-8.
"""

CONTAINER_SIZE = 24
CONTAINER_MAGIC = b"C11C"
CONTAINER_VERSIONS = (1, 2)

METADATA_SIZE = 52
METADATA_MAGIC = b"META"
METADATA_VERSION = 1
# Bit 0x04 in META.indicadores selects the new 76-byte scientific record.
LAYOUT_NUEVO_BIT = 0x04

EVENT_HEADER_SIZE = 44
EVENT_MAGIC = b"EVT1"
EVENT_VERSION = 1

CRC_SIZE = 8
CRC_MAGIC = b"CRC1"

COMMIT_SIZE = 20
COMMIT_MAGIC = b"CMT1"

RECORD_SIZE = 76
SENSOR_MPU = 1
SENSOR_GEOFONO = 2
