from engine.fft_image import FFTImageExtractor
from engine.frequency_engine import analyze_orders
from engine.fault_evidence import build_fault_evidence
from engine.fault_features import build_fault_features

import matplotlib.pyplot as plt


# ============================================================
# CONFIG
# ============================================================

IMAGE_PATH = "test_fft.png"
RPM = 1500


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# PLOT SPECTRUM
# ============================================================

def plot_extracted_spectrum(spectrum):
    """
    نمایش خروجی واقعی FFTImageExtractor.

    X = Frequency (Hz)
    Y = Amplitude

    خط:
        منحنی بازسازی‌شده

    نقاط:
        Peakهای تشخیص داده‌شده
    """

    frequencies = [
        safe_float(x)
        for x in spectrum.frequency_hz
    ]

    amplitudes = [
        safe_float(y)
        for y in spectrum.amplitude
    ]

    peaks = spectrum.peaks

    if not frequencies or not amplitudes:

        print()
        print("[PLOT] No spectrum data available.")

        return

    # ========================================================
    # FIGURE
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(18, 9)
    )

    # ========================================================
    # RECONSTRUCTED SPECTRUM
    # ========================================================

    ax.plot(
        frequencies,
        amplitudes,
        linewidth=1.4,
        label="Reconstructed Spectrum",
        zorder=2
    )

    # ========================================================
    # DETECTED PEAKS
    # ========================================================

    if peaks:

        peak_x = []
        peak_y = []

        for peak in peaks:

            x = safe_float(
                peak.frequency_hz
            )

            y = safe_float(
                peak.amplitude
            )

            peak_x.append(x)
            peak_y.append(y)

        # ----------------------------------------------------
        # Peak markers
        # ----------------------------------------------------

        ax.scatter(
            peak_x,
            peak_y,
            s=55,
            zorder=10,
            label=f"Detected Peaks ({len(peaks)})"
        )

        # ----------------------------------------------------
        # Peak labels
        # ----------------------------------------------------

        for index, peak in enumerate(
            peaks,
            start=1
        ):

            x = safe_float(
                peak.frequency_hz
            )

            y = safe_float(
                peak.amplitude
            )

            ax.annotate(
                f"{index}: {x:.2f}",
                xy=(x, y),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=45
            )

    else:

        ax.text(
            0.5,
            0.95,
            "NO PEAKS DETECTED",
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=12
        )

    # ========================================================
    # AXES
    # ========================================================

    ax.set_xlabel(
        "Frequency (Hz)",
        fontsize=13
    )

    ax.set_ylabel(
        "Amplitude",
        fontsize=13
    )

    # ========================================================
    # TITLE
    # ========================================================

    ax.set_title(
        "FFT Image → Reconstructed Spectrum + Detected Peaks",
        fontsize=15
    )

    # ========================================================
    # GRID
    # ========================================================

    ax.grid(
        True,
        alpha=0.25
    )

    # ========================================================
    # LEGEND
    # ========================================================

    ax.legend()

    # ========================================================
    # LIMITS
    # ========================================================

    if frequencies:

        ax.set_xlim(
            min(frequencies),
            max(frequencies)
        )

    # ========================================================
    # LAYOUT
    # ========================================================

    plt.tight_layout()

    # ========================================================
    # SHOW
    # ========================================================

    plt.show()


# ============================================================
# DIAGNOSTIC INTERPRETATION
# ============================================================

