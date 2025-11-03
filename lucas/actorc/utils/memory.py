import re


def parse_memory_string(memory_str):
    """
    Convert Kubernetes-style memory string to bytes
    Supported units: K, M, G, T, P, E (base 1000) and Ki, Mi, Gi, Ti, Pi, Ei (base 1024)

    Args:
        memory_str: Memory string, e.g. "1024Mi", "2Gi", "512M", etc.

    Returns:
        int: Memory size in bytes
    """
    if memory_str is None:
        return 0

    if isinstance(memory_str, (int, float)):
        return int(memory_str)

    if not isinstance(memory_str, str):
        raise ValueError(f"Invalid memory format: {memory_str}")

    # Remove whitespace and convert to uppercase
    memory_str = memory_str.strip()

    # Regular expression to match numbers and units
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGTPE]i?)?$", memory_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid memory format: {memory_str}")

    value = float(match.group(1))
    unit = match.group(2)

    if not unit:
        # No unit, default to bytes
        return int(value)

    unit = unit.upper()

    # Base 1024 units (Ki, Mi, Gi, Ti, Pi, Ei)
    if unit.endswith("I"):
        multipliers = {
            "KI": 1024,
            "MI": 1024**2,
            "GI": 1024**3,
            "TI": 1024**4,
            "PI": 1024**5,
            "EI": 1024**6,
        }
    else:
        # Base 1000 units (K, M, G, T, P, E)
        multipliers = {
            "K": 1000,
            "M": 1000**2,
            "G": 1000**3,
            "T": 1000**4,
            "P": 1000**5,
            "E": 1000**6,
        }

    if unit not in multipliers:
        raise ValueError(f"Unknown memory unit: {unit}")

    return int(value * multipliers[unit])