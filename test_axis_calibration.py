# test_axis_calibration.py

from pathlib import Path
import re

import numpy as np
import pytesseract
import cv2

from engine.axis_detector import FFTAxisDetector


# ============================================================
# تنظیمات
# ============================================================

IMAGE_PATH = Path("test_fft.png")

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ============================================================
# ابزارهای OCR
# ============================================================

def normalize_digits(text):
    """
    تبدیل ارقام فارسی و عربی به انگلیسی
    """

    if text is None:
        return ""

    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )

    return text.translate(translation)


def clean_numeric_text(text):
    """
    تمیز کردن متن OCR برای استخراج عدد
    """

    text = normalize_digits(text)

    # حذف کاراکترهای اضافی ابتدا و انتها
    text = text.strip()

    # OCR ممکن است + یا ~ یا © یا ... بخواند
    text = re.sub(r"^[^0-9.\-]+", "", text)
    text = re.sub(r"[^0-9.\-]+$", "", text)

    return text


def parse_number(text):
    """
    تبدیل متن OCR به عدد
    """

    if text is None:
        return None

    text = clean_numeric_text(text)

    if not text:
        return None

    # مواردی مثل:
    # 2000
    # 4000
    # 0.0004
    # 50.000
    #
    # را قبول می‌کنیم.

    try:
        return float(text)
    except ValueError:
        return None


# ============================================================
# OCR کامل تصویر
# ============================================================