def diagnose_faults(features):

    harmonic = features.get(
        "harmonic_features",
        {}
    )

    fundamental = features.get(
        "fundamental",
        {}
    )

    ratios = features.get(
        "order_ratios",
        {}
    )

    present_orders = harmonic.get(
        "present_orders",
        []
    )

    harmonic_count = len(
        present_orders
    )

    highest_order = safe_float(
        harmonic.get(
            "highest_order",
            0
        )
    )

    dominant_order = fundamental.get(
        "dominant_order",
        None
    )

    fundamental_amplitude = safe_float(
        fundamental.get(
            "fundamental_amplitude",
            0
        )
    )

    dominant_amplitude = safe_float(
        fundamental.get(
            "dominant_amplitude",
            0
        )
    )

    ratio_2x_1x = safe_float(
        ratios.get(
            "2X_to_1X",
            0
        )
    )

    ratio_3x_1x = safe_float(
        ratios.get(
            "3X_to_1X",
            0
        )
    )

    observations = []

    possible_mechanisms = []

    # ========================================================
    # OBSERVED PATTERN
    # ========================================================

    if harmonic_count >= 4:

        observations.append(
            "Multiple running-speed harmonics are present."
        )

    if 2 in present_orders:

        observations.append(
            "A significant 2X component is present."
        )

    if 3 in present_orders:

        observations.append(
            "A 3X component is present."
        )

    if dominant_order == "3X":

        observations.append(
            "3X is the dominant running-speed order."
        )

    if highest_order >= 5:

        observations.append(
            f"Harmonic content extends to "
            f"{int(highest_order)}X."
        )

    if (
        fundamental_amplitude > 0
        and dominant_amplitude > 0
    ):

        dominant_to_1x = (
            dominant_amplitude
            / fundamental_amplitude
        )

        if dominant_to_1x >= 2.0:

            observations.append(
                "Higher-order energy is substantially "
                "stronger than 1X."
            )

    # ========================================================
    # MISALIGNMENT
    # ========================================================

    if (
        1 in present_orders
        and 2 in present_orders
        and ratio_2x_1x >= 0.5
    ):

        possible_mechanisms.append(
            "Misalignment-compatible harmonic pattern"
        )

    # ========================================================
    # LOOSENESS
    # ========================================================

    if (
        harmonic_count >= 4
        and highest_order >= 4
    ):

        possible_mechanisms.append(
            "Mechanical-looseness-compatible "
            "harmonic pattern"
        )

    # ========================================================
    # UNBALANCE
    # ========================================================

    if (
        dominant_order == "1X"
        and harmonic_count <= 3
    ):

        possible_mechanisms.append(
            "Unbalance-compatible "
            "1X-dominant pattern"
        )

    # ========================================================
    # FALLBACK
    # ========================================================

    if not possible_mechanisms:

        possible_mechanisms.append(
            "Other running-speed harmonic mechanism"
        )

    # ========================================================
    # INTERPRETATION
    # ========================================================

    if (
        dominant_order is not None
        and harmonic_count >= 4
    ):

        interpretation = (
            "Multiple-harmonic mechanical pattern"
        )

    elif dominant_order == "1X":

        interpretation = (
            "1X-dominant rotational pattern"
        )

    else:

        interpretation = (
            "Non-unique vibration pattern"
        )

    return {

        "interpretation":
            interpretation,

        "observations":
            observations,

        "possible_mechanisms":
            possible_mechanisms,

        "dominant_order":
            dominant_order,

        "harmonic_count":
            harmonic_count,

        "highest_order":
            highest_order,

        "2X_to_1X":
            ratio_2x_1x,

        "3X_to_1X":
            ratio_3x_1x,
    }


# ============================================================
# IMAGE → SPECTRUM
# ============================================================

print()
print("=" * 75)
print("IMAGE → SPECTRUM")
print("=" * 75)


# ============================================================
# CREATE EXTRACTOR ONLY ONCE
# ============================================================

extractor = FFTImageExtractor(
    IMAGE_PATH
)


# ============================================================
# CREATE SPECTRUM
# ============================================================

try:

    spectrum = (
        extractor.create_spectrum_from_image(
            rpm=RPM,
            machine_name="Test Machine",
            measurement_point="Motor DE",
            direction="Horizontal"
        )
    )

