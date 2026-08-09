"""Shared exceptions for server-side data transfers."""


class DataTransferError(Exception):
    """Gọi khi có lỗi xảy ra trong quá trình truyền dữ liệu giữa server và client."""
