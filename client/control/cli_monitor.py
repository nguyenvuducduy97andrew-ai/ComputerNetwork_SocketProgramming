def draw_progress_bar(
    current_bytes: int,
    total_bytes: int,
    bar_length: int = 40,
    label: str = "Transfer",
) -> None:
    """Render one in-place byte progress bar for a CLI transfer."""
    safe_total = max(total_bytes, 0)
    safe_current = max(current_bytes, 0)

    if safe_total == 0:
        percent = 1.0
    else:
        percent = min(safe_current / safe_total, 1.0)

    filled_length = int(bar_length * percent)
    bar = "#" * filled_length + "-" * (bar_length - filled_length)

    print(
        f"\r{label:<10} |{bar}| "
        f"{percent:6.2%} "
        f"({min(safe_current, safe_total)}/{safe_total} bytes)",
        end="",
        flush=True,
    )

    if safe_current >= safe_total:
        print()


def make_progress_callback(label: str):
    """Create the callback shape expected by reliable_send/reliable_recv."""
    last_state: tuple[int, int] | None = None

    def update(current_bytes: int, total_bytes: int) -> None:
        nonlocal last_state
        state = (current_bytes, total_bytes)

        if state == last_state:
            return

        last_state = state
        draw_progress_bar(
            current_bytes,
            total_bytes,
            label=label,
        )

    return update