except Exception as e:

    import traceback

    print()
    print("=" * 75)
    print("!!! CREATE SPECTRUM ERROR !!!")
    print("=" * 75)

    print()
    print("Exception Type:")
    print(type(e).__name__)

    print()
    print("Exception Message:")
    print(str(e))

    print()
    print("FULL TRACEBACK:")
    print("-" * 75)

    traceback.print_exc()

    print()
    print("=" * 75)

    raise


# ============================================================
# PRINT SPECTRUM
# ============================================================

print()
print(
    f"{'Frequency (Hz)':<20}"
    f"{'Amplitude':<20}"
)

print("-" * 40)


for peak in spectrum.peaks:

    print(
        f"{peak.frequency_hz:<20.3f}"
        f"{peak.amplitude:<20.2f}"
    )


# ============================================================
# 2D PLOT
# ============================================================

print()
print("=" * 75)
print("2D SPECTRUM PLOT")
print("=" * 75)

print()
print(
    f"Total reconstructed points : "
    f"{len(spectrum.frequency_hz)}"
)

print(
    f"Detected peaks             : "
    f"{len(spectrum.peaks)}"
)

print()
print("Opening plot...")

plot_extracted_spectrum(
    spectrum
)


# ============================================================
# ORDER ANALYSIS
# ============================================================

print()
print("=" * 75)
print("ORDER ANALYSIS")
print("=" * 75)


orders = analyze_orders(
    spectrum.peaks,
    rpm=RPM,
    max_order=10,
    rpm_tolerance=10,
    percent_tolerance=3.0
)


for item in orders:

    peak = item.get(
        "peak",
        {}
    )

    match = item.get(
        "match",
        {}
    )

    frequency = safe_float(
        peak.get(
            "frequency_hz",
            0
        )
    )

    estimated_order = safe_float(
        match.get(
            "estimated_order",
            0
        )
    )

    order_error = safe_float(
        match.get(
            "order_error",
            0
        )
    )

    confidence = safe_float(
        match.get(
            "confidence",
            0
        )
    )

    matched = match.get(
        "matched",
        False
    )

    order_number = int(
        round(
            estimated_order
        )
    )

    order_name = (
        f"{order_number}X"
    )

    print(
        f"{frequency:.3f} Hz"
        f" → {order_name}"
        f" | estimated={estimated_order:.4f}X"
        f" | error={order_error:.4f}"
        f" | confidence={confidence:.3f}"
        f" | matched={matched}"
    )


# ============================================================
# FAULT EVIDENCE
# ============================================================

print()
print("=" * 75)
print("FAULT EVIDENCE")
print("=" * 75)


evidence = build_fault_evidence(
    orders,
    rpm=RPM,
    max_order=10
)


order_map = evidence.get(
    "order_map",
    {}
)


for order_name, data in order_map.items():

    frequency = safe_float(
        data.get(
            "frequency_hz",
            0
        )
    )

    amplitude = safe_float(
        data.get(
            "amplitude",
            0
        )
    )

    relative = safe_float(
        data.get(
            "relative_amplitude",
            0
        )
    )

    confidence = safe_float(
        data.get(
            "confidence",
            0
        )
    )

    print(
        f"{order_name:<5}"
        f" freq={frequency:<10.3f}"
        f" amp={amplitude:<10.2f}"
        f" relative={relative:.3f}"
        f" confidence={confidence:.3f}"
    )


# ============================================================
# HARMONICS
# ============================================================

harmonics = evidence.get(
    "harmonics",
    {}
)


print()
print(
    f"Present Orders : "
    f"{harmonics.get('present_orders', [])}"
)

print(
    f"Missing Orders : "
    f"{harmonics.get('missing_orders', [])}"
)

print(
    f"Harmonic Count : "
    f"{harmonics.get('harmonic_count', 0)}"
)

print(
    f"Highest Order  : "
    f"{harmonics.get('highest_order', 0)}"
)


# ============================================================
# RATIOS
# ============================================================

