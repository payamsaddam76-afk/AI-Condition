import numpy as np
from scipy.signal import find_peaks, savgol_filter

from .spectrum import Spectrum, Peak


def detect_peaks(
    spectrum: Spectrum,
    prominence_percent: float = 5.0,
    min_distance_hz: float = 0.0,
    smoothing: bool = True,
):
    """
    استخراج پیک‌های FFT

    prominence_percent:
        حداقل prominence نسبت به بیشترین دامنه

    min_distance_hz:
        حداقل فاصله بین دو پیک بر حسب Hz
    """

    spectrum.validate()

    freq = np.asarray(spectrum.frequency_hz, dtype=float)
    amp = np.asarray(spectrum.amplitude, dtype=float)

    # حذف مقادیر نامعتبر
    mask = np.isfinite(freq) & np.isfinite(amp)

    freq = freq[mask]
    amp = amp[mask]

    if len(freq) < 3:
        return []

    # مرتب‌سازی بر اساس Frequency
    order = np.argsort(freq)

    freq = freq[order]
    amp = amp[order]

    # smoothing
    if smoothing and len(amp) >= 11:
        window = min(21, len(amp))

        if window % 2 == 0:
            window -= 1

        if window >= 5:
            try:
                amp_for_detection = savgol_filter(
                    amp,
                    window_length=window,
                    polyorder=2
                )
            except Exception:
                amp_for_detection = amp
        else:
            amp_for_detection = amp
    else:
        amp_for_detection = amp

    max_amp = np.max(np.abs(amp_for_detection))

    if max_amp <= 0:
        return []

    prominence = max_amp * (prominence_percent / 100)

    # تبدیل min_distance_hz به تعداد sample
    distance_samples = 1

    if min_distance_hz > 0 and len(freq) > 1:

        resolution = np.median(np.diff(freq))

        if resolution > 0:
            distance_samples = max(
                1,
                int(min_distance_hz / resolution)
            )

    indices, properties = find_peaks(
        amp_for_detection,
        prominence=prominence,
        distance=distance_samples
    )

    peaks = []

    for i, idx in enumerate(indices):

        peaks.append(
            Peak(
                frequency_hz=float(freq[idx]),
                amplitude=float(amp[idx]),
                prominence=float(
                    properties["prominences"][i]
                ),
                source=spectrum.source
            )
        )

    # بزرگ‌ترین پیک‌ها اول
    peaks.sort(
        key=lambda p: p.amplitude,
        reverse=True
    )

    spectrum.peaks = peaks

    return peaks