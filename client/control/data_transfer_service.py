import os
import zlib
from pathlib import Path


class ClientDataProcessingError(Exception):
    """Raised when transferred bytes cannot be converted as configured."""


def _apply_outgoing_type(data: bytes, transfer_type: str) -> bytes:
    if transfer_type == "I":
        return data

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClientDataProcessingError(
            "The upload is not valid UTF-8 and cannot use TYPE A."
        ) from exc

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", "\r\n").encode("utf-8")


def _apply_outgoing_mode(data: bytes, transfer_mode: str) -> bytes:
    if transfer_mode in {"S", "B"}:
        return data

    if transfer_mode == "C":
        return zlib.compress(data)

    raise ClientDataProcessingError(
        f"Unsupported transfer mode: {transfer_mode}"
    )


def prepare_upload_data(
    file_path: Path,
    transfer_type: str,
    transfer_mode: str,
) -> bytes:
    data = file_path.read_bytes()
    data = _apply_outgoing_type(data, transfer_type)
    return _apply_outgoing_mode(data, transfer_mode)


def process_download_data(
    data: bytes,
    transfer_type: str,
    transfer_mode: str,
) -> bytes:
    if transfer_mode == "C":
        try:
            data = zlib.decompress(data)
        except zlib.error as exc:
            raise ClientDataProcessingError(
                "The downloaded compressed payload is invalid."
            ) from exc
    elif transfer_mode not in {"S", "B"}:
        raise ClientDataProcessingError(
            f"Unsupported transfer mode: {transfer_mode}"
        )

    if transfer_type == "I":
        return data

    if transfer_type != "A":
        raise ClientDataProcessingError(
            f"Unsupported transfer type: {transfer_type}"
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClientDataProcessingError(
            "The downloaded TYPE A payload is not valid UTF-8."
        ) from exc

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", os.linesep).encode("utf-8")
