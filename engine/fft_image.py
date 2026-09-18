# engine/fft_image.py

from __future__ import annotations

import os
from typing import Optional, List, Tuple, Dict, Any

import cv2
import numpy as np
import matplotlib.pyplot as plt

from .spectrum import Spectrum, Peak
from .axis_detector import FFTAxisDetector


# ============================================================
# UTILITIES
# ============================================================

def _safe_float(v, default=0.0):
    try:
        a = np.asarray(v)

        if a.size == 0:
            return float(default)

        return float(a.reshape(-1)[0])

    except Exception:
        return float(default)


def _normalize(v):
    v = np.asarray(v, dtype=np.float32)

    if v.size == 0:
        return v

    finite = np.isfinite(v)

    if not np.any(finite):
        return np.zeros_like(v)

    values = v[finite]

    mn = float(np.min(values))
    mx = float(np.max(values))

    if mx - mn < 1e-9:
        return np.zeros_like(v)

    out = (v - mn) / (mx - mn)

    return np.clip(
        out,
        0.0,
        1.0,
    ).astype(np.float32)


def _robust_normalize(v, low=2.0, high=98.0):
    v = np.asarray(v, dtype=np.float32)

    if v.size == 0:
        return v

    finite = np.isfinite(v)

    if not np.any(finite):
        return np.zeros_like(v)

    values = v[finite]

    lo = float(np.percentile(values, low))
    hi = float(np.percentile(values, high))

    if hi - lo < 1e-9:
        return np.zeros_like(v)

    out = (v - lo) / (hi - lo)

    return np.clip(
        out,
        0.0,
        1.0,
    ).astype(np.float32)


def _mad(x):
    x = np.asarray(x, dtype=np.float32)

    if x.size == 0:
        return 0.0

    finite = np.isfinite(x)

    if not np.any(finite):
        return 0.0

    x = x[finite]

    med = np.median(x)

    return float(
        np.median(
            np.abs(x - med)
        )
    )


# ============================================================
# FFT IMAGE EXTRACTOR
# ============================================================

