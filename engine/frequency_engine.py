from dataclasses import dataclass
from typing import Optional


@dataclass
class FrequencyMatch:
    measured_hz: float
    reference_hz: float
    name: str

    # Order واقعی نسبت به 1X
    estimated_order: float

    # فاصله Order واقعی از Order صحیح
    order_error: float

    difference_hz: float
    difference_percent: float

    rpm_tolerance: float
    allowed_error_hz: float

    matched: bool
    confidence: float

    def to_dict(self):
        return {
            "measured_hz": round(self.measured_hz, 4),
            "reference_hz": round(self.reference_hz, 4),
            "name": self.name,
            "estimated_order": round(
                self.estimated_order,
                4
            ),
            "order_error": round(
                self.order_error,
                4
            ),
            "difference_hz": round(
                self.difference_hz,
                4
            ),
            "difference_percent": round(
                self.difference_percent,
                2
            ),
            "rpm_tolerance": self.rpm_tolerance,
            "allowed_error_hz": round(
                self.allowed_error_hz,
                4
            ),
            "matched": self.matched,
            "confidence": round(
                self.confidence,
                3
            ),
        }


# ============================================================
# RPM / FREQUENCY
# ============================================================

def rpm_to_hz(rpm: float) -> float:
    return rpm / 60.0


def hz_to_rpm(hz: float) -> float:
    return hz * 60.0


# ============================================================
# REFERENCE RANGE
# ============================================================

def reference_range(
    reference_hz: float,
    rpm_tolerance: float = 10,
    percent_tolerance: float = 2.0,
):
    """
    محدوده مجاز فرکانس مرجع.
    """

    if reference_hz <= 0:
        return (
            0.0,
            0.0
        )

    rpm_based_tolerance = (
        rpm_tolerance / 60.0
    )

    percent_based_tolerance = (
        reference_hz
        * percent_tolerance
        / 100.0
    )

    allowed_error = max(
        rpm_based_tolerance,
        percent_based_tolerance,
    )

    return (
        reference_hz - allowed_error,
        reference_hz + allowed_error,
    )


# ============================================================
# ALLOWED FREQUENCY ERROR
# ============================================================

def calculate_allowed_error(
    reference_hz: float,
    rpm_tolerance: float = 10,
    percent_tolerance: float = 2.0,
    fft_resolution_hz: Optional[float] = None,
    calibration_error_hz: float = 0.0,
):
    """
    محاسبه خطای مجاز فرکانس.

    منابع خطا:

    1. خطای RPM
    2. خطای درصدی
    3. FFT resolution
    4. خطای calibration
    """

    if reference_hz <= 0:
        return 0.0

    rpm_error = (
        rpm_tolerance / 60.0
    )

    percent_error = (
        reference_hz
        * percent_tolerance
        / 100.0
    )

    if (
        fft_resolution_hz is not None
        and fft_resolution_hz > 0
    ):
        fft_error = (
            fft_resolution_hz / 2.0
        )
    else:
        fft_error = 0.0

    calibration_error = max(
        0.0,
        calibration_error_hz
    )

    base_error = max(
        rpm_error,
        percent_error,
    )

    return (
        base_error
        + fft_error
        + calibration_error
    )


# ============================================================
# ESTIMATED ORDER
# ============================================================

def calculate_estimated_order(
    measured_hz: float,
    rpm: float,
):
    """
    محاسبه Order واقعی نسبت به 1X.

    مثال:

        RPM = 1500
        1X = 25 Hz

        measured = 25.644 Hz

        estimated_order =
            25.644 / 25

        = 1.02576X
    """

    if rpm is None or rpm <= 0:
        return None

    one_x = rpm_to_hz(rpm)

    if one_x <= 0:
        return None

    return (
        measured_hz / one_x
    )


# ============================================================
# FREQUENCY MATCH
# ============================================================

