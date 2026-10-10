"""Bounded .ndu wrapper; CRC is integrity checking, not authentication."""
from dataclasses import dataclass
import struct
import zlib
from hardware import boot_image

HEADER_SIZE = 128
MAX_IMAGE_SIZE = boot_image.MAX_SIZE
BOOT_API = 1
SETTINGS_ABI = 1


@dataclass(frozen=True)
class UpdatePackage:
    image: bytes
    image_crc: int
    minimum_boot_api: int
    settings_abi: int


def validate_header(header: bytes, *, boot_api: int = BOOT_API,
                    settings_abi: int = SETTINGS_ABI) -> tuple[int, int]:
    if len(header) != HEADER_SIZE:
        raise ValueError('Invalid update header length')
    magic, version, board, size, crc, minimum, abi = struct.unpack_from('<8s6I', header)
    if (magic, version, board) != (b'ND15UPD1', 1, 0x54583135):
        raise ValueError('Invalid update format or board')
    if not 1 <= minimum <= boot_api or not abi or abi != settings_abi:
        raise ValueError('Incompatible boot API or settings ABI')
    if not 64 <= size <= MAX_IMAGE_SIZE or any(header[32:124]):
        raise ValueError('Invalid update size or reserved fields')
    if zlib.crc32(header[:124]) != struct.unpack_from('<I', header, 124)[0]:
        raise ValueError('Update header CRC mismatch')
    return size, crc


def unpack(package: bytes, *, boot_api: int = BOOT_API,
           settings_abi: int = SETTINGS_ABI) -> UpdatePackage:
    package = bytes(package)
    size, crc = validate_header(package[:HEADER_SIZE], boot_api=boot_api, settings_abi=settings_abi)
    if len(package) != HEADER_SIZE + size:
        raise ValueError('Truncated or trailing update bytes')
    image = package[HEADER_SIZE:]
    if zlib.crc32(image) != crc:
        raise ValueError('Update image CRC mismatch')
    boot_image.unpack(image)
    minimum, abi = struct.unpack_from('<2I', package, 24)
    return UpdatePackage(image, crc, minimum, abi)


def pack(image: bytes, *, boot_api: int = BOOT_API,
         settings_abi: int = SETTINGS_ABI) -> bytes:
    image = bytes(image)
    boot_image.unpack(image)
    if not 1 <= boot_api <= 0xffffffff or not 1 <= settings_abi <= 0xffffffff:
        raise ValueError('Invalid version')
    h = struct.pack('<8s6I', b'ND15UPD1', 1, 0x54583135, len(image),
                    zlib.crc32(image), boot_api, settings_abi) + bytes(92)
    return h + struct.pack('<I', zlib.crc32(h)) + image
