from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import re

import cv2
import numpy as np
import pytesseract


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class AxisLabel:
    text: str
    value: float
    pixel_x: float
    pixel_y: float
    confidence: float = 0.0

    def to_dict(self):
        return {
            "text": self.text,
            "value": round(self.value, 4),
            "pixel_x": round(self.pixel_x, 2),
            "pixel_y": round(self.pixel_y, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class AxisResult:
    x_axis_y: Optional[float] = None
    unit: Optional[str] = None

    x_labels: List[AxisLabel] = field(default_factory=list)

    pixel_x1: Optional[float] = None
    value_x1: Optional[float] = None

    pixel_x2: Optional[float] = None
    value_x2: Optional[float] = None

    slope: Optional[float] = None
    intercept: Optional[float] = None

    axis_step: Optional[float] = None

    rmse: Optional[float] = None
    hz_per_pixel: Optional[float] = None

    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "x_axis_y": self.x_axis_y,
            "unit": self.unit,
            "x_labels": [x.to_dict() for x in self.x_labels],

            "pixel_x1": self.pixel_x1,
            "value_x1": self.value_x1,

            "pixel_x2": self.pixel_x2,
            "value_x2": self.value_x2,

            "slope": self.slope,
            "intercept": self.intercept,

            "axis_step": self.axis_step,

            "rmse": self.rmse,
            "hz_per_pixel": self.hz_per_pixel,

            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# FFT AXIS DETECTOR
# ============================================================

class FFTAxisDetector:

    def __init__(self, image_path: str):

        self.image_path = Path(image_path)

        if not self.image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        self.image = cv2.imread(str(self.image_path))

        if self.image is None:
            raise ValueError("تصویر قابل خواندن نیست.")

        self.gray = cv2.cvtColor(
            self.image,
            cv2.COLOR_BGR2GRAY
        )

        self.height, self.width = self.gray.shape

    # ========================================================
    # OCR
    # ========================================================

    def _ocr(self):

        results = []

        scale = 3.0

        enlarged = cv2.resize(
            self.gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

        # چند preprocessing مختلف
        variants = []

        # Variant 1
        blur = cv2.GaussianBlur(
            enlarged,
            (3, 3),
            0
        )

        binary_180 = cv2.threshold(
            blur,
            180,
            255,
            cv2.THRESH_BINARY
        )[1]

        variants.append(binary_180)

        # Variant 2
        binary_150 = cv2.threshold(
            blur,
            150,
            255,
            cv2.THRESH_BINARY
        )[1]

        variants.append(binary_150)

        # Variant 3
        adaptive = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            7
        )

        variants.append(adaptive)

        # OCR with multiple PSM
        for image_variant in variants:

            for psm in (6, 11):

                try:

                    data = pytesseract.image_to_data(
                        image_variant,
                        config=f"--psm {psm}",
                        output_type=pytesseract.Output.DICT
                    )

                except Exception:
                    continue

                for i in range(len(data["text"])):

                    text = data["text"][i].strip()

                    if not text:
                        continue

                    try:
                        confidence = float(
                            data["conf"][i]
                        )
                    except Exception:
                        confidence = 0.0

                    if confidence < 5:
                        continue

                    try:

                        x = int(
                            data["left"][i] / scale
                        )

                        y = int(
                            data["top"][i] / scale
                        )

                        w = int(
                            data["width"][i] / scale
                        )

                        h = int(
                            data["height"][i] / scale
                        )

                    except Exception:
                        continue

                    results.append(
                        {
                            "text": text,
                            "x": x,
                            "y": y,
                            "w": w,
                            "h": h,
                            "confidence": confidence,
                        }
                    )

        # حذف OCR های تکراری
        unique = []

        for item in results:

            duplicate = False

            for old in unique:

                if (
                    abs(item["x"] - old["x"]) < 8
                    and
                    abs(item["y"] - old["y"]) < 8
                    and
                    item["text"].lower()
                    == old["text"].lower()
                ):
                    duplicate = True

                    if item["confidence"] > old["confidence"]:
                        old.update(item)

                    break

            if not duplicate:
                unique.append(item)

        return unique

    # ========================================================
    # DIGIT NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize_digits(text):

        translation = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789"
        )

        return str(text).translate(translation)

    # ========================================================
    # NUMBER PARSER
    # ========================================================

    @classmethod
    def parse_number(cls, text):

        if text is None:
            return None

        text = cls.normalize_digits(text)

        text = str(text).strip()

        # OCR corrections
        replacements = {
            "O": "0",
            "o": "0",
            "I": "1",
            "l": "1",
            "|": "1",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # حذف comma و space
        text = text.replace(",", "")
        text = text.replace(" ", "")

        # X axis order مثل 1X / 2X
        order_match = re.fullmatch(
            r"[-+]?\d+(?:\.\d+)?[xX]",
            text
        )

        if order_match:
            try:
                return float(
                    text[:-1]
                )
            except Exception:
                return None

        # حالت k مثل 1k
        k_match = re.fullmatch(
            r"([-+]?\d+(?:\.\d+)?)k",
            text,
            flags=re.IGNORECASE
        )

        if k_match:

            try:
                return float(
                    k_match.group(1)
                ) * 1000.0
            except Exception:
                return None

        # عدد معمولی
        match = re.search(
            r"[-+]?\d+(?:\.\d+)?",
            text
        )

        if not match:
            return None

        try:
            return float(
                match.group(0)
            )
        except ValueError:
            return None

    # ========================================================
    # UNIT DETECTION
    # ========================================================

    def detect_unit(self, ocr_items):

        if not ocr_items:
            return None

        # ---------------------------------------------
        # اول دنبال Unit واقعی بگرد
        # ---------------------------------------------

        candidates = []

        for item in ocr_items:

            text = item["text"].strip().lower()

            if not text:
                continue

            candidates.append(
                (
                    text,
                    item["x"],
                    item["y"],
                    item["confidence"]
                )
            )

        # اولویت Unit ها
        unit_patterns = [
            ("CPM", [r"\bcpm\b"]),
            ("Hz", [r"\bhz\b"]),
            ("RPM", [r"\brpm\b"]),
            ("Order", [r"\border\b"]),
            ("Order", [r"\b1x\b", r"\b2x\b"]),
        ]

        # پایین تصویر وزن بیشتری دارد
        scored = []

        for text, x, y, confidence in candidates:

            lower_bonus = 0.0

            if y > self.height * 0.55:
                lower_bonus += 20.0

            for unit_name, patterns in unit_patterns:

                for pattern in patterns:

                    if re.search(pattern, text):

                        score = (
                            confidence
                            +
                            lower_bonus
                        )

                        scored.append(
                            (
                                score,
                                unit_name
                            )
                        )

        if scored:

            scored.sort(
                key=lambda z: z[0],
                reverse=True
            )

            return scored[0][1]

        # ---------------------------------------------
        # اگر Unit مستقیم پیدا نشد
        # از متن‌های نزدیک پایین تصویر کمک بگیر
        # ---------------------------------------------

        lower_text = " ".join(
            item["text"].lower()
            for item in ocr_items
            if item["y"] > self.height * 0.55
        )

        if "cpm" in lower_text:
            return "CPM"

        if "rpm" in lower_text:
            return "RPM"

        if "hz" in lower_text:
            return "Hz"

        if "order" in lower_text:
            return "Order"

        if re.search(r"\b[0-9]+x\b", lower_text):
            return "Order"

        return None

    # ========================================================
    # FIND X AXIS Y
    # ========================================================

    def estimate_x_axis_y_from_labels(
        self,
        labels
    ):

        if not labels:
            return None

        median_y = float(
            np.median(
                [
                    label.pixel_y
                    for label in labels
                ]
            )
        )

        # معمولاً Label کمی پایین‌تر از خط محور قرار دارد
        offset = max(
            12.0,
            min(
                30.0,
                self.height * 0.035
            )
        )

        estimated = median_y - offset

        return max(
            0.0,
            min(
                float(self.height - 1),
                estimated
            )
        )

    # ========================================================
    # HOUGH X AXIS
    # ========================================================

    def detect_x_axis_y_hough(self):

        edges = cv2.Canny(
            self.gray,
            50,
            150
        )

        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=80,
            minLineLength=int(
                self.width * 0.25
            ),
            maxLineGap=30
        )

        candidates = []

        if lines is None:
            return None

        for line in lines:

            values = np.asarray(
                line
            ).reshape(-1)

            if len(values) != 4:
                continue

            x1, y1, x2, y2 = map(
                int,
                values
            )

            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            if dx < self.width * 0.25:
                continue

            if dy > 5:
                continue

            y = (
                y1 + y2
            ) / 2.0

            # محور X معمولاً پایین نمودار است
            if y < self.height * 0.50:
                continue

            candidates.append(
                {
                    "y": y,
                    "length": dx
                }
            )

        if not candidates:
            return None

        # خطوط خیلی پایین یا نزدیک پایین تصویر اولویت دارند
        candidates.sort(
            key=lambda item: (
                item["length"],
                item["y"]
            ),
            reverse=True
        )

        return float(
            candidates[0]["y"]
        )

    # ========================================================
    # X AXIS
    # ========================================================

    def detect_x_axis_y(
        self,
        labels=None
    ):

        if labels:

            estimated = (
                self.estimate_x_axis_y_from_labels(
                    labels
                )
            )

            if estimated is not None:
                return estimated

        return self.detect_x_axis_y_hough()

    # ========================================================
    # DETECT X LABELS
    # ========================================================

    def detect_x_labels(
        self,
        ocr_items,
        axis_y=None
    ):

        if not ocr_items:
            return []

        candidates = []

        # اگر محور داریم، Label باید نزدیک پایین محور باشد
        if axis_y is None:
            min_y = self.height * 0.45
            max_y = self.height
        else:
            min_y = max(
                0,
                axis_y - self.height * 0.02
            )

            max_y = min(
                self.height,
                axis_y + self.height * 0.22
            )

        for item in ocr_items:

            value = self.parse_number(
                item["text"]
            )

            if value is None:
                continue

            x = item["x"]
            y = item["y"]
            w = item["w"]
            h = item["h"]

            center_x = (
                x + w / 2.0
            )

            center_y = (
                y + h / 2.0
            )

            # خارج محدوده عمودی
            if center_y < min_y:
                continue

            if center_y > max_y:
                continue

            # اندازه غیرمنطقی
            if w <= 0 or h <= 0:
                continue

            # confidence خیلی پایین
            if item["confidence"] < 10:
                continue

            # مقادیر بسیار غیرمنطقی
            if not np.isfinite(value):
                continue

            if abs(value) > 1_000_000:
                continue

            candidates.append(
                AxisLabel(
                    text=item["text"],
                    value=value,
                    pixel_x=center_x,
                    pixel_y=center_y,
                    confidence=item["confidence"]
                )
            )

        if not candidates:
            return []

        # ----------------------------------------------------
        # گروه‌بندی Label ها بر اساس Y
        # ----------------------------------------------------

        candidates.sort(
            key=lambda z: z.pixel_y
        )

        groups = []

        for candidate in candidates:

            placed = False

            for group in groups:

                median_y = np.median(
                    [
                        x.pixel_y
                        for x in group
                    ]
                )

                if abs(
                    candidate.pixel_y
                    -
                    median_y
                ) <= max(
                    18.0,
                    self.height * 0.025
                ):

                    group.append(
                        candidate
                    )

                    placed = True
                    break

            if not placed:
                groups.append(
                    [candidate]
                )

        # ----------------------------------------------------
        # امتیازدهی به گروه‌ها
        # ----------------------------------------------------

        scored_groups = []

        for group in groups:

            if len(group) < 2:
                continue

            median_y = float(
                np.median(
                    [
                        x.pixel_y
                        for x in group
                    ]
                )
            )

            x_span = (
                max(x.pixel_x for x in group)
                -
                min(x.pixel_x for x in group)
            )

            # گروهی که گستره X بیشتری دارد احتمالاً محور است
            score = (
                len(group) * 100.0
                +
                min(
                    x_span / max(self.width, 1),
                    1.0
                ) * 50.0
            )

            # پایین‌تر بودن امتیاز بیشتر
            if median_y > self.height * 0.70:
                score += 30.0

            scored_groups.append(
                (
                    score,
                    group
                )
            )

        if not scored_groups:
            return []

        scored_groups.sort(
            key=lambda z: z[0],
            reverse=True
        )

        best_group = scored_groups[0][1]

        best_group.sort(
            key=lambda z: z.pixel_x
        )

        # ----------------------------------------------------
        # حذف Duplicate های مکانی
        # ----------------------------------------------------

        result = []

        for label in best_group:

            duplicate = None

            for old in result:

                if (
                    abs(
                        label.pixel_x
                        -
                        old.pixel_x
                    )
                    <
                    max(
                        10.0,
                        self.width * 0.006
                    )
                ):

                    duplicate = old
                    break

            if duplicate is None:

                result.append(
                    AxisLabel(
                        text=label.text,
                        value=label.value,
                        pixel_x=label.pixel_x,
                        pixel_y=label.pixel_y,
                        confidence=label.confidence
                    )
                )

            else:

                if (
                    label.confidence
                    >
                    duplicate.confidence
                ):

                    duplicate.text = (
                        label.text
                    )

                    duplicate.value = (
                        label.value
                    )

                    duplicate.confidence = (
                        label.confidence
                    )

        return result

    # ========================================================
    # MERGE SPLIT LABELS
    # ========================================================

    def merge_split_labels(
        self,
        labels
    ):

        if not labels:
            return []

        labels = sorted(
            labels,
            key=lambda x: x.pixel_x
        )

        result = []

        for label in labels:

            duplicate = None

            for old in result:

                if (
                    abs(
                        label.pixel_x
                        -
                        old.pixel_x
                    )
                    <
                    max(
                        12.0,
                        self.width * 0.007
                    )
                ):

                    duplicate = old
                    break

            if duplicate is None:

                result.append(
                    AxisLabel(
                        text=label.text,
                        value=label.value,
                        pixel_x=label.pixel_x,
                        pixel_y=label.pixel_y,
                        confidence=label.confidence
                    )
                )

            else:

                if (
                    label.confidence
                    >
                    duplicate.confidence
                ):

                    duplicate.text = (
                        label.text
                    )

                    duplicate.value = (
                        label.value
                    )

                    duplicate.confidence = (
                        label.confidence
                    )

        return result

    # ========================================================
    # AXIS STEP
    # ========================================================

    def detect_axis_step(
        self,
        labels
    ):

        if labels is None:
            return None

        if len(labels) < 2:
            return None

        values = []

        for label in labels:

            try:
                value = float(
                    label.value
                )
            except Exception:
                continue

            if not np.isfinite(value):
                continue

            values.append(value)

        if len(values) < 2:
            return None

        values = sorted(
            set(
                round(v, 8)
                for v in values
            )
        )

        if len(values) < 2:
            return None

        diffs = []

        for i in range(
            1,
            len(values)
        ):

            diff = (
                values[i]
                -
                values[i - 1]
            )

            if diff > 0:
                diffs.append(diff)

        if not diffs:
            return None

        # ----------------------------------------------------
        # اگر چند اختلاف مشابه داریم
        # median بهترین تخمین است
        # ----------------------------------------------------

        diffs = np.asarray(
            diffs,
            dtype=float
        )

        median_diff = float(
            np.median(diffs)
        )

        if median_diff <= 0:
            return None

        # ----------------------------------------------------
        # Normalize برای Step های معمول
        # ----------------------------------------------------

        exponent = np.floor(
            np.log10(
                median_diff
            )
        )

        base = (
            10.0 ** exponent
        )

        normalized = (
            median_diff
            /
            base
        )

        if normalized < 1.5:
            nice = 1.0
        elif normalized < 3.5:
            nice = 2.0
        elif normalized < 7.5:
            nice = 5.0
        else:
            nice = 10.0

        candidate = (
            nice * base
        )

        # اگر candidate با داده خیلی فاصله دارد
        # همان median را نگه می‌داریم
        relative_error = (
            abs(
                candidate
                -
                median_diff
            )
            /
            max(
                abs(median_diff),
                1e-12
            )
        )

        if relative_error <= 0.20:
            return float(candidate)

        return float(
            median_diff
        )

    # ========================================================
    # VALIDATE LABELS
    # ========================================================

    def validate_labels(
        self,
        labels
    ):

        if not labels:
            return []

        labels = sorted(
            labels,
            key=lambda x: x.pixel_x
        )

        # ----------------------------------------------------
        # حذف duplicate مکانی
        # ----------------------------------------------------

        cleaned = []

        for label in labels:

            if not cleaned:

                cleaned.append(
                    label
                )

                continue

            previous = cleaned[-1]

            if (
                abs(
                    label.pixel_x
                    -
                    previous.pixel_x
                )
                <
                max(
                    10.0,
                    self.width * 0.006
                )
            ):

                if (
                    label.confidence
                    >
                    previous.confidence
                ):

                    cleaned[-1] = label

                continue

            cleaned.append(
                label
            )

        labels = cleaned

        if len(labels) < 2:
            return []

        # ----------------------------------------------------
        # مقدارها باید از چپ به راست افزایشی باشند
        # ----------------------------------------------------

        increasing = []

        for label in labels:

            if not increasing:

                increasing.append(
                    label
                )

                continue

            previous = increasing[-1]

            if (
                label.value
                >
                previous.value
            ):

                increasing.append(
                    label
                )

        labels = increasing

        if len(labels) < 2:
            return []

        axis_step = (
            self.detect_axis_step(
                labels
            )
        )

        if axis_step is None:
            return labels

        # ----------------------------------------------------
        # حذف پرش‌های غیرمنطقی
        # ----------------------------------------------------

        validated = [
            labels[0]
        ]

        for label in labels[1:]:

            previous = validated[-1]

            dv = (
                label.value
                -
                previous.value
            )

            if dv <= 0:
                continue

            ratio = (
                dv
                /
                axis_step
            )

            nearest = max(
                1,
                round(ratio)
            )

            expected = (
                axis_step
                *
                nearest
            )

            error = (
                abs(
                    dv
                    -
                    expected
                )
                /
                max(
                    abs(expected),
                    1e-12
                )
            )

            # اجازه پرش چند Step را می‌دهیم
            if error <= 0.30:

                validated.append(
                    label
                )

        # اگر validation بیش از حد سخت شد،
        # حداقل دو Label معتبر را نگه دار
        if len(validated) < 2:

            return labels[:2]

        return validated

    # ========================================================
    # CALIBRATION
    # ========================================================

    def calculate_calibration(
        self,
        labels
    ):

        if labels is None:
            return None

        if len(labels) < 2:
            return None

        x = np.array(
            [
                label.pixel_x
                for label in labels
            ],
            dtype=float
        )

        y = np.array(
            [
                label.value
                for label in labels
            ],
            dtype=float
        )

        if len(x) < 2:
            return None

        if not np.all(
            np.isfinite(x)
        ):
            return None

        if not np.all(
            np.isfinite(y)
        ):
            return None

        if np.ptp(x) <= 0:
            return None

        # ----------------------------------------------------
        # Initial fit
        # ----------------------------------------------------

        try:

            slope, intercept = np.polyfit(
                x,
                y,
                1
            )

        except Exception:
            return None

        if not np.isfinite(slope):
            return None

        if not np.isfinite(intercept):
            return None

        # محور X باید معمولاً از چپ به راست افزایش داشته باشد
        if slope <= 0:

            return None

        # ----------------------------------------------------
        # Robust fitting
        # ----------------------------------------------------

        mask = np.ones(
            len(x),
            dtype=bool
        )

        for _ in range(6):

            if np.sum(mask) < 2:
                break

            try:

                slope, intercept = np.polyfit(
                    x[mask],
                    y[mask],
                    1
                )

            except Exception:
                break

            predicted = (
                slope * x
                +
                intercept
            )

            residuals = np.abs(
                y
                -
                predicted
            )

            active_residuals = (
                residuals[mask]
            )

            if len(
                active_residuals
            ) == 0:

                break

            median_error = float(
                np.median(
                    active_residuals
                )
            )

            # threshold متناسب با Step
            label_range = (
                np.ptp(y)
                if len(y) > 1
                else 1.0
            )

            threshold = max(
                0.03 * max(
                    label_range,
                    1.0
                ),
                median_error * 3.0,
                0.5
            )

            new_mask = (
                residuals
                <=
                threshold
            )

            if np.sum(new_mask) < 2:
                break

            if np.array_equal(
                new_mask,
                mask
            ):

                break

            mask = new_mask

        # ----------------------------------------------------
        # Final fit
        # ----------------------------------------------------

        if np.sum(mask) < 2:
            return None

        try:

            slope, intercept = np.polyfit(
                x[mask],
                y[mask],
                1
            )

        except Exception:
            return None

        if slope <= 0:
            return None

        predicted = (
            slope * x[mask]
            +
            intercept
        )

        rmse = float(
            np.sqrt(
                np.mean(
                    (
                        y[mask]
                        -
                        predicted
                    ) ** 2
                )
            )
        )

        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "rmse": rmse,
            "used_points": int(
                np.sum(mask)
            ),
            "total_points": int(
                len(labels)
            )
        }

    # ========================================================
    # PIXEL → VALUE
    # ========================================================

    @staticmethod
    def pixel_to_value(
        pixel_x,
        slope,
        intercept,
        unit="CPM"
    ):

        value = (
            slope
            *
            pixel_x
            +
            intercept
        )

        unit = (
            unit or ""
        ).upper()

        # Hz
        if unit == "HZ":
            return value

        # CPM
        if unit == "CPM":
            return value / 60.0

        # RPM
        if unit == "RPM":
            return value / 60.0

        # Order / X
        if unit in (
            "ORDER",
            "X",
            "1X"
        ):
            return value

        return value

    # ========================================================
    # ANALYZE
    # ========================================================

    def analyze(
        self,
        rpm=None
    ):

        result = AxisResult()

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        ocr_items = self._ocr()

        # ----------------------------------------------------
        # Unit
        # ----------------------------------------------------

        result.unit = (
            self.detect_unit(
                ocr_items
            )
        )

        # ----------------------------------------------------
        # First attempt:
        # X labels without knowing axis Y
        # ----------------------------------------------------

        labels = self.detect_x_labels(
            ocr_items,
            axis_y=None
        )

        labels = self.merge_split_labels(
            labels
        )

        labels = self.validate_labels(
            labels
        )

        # ----------------------------------------------------
        # Axis Y
        # ----------------------------------------------------

        result.x_axis_y = (
            self.detect_x_axis_y(
                labels
            )
        )

        # ----------------------------------------------------
        # اگر Axis Y داریم،
        # یک بار دیگر OCR labels را دقیق‌تر پیدا کن
        # ----------------------------------------------------

        refined_labels = self.detect_x_labels(
            ocr_items,
            axis_y=result.x_axis_y
        )

        refined_labels = (
            self.merge_split_labels(
                refined_labels
            )
        )

        refined_labels = (
            self.validate_labels(
                refined_labels
            )
        )

        if len(refined_labels) >= 2:

            labels = refined_labels

        result.x_labels = labels

        # ----------------------------------------------------
        # Axis Step
        # ----------------------------------------------------

        result.axis_step = (
            self.detect_axis_step(
                labels
            )
        )

        # ----------------------------------------------------
        # Calibration
        # ----------------------------------------------------

        calibration = (
            self.calculate_calibration(
                labels
            )
        )

        if calibration is None:

            result.warnings.append(
                "Calibration معتبر پیدا نشد."
            )

        else:

            result.slope = (
                calibration["slope"]
            )

            result.intercept = (
                calibration["intercept"]
            )

            result.rmse = (
                calibration["rmse"]
            )

            result.pixel_x1 = (
                labels[0].pixel_x
            )

            result.value_x1 = (
                labels[0].value
            )

            result.pixel_x2 = (
                labels[-1].pixel_x
            )

            result.value_x2 = (
                labels[-1].value
            )

            # ------------------------------------------------
            # Hz / CPM / RPM
            # ------------------------------------------------

            unit = (
                result.unit or ""
            ).upper()

            if unit == "HZ":

                result.hz_per_pixel = (
                    calibration["slope"]
                )

            elif unit in (
                "CPM",
                "RPM"
            ):

                result.hz_per_pixel = (
                    calibration["slope"]
                    /
                    60.0
                )

            elif unit == "ORDER":

                if rpm is not None:

                    try:

                        rpm_value = float(
                            rpm
                        )

                        result.hz_per_pixel = (
                            calibration["slope"]
                            *
                            rpm_value
                            /
                            60.0
                        )

                    except Exception:
                        result.hz_per_pixel = None

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = 0.0

        # Axis line
        if result.x_axis_y is not None:
            confidence += 15.0

        # Labels
        if len(labels) >= 2:
            confidence += 20.0

        if len(labels) >= 3:
            confidence += 15.0

        if len(labels) >= 5:
            confidence += 10.0

        if len(labels) >= 10:
            confidence += 10.0

        # Unit
        if result.unit is not None:
            confidence += 10.0

        # Calibration
        if result.slope is not None:
            confidence += 10.0

        # RMSE
        if result.rmse is not None:

            if result.axis_step is not None:

                relative_rmse = (
                    result.rmse
                    /
                    max(
                        abs(
                            result.axis_step
                        ),
                        1e-12
                    )
                )

                if relative_rmse <= 0.02:
                    confidence += 10.0

                elif relative_rmse <= 0.05:
                    confidence += 7.0

                elif relative_rmse <= 0.10:
                    confidence += 4.0

                elif relative_rmse <= 0.20:
                    confidence += 2.0

            else:

                if result.rmse <= 1.0:
                    confidence += 5.0

        # فقط دو Label → اعتماد کمتر
        if len(labels) == 2:

            result.warnings.append(
                "Calibration بر اساس فقط دو Label انجام شد."
            )

            confidence *= 0.80

        # Unit نامشخص
        if result.unit is None:

            result.warnings.append(
                "واحد محور X به صورت قطعی تشخیص داده نشد."
            )

        result.confidence = min(
            100.0,
            float(confidence)
        )

        # ----------------------------------------------------
        # Debug
        # ----------------------------------------------------

        print()
        print(
            "[FFTAxisDetector] "
            "X-axis unit:",
            result.unit
        )

        print(
            "[FFTAxisDetector] "
            "Detected X labels:",
            len(result.x_labels)
        )

        for label in result.x_labels:

            print(
                "    "
                f"text={label.text!r} "
                f"value={label.value:.4f} "
                f"x={label.pixel_x:.1f} "
                f"y={label.pixel_y:.1f} "
                f"conf={label.confidence:.1f}"
            )

        print(
            "[FFTAxisDetector] "
            "Axis step:",
            result.axis_step
        )

        print(
            "[FFTAxisDetector] "
            "Calibration slope:",
            result.slope
        )

        print(
            "[FFTAxisDetector] "
            "Calibration intercept:",
            result.intercept
        )

        print(
            "[FFTAxisDetector] "
            "Calibration RMSE:",
            result.rmse
        )

        print(
            "[FFTAxisDetector] "
            "Hz/pixel:",
            result.hz_per_pixel
        )

        print(
            "[FFTAxisDetector] "
            "Confidence:",
            round(
                result.confidence,
                2
            )
        )

        if result.warnings:

            print(
                "[FFTAxisDetector] "
                "Warnings:"
            )

            for warning in result.warnings:

                print(
                    "   -",
                    warning
                )

        return result


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

AxisDetector = FFTAxisDetector