def match_frequency(
    measured_hz: float,
    reference_hz: float,
    name: str,
    rpm_tolerance: float = 10,
    percent_tolerance: float = 2.0,
    fft_resolution_hz: Optional[float] = None,
    calibration_error_hz: float = 0.0,
    order_tolerance: Optional[float] = None,

    # این دو پارامتر برای Order واقعی اضافه شده‌اند
    rpm: Optional[float] = None,
    target_order: Optional[int] = None,
) -> FrequencyMatch:
    """
    بررسی تطابق Peak با یک Order مشخص.

    مثال:

        measured = 49.886
        rpm = 1500
        target_order = 2

        1X = 25 Hz

        estimated_order =
            49.886 / 25
            = 1.99544X

        order_error =
            |1.99544 - 2|
            = 0.00456

    """

    # --------------------------------------------------------
    # Frequency difference
    # --------------------------------------------------------

    difference = abs(
        measured_hz
        - reference_hz
    )

    if reference_hz > 0:

        difference_percent = (
            difference
            / reference_hz
        ) * 100.0

    else:

        difference_percent = 999.0

    # --------------------------------------------------------
    # Allowed frequency error
    # --------------------------------------------------------

    allowed_error = (
        calculate_allowed_error(
            reference_hz=reference_hz,
            rpm_tolerance=rpm_tolerance,
            percent_tolerance=percent_tolerance,
            fft_resolution_hz=fft_resolution_hz,
            calibration_error_hz=calibration_error_hz,
        )
    )

    # --------------------------------------------------------
    # Estimated Order
    # --------------------------------------------------------

    estimated_order = None

    if rpm is not None:

        estimated_order = (
            calculate_estimated_order(
                measured_hz,
                rpm
            )
        )

    # اگر RPM داده نشده،
    # از target order به عنوان fallback استفاده می‌کنیم.
    if estimated_order is None:

        if target_order is not None:
            estimated_order = float(
                target_order
            )
        else:
            estimated_order = 0.0

    # --------------------------------------------------------
    # Target order
    # --------------------------------------------------------

    if target_order is None:

        if estimated_order > 0:

            target_order = int(
                round(
                    estimated_order
                )
            )

        else:

            target_order = 0

    # --------------------------------------------------------
    # Order error
    # --------------------------------------------------------

    order_error = abs(
        estimated_order
        - target_order
    )

    # --------------------------------------------------------
    # Order tolerance
    # --------------------------------------------------------

    if order_tolerance is None:

        order_tolerance = (
            percent_tolerance
            / 100.0
        )

    # --------------------------------------------------------
    # Frequency Match
    # --------------------------------------------------------

    frequency_match = (
        difference
        <= allowed_error
    )

    # --------------------------------------------------------
    # Order Match
    # --------------------------------------------------------

    order_match = (
        order_error
        <= order_tolerance
    )

    # --------------------------------------------------------
    # Final Match
    # --------------------------------------------------------

    matched = (
        frequency_match
        or order_match
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    if order_tolerance > 0:

        order_confidence = max(
            0.0,
            1.0
            - (
                order_error
                / order_tolerance
            )
        )

    else:

        order_confidence = 0.0

    if allowed_error > 0:

        frequency_confidence = max(
            0.0,
            1.0
            - (
                difference
                / allowed_error
            )
        )

    else:

        frequency_confidence = 0.0

    # برای Order analysis،
    # confidence اصلی از Order می‌آید.
    confidence = max(
        frequency_confidence,
        order_confidence,
    )

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return FrequencyMatch(
        measured_hz=measured_hz,
        reference_hz=reference_hz,
        name=name,

        estimated_order=estimated_order,
        order_error=order_error,

        difference_hz=difference,
        difference_percent=difference_percent,

        rpm_tolerance=rpm_tolerance,
        allowed_error_hz=allowed_error,

        matched=matched,
        confidence=confidence,
    )


# ============================================================
# FFT RESOLUTION
# ============================================================

def estimate_fft_resolution(
    frequencies
):
    """
    تخمین Resolution از روی Frequency bins.
    """

    if frequencies is None:
        return None

    if len(frequencies) < 2:
        return None

    differences = []

    for i in range(1, len(frequencies)):

        diff = abs(
            float(frequencies[i])
            - float(frequencies[i - 1])
        )

        if diff > 0:
            differences.append(
                diff
            )

    if not differences:
        return None

    differences.sort()

    middle = (
        len(differences) // 2
    )

    if (
        len(differences) % 2 == 0
    ):

        resolution = (
            differences[middle - 1]
            + differences[middle]
        ) / 2.0

    else:

        resolution = (
            differences[middle]
        )

    return float(
        resolution
    )


# ============================================================
# ORDER ANALYSIS
# ============================================================
def analyze_orders(
    peaks,
    rpm,
    max_order=10,
    rpm_tolerance=10,
    percent_tolerance=3.0,
    order_tolerance=0.03
):
    """
    Analyze FFT peaks based on rotational orders.

    Order is always calculated relative to 1X:

        1X = RPM / 60
        Order = frequency / 1X

    If multiple peaks match the same order,
    only the best peak is kept.

    Best peak priority:

        1. Lowest relative order error
        2. Highest confidence
        3. Highest amplitude
    """

    if not peaks:
        return []

    if rpm is None or rpm <= 0:
        return []

    # ========================================================
    # 1X
    # ========================================================

    one_x = rpm_to_hz(rpm)

    if one_x <= 0:
        return []

    # ========================================================
    # Temporary storage
    #
    # One entry per order
    # ========================================================

    best_matches = {}

    # ========================================================
    # Analyze peaks
    # ========================================================

    for peak in peaks:

        # ----------------------------------------------------
        # Frequency
        # ----------------------------------------------------

        if hasattr(peak, "frequency_hz"):

            measured_hz = float(
                peak.frequency_hz
            )

        elif isinstance(peak, dict):

            measured_hz = float(
                peak.get(
                    "frequency_hz",
                    0.0
                )
            )

        else:

            continue

        if measured_hz <= 0:
            continue

        # ====================================================
        # Estimated order
        # ====================================================

        estimated_order = (
            measured_hz / one_x
        )

        if estimated_order <= 0:
            continue

        # ----------------------------------------------------
        # Ignore clearly out-of-range orders
        # ----------------------------------------------------

        if estimated_order > (
            max_order + 0.5
        ):
            continue

        # ====================================================
        # Nearest integer order
        # ====================================================

        nearest_order = int(
            round(estimated_order)
        )

        if nearest_order < 1:
            continue

        if nearest_order > max_order:
            continue

        # ====================================================
        # Order error
        # ====================================================

        order_error = abs(
            estimated_order - nearest_order
        )

        # ====================================================
        # Relative Order Error
        # ====================================================

        relative_order_error = (
            order_error / nearest_order
        )

        if relative_order_error > order_tolerance:
            continue

        # ====================================================
        # Reference frequency
        # ====================================================

        reference_hz = (
            one_x * nearest_order
        )

        order_name = (
            f"{nearest_order}X"
        )

        # ====================================================
        # Match Frequency
        # ====================================================

        try:

            match = match_frequency(
                measured_hz,
                reference_hz,
                order_name,
                rpm=rpm,
                rpm_tolerance=rpm_tolerance,
                percent_tolerance=percent_tolerance,
                target_order=nearest_order,
                order_tolerance=order_tolerance
            )

        except TypeError:

            match = match_frequency(
                measured_hz,
                reference_hz,
                order_name
            )

        # ====================================================
        # Force Order Match
        # ====================================================

        match.matched = True

        # ====================================================
        # Correct values
        # ====================================================

        match.estimated_order = (
            estimated_order
        )

        match.order_error = (
            order_error
        )

        match.reference_hz = (
            reference_hz
        )

        match.difference_hz = abs(
            measured_hz - reference_hz
        )

        if reference_hz > 0:

            match.difference_percent = (
                abs(
                    measured_hz - reference_hz
                )
                / reference_hz
                * 100.0
            )

        else:

            match.difference_percent = 0.0

        # ====================================================
        # Peak data
        # ====================================================

        if hasattr(peak, "to_dict"):

            peak_data = peak.to_dict()

        else:

            peak_data = peak

        # ====================================================
        # Amplitude
        # ====================================================

        try:

            amplitude = float(
                peak_data.get(
                    "amplitude",
                    0.0
                )
            )

        except (TypeError, ValueError):

            amplitude = 0.0

        # ====================================================
        # Candidate
        # ====================================================

        candidate = {
            "peak": peak_data,
            "match": match.to_dict(),
            "_relative_order_error": relative_order_error,
            "_amplitude": amplitude,
        }

        # ====================================================
        # Check duplicate order
        # ====================================================

        existing = best_matches.get(
            nearest_order
        )

        if existing is None:

            best_matches[
                nearest_order
            ] = candidate

        else:

            # -----------------------------------------------
            # Current candidate quality
            # -----------------------------------------------

            candidate_key = (
                relative_order_error,
                -float(
                    candidate["match"].get(
                        "confidence",
                        0.0
                    )
                ),
                -amplitude
            )

            # -----------------------------------------------
            # Existing candidate quality
            # -----------------------------------------------

            existing_key = (
                existing["_relative_order_error"],
                -float(
                    existing["match"].get(
                        "confidence",
                        0.0
                    )
                ),
                -existing["_amplitude"]
            )

            # -----------------------------------------------
            # Replace if candidate is better
            # -----------------------------------------------

            if candidate_key < existing_key:

                best_matches[
                    nearest_order
                ] = candidate

    # ========================================================
    # Convert to result list
    # ========================================================

    results = []

    for order_number in sorted(
        best_matches.keys()
    ):

        item = best_matches[
            order_number
        ]

        # Remove internal fields

        item.pop(
            "_relative_order_error",
            None
        )

        item.pop(
            "_amplitude",
            None
        )

        results.append(
            item
        )

    return results


# ============================================================
# CALCULATE ALL ORDERS
# ============================================================

def calculate_orders(
    rpm: float,
    max_order: int = 10
):
    """
    تولید فرکانس مرجع Orderها.
    """

    if rpm is None or rpm <= 0:
        return {}

    one_x = rpm_to_hz(rpm)

    return {
        f"{order}X": {
            "hz": one_x * order,
            "rpm": rpm * order
        }
        for order in range(
            1,
            max_order + 1
        )
    }