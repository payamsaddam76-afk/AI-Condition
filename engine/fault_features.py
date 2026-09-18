from typing import Dict, Any, List


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_order_number(order_name):
    """
    Convert:
        1X -> 1
        2X -> 2
        10X -> 10
    """

    if order_name is None:
        return None

    try:
        text = str(order_name).strip().upper()

        if text.endswith("X"):
            text = text[:-1]

        return int(float(text))

    except (TypeError, ValueError):
        return None


def get_order_name(order_number):
    """
    Convert:
        1 -> 1X
        2 -> 2X
    """

    try:
        return f"{int(order_number)}X"
    except (TypeError, ValueError):
        return None


# ============================================================
# EVIDENCE ACCESS
# ============================================================

def get_order_map(evidence):
    """
    Extract order_map from fault evidence.

    Current evidence structure:

        evidence["order_map"]

    Example:

        {
            "1X": {...},
            "2X": {...},
            "3X": {...}
        }
    """

    if not isinstance(evidence, dict):
        return {}

    order_map = evidence.get(
        "order_map",
        {}
    )

    if not isinstance(order_map, dict):
        return {}

    return order_map


def get_order_data(evidence, order_name):
    """
    Return data for a specific order.
    """

    order_map = get_order_map(evidence)

    return order_map.get(
        order_name,
        {}
    )


def get_amplitude(order_data):
    """
    Read amplitude from an order entry.
    """

    if not isinstance(order_data, dict):
        return 0.0

    return safe_float(
        order_data.get(
            "amplitude",
            0.0
        )
    )


def get_frequency(order_data):
    """
    Read frequency from an order entry.
    """

    if not isinstance(order_data, dict):
        return 0.0

    return safe_float(
        order_data.get(
            "frequency_hz",
            0.0
        )
    )


def get_confidence(order_data):
    """
    Read confidence from an order entry.
    """

    if not isinstance(order_data, dict):
        return 0.0

    return safe_float(
        order_data.get(
            "confidence",
            0.0
        )
    )


# ============================================================
# FUNDAMENTAL FEATURES
# ============================================================

def calculate_fundamental_features(evidence):
    """
    Calculate 1X and dominant-order features.

    The fundamental is explicitly read from 1X.
    The dominant order is the order with the highest amplitude.
    """

    order_map = get_order_map(
        evidence
    )

    fundamental = order_map.get(
        "1X",
        {}
    )

    fundamental_amplitude = get_amplitude(
        fundamental
    )

    fundamental_frequency = get_frequency(
        fundamental
    )

    fundamental_confidence = get_confidence(
        fundamental
    )

    dominant_order = None
    dominant_amplitude = 0.0
    dominant_frequency = 0.0
    dominant_confidence = 0.0

    for order_name, data in order_map.items():

        amplitude = get_amplitude(
            data
        )

        if amplitude > dominant_amplitude:

            dominant_amplitude = amplitude
            dominant_order = order_name
            dominant_frequency = get_frequency(
                data
            )
            dominant_confidence = get_confidence(
                data
            )

    if dominant_amplitude > 0:

        dominant_relative = (
            fundamental_amplitude
            / dominant_amplitude
        )

    else:

        dominant_relative = 0.0

    return {
        "fundamental_order": "1X",

        "fundamental_amplitude":
            fundamental_amplitude,

        "fundamental_frequency":
            fundamental_frequency,

        "fundamental_confidence":
            fundamental_confidence,

        "dominant_order":
            dominant_order,

        "dominant_amplitude":
            dominant_amplitude,

        "dominant_frequency":
            dominant_frequency,

        "dominant_confidence":
            dominant_confidence,

        "dominant_relative":
            dominant_relative,
    }


# ============================================================
# ORDER RATIOS
# ============================================================

def calculate_order_ratios(evidence):
    """
    Calculate amplitude ratios between running-speed orders.
    """

    order_map = get_order_map(
        evidence
    )

    amplitudes = {}

    for order_name, data in order_map.items():

        order_number = get_order_number(
            order_name
        )

        if order_number is None:
            continue

        amplitudes[order_number] = get_amplitude(
            data
        )

    one_x = amplitudes.get(
        1,
        0.0
    )

    two_x = amplitudes.get(
        2,
        0.0
    )

    three_x = amplitudes.get(
        3,
        0.0
    )

    four_x = amplitudes.get(
        4,
        0.0
    )

    five_x = amplitudes.get(
        5,
        0.0
    )

    seven_x = amplitudes.get(
        7,
        0.0
    )

    eight_x = amplitudes.get(
        8,
        0.0
    )

    def ratio(
        numerator,
        denominator
    ):

        if denominator <= 0:
            return 0.0

        return numerator / denominator

    return {

        "2X_to_1X":
            ratio(
                two_x,
                one_x
            ),

        "3X_to_1X":
            ratio(
                three_x,
                one_x
            ),

        "4X_to_1X":
            ratio(
                four_x,
                one_x
            ),

        "5X_to_1X":
            ratio(
                five_x,
                one_x
            ),

        "7X_to_1X":
            ratio(
                seven_x,
                one_x
            ),

        "8X_to_1X":
            ratio(
                eight_x,
                one_x
            ),

        "3X_to_2X":
            ratio(
                three_x,
                two_x
            ),

        "4X_to_2X":
            ratio(
                four_x,
                two_x
            ),

        "5X_to_2X":
            ratio(
                five_x,
                two_x
            ),

        "7X_to_2X":
            ratio(
                seven_x,
                two_x
            ),

        "8X_to_2X":
            ratio(
                eight_x,
                two_x
            ),

        "2X_plus_3X_to_1X":
            ratio(
                two_x + three_x,
                one_x
            ),
    }


