from typing import Dict, List, Optional


# ============================================================
# BASIC HELPERS
# ============================================================

def _order_number(order_name: str) -> int:
    """
    تبدیل:

        1X -> 1
        2X -> 2
        10X -> 10
    """

    try:
        return int(
            order_name.upper().replace("X", "")
        )
    except (ValueError, AttributeError):
        return 0


# ============================================================
# BUILD ORDER MAP
# ============================================================

def build_order_map(order_results) -> Dict[str, dict]:
    """
    تبدیل خروجی analyze_orders به Order Map.

    ورودی:

        [
            {
                "peak": {...},
                "match": {...}
            }
        ]

    خروجی:

        {
            "1X": {...},
            "2X": {...}
        }
    """

    order_map = {}

    if not order_results:
        return order_map

    for item in order_results:

        peak = item.get("peak", {})
        match = item.get("match", {})

        name = match.get("name")

        if not name:
            continue

        order_map[name] = {
            "order": name,

            "order_number": _order_number(
                name
            ),

            "frequency_hz": float(
                peak.get(
                    "frequency_hz",
                    0.0
                )
            ),

            "amplitude": float(
                peak.get(
                    "amplitude",
                    0.0
                )
            ),

            "prominence": float(
                peak.get(
                    "prominence",
                    0.0
                )
            ),

            "estimated_order": float(
                match.get(
                    "estimated_order",
                    0.0
                )
            ),

            "order_error": float(
                match.get(
                    "order_error",
                    0.0
                )
            ),

            "confidence": float(
                match.get(
                    "confidence",
                    0.0
                )
            ),

            "matched": bool(
                match.get(
                    "matched",
                    False
                )
            ),
        }

    return order_map


# ============================================================
# AMPLITUDE NORMALIZATION
# ============================================================

def calculate_relative_amplitude(
    order_map: Dict[str, dict]
) -> Dict[str, dict]:
    """
    محاسبه Amplitude نسبی نسبت به بیشترین Peak.

    مثال:

        max amplitude = 243

        1X = 53
        relative = 53 / 243
    """

    if not order_map:
        return {}

    max_amplitude = max(
        item["amplitude"]
        for item in order_map.values()
    )

    if max_amplitude <= 0:
        max_amplitude = 1.0

    result = {}

    for order, item in order_map.items():

        data = dict(item)

        data["relative_amplitude"] = (
            item["amplitude"]
            / max_amplitude
        )

        result[order] = data

    return result


# ============================================================
# HARMONIC ANALYSIS
# ============================================================