def get_ocr_data(image):
    """
    OCR با مختصات هر Token
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # بزرگ‌نمایی برای OCR
    scale = 2.0

    enlarged = cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    # threshold
    binary = cv2.threshold(
        enlarged,
        180,
        255,
        cv2.THRESH_BINARY
    )[1]

    data = pytesseract.image_to_data(
        binary,
        config="--psm 6",
        output_type=pytesseract.Output.DICT
    )

    results = []

    n = len(data["text"])

    for i in range(n):

        text = data["text"][i].strip()

        if not text:
            continue

        try:
            confidence = float(data["conf"][i])
        except Exception:
            confidence = 0

        x = int(data["left"][i] / scale)
        y = int(data["top"][i] / scale)
        w = int(data["width"][i] / scale)
        h = int(data["height"][i] / scale)

        results.append({
            "text": text,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "confidence": confidence
        })

    return results


# ============================================================
# پیدا کردن Labelهای محور X
# ============================================================

def select_x_axis_labels(
    ocr_items,
    axis_y,
    image_height
):
    """
    فقط Tokenهایی که احتمالاً مربوط به محور X هستند.
    """

    candidates = []

    # محدوده اطراف محور X
    #
    # معمولاً Labelهای X زیر محور قرار دارند.
    #
    min_y = axis_y - 10
    max_y = axis_y + image_height * 0.16

    for item in ocr_items:

        text = item["text"]

        value = parse_number(text)

        if value is None:
            continue

        x = item["x"]
        y = item["y"]
        w = item["w"]
        h = item["h"]

        center_x = x + w / 2
        center_y = y + h / 2

        # باید نزدیک محور X باشد
        if center_y < min_y:
            continue

        if center_y > max_y:
            continue

        # عددهای خیلی کوچک اعشاری مثل 0.0004
        # معمولاً متعلق به Y axis هستند
        if abs(value) < 1:
            continue

        # Labelهای خیلی دور از پایین/بالای محور حذف شوند
        if h > image_height * 0.08:
            continue

        candidates.append({
            "text": text,
            "value": value,
            "pixel_x": center_x,
            "pixel_y": center_y,
            "confidence": item["confidence"]
        })

    return candidates


# ============================================================
# بازسازی OCR های شکسته
# ============================================================

def merge_split_axis_labels(labels):
    """
    OCR گاهی 40000 را این‌طور می‌خواند:

        40
        000

    این تابع Tokenهای نزدیک را بررسی می‌کند و در صورت امکان
    آن‌ها را به یک عدد تبدیل می‌کند.
    """

    labels = sorted(
        labels,
        key=lambda item: item["pixel_x"]
    )

    used = set()
    merged = []

    for i, current in enumerate(labels):

        if i in used:
            continue

        current_text = clean_numeric_text(
            current["text"]
        )

        current_value = current["value"]

        # ----------------------------------------
        # دنبال Token بعدی می‌گردیم
        # ----------------------------------------

        merged_item = None

        for j in range(i + 1, len(labels)):

            if j in used:
                continue

            nxt = labels[j]

            distance = (
                nxt["pixel_x"]
                - current["pixel_x"]
            )

            # Tokenهای خیلی دور را بررسی نکن
            if distance > 45:
                break

            nxt_text = clean_numeric_text(
                nxt["text"]
            )

            # فقط اگر هر دو بخش عددی باشند
            if not nxt_text.isdigit():
                continue

            if not current_text.isdigit():
                continue

            # ------------------------------------
            # مثال:
            #
            # 40 + 000 = 40000
            # ------------------------------------

            combined = current_text + nxt_text

            try:
                combined_value = float(combined)
            except Exception:
                continue

            # فقط اعداد بزرگ و منطقی
            if combined_value < 1000:
                continue

            # میانگین موقعیت دو Token
            combined_x = (
                current["pixel_x"]
                + nxt["pixel_x"]
            ) / 2

            merged_item = {
                "text": combined,
                "value": combined_value,
                "pixel_x": combined_x,
                "pixel_y": (
                    current["pixel_y"]
                    + nxt["pixel_y"]
                ) / 2,
                "confidence": min(
                    current["confidence"],
                    nxt["confidence"]
                )
            }

            used.add(j)
            break

        if merged_item is not None:

            merged.append(merged_item)

        else:

            merged.append(current)

    return merged


# ============================================================
# حذف Labelهای نامعتبر
# ============================================================

def clean_axis_labels(labels):
    """
    حذف موارد مشکوک OCR
    """

    cleaned = []

    for item in labels:

        value = item["value"]

        # محور فرکانس نباید مقدار منفی داشته باشد
        if value < 0:
            continue

        # مقادیر خیلی کوچک احتمالاً Y-axis هستند
        if value < 100:
            continue

        # Confidence خیلی پایین
        if item["confidence"] < 25:
            continue

        cleaned.append(item)

    return cleaned


# ============================================================
# تشخیص Step محور
# ============================================================

def estimate_axis_step(labels):
    """
    پیدا کردن فاصله واقعی غالب بین Labelهای محور.

    مثال:

        2000
        4000
        6000
        8000

    نتیجه:

        step = 2000

    نکته مهم:
    اگر اختلاف واقعی Labelها 2000 باشد،
    نباید 500 یا 1000 انتخاب شود فقط چون
    2000 مضربی از آن‌هاست.
    """

    values = sorted(
        set(
            round(float(item["value"]), 6)
            for item in labels
        )
    )

    if len(values) < 2:
        return None

    diffs = np.diff(values)

    # فقط اختلاف‌های مثبت
    diffs = diffs[
        diffs > 0
    ]

    if len(diffs) == 0:
        return None

    # --------------------------------------------------------
    # ابتدا Median اختلاف واقعی Labelها
    # --------------------------------------------------------

    median_diff = float(
        np.median(diffs)
    )

    # --------------------------------------------------------
    # اگر اختلاف‌ها تقریباً یکسان باشند،
    # همان اختلاف را Step واقعی در نظر بگیر.
    # --------------------------------------------------------

    relative_errors = np.abs(
        diffs - median_diff
    ) / max(
        median_diff,
        1e-9
    )

    # اگر حداقل 60 درصد اختلاف‌ها
    # نزدیک Median باشند
    close_ratio = np.mean(
        relative_errors < 0.05
    )

    if close_ratio >= 0.60:
        return median_diff

    # --------------------------------------------------------
    # در حالت OCR خراب:
    # Stepهای متعارف را بررسی می‌کنیم.
    # --------------------------------------------------------

    possible_steps = [
        10,
        20,
        50,
        100,
        200,
        500,
        1000,
        2000,
        2500,
        5000,
        10000
    ]

    best_step = None
    best_score = -1

    for step in possible_steps:

        score = 0.0

        for diff in diffs:

            # چند برابر Step است؟
            ratio = diff / step

            nearest = round(ratio)

            if nearest < 1:
                continue

            error = abs(
                ratio - nearest
            )

            # هرچه نزدیک‌تر به مضرب صحیح باشد،
            # امتیاز بیشتر
            if error < 0.05:
                score += 3.0

            elif error < 0.10:
                score += 2.0

            elif error < 0.15:
                score += 1.0

        # ----------------------------------------------------
        # جریمه برای Stepهای کوچک‌تر
        #
        # مثلاً اگر diff = 2000 باشد،
        # Step=500 هم از نظر ریاضی ممکن است،
        # اما Step=2000 ترجیح داده می‌شود.
        # ----------------------------------------------------

        score += step / max(
            possible_steps
        ) * 0.01

        if score > best_score:

            best_score = score
            best_step = step

    # --------------------------------------------------------
    # اگر چیزی پیدا نشد، Median
    # --------------------------------------------------------

    if best_step is None:
        return median_diff

    return float(best_step)
# ============================================================
# ساخت Sequence معتبر
# ============================================================

def build_axis_sequence(labels):
    """
    ساخت دنباله معتبر محور X.

    هدف:

    2000 @ x=455
    4000 @ x=510
    6000 @ x=565
    ...

    """

    if len(labels) < 2:
        return []

    labels = sorted(
        labels,
        key=lambda item: item["pixel_x"]
    )

    step = estimate_axis_step(labels)

    if step is None:
        return []

    result = []

    for item in labels:

        value = item["value"]

        # مقدار باید تقریباً روی شبکه Step باشد
        ratio = value / step

        nearest = round(ratio)

        error = abs(
            ratio - nearest
        )

        if error > 0.10:
            continue

        # ----------------------------------------
        # بررسی فاصله Pixel
        # ----------------------------------------

        if result:

            previous = result[-1]

            dv = (
                value
                - previous["value"]
            )

            dx = (
                item["pixel_x"]
                - previous["pixel_x"]
            )

            if dx <= 0:
                continue

            # اگر یک جهش خیلی بزرگ عددی وجود دارد
            # احتمال OCR اشتباه است
            expected_multiples = round(
                dv / step
            )

            if expected_multiples < 1:
                continue

            if expected_multiples > 10:
                continue

        result.append(item)

    # ----------------------------------------
    # حذف نقاطی که دنباله مناسبی نمی‌سازند
    # ----------------------------------------

    if len(result) < 2:
        return []

    return result


# ============================================================
# Robust Calibration
# ============================================================

def robust_calibration(labels):
    """
    محاسبه رابطه:

        Value = slope * Pixel + intercept

    با حذف Outlierها
    """

    if len(labels) < 2:
        return None

    x = np.array(
        [
            item["pixel_x"]
            for item in labels
        ],
        dtype=float
    )

    y = np.array(
        [
            item["value"]
            for item in labels
        ],
        dtype=float
    )

    # ----------------------------------------
    # مرحله اول Regression
    # ----------------------------------------

    slope, intercept = np.polyfit(
        x,
        y,
        1
    )

    predicted = (
        slope * x
        + intercept
    )

    residuals = np.abs(
        y - predicted
    )

    # ----------------------------------------
    # تعیین Threshold مقاوم
    # ----------------------------------------

    median_error = np.median(
        residuals
    )

    threshold = max(
        50.0,
        median_error * 3.0
    )

    mask = (
        residuals <= threshold
    )

    # حداقل دو نقطه
    if np.sum(mask) < 2:
        mask = np.ones(
            len(x),
            dtype=bool
        )

    # ----------------------------------------
    # Regression نهایی
    # ----------------------------------------

    x2 = x[mask]
    y2 = y[mask]

    slope, intercept = np.polyfit(
        x2,
        y2,
        1
    )

    predicted2 = (
        slope * x2
        + intercept
    )

    rmse = np.sqrt(
        np.mean(
            (y2 - predicted2) ** 2
        )
    )

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "rmse": float(rmse),
        "used_points": int(np.sum(mask)),
        "total_points": int(len(x)),
        "mask": mask
    }


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 70)
    print("UNIVERSAL FFT AXIS CALIBRATION")
    print("=" * 70)

    # ----------------------------------------
    # Load Image
    # ----------------------------------------

    if not IMAGE_PATH.exists():

        print(
            f"ERROR: Image not found: {IMAGE_PATH}"
        )

        return

    image = cv2.imread(
        str(IMAGE_PATH)
    )

    if image is None:

        print(
            "ERROR: Cannot read image."
        )

        return

    height, width = image.shape[:2]

    print()
    print("IMAGE")
    print("-" * 70)
    print(f"Width  : {width}")
    print(f"Height : {height}")

    # ----------------------------------------
    # Axis Detector
    # ----------------------------------------

    detector = FFTAxisDetector(
        str(IMAGE_PATH)
    )

    axis_result = detector.analyze()

    axis_y = axis_result.x_axis_y

    # ----------------------------------------
    # DEBUG DRAW AXIS LINE BLUE
    # ----------------------------------------

    debug_image = image.copy()

    cv2.line(
        debug_image,
        (0, int(axis_y)),
        (width, int(axis_y)),
        (255, 0, 0),   # BLUE (BGR)
        4
    )

    cv2.putText(
        debug_image,
        f"X AXIS Y={axis_y}",
        (50, max(40, int(axis_y)-20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    cv2.imwrite(
        "debug_axis_blue.png",
        debug_image
    )

    print()
    print("DEBUG IMAGE")
    print("-" * 70)
    print(
        "Saved: debug_axis_blue.png"
    )

    print()
    print("X AXIS")
    print("-" * 70)

    print(
        f"X Axis Y = {axis_y}"
    )

    # ----------------------------------------
    # OCR
    # ----------------------------------------

    print()
    print("OCR")
    print("-" * 70)

    ocr_items = get_ocr_data(
        image
    )

    print(
        f"OCR tokens = {len(ocr_items)}"
    )

    # ----------------------------------------
    # انتخاب Labelهای X
    # ----------------------------------------

    labels = select_x_axis_labels(
        ocr_items,
        axis_y,
        height
    )

    print()
    print("RAW X AXIS LABELS")
    print("-" * 70)

    for item in labels:

        print(
            f"value={item['value']:10.2f} "
            f"pixel={item['pixel_x']:8.2f} "
            f"conf={item['confidence']:5.1f} "
            f"text='{item['text']}'"
        )

    # ----------------------------------------
    # Merge OCR fragments
    # ----------------------------------------

    labels = merge_split_axis_labels(
        labels
    )

    # ----------------------------------------
    # Clean
    # ----------------------------------------

    labels = clean_axis_labels(
        labels
    )

    # مرتب‌سازی بر اساس Pixel
    labels = sorted(
        labels,
        key=lambda item: item["pixel_x"]
    )

    print()
    print("CLEANED LABELS")
    print("-" * 70)

    for item in labels:

        print(
            f"{item['value']:10.2f}"
            f" @ pixel={item['pixel_x']:8.2f}"
            f"  conf={item['confidence']:5.1f}"
            f"  text='{item['text']}'"
        )

    # ----------------------------------------
    # ساخت Sequence
    # ----------------------------------------

    sequence = build_axis_sequence(
        labels
    )

    print()
    print("VALIDATED X AXIS")
    print("-" * 70)

    for item in sequence:

        print(
            f"{item['value']:10.2f}"
            f" @ pixel={item['pixel_x']:8.2f}"
        )

    if len(sequence) < 2:

        print()
        print(
            "ERROR: Could not build valid axis sequence."
        )

        return

    # ----------------------------------------
    # Step
    # ----------------------------------------

    step = estimate_axis_step(
        sequence
    )

    print()
    print("AXIS STEP")
    print("-" * 70)

    print(
        f"Detected Step = {step:.4f}"
    )

    # ----------------------------------------
    # Calibration
    # ----------------------------------------

    calibration = robust_calibration(
        sequence
    )

    if calibration is None:

        print(
            "ERROR: Calibration failed."
        )

        return

    slope = calibration["slope"]
    intercept = calibration["intercept"]
    rmse = calibration["rmse"]

    print()
    print("CALIBRATION")
    print("-" * 70)

    print(
        "Value = "
        f"{slope:.8f} * Pixel "
        f"+ {intercept:.8f}"
    )

    print(
        f"RMSE = {rmse:.4f} CPM"
    )

    print(
        f"CPM / Pixel = {slope:.8f}"
    )

    print(
        f"Hz / Pixel = {slope / 60:.8f}"
    )

    print(
        f"Used points = "
        f"{calibration['used_points']} / "
        f"{calibration['total_points']}"
    )

    # ----------------------------------------
    # کیفیت Calibration
    # ----------------------------------------

    print()
    print("CALIBRATION QUALITY")
    print("-" * 70)

    if rmse < 20:

        print(
            "Excellent calibration"
        )

    elif rmse < 50:

        print(
            "Good calibration"
        )

    elif rmse < 100:

        print(
            "Acceptable calibration"
        )

    else:

        print(
            "Calibration needs improvement"
        )

    # ----------------------------------------
    # Test چند نقطه
    # ----------------------------------------

    print()
    print("CALIBRATION TEST")
    print("-" * 70)

    test_pixels = [
        sequence[0]["pixel_x"],
        sequence[len(sequence) // 2]["pixel_x"],
        sequence[-1]["pixel_x"]
    ]

    for pixel in test_pixels:

        value = (
            slope * pixel
            + intercept
        )

        hz = value / 60.0

        print(
            f"Pixel {pixel:8.2f}"
            f" -> {value:10.2f} CPM"
            f" -> {hz:10.4f} Hz"
        )

    # ----------------------------------------
    # خروجی نهایی قابل استفاده
    # ----------------------------------------

    print()
    print("FINAL CALIBRATION OBJECT")
    print("-" * 70)

    print(
        {
            "unit": "CPM",
            "slope_cpm_per_pixel": round(
                slope,
                8
            ),
            "intercept_cpm": round(
                intercept,
                8
            ),
            "hz_per_pixel": round(
                slope / 60,
                8
            ),
            "rmse_cpm": round(
                rmse,
                4
            ),
            "points_used": calibration[
                "used_points"
            ]
        }
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()