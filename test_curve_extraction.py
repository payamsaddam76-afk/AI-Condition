# test_curve_extraction.py

from pathlib import Path
import cv2
import numpy as np


IMAGE_PATH = Path("test_fft.png")
OUTPUT_PATH = Path("debug_fft_curve.png")


# ============================================================
# پیدا کردن ROI نمودار
# ============================================================

def crop_graph_area(image):

    h, w = image.shape[:2]

    # طبق تست قبلی:
    # محور X حدود y=434 است
    #
    # نمودار معمولاً بالای محور قرار دارد

    x1 = int(w * 0.05)
    x2 = int(w * 0.95)

    y1 = int(h * 0.08)
    y2 = int(h * 0.88)

    return image[y1:y2, x1:x2], (x1, y1)


# ============================================================
# استخراج خطوط
# ============================================================

def extract_curve(roi):

    gray = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2GRAY
    )


    # افزایش کنتراست

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8,8)
    )

    enhanced = clahe.apply(gray)


    # Threshold تطبیقی

    binary = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8
    )


    # حذف خطوط افقی Grid

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (40,1)
    )


    horizontal = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        horizontal_kernel
    )


    # حذف خطوط عمودی Grid

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1,40)
    )


    vertical = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        vertical_kernel
    )


    grid = cv2.bitwise_or(
        horizontal,
        vertical
    )


    clean = cv2.subtract(
        binary,
        grid
    )


    # اتصال قسمت‌های شکسته منحنی

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3,3)
    )


    clean = cv2.morphologyEx(
        clean,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2
    )


    return clean



# ============================================================
# پیدا کردن Contour اصلی
# ============================================================

def find_curve_contour(mask):


    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE
    )


    if not contours:
        return None


    candidates=[]


    for c in contours:

        area = cv2.contourArea(c)

        length = cv2.arcLength(
            c,
            False
        )


        if length < 100:
            continue


        candidates.append(
            (
                length,
                c
            )
        )


    if not candidates:
        return None


    # بلندترین خط احتمالاً Spectrum است

    candidates.sort(
        key=lambda x:x[0],
        reverse=True
    )


    return candidates[0][1]



# ============================================================
# استخراج نقاط منحنی
# ============================================================

def contour_to_points(contour):

    points=[]

    for p in contour:

        x,y = p[0]

        points.append(
            (
                int(x),
                int(y)
            )
        )

    return points



# ============================================================
# Main
# ============================================================

def main():

    print("="*70)
    print("FFT CURVE EXTRACTION TEST")
    print("="*70)


    image=cv2.imread(
        str(IMAGE_PATH)
    )


    if image is None:

        print(
            "Image not found"
        )

        return


    roi, offset = crop_graph_area(
        image
    )


    mask = extract_curve(
        roi
    )


    contour = find_curve_contour(
        mask
    )


    debug = image.copy()


    if contour is None:

        print(
            "No curve detected"
        )

    else:


        points = contour_to_points(
            contour
        )


        print(
            "Curve points:",
            len(points)
        )


        # انتقال مختصات به تصویر اصلی

        contour_shifted = contour.copy()

        contour_shifted[:,:,0] += offset[0]
        contour_shifted[:,:,1] += offset[1]


        cv2.drawContours(
            debug,
            [
                contour_shifted
            ],
            -1,
            (0,0,255),
            2
        )


        print(
            "Contour extracted"
        )


    cv2.imwrite(
        str(OUTPUT_PATH),
        debug
    )


    print()
    print(
        "Saved:",
        OUTPUT_PATH
    )


if __name__=="__main__":
    main()