def analyze_harmonics(
    order_map: Dict[str, dict],
    max_order: int = 10
) -> dict:
    """
    بررسی حضور Harmonicها.

    خروجی:

        {
            "present_orders": [...],
            "missing_orders": [...],
            "harmonic_count": ...,
            "highest_order": ...
        }
    """

    present_orders = []

    for order_name in order_map:

        number = _order_number(
            order_name
        )

        if (
            1 <= number <= max_order
        ):
            present_orders.append(
                number
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

    highest_order = (
        max(present_orders)
        if present_orders
        else 0
    )

    return {
        "present_orders": present_orders,
        "missing_orders": missing_orders,
        "harmonic_count": len(
            present_orders
        ),
        "highest_order": highest_order,
    }


# ============================================================
# IMPORTANT ORDER RATIOS
# ============================================================

def calculate_order_ratios(
    order_map: Dict[str, dict]
) -> dict:
    """
    محاسبه نسبت Amplitude بین Orderهای مهم.

    این نسبت‌ها در مرحله تشخیص عیب
    بسیار مهم خواهند بود.
    """

    def amp(order: str):
        item = order_map.get(order)

        if not item:
            return 0.0

        return float(
            item.get(
                "amplitude",
                0.0
            )
        )

    a1 = amp("1X")
    a2 = amp("2X")
    a3 = amp("3X")
    a4 = amp("4X")
    a5 = amp("5X")

    def ratio(
        numerator: float,
        denominator: float
    ):
        if denominator <= 0:
            return None

        return (
            numerator
            / denominator
        )

    return {
        "2X_to_1X": ratio(
            a2,
            a1
        ),

        "3X_to_1X": ratio(
            a3,
            a1
        ),

        "4X_to_1X": ratio(
            a4,
            a1
        ),

        "5X_to_1X": ratio(
            a5,
            a1
        ),

        "3X_to_2X": ratio(
            a3,
            a2
        ),

        "2X_plus_3X_to_1X": (
            ratio(
                a2 + a3,
                a1
            )
        ),
    }


# ============================================================
# PROMINENCE ANALYSIS
# ============================================================

def analyze_prominence(
    order_map: Dict[str, dict]
) -> dict:
    """
    تحلیل prominence مربوط به Peakها.
    """

    if not order_map:
        return {
            "max_prominence": 0.0,
            "dominant_order": None,
            "prominence_sum": 0.0,
        }

    dominant_order = max(
        order_map,
        key=lambda order:
            order_map[order].get(
                "amplitude",
                0.0
            )
    )

    max_prominence = max(
        float(
            item.get(
                "prominence",
                0.0
            )
        )
        for item in order_map.values()
    )

    prominence_sum = sum(
        float(
            item.get(
                "prominence",
                0.0
            )
        )
        for item in order_map.values()
    )

    return {
        "max_prominence": max_prominence,

        "dominant_order":
            dominant_order,

        "prominence_sum":
            prominence_sum,
    }


# ============================================================
# DOMINANT ORDER
# ============================================================

def find_dominant_orders(
    order_map: Dict[str, dict],
    top_n: int = 5
) -> List[dict]:
    """
    پیدا کردن قوی‌ترین Orderها بر اساس Amplitude.
    """

    items = []

    for order, data in order_map.items():

        items.append({
            "order": order,

            "amplitude": float(
                data.get(
                    "amplitude",
                    0.0
                )
            ),

            "frequency_hz": float(
                data.get(
                    "frequency_hz",
                    0.0
                )
            ),

            "confidence": float(
                data.get(
                    "confidence",
                    0.0
                )
            ),
        })

    items.sort(
        key=lambda item:
            item["amplitude"],
        reverse=True
    )

    return items[:top_n]


# ============================================================
# BUILD COMPLETE EVIDENCE
# ============================================================

def build_fault_evidence(
    order_results,
    rpm: Optional[float] = None,
    max_order: int = 10
) -> dict:
    """
    ساخت Feature/Evidence کامل از Order Analysis.

    این تابع هنوز Fault تشخیص نمی‌دهد.

    فقط شواهد را استخراج می‌کند.
    """

    order_map = build_order_map(
        order_results
    )

    order_map = calculate_relative_amplitude(
        order_map
    )

    harmonics = analyze_harmonics(
        order_map,
        max_order=max_order
    )

    ratios = calculate_order_ratios(
        order_map
    )

    prominence = analyze_prominence(
        order_map
    )

    dominant_orders = find_dominant_orders(
        order_map
    )

    # --------------------------------------------------------
    # Total amplitude
    # --------------------------------------------------------

    total_amplitude = sum(
        item["amplitude"]
        for item in order_map.values()
    )

    # --------------------------------------------------------
    # Average confidence
    # --------------------------------------------------------

    if order_map:

        average_confidence = (
            sum(
                item["confidence"]
                for item in order_map.values()
            )
            / len(order_map)
        )

    else:

        average_confidence = 0.0

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    return {
        "rpm": rpm,

        "order_map": order_map,

        "harmonics": harmonics,

        "ratios": ratios,

        "prominence": prominence,

        "dominant_orders": dominant_orders,

        "total_matched_peaks": len(
            order_map
        ),

        "total_amplitude": (
            total_amplitude
        ),

        "average_confidence": (
            average_confidence
        ),
    }