class FFTImageExtractor:

    def __init__(
        self,
        image_path: Optional[str] = None,
        debug: bool = True,
        debug_dir: Optional[str] = None,
    ):

        self.image_path = image_path
        self.debug = bool(debug)

        if debug_dir is None:

            if image_path:

                folder = os.path.dirname(
                    os.path.abspath(
                        image_path
                    )
                )

            else:

                folder = os.getcwd()

            debug_dir = os.path.join(
                folder,
                "_debug",
            )

        self.debug_dir = debug_dir

        if self.debug:

            os.makedirs(
                self.debug_dir,
                exist_ok=True,
            )

    # ========================================================
    # PUBLIC
    # ========================================================

    def extract(
        self,
        image_path: Optional[str] = None,
        rpm: Optional[float] = None,
        debug: Optional[bool] = None,
        *,
        machine_name: Optional[str] = None,
        measurement_point: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> Spectrum:

        if image_path is None:
            image_path = self.image_path

        if image_path is None:
            raise ValueError(
                "image_path مشخص نشده است."
            )

        self.image_path = image_path

        if debug is not None:
            self.debug = bool(debug)

        if self.debug:

            self.debug_dir = os.path.join(
                os.path.dirname(
                    os.path.abspath(
                        image_path
                    )
                ),
                "_debug",
            )

            os.makedirs(
                self.debug_dir,
                exist_ok=True,
            )

        # ====================================================
        # READ IMAGE
        # ====================================================

        image = cv2.imread(
            image_path,
            cv2.IMREAD_COLOR,
        )

        if image is None:

            raise FileNotFoundError(
                f"تصویر قابل خواندن نیست:\n{image_path}"
            )

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        height, width = gray.shape

        # ====================================================
        # X AXIS
        #
        # RPM IS DELIBERATELY NOT USED HERE.
        # ====================================================

        axis_detector = FFTAxisDetector(
            image_path
        )

        axis_result = axis_detector.analyze(
            rpm=None
        )

        x1 = int(
            round(
                _safe_float(
                    getattr(
                        axis_result,
                        "pixel_x1",
                        0,
                    ),
                    0,
                )
            )
        )

        x2 = int(
            round(
                _safe_float(
                    getattr(
                        axis_result,
                        "pixel_x2",
                        width - 1,
                    ),
                    width - 1,
                )
            )
        )

        axis_y = int(
            round(
                _safe_float(
                    getattr(
                        axis_result,
                        "x_axis_y",
                        height - 1,
                    ),
                    height - 1,
                )
            )
        )

        x1 = int(
            np.clip(
                x1,
                0,
                width - 1,
            )
        )

        x2 = int(
            np.clip(
                x2,
                0,
                width - 1,
            )
        )

        axis_y = int(
            np.clip(
                axis_y,
                0,
                height - 1,
            )
        )

        if x2 <= x1:

            raise ValueError(
                "X-axis range نامعتبر است."
            )

        print(
            "[FFTImageExtractor] "
            f"EXACT Chart X range: "
            f"{x1} -> {x2}"
        )

        print(
            "[FFTImageExtractor] "
            f"X unit: "
            f"{getattr(axis_result, 'unit', '')}"
        )

        if self.debug:

            self._save_x_axis_debug(
                image,
                x1,
                x2,
                axis_y,
                axis_result,
            )

        # ====================================================
        # Y AXIS
        #
        # IMPORTANT:
        # Y IS CALIBRATED IN GLOBAL IMAGE COORDINATES.
        # ====================================================

        y_info = self._detect_y_axis(
            gray=gray,
            image=image,
            x1=x1,
            x2=x2,
            axis_y=axis_y,
        )

        y_top = int(
            y_info["y_top"]
        )

        y_bottom = int(
            y_info["y_bottom"]
        )

        print(
            "[FFTImageExtractor] "
            f"Chart ROI: "
            f"({x1},{y_top}) -> "
            f"({x2},{y_bottom})"
        )

        print(
            "[FFTImageExtractor] "
            f"Y calibration: "
            f"slope={y_info['slope']:.8f}, "
            f"intercept={y_info['intercept']:.6f}, "
            f"confidence={y_info['confidence']:.1f}"
        )

        if self.debug:

            self._save_y_debug(
                image,
                x1,
                x2,
                axis_y,
                y_info,
            )

        # ====================================================
        # ROI
        # ====================================================

        roi_gray = gray[
            y_top:y_bottom + 1,
            x1:x2 + 1
        ].copy()

        roi_color = image[
            y_top:y_bottom + 1,
            x1:x2 + 1
        ].copy()

        if roi_gray.size == 0:

            raise ValueError(
                "ROI خالی است."
            )

        if roi_gray.shape[0] < 10:

            raise ValueError(
                "ارتفاع Chart ROI بسیار کم است."
            )

        if roi_gray.shape[1] < 10:

            raise ValueError(
                "عرض Chart ROI بسیار کم است."
            )

        if self.debug:

            self._save_original_roi_debug(
                roi_color
            )

        # ====================================================
        # CURVE EVIDENCE
        # ====================================================

        evidence_data = (
            self._build_curve_evidence(
                roi_gray,
                roi_color,
            )
        )

        evidence = (
            evidence_data["combined"]
        )

        if self.debug:

            self._save_evidence_debug(
                roi_gray,
                evidence,
            )

            self._save_color_debug(
                evidence_data
            )

            self._save_edge_debug(
                evidence_data
            )

        # ====================================================
        # RECONSTRUCT FULL CURVE
        # ====================================================

        trace = self._reconstruct_curve(
            roi_gray=roi_gray,
            roi_color=roi_color,
            evidence_data=evidence_data,
        )

        trace = self._repair_trace(
            trace,
            evidence,
        )

        # ====================================================
        # REAL GEOMETRIC AMPLITUDE RECOVERY
        # ====================================================

        trace = (
            self._recover_real_curve_amplitude(
                roi_gray=roi_gray,
                roi_color=roi_color,
                evidence_data=evidence_data,
                trace=trace,
            )
        )

        trace = self._repair_trace(
            trace,
            evidence,
        )

        # ====================================================
        # CONTINUITY / PEAK SUPPORT
        # ====================================================

        continuity_mask, continuity_groups = (
            self._build_continuity_peak_mask(
                roi_gray,
                evidence_data,
                trace,
            )
        )

        if self.debug:

            self._save_continuity_debug(
                continuity_mask
            )

            self._save_continuity_new_debug(
                image,
                x1,
                x2,
                y_top,
                y_bottom,
                continuity_mask,
            )

        print(
            "[FFTImageExtractor] "
            f"continuity pixels: "
            f"{int(np.sum(continuity_mask > 0))}"
        )

        print(
            "[FFTImageExtractor] "
            f"continuity groups: "
            f"{len(continuity_groups)}"
        )

        # ====================================================
        # GLOBAL IMAGE TRACE
        # ====================================================

        image_y = (
            trace
            + float(y_top)
        )

        image_y = (
            self._clean_axis_contamination(
                image_y,
                axis_y,
                y_top,
                y_bottom,
            )
        )

        if self.debug:

            self._save_curve_debug(
                image,
                x1,
                x2,
                image_y,
                y_top,
                y_bottom,
            )

        # ====================================================
        # TRACE -> SPECTRUM
        # ====================================================

        spectrum = self._trace_to_spectrum(
            trace=image_y,
            x1=x1,
            x2=x2,
            y_info=y_info,
            axis_result=axis_result,
            rpm=rpm,
            machine_name=machine_name,
            measurement_point=measurement_point,
            direction=direction,
        )

        # ====================================================
        # PEAKS
        # ====================================================

        peaks = self._detect_peaks(
            frequency=spectrum.frequency_hz,
            amplitude=spectrum.amplitude,
            trace=image_y,
            y_info=y_info,
            y_top=y_top,
            y_bottom=y_bottom,
        )

        spectrum.peaks = peaks

        if self.debug:

            self._save_peak_debug(
                image,
                x1,
                x2,
                image_y,
                spectrum,
                peaks,
            )

            plot_extracted_spectrum(
                spectrum,
                save_path=os.path.join(
                    self.debug_dir,
                    "08_spectrum_plot.png",
                ),
                show=False,
            )

        print(
            "[FFTImageExtractor] "
            f"Final reconstructed points: "
            f"{len(spectrum.frequency_hz)}"
        )

        print(
            "[FFTImageExtractor] "
            f"Final peaks: "
            f"{len(peaks)}"
        )

        for p in peaks:

            print(
                f"    "
                f"{p.frequency_hz:.3f} Hz"
                f"    "
                f"{p.amplitude:.3f}"
            )

        return spectrum

    # ========================================================
    # COMPATIBILITY
    # ========================================================

    def create_spectrum_from_image(
        self,
        image_path=None,
        rpm=None,
        debug=None,
        *,
        machine_name=None,
        measurement_point=None,
        direction=None,
    ):

        return self.extract(
            image_path=image_path,
            rpm=rpm,
            debug=debug,
            machine_name=machine_name,
            measurement_point=measurement_point,
            direction=direction,
        )

    # ========================================================
    # Y AXIS DETECTION
    # ========================================================

    def _detect_y_axis(
        self,
        gray,
        image,
        x1,
        x2,
        axis_y,
    ):

        h, w = gray.shape

        # ----------------------------------------------------
        # Search area left of the X-axis.
        # ----------------------------------------------------

        label_left = max(
            0,
            x1 - int(
                max(
                    100,
                    min(
                        260,
                        w * 0.18,
                    ),
                )
            ),
        )

        label_right = min(
            w - 1,
            x1 + 8,
        )

        label_top = max(
            0,
            axis_y - int(
                h * 0.82
            ),
        )

        label_bottom = min(
            h - 1,
            axis_y + 5,
        )

        strip = gray[
            label_top:label_bottom + 1,
            label_left:label_right + 1
        ]

        ocr_pairs = self._ocr_y_labels(
            strip=strip,
            offset_x=label_left,
            offset_y=label_top,
            x_axis_start=x1,
        )

        grid_y = self._detect_horizontal_levels(
            gray=gray,
            x1=x1,
            x2=x2,
            axis_y=axis_y,
        )

        # ----------------------------------------------------
        # Match OCR labels to actual horizontal levels.
        # ----------------------------------------------------

        pairs = []

        for oy, value, right_edge in ocr_pairs:

            if grid_y:

                nearest = min(
                    grid_y,
                    key=lambda gy:
                    abs(
                        gy - oy
                    )
                )

                distance = abs(
                    nearest - oy
                )

                if distance <= max(
                    10,
                    int(
                        h * 0.025
                    ),
                ):

                    gap = (
                        x1
                        - right_edge
                    )

                    if (
                        gap >= -8
                        and
                        gap <= 140
                    ):

                        pairs.append(
                            (
                                float(nearest),
                                float(value),
                                "ocr+grid",
                            )
                        )

            else:

                pairs.append(
                    (
                        float(oy),
                        float(value),
                        "ocr",
                    )
                )

        # ----------------------------------------------------
        # If OCR+grid matching failed, use OCR positions.
        # ----------------------------------------------------

        if len(pairs) < 2:

            pairs = [
                (
                    float(y),
                    float(value),
                    "ocr",
                )
                for y, value, _ in ocr_pairs
            ]

        # ----------------------------------------------------
        # Remove duplicate Y positions.
        # ----------------------------------------------------

        pairs.sort(
            key=lambda z: z[0]
        )

        cleaned_pairs = []

        for item in pairs:

            if not cleaned_pairs:

                cleaned_pairs.append(
                    item
                )

                continue

            previous = cleaned_pairs[
                -1
            ]

            if abs(
                item[0]
                - previous[0]
            ) <= 3:

                # Prefer OCR+grid.
                if (
                    item[2]
                    == "ocr+grid"
                    and
                    previous[2]
                    != "ocr+grid"
                ):

                    cleaned_pairs[-1] = (
                        item
                    )

            else:

                cleaned_pairs.append(
                    item
                )

        pairs = cleaned_pairs

        # ----------------------------------------------------
        # Y calibration.
        # ----------------------------------------------------

        if len(pairs) >= 2:

            ys = np.array(
                [
                    p[0]
                    for p in pairs
                ],
                dtype=np.float64,
            )

            values = np.array(
                [
                    p[1]
                    for p in pairs
                ],
                dtype=np.float64,
            )

            slope, intercept = (
                self._robust_linear_fit(
                    ys,
                    values,
                )
            )

            predicted = (
                slope * ys
                + intercept
            )

            residual = (
                predicted
                - values
            )

            rmse = float(
                np.sqrt(
                    np.mean(
                        residual ** 2
                    )
                )
            )

            value_range = max(
                float(
                    np.ptp(values)
                ),
                1e-9,
            )

            fit_quality = max(
                0.0,
                1.0
                - rmse
                / value_range,
            )

            confidence = min(
                100.0,
                45.0
                + 40.0
                * fit_quality
                + min(
                    15.0,
                    len(pairs) * 2.0,
                ),
            )

        else:

            # ------------------------------------------------
            # Last-resort automatic Y calibration.
            #
            # This is NOT a fixed numerical amplitude.
            # It uses the actual X-axis position and the
            # detected chart levels.
            # ------------------------------------------------

            if grid_y:

                usable = [
                    y
                    for y in grid_y
                    if y < axis_y - 2
                ]

            else:

                usable = []

            if len(usable) >= 2:

                # Without OCR values we cannot know the
                # absolute amplitude scale.
                # Preserve geometric Y and mark confidence low.

                y0 = float(
                    min(usable)
                )

                y1 = float(
                    max(usable)
                )

                slope = -1.0 / max(
                    1.0,
                    y1 - y0,
                )

                intercept = (
                    -slope
                    * y1
                )

                confidence = 15.0

            else:

                # Very low-confidence fallback.
                slope = -1.0
                intercept = float(
                    axis_y
                )
                confidence = 5.0

        # ----------------------------------------------------
        # Determine chart top.
        #
        # Use horizontal levels first.
        # ----------------------------------------------------

        usable_grid = [
            y
            for y in grid_y
            if (
                y < axis_y - 3
                and
                y > 0
            )
        ]

        if usable_grid:

            # The first horizontal level nearest the top
            # is a strong chart boundary candidate.
            top_grid = min(
                usable_grid
            )

            # Do not expand too aggressively.
            y_top = max(
                0,
                int(
                    top_grid - max(
                        2,
                        min(
                            12,
                            int(
                                h * 0.02
                            ),
                        ),
                    )
                ),
            )

        else:

            # Search chart background transitions.
            y_top = self._estimate_chart_top(
                gray,
                x1,
                x2,
                axis_y,
            )

        # ----------------------------------------------------
        # Bottom is intentionally close to X axis but does not
        # include the X-axis line itself.
        # ----------------------------------------------------

        bottom_margin = max(
            3,
            min(
                12,
                int(
                    h * 0.025
                ),
            ),
        )

        y_bottom = max(
            y_top + 20,
            axis_y - bottom_margin,
        )

        y_bottom = min(
            h - 1,
            y_bottom,
        )

        # ----------------------------------------------------
        # Sanity.
        # ----------------------------------------------------

        if y_bottom <= y_top:

            y_top = max(
                0,
                axis_y
                - int(
                    h * 0.65
                ),
            )

            y_bottom = max(
                y_top + 20,
                axis_y - 4,
            )

            y_bottom = min(
                h - 1,
                y_bottom,
            )

        return {
            "pairs": pairs,
            "grid_y": grid_y,
            "slope": float(slope),
            "intercept": float(intercept),
            "confidence": float(confidence),
            "y_top": int(y_top),
            "y_bottom": int(y_bottom),
        }

    # ========================================================
    # ESTIMATE CHART TOP
    # ========================================================

    def _estimate_chart_top(
        self,
        gray,
        x1,
        x2,
        axis_y,
    ):

        h, w = gray.shape

        xa = max(
            0,
            x1,
        )

        xb = min(
            w,
            x2 + 1,
        )

        if xb <= xa:
            return max(
                0,
                axis_y - int(
                    h * 0.65
                ),
            )

        # Use several horizontal bands instead of one line.
        profile = np.mean(
            gray[
                :axis_y,
                xa:xb
            ],
            axis=1,
        )

        if profile.size < 10:

            return max(
                0,
                axis_y - int(
                    h * 0.65
                ),
            )

        smooth = cv2.GaussianBlur(
            profile.astype(
                np.float32
            ).reshape(
                -1,
                1
            ),
            (
                1,
                0
            ),
            0,
        ).reshape(-1)

        # Find first strong change from top.
        derivative = np.abs(
            np.diff(
                smooth
            )
        )

        if derivative.size:

            threshold = np.percentile(
                derivative,
                90,
            )

            candidates = np.where(
                derivative
                >= threshold
            )[0]

            candidates = [
                int(y)
                for y in candidates
                if (
                    y > 5
                    and
                    y < axis_y - 20
                )
            ]

            if candidates:

                candidate = min(
                    candidates
                )

                if candidate < axis_y * 0.7:

                    return max(
                        0,
                        candidate - 5,
                    )

        return max(
            0,
            axis_y
            - int(
                h * 0.65
            ),
        )

    # ========================================================
    # OCR Y LABELS
    # ========================================================

    def _ocr_y_labels(
        self,
        strip,
        offset_x,
        offset_y,
        x_axis_start,
    ):

        result = []

        try:

            import pytesseract

        except Exception:

            return result

        try:

            if strip is None:
                return result

            if strip.size == 0:
                return result

            scale = 4

            up = cv2.resize(
                strip,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )

            # Multiple OCR variants.
            variants = []

            variants.append(
                up
            )

            gray_up = up

            _, bw1 = cv2.threshold(
                gray_up,
                0,
                255,
                cv2.THRESH_BINARY
                + cv2.THRESH_OTSU,
            )

            variants.append(
                bw1
            )

            adaptive = cv2.adaptiveThreshold(
                gray_up,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                5,
            )

            variants.append(
                adaptive
            )

            all_items = []

            for variant in variants:

                data = pytesseract.image_to_data(
                    variant,
                    config=(
                        "--psm 6 "
                        "-c "
                        "tessedit_char_whitelist="
                        "0123456789.-"
                    ),
                    output_type=(
                        pytesseract.Output.DICT
                    ),
                )

                n = len(
                    data.get(
                        "text",
                        []
                    )
                )

                for i in range(n):

                    text = str(
                        data["text"][i]
                    ).strip()

                    if not text:
                        continue

                    text = (
                        text
                        .replace(
                            ",",
                            "",
                        )
                        .replace(
                            " ",
                            "",
                        )
                    )

                    try:

                        value = float(
                            text
                        )

                    except Exception:

                        continue

                    left = (
                        float(
                            data["left"][i]
                        )
                        / scale
                    )

                    top = (
                        float(
                            data["top"][i]
                        )
                        / scale
                    )

                    width = (
                        float(
                            data["width"][i]
                        )
                        / scale
                    )

                    height = (
                        float(
                            data["height"][i]
                        )
                        / scale
                    )

                    abs_left = (
                        offset_x
                        + left
                    )

                    abs_top = (
                        offset_y
                        + top
                    )

                    abs_right = (
                        abs_left
                        + width
                    )

                    center_y = (
                        abs_top
                        + height
                        / 2.0
                    )

                    gap = (
                        x_axis_start
                        - abs_right
                    )

                    if (
                        gap < -8
                        or
                        gap > 140
                    ):
                        continue

                    if (
                        height < 5
                        or
                        height > 50
                    ):
                        continue

                    confidence = _safe_float(
                        data.get(
                            "conf",
                            [0] * n
                        )[i],
                        0,
                    )

                    all_items.append(
                        (
                            center_y,
                            value,
                            abs_right,
                            confidence,
                        )
                    )

            # ------------------------------------------------
            # Deduplicate OCR detections.
            # ------------------------------------------------

            all_items.sort(
                key=lambda x: (
                    x[0],
                    -x[3],
                )
            )

            for item in all_items:

                y, value, right, conf = (
                    item
                )

                duplicate = False

                for old in result:

                    if (
                        abs(
                            old[0]
                            - y
                        ) <= 5
                        and
                        abs(
                            old[1]
                            - value
                        ) <= max(
                            1.0,
                            abs(value) * 0.02,
                        )
                    ):

                        duplicate = True
                        break

                if not duplicate:

                    result.append(
                        (
                            y,
                            value,
                            right,
                        )
                    )

        except Exception:
            return result

        result.sort(
            key=lambda x: x[0]
        )

        return result

    # ========================================================
    # HORIZONTAL LEVELS
    # ========================================================

    def _detect_horizontal_levels(
        self,
        gray,
        x1,
        x2,
        axis_y,
    ):

        h, w = gray.shape

        left = max(
            0,
            x1,
        )

        right = min(
            w - 1,
            x2,
        )

        top = max(
            0,
            axis_y
            - int(
                h * 0.82
            ),
        )

        bottom = max(
            top + 20,
            axis_y - 4,
        )

        roi = gray[
            top:bottom,
            left:right + 1
        ]

        if roi.size == 0:
            return []

        # ----------------------------------------------------
        # Horizontal evidence.
        # ----------------------------------------------------

        u8 = np.asarray(
            roi,
            dtype=np.uint8,
        )

        # Dark structures.
        blackhat = cv2.morphologyEx(
            u8,
            cv2.MORPH_BLACKHAT,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (
                    max(
                        25,
                        roi.shape[1] // 15,
                    ),
                    1,
                ),
            ),
        )

        score1 = np.mean(
            blackhat > 0,
            axis=1,
        )

        # Edge-based horizontal levels.
        edges = cv2.Canny(
            u8,
            30,
            100,
        )

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                max(
                    30,
                    roi.shape[1] // 10,
                ),
                1,
            ),
        )

        horizontal = cv2.morphologyEx(
            edges,
            cv2.MORPH_OPEN,
            horizontal_kernel,
        )

        score2 = np.mean(
            horizontal > 0,
            axis=1,
        )

        score = (
            0.55
            * _normalize(
                score1
            )
            +
            0.45
            * _normalize(
                score2
            )
        )

        # ----------------------------------------------------
        # Candidate horizontal levels.
        # ----------------------------------------------------

        candidates = []

        for y in range(
            2,
            len(score) - 2,
        ):

            local = score[
                y - 2:y + 3
            ]

            if (
                score[y]
                < np.max(local)
            ):
                continue

            if score[y] < 0.12:
                continue

            candidates.append(
                top + y
            )

        # ----------------------------------------------------
        # Cluster neighboring detections.
        # ----------------------------------------------------

        result = []

        for y in candidates:

            if not result:

                result.append(
                    int(y)
                )

                continue

            if abs(
                y
                - result[-1]
            ) <= 5:

                result[-1] = int(
                    round(
                        (
                            result[-1]
                            + y
                        )
                        / 2.0
                    )
                )

            else:

                result.append(
                    int(y)
                )

        # ----------------------------------------------------
        # Keep plausible levels only.
        # ----------------------------------------------------

        result = [
            y
            for y in result
            if (
                y > 0
                and
                y < axis_y
            )
        ]

        return result

    # ========================================================
    # ROBUST LINEAR FIT
    # ========================================================

    def _robust_linear_fit(
        self,
        x,
        y,
    ):

        x = np.asarray(
            x,
            dtype=np.float64,
        )

        y = np.asarray(
            y,
            dtype=np.float64,
        )

        valid = (
            np.isfinite(x)
            &
            np.isfinite(y)
        )

        x = x[valid]
        y = y[valid]

        if len(x) < 2:

            return -1.0, 1.0

        # ----------------------------------------------------
        # Start with ordinary least squares.
        # ----------------------------------------------------

        try:

            p = np.polyfit(
                x,
                y,
                1,
            )

            best_slope = float(
                p[0]
            )

            best_intercept = float(
                p[1]
            )

        except Exception:

            best_slope = -1.0
            best_intercept = 1.0

        # ----------------------------------------------------
        # Iterative robust refinement.
        # ----------------------------------------------------

        for _ in range(8):

            predicted = (
                best_slope * x
                + best_intercept
            )

            residual = (
                y - predicted
            )

            med = float(
                np.median(
                    residual
                )
            )

            mad = _mad(
                residual
            )

            threshold = max(
                2.0,
                3.0 * 1.4826 * mad,
            )

            inliers = (
                np.abs(
                    residual - med
                )
                <= threshold
            )

            if np.sum(inliers) < 2:
                break

            try:

                p = np.polyfit(
                    x[inliers],
                    y[inliers],
                    1,
                )

                new_slope = float(
                    p[0]
                )

                new_intercept = float(
                    p[1]
                )

            except Exception:

                break

            if (
                abs(
                    new_slope
                    - best_slope
                )
                < 1e-10
                and
                abs(
                    new_intercept
                    - best_intercept
                )
                < 1e-8
            ):

                best_slope = (
                    new_slope
                )

                best_intercept = (
                    new_intercept
                )

                break

            best_slope = (
                new_slope
            )

            best_intercept = (
                new_intercept
            )

        return (
            best_slope,
            best_intercept,
        )

    # ========================================================
    # CURVE EVIDENCE
    # ========================================================

    def _build_curve_evidence(
        self,
        roi_gray,
        roi_color,
    ):

        gray = np.asarray(
            roi_gray,
            dtype=np.float32,
        )

        color = np.asarray(
            roi_color,
            dtype=np.uint8,
        )

        h, w = gray.shape

        # ====================================================
        # 1. DARKNESS
        # ====================================================

        local_mean = cv2.GaussianBlur(
            gray,
            (0, 0),
            3.0,
        )

        darkness = np.maximum(
            local_mean - gray,
            0,
        )

        darkness = _robust_normalize(
            darkness,
            5,
            99,
        )

        # ====================================================
        # 2. COLOR / CHROMA
        #
        # Works for colored curves without assuming green.
        # ====================================================

        hsv = cv2.cvtColor(
            color,
            cv2.COLOR_BGR2HSV,
        )

        saturation = (
            hsv[:, :, 1]
            .astype(np.float32)
            / 255.0
        )

        # Chroma difference from neutral gray.
        b = color[
            :, :, 0
        ].astype(
            np.float32
        )

        g = color[
            :, :, 1
        ].astype(
            np.float32
        )

        r = color[
            :, :, 2
        ].astype(
            np.float32
        )

        chroma = np.maximum.reduce(
            [
                np.abs(
                    r - g
                ),
                np.abs(
                    g - b
                ),
                np.abs(
                    r - b
                ),
            ]
        )

        chroma = (
            chroma
            / 255.0
        )

        # Colored-curve evidence.
        color_evidence = (
            0.55 * saturation
            +
            0.45 * chroma
        )

        color_evidence = _normalize(
            color_evidence
        )

        # ====================================================
        # 3. EDGE
        # ====================================================

        gray_u8 = np.clip(
            gray,
            0,
            255,
        ).astype(
            np.uint8
        )

        edges = cv2.Canny(
            gray_u8,
            25,
            100,
        ).astype(
            np.float32
        ) / 255.0

        # ====================================================
        # 4. GRADIENT
        # ====================================================

        gx = cv2.Sobel(
            gray,
            cv2.CV_32F,
            1,
            0,
            ksize=3,
        )

        gy = cv2.Sobel(
            gray,
            cv2.CV_32F,
            0,
            1,
            ksize=3,
        )

        gradient = cv2.magnitude(
            gx,
            gy,
        )

        gradient = _robust_normalize(
            gradient,
            5,
            99,
        )

        # ====================================================
        # 5. VERTICAL EDGE
        #
        # FFT curve normally changes amplitude vertically.
        # Grid lines are mostly horizontal.
        # ====================================================

        vertical_edge = _robust_normalize(
            np.abs(gy),
            5,
            99,
        )

        # ====================================================
        # 6. BLACKHAT
        # ====================================================

        blackhat = cv2.morphologyEx(
            gray_u8,
            cv2.MORPH_BLACKHAT,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (
                    max(
                        5,
                        min(
                            11,
                            w // 100,
                        ),
                    ),
                    max(
                        5,
                        min(
                            11,
                            h // 40,
                        ),
                    ),
                ),
            ),
        ).astype(
            np.float32
        )

        blackhat = _robust_normalize(
            blackhat,
            5,
            99,
        )

        # ====================================================
        # 7. HORIZONTAL GRID PENALTY
        # ====================================================

        horizontal_kernel = (
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (
                    max(
                        21,
                        w // 18,
                    ),
                    1,
                ),
            )
        )

        horizontal = cv2.morphologyEx(
            gray_u8,
            cv2.MORPH_OPEN,
            horizontal_kernel,
        ).astype(
            np.float32
        )

        horizontal = _normalize(
            horizontal
        )

        # ====================================================
        # 8. VERTICAL AXIS / BORDER PENALTY
        # ====================================================

        vertical_kernel = (
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (
                    1,
                    max(
                        15,
                        h // 15,
                    ),
                ),
            )
        )

        vertical = cv2.morphologyEx(
            gray_u8,
            cv2.MORPH_OPEN,
            vertical_kernel,
        ).astype(
            np.float32
        )

        vertical = _normalize(
            vertical
        )

        # ====================================================
        # 9. LOCAL CONTRAST
        # ====================================================

        local_blur = cv2.GaussianBlur(
            gray,
            (0, 0),
            1.5,
        )

        local_contrast = np.abs(
            gray
            - local_blur
        )

        local_contrast = _robust_normalize(
            local_contrast,
            5,
            99,
        )

        # ====================================================
        # COMBINATION
        #
        # Color gets strong evidence, but not enough to destroy
        # grayscale curves.
        # ====================================================

        combined = (
            0.24 * darkness
            +
            0.18 * color_evidence
            +
            0.18 * edges
            +
            0.14 * vertical_edge
            +
            0.10 * gradient
            +
            0.08 * blackhat
            +
            0.08 * local_contrast
        )

        # Remove obvious long horizontal grid structures.
        combined -= (
            0.24 * horizontal
        )

        # Remove obvious long vertical structures.
        combined -= (
            0.10 * vertical
        )

        combined = np.clip(
            combined,
            0,
            1,
        )

        # ====================================================
        # SUPPORT
        #
        # Small blur only provides continuity. It does NOT
        # replace the original evidence.
        # ====================================================

        support = cv2.GaussianBlur(
            combined,
            (
                0,
                0,
            ),
            1.0,
        )

        combined = (
            0.86 * combined
            +
            0.14 * support
        )

        combined = np.clip(
            combined,
            0,
            1,
        ).astype(
            np.float32
        )

        return {
            "combined": combined,
            "darkness": darkness.astype(
                np.float32
            ),
            "color": color_evidence.astype(
                np.float32
            ),
            "edges": edges.astype(
                np.float32
            ),
            "gradient": gradient.astype(
                np.float32
            ),
            "vertical_edge":
                vertical_edge.astype(
                    np.float32
                ),
            "blackhat": blackhat.astype(
                np.float32
            ),
            "horizontal":
                horizontal.astype(
                    np.float32
                ),
            "vertical":
                vertical.astype(
                    np.float32
                ),
            "local_contrast":
                local_contrast.astype(
                    np.float32
                ),
        }

    # ========================================================
    # RECONSTRUCT CURVE
    # ========================================================

    def _reconstruct_curve(
        self,
        roi_gray,
        roi_color,
        evidence_data,
    ):

        ev = np.asarray(
            evidence_data["combined"],
            dtype=np.float32,
        )

        darkness = np.asarray(
            evidence_data["darkness"],
            dtype=np.float32,
        )

        color = np.asarray(
            evidence_data["color"],
            dtype=np.float32,
        )

        vertical_edge = np.asarray(
            evidence_data["vertical_edge"],
            dtype=np.float32,
        )

        h, w = ev.shape

        if h < 5 or w < 5:

            return np.full(
                w,
                h / 2.0,
                dtype=np.float32,
            )

        # ====================================================
        # Candidate generation.
        # ====================================================

        candidates = []

        for x in range(w):

            col = ev[
                :,
                x
            ]

            local_candidates = []

            # Local maxima.
            for y in range(
                1,
                h - 1,
            ):

                value = float(
                    col[y]
                )

                if value < 0.075:
                    continue

                if (
                    value >= col[y - 1]
                    and
                    value >= col[y + 1]
                ):

                    local_candidates.append(
                        (
                            y,
                            value,
                        )
                    )

            # Strongest candidates are always retained.
            order = np.argsort(
                col
            )[::-1]

            for y in order[:25]:

                y = int(y)

                if (
                    y <= 0
                    or
                    y >= h - 1
                ):
                    continue

                if float(
                    col[y]
                ) < 0.065:
                    continue

                if not any(
                    abs(
                        y - old_y
                    ) <= 2
                    for old_y, _
                    in local_candidates
                ):

                    local_candidates.append(
                        (
                            y,
                            float(
                                col[y]
                            ),
                        )
                    )

            # Keep spatially separated candidates.
            local_candidates.sort(
                key=lambda p:
                p[1],
                reverse=True,
            )

            selected = []

            for y, score in local_candidates:

                if all(
                    abs(
                        y - old_y
                    ) >= 2
                    for old_y, _
                    in selected
                ):

                    selected.append(
                        (
                            int(y),
                            float(score),
                        )
                    )

                if len(selected) >= 24:
                    break

            candidates.append(
                selected
            )

        # ====================================================
        # Find good starting trace.
        # ====================================================

        initial = np.full(
            w,
            np.nan,
            dtype=np.float32,
        )

        for x in range(w):

            if candidates[x]:

                # Use combined evidence first.
                initial[x] = float(
                    candidates[x][0][0]
                )

        valid = np.isfinite(
            initial
        )

        if np.sum(valid) < max(
            5,
            w // 20,
        ):

            # Global column maximum fallback.
            for x in range(w):

                y = int(
                    np.argmax(
                        ev[
                            :,
                            x
                        ]
                    )
                )

                initial[x] = float(
                    y
                )

            valid = np.ones(
                w,
                dtype=bool,
            )

        xx = np.arange(w)

        initial[~valid] = np.interp(
            xx[~valid],
            xx[valid],
            initial[valid],
        )

        # ====================================================
        # Candidate score.
        # ====================================================

        def score_candidate(
            x,
            y,
            previous_y,
            previous_dy,
        ):

            yy = int(
                np.clip(
                    round(y),
                    0,
                    h - 1,
                )
            )

            evidence_score = float(
                ev[
                    yy,
                    x
                ]
            )

            darkness_score = float(
                darkness[
                    yy,
                    x
                ]
            )

            color_score = float(
                color[
                    yy,
                    x
                ]
            )

            edge_score = float(
                vertical_edge[
                    yy,
                    x
                ]
            )

            dy = (
                float(y)
                - previous_y
            )

            abs_dy = abs(
                dy
            )

            score = (
                5.0
                * evidence_score
                +
                1.15
                * darkness_score
                +
                0.85
                * color_score
                +
                0.90
                * edge_score
            )

            # Continuity.
            if abs_dy <= 2:

                score += 1.5

            elif abs_dy <= 5:

                score += 1.1

            elif abs_dy <= 10:

                score += 0.55

            elif abs_dy <= 20:

                score -= (
                    0.025
                    * (
                        abs_dy
                        - 10
                    )
                )

            else:

                score -= (
                    0.045
                    * min(
                        abs_dy - 20,
                        45,
                    )
                )

            # Curvature.
            curvature = abs(
                dy
                - previous_dy
            )

            if curvature <= 4:

                score += 0.35

            elif curvature <= 10:

                score += 0.15

            else:

                score -= (
                    0.008
                    * min(
                        curvature,
                        50,
                    )
                )

            # ------------------------------------------------
            # Important:
            # A strong, narrow peak is allowed to make a large
            # vertical move.
            # ------------------------------------------------

            if abs_dy > 10:

                x0 = max(
                    0,
                    x - 3,
                )

                x1 = min(
                    w,
                    x + 4,
                )

                y0 = max(
                    0,
                    yy - 5,
                )

                y1 = min(
                    h,
                    yy + 6,
                )

                neighborhood = ev[
                    y0:y1,
                    x0:x1
                ]

                if neighborhood.size:

                    local_max = float(
                        np.max(
                            neighborhood
                        )
                    )

                    local_mean = float(
                        np.mean(
                            neighborhood
                        )
                    )

                    peak_support = (
                        0.65
                        * local_max
                        +
                        0.35
                        * local_mean
                    )

                    if (
                        evidence_score
                        >= 0.24
                        and
                        peak_support
                        >= 0.22
                    ):

                        score += (
                            1.8
                            +
                            2.5
                            * peak_support
                        )

            return score

        # ====================================================
        # Bidirectional tracking.
        # ====================================================

        seed_xs = np.linspace(
            0,
            w - 1,
            min(
                120,
                max(
                    30,
                    w // 10,
                ),
            ),
        ).astype(
            int
        )

        best_trace = None
        best_score = -1e30

        for sx in seed_xs:

            if not candidates[sx]:
                continue

            for sy, seed_score in candidates[
                sx
            ][:10]:

                trace = np.full(
                    w,
                    np.nan,
                    dtype=np.float32,
                )

                trace[sx] = float(
                    sy
                )

                total = (
                    float(seed_score)
                    * 6.0
                )

                # ------------------------------------------------
                # RIGHT
                # ------------------------------------------------

                current_y = float(
                    sy
                )

                previous_dy = 0.0

                for x in range(
                    sx + 1,
                    w,
                ):

                    cand = candidates[x]

                    if not cand:

                        trace[x] = (
                            current_y
                        )

                        continue

                    best_y = None
                    best_local = -1e30

                    for y, _ in cand:

                        c = score_candidate(
                            x,
                            y,
                            current_y,
                            previous_dy,
                        )

                        if c > best_local:

                            best_local = c
                            best_y = y

                    if best_y is None:

                        trace[x] = (
                            current_y
                        )

                        continue

                    new_dy = (
                        float(best_y)
                        - current_y
                    )

                    trace[x] = float(
                        best_y
                    )

                    current_y = float(
                        best_y
                    )

                    previous_dy = (
                        new_dy
                    )

                    total += (
                        best_local
                    )

                # ------------------------------------------------
                # LEFT
                # ------------------------------------------------

                current_y = float(
                    sy
                )

                previous_dy = 0.0

                for x in range(
                    sx - 1,
                    -1,
                    -1,
                ):

                    cand = candidates[x]

                    if not cand:

                        trace[x] = (
                            current_y
                        )

                        continue

                    best_y = None
                    best_local = -1e30

                    for y, _ in cand:

                        c = score_candidate(
                            x,
                            y,
                            current_y,
                            previous_dy,
                        )

                        if c > best_local:

                            best_local = c
                            best_y = y

                    if best_y is None:

                        trace[x] = (
                            current_y
                        )

                        continue

                    new_dy = (
                        float(best_y)
                        - current_y
                    )

                    trace[x] = float(
                        best_y
                    )

                    current_y = float(
                        best_y
                    )

                    previous_dy = (
                        new_dy
                    )

                    total += (
                        best_local
                    )

                trace = (
                    self._interpolate_nan_trace(
                        trace
                    )
                )

                yi = np.clip(
                    np.rint(
                        trace
                    ).astype(
                        int
                    ),
                    0,
                    h - 1,
                )

                trace_ev = float(
                    np.mean(
                        ev[
                            yi,
                            np.arange(w)
                        ]
                    )
                )

                trace_color = float(
                    np.mean(
                        color[
                            yi,
                            np.arange(w)
                        ]
                    )
                )

                coverage = 1.0

                dy = np.diff(
                    trace
                )

                large_jumps = int(
                    np.sum(
                        np.abs(dy)
                        > 25
                    )
                )

                final_score = (
                    total
                    +
                    150.0
                    * coverage
                    +
                    180.0
                    * trace_ev
                    +
                    50.0
                    * trace_color
                    -
                    0.15
                    * max(
                        0,
                        large_jumps - 20,
                    )
                )

                if (
                    final_score
                    > best_score
                ):

                    best_score = (
                        final_score
                    )

                    best_trace = (
                        trace.copy()
                    )

        if best_trace is None:

            best_trace = initial.copy()

        best_trace = (
            self._interpolate_nan_trace(
                best_trace
            )
        )

        # ====================================================
        # Local evidence correction.
        #
        # Only isolated unsupported jumps are repaired.
        # Real peaks remain untouched.
        # ====================================================

        result = best_trace.copy()

        for x in range(
            2,
            w - 2,
        ):

            a = float(
                result[x - 1]
            )

            b = float(
                result[x]
            )

            c = float(
                result[x + 1]
            )

            if (
                abs(b - a) > 28
                and
                abs(b - c) > 28
            ):

                yy = int(
                    np.clip(
                        round(b),
                        0,
                        h - 1,
                    )
                )

                local_ev = float(
                    ev[
                        yy,
                        x
                    ]
                )

                if local_ev < 0.16:

                    result[x] = (
                        a + c
                    ) / 2.0

        return np.clip(
            result,
            0,
            h - 1,
        ).astype(
            np.float32
        )

    # ========================================================
    # REAL AMPLITUDE RECOVERY
    # ========================================================

    def _recover_real_curve_amplitude(
        self,
        roi_gray,
        roi_color,
        evidence_data,
        trace,
    ):

        gray = np.asarray(
            roi_gray,
            dtype=np.float32,
        )

        color = np.asarray(
            roi_color,
            dtype=np.uint8,
        )

        ev = np.asarray(
            evidence_data["combined"],
            dtype=np.float32,
        )

        darkness = np.asarray(
            evidence_data["darkness"],
            dtype=np.float32,
        )

        color_ev = np.asarray(
            evidence_data["color"],
            dtype=np.float32,
        )

        vertical_edge = np.asarray(
            evidence_data["vertical_edge"],
            dtype=np.float32,
        )

        h, w = gray.shape

        result = np.asarray(
            trace,
            dtype=np.float32,
        ).copy()

        if w < 5 or h < 5:
            return result

        # ====================================================
        # Original-pixel geometric score.
        # ====================================================

        score = (
            0.46 * ev
            +
            0.22 * darkness
            +
            0.18 * color_ev
            +
            0.14 * vertical_edge
        )

        # ====================================================
        # Baseline of geometric trace.
        # ====================================================

        window = max(
            11,
            min(
                101,
                (w // 18) | 1,
            ),
        )

        if window % 2 == 0:
            window += 1

        pad = window // 2

        padded = np.pad(
            result,
            (
                pad,
                pad,
            ),
            mode="edge",
        )

        baseline = np.empty(
            w,
            dtype=np.float32,
        )

        for x in range(w):

            baseline[x] = np.median(
                padded[
                    x:x + window
                ]
            )

        # ====================================================
        # First recovery pass.
        #
        # Do NOT force the candidate to remain near the old
        # trace when evidence clearly shows the actual tip.
        # ====================================================

        recovered = result.copy()

        for x in range(w):

            center = int(
                np.clip(
                    round(
                        float(
                            result[x]
                        )
                    ),
                    1,
                    h - 2,
                )
            )

            radius = max(
                10,
                min(
                    75,
                    int(
                        h * 0.22
                    ),
                ),
            )

            ya = max(
                1,
                center - radius,
            )

            yb = min(
                h - 1,
                center + radius + 1,
            )

            column_score = score[
                ya:yb,
                x
            ]

            if column_score.size < 3:
                continue

            # Local maxima.
            candidates = []

            for i in range(
                1,
                len(column_score) - 1,
            ):

                s = float(
                    column_score[i]
                )

                if s < 0.14:
                    continue

                if (
                    s >= float(
                        column_score[i - 1]
                    )
                    and
                    s >= float(
                        column_score[i + 1]
                    )
                ):

                    candidates.append(
                        (
                            ya + i,
                            s,
                        )
                    )

            if not candidates:
                continue

            candidates.sort(
                key=lambda p:
                p[1],
                reverse=True,
            )

            current_score = float(
                score[
                    center,
                    x
                ]
            )

            best_y = center
            best_value = (
                current_score
            )

            for candidate_y, candidate_score in candidates[
                :16
            ]:

                distance = abs(
                    candidate_y
                    - center
                )

                # Nearby candidate.
                if distance <= 5:

                    continuity_bonus = 0.30

                elif distance <= 12:

                    continuity_bonus = 0.16

                elif distance <= 25:

                    continuity_bonus = 0.05

                else:

                    continuity_bonus = 0.0

                value = (
                    candidate_score
                    +
                    continuity_bonus
                )

                # Strong colored/dark evidence may override
                # the normal continuity penalty.
                if (
                    candidate_score
                    >= 0.35
                ):

                    value += 0.20

                if value > best_value:

                    best_value = value
                    best_y = int(
                        candidate_y
                    )

            recovered[x] = float(
                best_y
            )

        # ====================================================
        # Second pass: explicit narrow peak tip recovery.
        # ====================================================

        final = recovered.copy()

        for x in range(
            2,
            w - 2,
        ):

            left = float(
                recovered[x - 1]
            )

            center = float(
                recovered[x]
            )

            right = float(
                recovered[x + 1]
            )

            neighbor_y = (
                left + right
            ) / 2.0

            # Smaller image Y = higher amplitude.
            narrow_peak_height = (
                neighbor_y
                - center
            )

            if narrow_peak_height < 2.0:
                continue

            # Larger search area specifically for sharp peaks.
            radius = max(
                18,
                min(
                    100,
                    int(
                        h * 0.32
                    ),
                ),
            )

            ya = max(
                1,
                int(
                    min(
                        center,
                        neighbor_y,
                    )
                )
                - radius,
            )

            yb = min(
                h - 1,
                int(
                    max(
                        center,
                        neighbor_y,
                    )
                )
                + 6,
            )

            if yb <= ya:
                continue

            local = score[
                ya:yb,
                x
            ]

            if local.size == 0:
                continue

            best_idx = int(
                np.argmax(
                    local
                )
            )

            candidate_y = (
                ya + best_idx
            )

            candidate_score = float(
                local[
                    best_idx
                ]
            )

            current_y = int(
                np.clip(
                    round(
                        center
                    ),
                    0,
                    h - 1,
                )
            )

            current_score = float(
                score[
                    current_y,
                    x
                ]
            )

            # Local background.
            base = float(
                baseline[x]
            )

            current_excursion = (
                base
                - center
            )

            candidate_excursion = (
                base
                - candidate_y
            )

            improvement = (
                candidate_score
                - current_score
            )

            # ------------------------------------------------
            # Accept actual tip only if there is evidence.
            # ------------------------------------------------

            accept = False

            if (
                candidate_y
                < center - 2
                and
                candidate_score
                >= 0.23
            ):

                if (
                    improvement
                    >= 0.025
                ):

                    accept = True

                elif (
                    candidate_excursion
                    >
                    current_excursion
                    + 4
                    and
                    candidate_score
                    >= 0.27
                ):

                    accept = True

            if accept:

                final[x] = float(
                    candidate_y
                )

        # ====================================================
        # Third pass:
        # Preserve genuine narrow peaks.
        # Only repair isolated unsupported points.
        # ====================================================

        for x in range(
            2,
            w - 2,
        ):

            a = float(
                final[x - 1]
            )

            b = float(
                final[x]
            )

            c = float(
                final[x + 1]
            )

            if (
                abs(b - a) > 32
                and
                abs(b - c) > 32
            ):

                yy = int(
                    np.clip(
                        round(b),
                        0,
                        h - 1,
                    )
                )

                if float(
                    score[
                        yy,
                        x
                    ]
                ) < 0.18:

                    final[x] = (
                        a + c
                    ) / 2.0

        return np.clip(
            final,
            0,
            h - 1,
        ).astype(
            np.float32
        )

    # ========================================================
    # REPAIR
    # ========================================================

    def _repair_trace(
        self,
        trace,
        evidence,
    ):

        trace = np.asarray(
            trace,
            dtype=np.float32,
        ).copy()

        valid = np.isfinite(
            trace
        )

        if not np.any(valid):

            return trace

        x = np.arange(
            len(trace)
        )

        trace[~valid] = np.interp(
            x[~valid],
            x[valid],
            trace[valid],
        )

        return trace

    # ========================================================
    # INTERPOLATE
    # ========================================================

    def _interpolate_nan_trace(
        self,
        trace,
    ):

        trace = np.asarray(
            trace,
            dtype=np.float32,
        ).copy()

        valid = np.isfinite(
            trace
        )

        if not np.any(valid):

            return np.zeros_like(
                trace
            )

        x = np.arange(
            len(trace)
        )

        trace[~valid] = np.interp(
            x[~valid],
            x[valid],
            trace[valid],
        )

        return trace

    # ========================================================
    # AXIS CLEANING
    # ========================================================

    def _clean_axis_contamination(
        self,
        trace,
        axis_y,
        y_top,
        y_bottom,
    ):

        trace = np.asarray(
            trace,
            dtype=np.float32,
        ).copy()

        # ----------------------------------------------------
        # trace is in GLOBAL image coordinates.
        # ----------------------------------------------------

        near_axis = (
            np.abs(
                trace
                - float(axis_y)
            )
            <= 2
        )

        start = None

        for i, flag in enumerate(
            near_axis
        ):

            if (
                flag
                and
                start is None
            ):

                start = i

            elif (
                not flag
                and
                start is not None
            ):

                length = (
                    i - start
                )

                if length >= 12:

                    left = max(
                        0,
                        start - 4,
                    )

                    right = min(
                        len(trace) - 1,
                        i + 4,
                    )

                    neighbors = np.concatenate(
                        [
                            trace[
                                left:start
                            ],
                            trace[
                                i:right + 1
                            ],
                        ]
                    )

                    if neighbors.size:

                        trace[
                            start:i
                        ] = np.median(
                            neighbors
                        )

                start = None

        # Handle a run reaching the end.
        if start is not None:

            length = (
                len(trace)
                - start
            )

            if length >= 12:

                left = max(
                    0,
                    start - 4,
                )

                neighbors = trace[
                    left:start
                ]

                if neighbors.size:

                    trace[
                        start:
                    ] = np.median(
                        neighbors
                    )

        return np.clip(
            trace,
            y_top,
            y_bottom,
        )

    # ========================================================
    # CONTINUITY MASK
    # ========================================================

    def _build_continuity_peak_mask(
        self,
        roi_gray,
        evidence_data,
        trace,
    ):

        ev = np.asarray(
            evidence_data["combined"],
            dtype=np.float32,
        )

        h, w = ev.shape

        mask = np.zeros(
            (
                h,
                w,
            ),
            dtype=np.uint8,
        )

        if h < 3 or w < 3:

            return mask, []

        tr = self._interpolate_nan_trace(
            np.asarray(
                trace,
                dtype=np.float32,
            )
        )

        if len(tr) != w:

            tr = np.interp(
                np.linspace(
                    0,
                    len(tr) - 1,
                    w,
                ),
                np.arange(
                    len(tr)
                ),
                tr,
            )

        # ----------------------------------------------------
        # Local baseline.
        # ----------------------------------------------------

        window = max(
            11,
            min(
                81,
                (w // 22) | 1,
            ),
        )

        if window % 2 == 0:
            window += 1

        pad = window // 2

        padded = np.pad(
            tr,
            (
                pad,
                pad,
            ),
            mode="edge",
        )

        baseline = np.empty(
            w,
            dtype=np.float32,
        )

        for x in range(w):

            baseline[x] = np.median(
                padded[
                    x:x + window
                ]
            )

        excursion = (
            baseline
            - tr
        )

        positive = excursion[
            excursion > 0
        ]

        if positive.size:

            threshold = max(
                2.0,
                float(
                    np.percentile(
                        positive,
                        60,
                    )
                ),
            )

        else:

            threshold = 2.0

        trace_y = np.clip(
            np.rint(
                tr
            ).astype(
                int
            ),
            0,
            h - 1,
        )

        trace_score = ev[
            trace_y,
            np.arange(w)
        ]

        # ----------------------------------------------------
        # Draw complete actual trace.
        # ----------------------------------------------------

        for x in range(w):

            y = trace_y[x]

            ya = max(
                0,
                y - 1,
            )

            yb = min(
                h,
                y + 2,
            )

            mask[
                ya:yb,
                x
            ] = 255

        # ----------------------------------------------------
        # Peak columns.
        # ----------------------------------------------------

        peak_columns = (
            (
                excursion
                >= threshold
            )
            &
            (
                trace_score
                >= 0.12
            )
        )

        for x in np.flatnonzero(
            peak_columns
        ):

            y = trace_y[x]

            mask[
                max(
                    0,
                    y - 2,
                ):
                min(
                    h,
                    y + 3,
                ),
                x,
            ] = 255

        # ----------------------------------------------------
        # Connect small gaps.
        # ----------------------------------------------------

        connect_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (
                3,
                3,
            ),
        )

        connected = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            connect_kernel,
        )

        # Keep original trace plus connected peak evidence.
        mask = np.maximum(
            mask,
            connected,
        )

        # ----------------------------------------------------
        # Components.
        # ----------------------------------------------------

        binary = (
            mask > 0
        ).astype(
            np.uint8
        )

        n, labels, stats, _ = (
            cv2.connectedComponentsWithStats(
                binary,
                connectivity=8,
            )
        )

        final = np.zeros_like(
            binary,
            dtype=np.uint8,
        )

        groups = []

        for label in range(
            1,
            n,
        ):

            x = int(
                stats[
                    label,
                    cv2.CC_STAT_LEFT,
                ]
            )

            y = int(
                stats[
                    label,
                    cv2.CC_STAT_TOP,
                ]
            )

            width = int(
                stats[
                    label,
                    cv2.CC_STAT_WIDTH,
                ]
            )

            height = int(
                stats[
                    label,
                    cv2.CC_STAT_HEIGHT,
                ]
            )

            area = int(
                stats[
                    label,
                    cv2.CC_STAT_AREA,
                ]
            )

            component = (
                labels == label
            )

            xs = np.where(
                component
            )[1]

            if xs.size == 0:
                continue

            x_start = int(
                np.min(xs)
            )

            x_end = int(
                np.max(xs)
            )

            local_excursion = excursion[
                x_start:x_end + 1
            ]

            max_excursion = (
                float(
                    np.max(
                        local_excursion
                    )
                )
                if local_excursion.size
                else 0.0
            )

            # Since the complete trace itself is important,
            # don't aggressively remove small components.
            if (
                area < 2
                and
                width < 2
            ):

                continue

            final[
                component
            ] = 1

            groups.append(
                {
                    "x_start":
                        x_start,
                    "x_end":
                        x_end,
                    "width":
                        width,
                    "top_y":
                        y,
                    "height":
                        height,
                    "area":
                        area,
                    "max_excursion":
                        max_excursion,
                    "score":
                        float(
                            np.max(
                                ev[
                                    component
                                ]
                            )
                        ),
                }
            )

        groups.sort(
            key=lambda g:
            g["x_start"]
        )

        return (
            (
                final
                * 255
            ).astype(
                np.uint8
            ),
            groups,
        )

    # ========================================================
    # TRACE -> SPECTRUM
    # ========================================================

    def _trace_to_spectrum(
        self,
        trace,
        x1,
        x2,
        y_info,
        axis_result,
        rpm,
        machine_name,
        measurement_point,
        direction,
    ):

        trace = np.asarray(
            trace,
            dtype=np.float32,
        )

        width = len(
            trace
        )

        if width < 2:

            raise ValueError(
                "Trace برای ساخت Spectrum کافی نیست."
            )

        # ----------------------------------------------------
        # Pixel X is the actual detector-bounded X range.
        # ----------------------------------------------------

        px = np.linspace(
            float(x1),
            float(x2),
            width,
        )

        slope_x = _safe_float(
            getattr(
                axis_result,
                "slope",
                1.0,
            ),
            1.0,
        )

        intercept_x = _safe_float(
            getattr(
                axis_result,
                "intercept",
                0.0,
            ),
            0.0,
        )

        x_values = (
            slope_x * px
            + intercept_x
        )

        unit = str(
            getattr(
                axis_result,
                "unit",
                "",
            )
        ).upper()

        # ----------------------------------------------------
        # Source chart may be CPM.
        # Internal Spectrum is always Hz.
        # ----------------------------------------------------

        if (
            "CPM" in unit
            or
            "RPM" in unit
        ):

            frequency = (
                x_values
                / 60.0
            )

        else:

            frequency = (
                x_values
            )

        # ----------------------------------------------------
        # Y calibration uses GLOBAL image coordinates.
        # ----------------------------------------------------

        slope_y = float(
            y_info["slope"]
        )

        intercept_y = float(
            y_info["intercept"]
        )

        amplitude = (
            slope_y
            * trace
            +
            intercept_y
        )

        amplitude = np.asarray(
            amplitude,
            dtype=np.float64,
        )

        # ----------------------------------------------------
        # Physical amplitude should not be negative.
        # ----------------------------------------------------

        amplitude = np.maximum(
            amplitude,
            0.0,
        )

        spectrum = Spectrum(
            frequency_hz=[
                float(v)
                for v in frequency
            ],
            amplitude=[
                float(v)
                for v in amplitude
            ],
            rpm=rpm,
            machine_name=machine_name,
            measurement_point=measurement_point,
            direction=direction,
            source="fft_image",
        )

        spectrum.validate()

        return spectrum

    # ========================================================
    # PEAK DETECTION
    # ========================================================

    def _detect_peaks(
        self,
        frequency,
        amplitude,
        trace=None,
        y_info=None,
        y_top=None,
        y_bottom=None,
    ):

        f = np.asarray(
            frequency,
            dtype=np.float64,
        )

        a = np.asarray(
            amplitude,
            dtype=np.float64,
        )

        if len(a) < 7:
            return []

        valid = (
            np.isfinite(f)
            &
            np.isfinite(a)
        )

        f = f[valid]
        a = a[valid]

        if len(a) < 7:
            return []

        # ====================================================
        # Local baseline.
        # ====================================================

        n = len(a)

        window = max(
            7,
            min(
                101,
                (n // 40) | 1,
            ),
        )

        if window % 2 == 0:
            window += 1

        kernel = np.ones(
            window,
            dtype=np.float64,
        )

        kernel /= np.sum(
            kernel
        )

        pad = window // 2

        padded = np.pad(
            a,
            (
                pad,
                pad,
            ),
            mode="edge",
        )

        baseline = np.convolve(
            padded,
            kernel,
            mode="valid",
        )

        prominence = (
            a
            - baseline
        )

        # ====================================================
        # Noise estimate.
        # ====================================================

        noise = _mad(
            prominence
        )

        if noise <= 1e-12:

            noise = float(
                np.std(
                    prominence
                )
            )

        if noise <= 1e-12:

            noise = max(
                1e-9,
                float(
                    np.max(a)
                )
                * 1e-5,
            )

        # ====================================================
        # Candidate local maxima.
        # ====================================================

        candidates = []

        positive_prom = np.maximum(
            prominence,
            0.0,
        )

        p85 = float(
            np.percentile(
                positive_prom,
                85,
            )
        )

        p60 = float(
            np.percentile(
                positive_prom,
                60,
            )
        )

        threshold = max(
            noise * 2.5,
            p85 * 0.16,
            p60 * 0.30,
        )

        for i in range(
            1,
            n - 1,
        ):

            if (
                a[i]
                < a[i - 1]
                or
                a[i]
                < a[i + 1]
            ):
                continue

            prom = float(
                prominence[i]
            )

            if prom < threshold:
                continue

            # ------------------------------------------------
            # Local peak shape.
            # ------------------------------------------------

            left_i = max(
                0,
                i - 4,
            )

            right_i = min(
                n,
                i + 5,
            )

            local = a[
                left_i:right_i
            ]

            if local.size:

                local_min = float(
                    np.min(
                        local
                    )
                )

                local_height = (
                    float(a[i])
                    - local_min
                )

            else:

                local_height = 0.0

            # Keep strong local maxima.
            if (
                prom >= threshold
                or
                local_height
                >= noise * 4.0
            ):

                candidates.append(
                    i
                )

        if not candidates:
            return []

        # ====================================================
        # Peak distance.
        #
        # NO RPM.
        # ====================================================

        if len(f) > 1:

            diffs = np.diff(
                f
            )

            diffs = diffs[
                np.isfinite(
                    diffs
                )
                &
                (
                    np.abs(
                        diffs
                    )
                    > 1e-12
                )
            ]

            if diffs.size:

                freq_step = float(
                    np.median(
                        np.abs(
                            diffs
                        )
                    )
                )

            else:

                freq_step = 1.0

        else:

            freq_step = 1.0

        # Allow close peaks because image spectra can contain
        # narrow peaks. This is only a pixel-resolution limit.
        min_distance = max(
            freq_step * 1.15,
            1e-6,
        )

        # ====================================================
        # Rank candidates by prominence + height.
        # ====================================================

        ranked = sorted(
            candidates,
            key=lambda i: (
                prominence[i],
                a[i],
            ),
            reverse=True,
        )

        selected = []

        for idx in ranked:

            if not selected:

                selected.append(
                    idx
                )

                continue

            too_close = False

            for old in selected:

                if (
                    abs(
                        f[idx]
                        - f[old]
                    )
                    < min_distance
                ):

                    too_close = True
                    break

            if too_close:
                continue

            selected.append(
                idx
            )

        # Sort by frequency.
        selected.sort(
            key=lambda i:
            f[i]
        )

        peaks = []

        for idx in selected:

            peaks.append(
                Peak(
                    frequency_hz=float(
                        f[idx]
                    ),
                    amplitude=float(
                        max(
                            0.0,
                            a[idx],
                        )
                    ),
                    prominence=float(
                        max(
                            0.0,
                            prominence[idx],
                        )
                    ),
                    source="fft_image",
                )
            )

        return peaks

    # ========================================================
    # DEBUG: ORIGINAL ROI
    # ========================================================

    def _save_original_roi_debug(
        self,
        roi_color,
    ):

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "01_original_roi.png",
            ),
            roi_color,
        )

    # ========================================================
    # DEBUG: X AXIS
    # ========================================================

    def _save_x_axis_debug(
        self,
        image,
        x1,
        x2,
        axis_y,
        axis_result,
    ):

        dbg = image.copy()

        h, w = dbg.shape[:2]

        cv2.line(
            dbg,
            (x1, 0),
            (x1, h - 1),
            (255, 0, 255),
            2,
        )

        cv2.line(
            dbg,
            (x2, 0),
            (x2, h - 1),
            (255, 0, 255),
            2,
        )

        cv2.line(
            dbg,
            (0, axis_y),
            (w - 1, axis_y),
            (255, 0, 255),
            2,
        )

        slope = _safe_float(
            getattr(
                axis_result,
                "slope",
                0,
            )
        )

        intercept = _safe_float(
            getattr(
                axis_result,
                "intercept",
                0,
            )
        )

        unit = str(
            getattr(
                axis_result,
                "unit",
                "",
            )
        )

        text = (
            f"X1={x1} "
            f"X2={x2} "
            f"Y={axis_y} "
            f"slope={slope:.6f} "
            f"intercept={intercept:.3f} "
            f"unit={unit}"
        )

        cv2.putText(
            dbg,
            text,
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 0, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "02_x_axis_calibration.png",
            ),
            dbg,
        )

    # ========================================================
    # DEBUG: Y AXIS
    # ========================================================

    def _save_y_debug(
        self,
        image,
        x1,
        x2,
        axis_y,
        y_info,
    ):

        dbg = image.copy()

        for py, value, source in y_info[
            "pairs"
        ]:

            py = int(
                round(py)
            )

            cv2.line(
                dbg,
                (
                    max(
                        0,
                        x1 - 140,
                    ),
                    py,
                ),
                (
                    min(
                        dbg.shape[1] - 1,
                        x1 + 60,
                    ),
                    py,
                ),
                (0, 255, 255),
                1,
            )

            cv2.putText(
                dbg,
                f"{value:g}",
                (
                    max(
                        0,
                        x1 - 135,
                    ),
                    max(
                        12,
                        py - 3,
                    ),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )

        cv2.rectangle(
            dbg,
            (
                x1,
                y_info["y_top"],
            ),
            (
                x2,
                y_info["y_bottom"],
            ),
            (0, 255, 255),
            1,
        )

        text = (
            f"Y slope="
            f"{y_info['slope']:.8f} "
            f"intercept="
            f"{y_info['intercept']:.5f} "
            f"confidence="
            f"{y_info['confidence']:.1f} "
            f"ROI="
            f"{y_info['y_top']}:"
            f"{y_info['y_bottom']}"
        )

        cv2.putText(
            dbg,
            text,
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "03_y_axis_calibration.png",
            ),
            dbg,
        )

    # ========================================================
    # DEBUG: EVIDENCE
    # ========================================================

    def _save_evidence_debug(
        self,
        roi_gray,
        evidence,
    ):

        ev = np.clip(
            evidence * 255,
            0,
            255,
        ).astype(
            np.uint8
        )

        debug = cv2.applyColorMap(
            ev,
            cv2.COLORMAP_JET,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "04_curve_evidence.png",
            ),
            debug,
        )

    # ========================================================
    # DEBUG: COLOR
    # ========================================================

    def _save_color_debug(
        self,
        evidence_data,
    ):

        color = np.clip(
            evidence_data["color"]
            * 255,
            0,
            255,
        ).astype(
            np.uint8
        )

        debug = cv2.applyColorMap(
            color,
            cv2.COLORMAP_JET,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "04_color_evidence.png",
            ),
            debug,
        )

    # ========================================================
    # DEBUG: EDGE
    # ========================================================

    def _save_edge_debug(
        self,
        evidence_data,
    ):

        edges = np.clip(
            evidence_data["edges"]
            * 255,
            0,
            255,
        ).astype(
            np.uint8
        )

        debug = np.zeros(
            (
                edges.shape[0],
                edges.shape[1],
                3,
            ),
            dtype=np.uint8,
        )

        debug[
            edges > 0
        ] = (
            255,
            255,
            255,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "04_edges.png",
            ),
            debug,
        )

    # ========================================================
    # DEBUG: CONTINUITY
    # ========================================================

    def _save_continuity_debug(
        self,
        continuity_mask,
    ):

        mask = np.asarray(
            continuity_mask,
            dtype=np.uint8,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "05_continuity.png",
            ),
            mask,
        )

    # ========================================================
    # DEBUG: CONTINUITY GLOBAL
    # ========================================================

    def _save_continuity_new_debug(
        self,
        image,
        x1,
        x2,
        y_top,
        y_bottom,
        continuity_mask,
    ):

        h, w = image.shape[:2]

        debug = np.zeros(
            (
                h,
                w,
                3,
            ),
            dtype=np.uint8,
        )

        mask = np.asarray(
            continuity_mask,
            dtype=np.uint8,
        )

        expected_h = (
            y_bottom
            - y_top
            + 1
        )

        expected_w = (
            x2
            - x1
            + 1
        )

        if mask.shape != (
            expected_h,
            expected_w,
        ):

            mask = cv2.resize(
                mask,
                (
                    expected_w,
                    expected_h,
                ),
                interpolation=cv2.INTER_NEAREST,
            )

        actual_h = min(
            expected_h,
            h - y_top,
        )

        actual_w = min(
            expected_w,
            w - x1,
        )

        if (
            actual_h > 0
            and
            actual_w > 0
        ):

            region = debug[
                y_top:
                y_top + actual_h,
                x1:
                x1 + actual_w
            ]

            roi_mask = (
                mask[
                    :actual_h,
                    :actual_w
                ]
                > 0
            )

            region[
                roi_mask
            ] = (
                255,
                255,
                255,
            )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "06_continuity_new.png",
            ),
            debug,
        )

    # ========================================================
    # DEBUG: RECONSTRUCTED CURVE
    # ========================================================

    def _save_curve_debug(
        self,
        image,
        x1,
        x2,
        trace,
        y_top,
        y_bottom,
    ):

        dbg = image.copy()

        if len(trace) >= 2:

            points = []

            for i, y in enumerate(
                trace
            ):

                ratio = (
                    i
                    /
                    max(
                        1,
                        len(trace) - 1,
                    )
                )

                x = int(
                    round(
                        x1
                        +
                        ratio
                        * (
                            x2
                            - x1
                        )
                    )
                )

                yy = int(
                    np.clip(
                        round(y),
                        0,
                        dbg.shape[0] - 1,
                    )
                )

                points.append(
                    [
                        x,
                        yy,
                    ]
                )

            points = np.asarray(
                points,
                dtype=np.int32,
            ).reshape(
                -1,
                1,
                2,
            )

            cv2.polylines(
                dbg,
                [points],
                False,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        cv2.rectangle(
            dbg,
            (
                x1,
                y_top,
            ),
            (
                x2,
                y_bottom,
            ),
            (255, 0, 255),
            1,
        )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "06_reconstructed_curve.png",
            ),
            dbg,
        )

    # ========================================================
    # DEBUG: PEAKS
    # ========================================================

    def _save_peak_debug(
        self,
        image,
        x1,
        x2,
        trace,
        spectrum,
        peaks,
    ):

        dbg = image.copy()

        if len(trace) >= 2:

            points = []

            for i, y in enumerate(
                trace
            ):

                ratio = (
                    i
                    /
                    max(
                        1,
                        len(trace) - 1,
                    )
                )

                x = int(
                    round(
                        x1
                        +
                        ratio
                        * (
                            x2
                            - x1
                        )
                    )
                )

                yy = int(
                    np.clip(
                        round(y),
                        0,
                        dbg.shape[0] - 1,
                    )
                )

                points.append(
                    [
                        x,
                        yy,
                    ]
                )

            points = np.asarray(
                points,
                dtype=np.int32,
            ).reshape(
                -1,
                1,
                2,
            )

            cv2.polylines(
                dbg,
                [points],
                False,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        frequencies = np.asarray(
            spectrum.frequency_hz,
            dtype=np.float64,
        )

        if len(frequencies) >= 2:

            fmin = float(
                frequencies[0]
            )

            fmax = float(
                frequencies[-1]
            )

            if fmax > fmin:

                for peak in peaks:

                    ratio = (
                        peak.frequency_hz
                        - fmin
                    ) / (
                        fmax
                        - fmin
                    )

                    ratio = float(
                        np.clip(
                            ratio,
                            0.0,
                            1.0,
                        )
                    )

                    px = int(
                        round(
                            x1
                            +
                            ratio
                            * (
                                x2
                                - x1
                            )
                        )
                    )

                    idx = int(
                        np.clip(
                            round(
                                ratio
                                * (
                                    len(trace)
                                    - 1
                                )
                            ),
                            0,
                            len(trace) - 1,
                        )
                    )

                    py = int(
                        np.clip(
                            round(
                                trace[idx]
                            ),
                            0,
                            dbg.shape[0] - 1,
                        )
                    )

                    cv2.circle(
                        dbg,
                        (
                            px,
                            py,
                        ),
                        5,
                        (0, 0, 255),
                        2,
                    )

                    cv2.putText(
                        dbg,
                        f"{peak.frequency_hz:.2f} Hz",
                        (
                            px + 6,
                            max(
                                15,
                                py - 8,
                            ),
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.40,
                        (0, 0, 255),
                        1,
                        cv2.LINE_AA,
                    )

        cv2.imwrite(
            os.path.join(
                self.debug_dir,
                "07_final_peaks.png",
            ),
            dbg,
        )


# ============================================================
# SPECTRUM PLOT
# ============================================================

def plot_extracted_spectrum(
    spectrum,
    save_path=None,
    show=True,
):

    frequencies = np.asarray(
        spectrum.frequency_hz,
        dtype=np.float64,
    )

    amplitudes = np.asarray(
        spectrum.amplitude,
        dtype=np.float64,
    )

    peaks = list(
        spectrum.peaks
    )

    if len(frequencies) == 0:

        print(
            "No spectrum data available."
        )

        return

    fig = plt.figure(
        figsize=(18, 9)
    )

    ax = fig.add_subplot(
        111
    )

    ax.plot(
        frequencies,
        amplitudes,
        linewidth=1.3,
        label="Reconstructed FFT Curve",
    )

    if peaks:

        peak_x = [
            float(
                p.frequency_hz
            )
            for p in peaks
        ]

        peak_y = [
            float(
                p.amplitude
            )
            for p in peaks
        ]

        ax.scatter(
            peak_x,
            peak_y,
            s=55,
            zorder=10,
            label=(
                f"Detected Peaks "
                f"({len(peaks)})"
            ),
        )

        for i, peak in enumerate(
            peaks,
            start=1,
        ):

            ax.annotate(
                f"{i}: "
                f"{peak.frequency_hz:.2f}",
                xy=(
                    peak.frequency_hz,
                    peak.amplitude,
                ),
                xytext=(
                    0,
                    10,
                ),
                textcoords=(
                    "offset points"
                ),
                ha="center",
                fontsize=8,
                rotation=45,
            )

    ax.set_xlabel(
        "Frequency (Hz)",
        fontsize=12,
    )

    ax.set_ylabel(
        "Amplitude",
        fontsize=12,
    )

    ax.set_title(
        "FFT Image → Reconstructed Spectrum + Detected Peaks",
        fontsize=14,
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    if save_path:

        fig.savefig(
            save_path,
            dpi=160,
            bbox_inches="tight",
        )

    if show:

        plt.show()

    plt.close(
        fig
    )


# ============================================================
# MODULE-LEVEL COMPATIBILITY
# ============================================================

def extract_spectrum_from_image(
    image_path,
    rpm=None,
    debug=True,
    *,
    machine_name=None,
    measurement_point=None,
    direction=None,
):

    extractor = FFTImageExtractor(
        image_path=image_path,
        debug=debug,
    )

    return extractor.extract(
        image_path=image_path,
        rpm=rpm,
        debug=debug,
        machine_name=machine_name,
        measurement_point=measurement_point,
        direction=direction,
    )


def create_spectrum_from_image(
    image_path,
    rpm=None,
    debug=True,
    *,
    machine_name=None,
    measurement_point=None,
    direction=None,
):

    return extract_spectrum_from_image(
        image_path=image_path,
        rpm=rpm,
        debug=debug,
        machine_name=machine_name,
        measurement_point=measurement_point,
        direction=direction,
    )