# ============================================================
# HARMONIC FEATURES
# ============================================================

def calculate_harmonic_features(
    evidence,
    max_order=10
):
    """
    Calculate harmonic distribution features.
    """

    order_map = get_order_map(
        evidence
    )

    present_orders = []

    for order_name in order_map.keys():

        order_number = get_order_number(
            order_name
        )

        if order_number is None:
            continue

        if 1 <= order_number <= max_order:

            present_orders.append(
                order_number
            )

    present_orders = sorted(
        set(present_orders)
    )

    missing_orders = [
        order
        for order in range(
            1,
            max_order + 1
        )
        if order not in present_orders
    ]

    odd_orders = [
        order
        for order in present_orders
        if order % 2 == 1
    ]

    even_orders = [
        order
        for order in present_orders
        if order % 2 == 0
    ]

    odd_amplitude = 0.0
    even_amplitude = 0.0

    low_order_amplitude = 0.0
    mid_order_amplitude = 0.0
    high_order_amplitude = 0.0

    for order in present_orders:

        data = order_map.get(
            get_order_name(order),
            {}
        )

        amplitude = get_amplitude(
            data
        )

        if order % 2 == 1:
            odd_amplitude += amplitude
        else:
            even_amplitude += amplitude

        if 1 <= order <= 3:

            low_order_amplitude += amplitude

        elif 4 <= order <= 6:

            mid_order_amplitude += amplitude

        elif 7 <= order <= max_order:

            high_order_amplitude += amplitude

    if even_amplitude > 0:

        odd_even_ratio = (
            odd_amplitude
            / even_amplitude
        )

    else:

        odd_even_ratio = 0.0

    if low_order_amplitude > 0:

        high_low_ratio = (
            high_order_amplitude
            / low_order_amplitude
        )

    else:

        high_low_ratio = 0.0

    highest_order = (
        max(present_orders)
        if present_orders
        else 0
    )

    return {

        "present_orders":
            present_orders,

        "missing_orders":
            missing_orders,

        "harmonic_count":
            len(present_orders),

        "highest_order":
            highest_order,

        "odd_orders":
            odd_orders,

        "even_orders":
            even_orders,

        "odd_amplitude":
            odd_amplitude,

        "even_amplitude":
            even_amplitude,

        "odd_even_ratio":
            odd_even_ratio,

        "low_order_amplitude":
            low_order_amplitude,

        "mid_order_amplitude":
            mid_order_amplitude,

        "high_order_amplitude":
            high_order_amplitude,

        "high_low_ratio":
            high_low_ratio,
    }


# ============================================================
# ENERGY FEATURES
# ============================================================

def calculate_energy_features(evidence):
    """
    Calculate amplitude distribution statistics.
    """

    order_map = get_order_map(
        evidence
    )

    amplitudes = []

    for data in order_map.values():

        amplitude = get_amplitude(
            data
        )

        amplitudes.append(
            amplitude
        )

    if not amplitudes:

        return {
            "total_amplitude": 0.0,
            "mean_amplitude": 0.0,
            "maximum_amplitude": 0.0,
            "amplitude_spread": 0.0,
        }

    total_amplitude = sum(
        amplitudes
    )

    mean_amplitude = (
        total_amplitude
        / len(amplitudes)
    )

    maximum_amplitude = max(
        amplitudes
    )

    if mean_amplitude > 0:

        amplitude_spread = (
            maximum_amplitude
            / mean_amplitude
        )

    else:

        amplitude_spread = 0.0

    return {

        "total_amplitude":
            total_amplitude,

        "mean_amplitude":
            mean_amplitude,

        "maximum_amplitude":
            maximum_amplitude,

        "amplitude_spread":
            amplitude_spread,
    }


# ============================================================
# CONFIDENCE FEATURES
# ============================================================

def calculate_confidence_features(evidence):
    """
    Calculate confidence statistics.
    """

    order_map = get_order_map(
        evidence
    )

    confidences = []

    for data in order_map.values():

        confidence = get_confidence(
            data
        )

        confidences.append(
            confidence
        )

    if not confidences:

        return {
            "average_confidence": 0.0,
            "minimum_confidence": 0.0,
            "maximum_confidence": 0.0,
        }

    return {

        "average_confidence":
            sum(confidences)
            / len(confidences),

        "minimum_confidence":
            min(confidences),

        "maximum_confidence":
            max(confidences),
    }


# ============================================================
# COMPLETE FEATURE BUILDER
# ============================================================

def build_fault_features(
    evidence,
    max_order=10
):
    """
    Build complete fault feature vector.

    Output structure:

        {
            "rpm": ...,

            "fundamental": {...},

            "order_ratios": {...},

            "harmonic_features": {...},

            "energy_features": {...},

            "confidence_features": {...}
        }
    """

    if not isinstance(
        evidence,
        dict
    ):
        evidence = {}

    rpm = safe_float(
        evidence.get(
            "rpm",
            0
        )
    )

    fundamental = calculate_fundamental_features(
        evidence
    )

    order_ratios = calculate_order_ratios(
        evidence
    )

    harmonic_features = calculate_harmonic_features(
        evidence,
        max_order=max_order
    )

    energy_features = calculate_energy_features(
        evidence
    )

    confidence_features = calculate_confidence_features(
        evidence
    )

    return {

        "rpm":
            rpm,

        "fundamental":
            fundamental,

        "order_ratios":
            order_ratios,

        "harmonic_features":
            harmonic_features,

        "energy_features":
            energy_features,

        "confidence_features":
            confidence_features,
    }