ratios = evidence.get(
    "ratios",
    {}
)


print()
print("Order Ratios")
print("-" * 40)


for name, value in ratios.items():

    print(
        f"{name:<25}: "
        f"{safe_float(value):.4f}"
    )


# ============================================================
# PROMINENCE
# ============================================================

prominence = evidence.get(
    "prominence",
    {}
)


print()
print("Prominence")
print("-" * 40)


print(
    f"Max Prominence : "
    f"{safe_float(prominence.get('max_prominence', 0)):.3f}"
)

print(
    f"Dominant Order : "
    f"{prominence.get('dominant_order')}"
)

print(
    f"Prominence Sum : "
    f"{safe_float(prominence.get('prominence_sum', 0)):.3f}"
)


# ============================================================
# DOMINANT ORDERS
# ============================================================

dominant_orders = evidence.get(
    "dominant_orders",
    []
)


print()
print("Dominant Orders")
print("-" * 40)


for item in dominant_orders:

    order_name = item.get(
        "order",
        "?"
    )

    amplitude = safe_float(
        item.get(
            "amplitude",
            0
        )
    )

    frequency = safe_float(
        item.get(
            "frequency_hz",
            0
        )
    )

    confidence = safe_float(
        item.get(
            "confidence",
            0
        )
    )

    print(
        f"{order_name:<5}"
        f" Amplitude={amplitude:<10.2f}"
        f" Frequency={frequency:<10.3f}"
        f" Confidence={confidence:.3f}"
    )


# ============================================================
# EVIDENCE SUMMARY
# ============================================================

print()
print("Evidence Summary")
print("-" * 40)


print(
    f"RPM                : "
    f"{RPM}"
)

print(
    f"Matched Peaks      : "
    f"{evidence.get('total_matched_peaks', 0)}"
)

print(
    f"Total Amplitude    : "
    f"{safe_float(evidence.get('total_amplitude', 0)):.3f}"
)

print(
    f"Average Confidence : "
    f"{safe_float(evidence.get('average_confidence', 0)):.3f}"
)


# ============================================================
# FAULT FEATURES
# ============================================================

print()
print("=" * 75)
print("FAULT FEATURES")
print("=" * 75)


features = build_fault_features(
    evidence,
    max_order=10
)


fundamental = features.get(
    "fundamental",
    {}
)


print()
print(
    f"Fundamental Amplitude : "
    f"{safe_float(fundamental.get('fundamental_amplitude', 0))}"
)

print(
    f"Dominant Order        : "
    f"{fundamental.get('dominant_order')}"
)

print(
    f"Dominant Amplitude    : "
    f"{safe_float(fundamental.get('dominant_amplitude', 0))}"
)

print(
    f"Dominant Relative     : "
    f"{safe_float(fundamental.get('dominant_relative', 0)):.3f}"
)


# ============================================================
# FEATURE RATIOS
# ============================================================

feature_ratios = features.get(
    "order_ratios",
    {}
)


print()
print("Order Ratios")
print("-" * 40)


for name, value in feature_ratios.items():

    print(
        f"{name:<25}: "
        f"{safe_float(value):.4f}"
    )


# ============================================================
# HARMONIC FEATURES
# ============================================================

harmonic_features = features.get(
    "harmonic_features",
    {}
)


print()
print("Harmonic Features")
print("-" * 40)


print(
    f"Present Orders       : "
    f"{harmonic_features.get('present_orders', [])}"
)

print(
    f"Missing Orders       : "
    f"{harmonic_features.get('missing_orders', [])}"
)

print(
    f"Harmonic Count       : "
    f"{harmonic_features.get('harmonic_count', 0)}"
)

print(
    f"Highest Order        : "
    f"{harmonic_features.get('highest_order', 0)}"
)

print(
    f"Odd Orders           : "
    f"{harmonic_features.get('odd_orders', [])}"
)

print(
    f"Even Orders          : "
    f"{harmonic_features.get('even_orders', [])}"
)

