"""FTP-style MODE B framing shared by the client and server."""

import struct


BLOCK_HEADER = struct.Struct("!BH")
BLOCK_DESCRIPTOR_EOR = 0x80
BLOCK_DESCRIPTOR_EOF = 0x40
BLOCK_MAX_PAYLOAD = 0xFFFF
ALLOWED_DESCRIPTOR_BITS = BLOCK_DESCRIPTOR_EOR | BLOCK_DESCRIPTOR_EOF


class BlockModeError(ValueError):
    """Raised when a MODE B payload has invalid or incomplete framing."""


def encode_blocks(data: bytes) -> bytes:
    """Frame bytes as descriptor/count/data blocks terminated by EOF."""
    if not data:
        return BLOCK_HEADER.pack(BLOCK_DESCRIPTOR_EOF, 0)

    framed = bytearray()
    offset = 0

    while offset < len(data):
        chunk = data[offset:offset + BLOCK_MAX_PAYLOAD]
        offset += len(chunk)
        descriptor = BLOCK_DESCRIPTOR_EOF if offset == len(data) else 0
        framed.extend(BLOCK_HEADER.pack(descriptor, len(chunk)))
        framed.extend(chunk)

    return bytes(framed)


def decode_blocks(framed_data: bytes) -> bytes:
    """Validate MODE B framing and reconstruct the original bytes."""
    decoded = bytearray()
    offset = 0
    eof_seen = False

    while offset < len(framed_data):
        if len(framed_data) - offset < BLOCK_HEADER.size:
            raise BlockModeError("MODE B payload ended inside a block header.")

        descriptor, block_length = BLOCK_HEADER.unpack_from(framed_data, offset)
        offset += BLOCK_HEADER.size

        if descriptor & ~ALLOWED_DESCRIPTOR_BITS:
            raise BlockModeError("MODE B payload contains an unsupported descriptor.")

        block_end = offset + block_length
        if block_end > len(framed_data):
            raise BlockModeError("MODE B payload ended inside a data block.")

        decoded.extend(framed_data[offset:block_end])
        offset = block_end

        if descriptor & BLOCK_DESCRIPTOR_EOF:
            eof_seen = True
            if offset != len(framed_data):
                raise BlockModeError("MODE B payload contains data after the EOF block.")
            break

    if not eof_seen:
        raise BlockModeError("MODE B payload does not contain an EOF block.")

    return bytes(decoded)
