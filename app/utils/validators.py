from typing import Optional


def validate_pile_input(
    qc: Optional[float] = None,
    depth: Optional[float] = None,
    diameter: Optional[float] = None,
    length: Optional[float] = None,
    fs: Optional[float] = None,
) -> bool:
    """Validate pile/CPT inputs. Optional fields are only checked when present."""
    if qc is not None and qc < 0:
        raise ValueError("qc cannot be negative")
    if depth is not None and depth <= 0:
        raise ValueError("depth must be > 0")
    if diameter is not None and diameter <= 0:
        raise ValueError("diameter must be > 0")
    if length is not None and length <= 0:
        raise ValueError("length must be > 0")
    if fs is not None and fs < 0:
        raise ValueError("fs cannot be negative")
    return True