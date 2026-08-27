"""Observability package — real-time monitoring for the Helix Education engine."""


def RealTimeMonitor(*args, **kwargs):
    """Lazy import to avoid circular/ordering issues with `python -m`."""
    from .dashboard import RealTimeMonitor as _cls

    return _cls(*args, **kwargs)


__all__ = ["RealTimeMonitor"]
