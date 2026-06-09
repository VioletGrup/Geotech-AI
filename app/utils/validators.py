def validate_pile_input(qc, depth, diameter):
    if qc < 0:
        raise ValueError("qc cannot be negative")
    if depth <= 0:
        raise ValueError("depth must be > 0")
    if diameter <= 0:
        raise ValueError("diameter must be > 0")

    return True