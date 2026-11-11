"""Invented child: report the soft address-space limit."""

import resource


def soft_address_limit() -> int:
    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    return soft