print(
    f"Odd Amplitude        : "
    f"{safe_float(harmonic_features.get('odd_amplitude', 0)):.3f}"
)

print(
    f"Even Amplitude       : "
    f"{safe_float(harmonic_features.get('even_amplitude', 0)):.3f}"
)

print(
    f"Odd / Even Ratio     : "
    f"{safe_float(harmonic_features.get('odd_even_ratio', 0)):.4f}"
)

print(
    f"Low Order Amplitude  : "
    f"{safe_float(harmonic_features.get('low_order_amplitude', 0)):.3f}"
)

print(
    f"Mid Order Amplitude  : "
    f"{safe_float(harmonic_features.get('mid_order_amplitude', 0)):.3f}"
)

print(
    f"High Order Amplitude : "
    f"{safe_float(harmonic_features.get('high_order_amplitude', 0)):.3f}"
)

print(
    f"High / Low Ratio     : "
    f"{safe_float(harmonic_features.get('high_low_ratio', 0)):.4f}"
)


# ============================================================
# ENERGY FEATURES
# ============================================================

energy_features = features.get(
    "energy_features",
    {}
)


print()
print("Energy Features")
print("-" * 40)


print(
    f"Total Amplitude      : "
    f"{safe_float(energy_features.get('total_amplitude', 0)):.3f}"
)

print(
    f"Mean Amplitude       : "
    f"{safe_float(energy_features.get('mean_amplitude', 0)):.3f}"
)

print(
    f"Maximum Amplitude    : "
    f"{safe_float(energy_features.get('maximum_amplitude', 0)):.3f}"
)

print(
    f"Amplitude Spread     : "
    f"{safe_float(energy_features.get('amplitude_spread', 0)):.3f}"
)


# ============================================================
# CONFIDENCE FEATURES
# ============================================================

confidence_features = features.get(
    "confidence_features",
    {}
)


print()
print("Confidence Features")
print("-" * 40)


print(
    f"Average Confidence  : "
    f"{safe_float(confidence_features.get('average_confidence', 0)):.3f}"
)

print(
    f"Minimum Confidence  : "
    f"{safe_float(confidence_features.get('minimum_confidence', 0)):.3f}"
)

print(
    f"Maximum Confidence  : "
    f"{safe_float(confidence_features.get('maximum_confidence', 0)):.3f}"
)


# ============================================================
# DIAGNOSTIC INTERPRETATION
# ============================================================

diagnosis = diagnose_faults(
    features
)


print()
print("=" * 75)
print("DIAGNOSTIC INTERPRETATION")
print("=" * 75)


print()
print("Observed Pattern")
print("-" * 75)


print(
    f"Dominant Order       : "
    f"{diagnosis['dominant_order']}"
)

print(
    f"Harmonic Count       : "
    f"{diagnosis['harmonic_count']}"
)

print(
    f"Highest Order        : "
    f"{int(diagnosis['highest_order'])}X"
)

print(
    f"2X / 1X              : "
    f"{diagnosis['2X_to_1X']:.3f}"
)

print(
    f"3X / 1X              : "
    f"{diagnosis['3X_to_1X']:.3f}"
)


print()
print("Pattern Characteristics")
print("-" * 75)


for observation in diagnosis[
    "observations"
]:

    print(
        f"✓ {observation}"
    )


print()
print("Interpretation")
print("-" * 75)


print(
    diagnosis[
        "interpretation"
    ]
)


print()
print(
    "Possible mechanisms requiring "
    "additional evidence:"
)


for mechanism in diagnosis[
    "possible_mechanisms"
]:

    print(
        f"• {mechanism}"
    )


print()
print(
    "Current FFT evidence is not sufficient "
    "to uniquely confirm a single fault mechanism."
)


# ============================================================
# END
# ============================================================

print()
print("=" * 75)
print("END OF ANALYSIS")
print("=" * 75)