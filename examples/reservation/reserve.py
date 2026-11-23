def reserve(capacity: int, used: int, request: int) -> int | None:
    """Return the new usage if it fits. Inputs are nonnegative integers."""
    remaining = capacity - used
    if request > remaining:
        return None
    return used + request
