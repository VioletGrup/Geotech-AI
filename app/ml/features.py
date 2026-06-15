from typing import Any, Dict, Optional


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_features(qc, depth, diameter):
    """Legacy positional feature builder (kept for backward compatibility)."""
    qc = qc or 0
    depth = depth or 0
    diameter = diameter or 0
    return [qc, depth, diameter, qc / (depth + 1), diameter * depth]


def build_feature_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw graph/payload row into the model's feature dict.

    Numeric features may be None (the model pipeline imputes them).
    Categorical features default to "unknown" so one-hot/imputation is stable.
    """
    diameter = _num(record.get("diameter"))
    length = _num(record.get("length"))
    depth = _num(record.get("depth"))
    qc = _num(record.get("qc"))
    fs = _num(record.get("fs"))

    return {
        "diameter": diameter,
        "length": length,
        "depth": depth,
        "qc": qc,
        "fs": fs,
        "slenderness": (length / diameter) if (length is not None and diameter) else None,
        "qc_x_diameter": (qc * diameter) if (qc is not None and diameter is not None) else None,
        "length_x_diameter": (length * diameter) if (length is not None and diameter is not None) else None,
        "pile_type": record.get("pile_type") or "unknown",
        "soil_type": record.get("soil_type") or "unknown",
        "site_id": record.get("site_id") or "unknown",
    }