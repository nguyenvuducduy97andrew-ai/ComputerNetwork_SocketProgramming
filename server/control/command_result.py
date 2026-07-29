from collections.abc import Iterator
from dataclasses import dataclass

from server.control.ftp_codes import FTPReplyCode


@dataclass(frozen=True)
class CommandReply:
    """One reply emitted while executing a command."""

    code: FTPReplyCode
    message: str | None = None
    close_control: bool = False

    def format(self) -> str:
        return self.code.format(self.message)


CommandReplies = Iterator[CommandReply]
CommandHandlerResult = str | CommandReplies


def iter_command_replies(
    result: CommandHandlerResult,
) -> Iterator[tuple[str, bool]]:
    """Normalize legacy one-reply handlers and streaming multi-reply handlers."""
    if isinstance(result, str):
        yield result, False
        return

    for reply in result:
        yield reply.format(), reply.close_control
