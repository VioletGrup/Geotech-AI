def build_features(qc, depth, diameter):
    """Converts raw geotech inputs into ML-ready features"""
    return [
        qc,
        depth, 
        diameter,
        qc / (depth + 1),
        diameter * depth
    ]
