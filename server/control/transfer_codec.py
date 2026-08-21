"""Pure TYPE/MODE transformations for server-side transfer payloads."""

import os
import zlib

from server.control.transfer_errors import DataTransferError
from shared.block_mode import BlockModeError, decode_blocks, encode_blocks


def normalize_transfer_type(transfer_type: str) -> str:
    """Chuyển đổi loại truyền dữ liệu sang chữ hoa và kiểm tra hợp lệ. Chỉ chấp nhận A, I."""
    normalized = transfer_type.upper()
    if normalized not in {"A", "I"}:
        raise DataTransferError(f"Unsupported transfer type: {normalized}")
    return normalized


def normalize_transfer_mode(transfer_mode: str) -> str:
    """Chuyển đổi chế độ truyền dữ liệu sang chữ hoa và kiểm tra hợp lệ. Chỉ chấp nhận S, B, C."""
    normalized = transfer_mode.upper()
    if normalized not in {"S", "B", "C"}:
        raise DataTransferError(f"Unsupported transfer mode: {normalized}")
    return normalized


def encode_for_transfer(
    data: bytes,
    transfer_type: str,
    transfer_mode: str,
) -> bytes:
    """Convert các bytes thành biểu diễn trên dây chuyền (wire representation) để truyền đi."""
    transfer_type = normalize_transfer_type(transfer_type)
    transfer_mode = normalize_transfer_mode(transfer_mode)

    if transfer_type == "A":
        try:
            text = data.decode("utf-8") #Type A: dữ liệu văn bản, cần chuyển đổi sang CRLF
        except UnicodeDecodeError as exc:
            raise DataTransferError(
                "File cannot be transferred using TYPE A because it is not valid UTF-8 text."
            ) from exc

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        data = normalized.replace("\n", "\r\n").encode("utf-8")

    if transfer_mode == "B":
        return encode_blocks(data)

    if transfer_mode == "C": #MODE C: nén dữ liệu
        return zlib.compress(data)

    # MODE S giữ nguyên payload sau bước chuyển đổi TYPE.
    return data


def decode_from_transfer(
    data: bytes,
    transfer_type: str,
    transfer_mode: str,
) -> bytes:
    """Convert các bytes nhận được từ wire representation thành biểu diễn trong bộ nhớ (in-memory representation)."""
    transfer_type = normalize_transfer_type(transfer_type)
    transfer_mode = normalize_transfer_mode(transfer_mode)

    if transfer_mode == "B":
        try:
            data = decode_blocks(data)
        except BlockModeError as exc:
            raise DataTransferError(str(exc)) from exc
    elif transfer_mode == "C":
        try:
            data = zlib.decompress(data) #MODE C: giải nén dữ liệu nén
        except zlib.error as exc:
            raise DataTransferError("Received compressed data is invalid.") from exc

    if transfer_type == "I": #Type I: dữ liệu nhị phân, không cần chuyển đổi
        return data

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataTransferError(
            "Received TYPE A data is not valid UTF-8 text."
        ) from exc

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", os.linesep).encode("utf-8")
