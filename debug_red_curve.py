
from pathlib import Path

import cv2
import numpy as np

from engine.axis_detector import FFTAxisDetector


IMAGE_PATH = Path("test_fft.png")
OUTPUT_PATH = Path("debug_red_curve_v2.png")
MASK_OUTPUT_PATH = Path("debug_red_mask_v2.png")


# ============================================================
# SETTINGS
# ============================================================

MIN_RED_AREA = 20

# Maximum allowed movement of the curve between neighboring
# columns. This prevents jumping to unrelated red objects.
MAX_JUMP = 35

# How strongly we prefer continuity with the previous point.
CONTINUITY_WEIGHT = 3.0

# Smooth only the extracted curve.
SMOOTH_WINDOW = 7


# ============================================================
# RED DETECTION
# ============================================================

def detect_red_mask(image):
    """
    Detect red pixels using HSV.

    This is intentionally specific to the current test image.
    Later we will add a universal curve-color detector.
    """

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red_1 = np.array(
        [0, 70, 50],
        dtype=np.uint8
    )

    upper_red_1 = np.array(
        [10, 255, 255],
        dtype=np.uint8
    )

    lower_red_2 = np.array(
        [170, 70, 50],
        dtype=np.uint8
    )

    upper_red_2 = np.array(
        [179, 255, 255],
        dtype=np.uint8
    )

    mask1 = cv2.inRange(
        hsv,
        lower_red_1,
        upper_red_1
    )

    mask2 = cv2.inRange(
        hsv,
        lower_red_2,
        upper_red_2
    )

    mask = cv2.bitwise_or(
        mask1,
        mask2
    )

    # Remove isolated pixels.
    kernel = np.ones(
        (3, 3),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    # Close tiny gaps.
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    return mask


# ============================================================
# REMOVE SMALL COMPONENTS
# ============================================================

def remove_small_components(mask):
    """
    Remove tiny disconnected red objects.

    We do NOT remove all small objects aggressively because
    a real FFT peak can also be relatively small.
    """

    number_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask,
        connectivity=8
    )

    cleaned = np.zeros_like(mask)

    for label in range(1, number_labels):

        area = stats[label, cv2.CC_STAT_AREA]

        if area >= MIN_RED_AREA:
            cleaned[labels == label] = 255

    return cleaned


# ============================================================
# BUILD CANDIDATES PER COLUMN
# ============================================================

def get_column_candidates(mask, axis_y):
    """
    For every X column, return all possible Y positions.

    We intentionally keep multiple candidates because a column
    may contain several red objects.
    """

    height, width = mask.shape

    candidates = {}

    upper_limit = max(
        0,
        int(axis_y) - 4
    )

    for x in range(width):

        ys = np.where(
            mask[:upper_limit, x] > 0
        )[0]

        if len(ys) == 0:
            continue

        # Group neighboring red pixels into small vertical groups.
        groups = []

        current = [int(ys[0])]

        for y in ys[1:]:

            y = int(y)

            if y - current[-1] <= 2:
                current.append(y)
            else:
                groups.append(current)
                current = [y]

        groups.append(current)

        column_points = []

        for group in groups:

            # Use the CENTER of the red stroke.
            center_y = int(
                round(
                    np.mean(group)
                )
            )

            column_points.append(center_y)

        candidates[x] = column_points

    return candidates


# ============================================================
# CONTINUOUS CURVE TRACKING
# ============================================================

def track_curve(candidates):
    """
    Track the most continuous red curve.

    Instead of selecting the uppermost red pixel, we select
    the candidate that stays closest to the previous curve point.
    """

    if not candidates:
        return (
            np.array([], dtype=np.int32),
            np.array([], dtype=np.int32)
        )

    all_x = sorted(candidates.keys())

    curve_x = []
    curve_y = []

    previous_y = None

    for x in all_x:

        ys = candidates[x]

        if not ys:
            continue

        # ----------------------------------------------------
        # First point
        # ----------------------------------------------------

        if previous_y is None:

            # Start near the upper/middle graph area.
            selected_y = ys[0]

        else:

            # ------------------------------------------------
            # Score each candidate
            # ------------------------------------------------

            scored = []

            for y in ys:

                distance = abs(
                    y - previous_y
                )

                # Strong penalty for sudden jumps.
                if distance > MAX_JUMP:
                    jump_penalty = 1000
                else:
                    jump_penalty = 0

                score = (
                    distance * CONTINUITY_WEIGHT
                    + jump_penalty
                )

                scored.append(
                    (score, y)
                )

            scored.sort(
                key=lambda item: item[0]
            )

            selected_y = scored[0][1]

        curve_x.append(x)
        curve_y.append(selected_y)

        previous_y = selected_y

    return (
        np.asarray(curve_x, dtype=np.int32),
        np.asarray(curve_y, dtype=np.int32)
    )


# ============================================================
# REMOVE SUDDEN JUMPS
# ============================================================

def remove_large_jumps(x, y):
    """
    Remove points caused by accidental jumps to another object.
    """

    if len(x) < 3:
        return x, y

    keep_x = [int(x[0])]
    keep_y = [int(y[0])]

    previous_y = int(y[0])

    for i in range(1, len(x)):

        current_y = int(y[i])

        if abs(current_y - previous_y) <= MAX_JUMP:

            keep_x.append(int(x[i]))
            keep_y.append(current_y)

            previous_y = current_y

    return (
        np.asarray(keep_x, dtype=np.int32),
        np.asarray(keep_y, dtype=np.int32)
    )


# ============================================================
# INTERPOLATE
# ============================================================

def interpolate_curve(x, y):
    """
    Fill small missing sections in the curve.
    """

    if len(x) < 2:
        return x, y

    order = np.argsort(x)

    x = x[order]
    y = y[order]

    unique_x, indices = np.unique(
        x,
        return_index=True
    )

    unique_y = y[indices]

    if len(unique_x) < 2:
        return unique_x, unique_y

    full_x = np.arange(
        int(unique_x[0]),
        int(unique_x[-1]) + 1
    )

    full_y = np.interp(
        full_x,
        unique_x,
        unique_y
    )

    return (
        full_x.astype(np.int32),
        np.round(full_y).astype(np.int32)
    )


# ============================================================
# SMOOTH CURVE
# ============================================================

def smooth_curve(y):
    """
    Light smoothing.

    We deliberately keep this weak so real FFT peaks are not
    flattened.
    """

    if len(y) < SMOOTH_WINDOW:
        return y

    kernel = np.ones(
        SMOOTH_WINDOW,
        dtype=float
    )

    kernel /= np.sum(kernel)

    smoothed = np.convolve(
        y.astype(float),
        kernel,
        mode="same"
    )

    # Prevent edge artifacts.
    half = SMOOTH_WINDOW // 2

    smoothed[:half] = y[:half]
    smoothed[-half:] = y[-half:]

    return np.round(
        smoothed
    ).astype(np.int32)


# ============================================================
# DRAW
# ============================================================

def draw_result(image, x, y, axis_y):

    output = image.copy()

    if len(x) >= 2:

        points = np.column_stack(
            (x, y)
        )

        # BLUE = extracted curve
        cv2.polylines(
            output,
            [points],
            False,
            (255, 0, 0),
            2
        )

    # X axis
    cv2.line(
        output,
        (0, int(axis_y)),
        (
            output.shape[1],
            int(axis_y)
        ),
        (255, 0, 0),
        3
    )

    cv2.putText(
        output,
        "BLUE = EXTRACTED FFT CURVE V2",
        (30, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("FFT CURVE EXTRACTION V2")
    print("=" * 70)

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    if not IMAGE_PATH.exists():

        print()
        print("ERROR:")
        print("test_fft.png not found.")

        return

    image = cv2.imread(
        str(IMAGE_PATH)
    )

    if image is None:

        print()
        print("ERROR:")
        print("Cannot read image.")

        return

    height, width = image.shape[:2]

    print()
    print("IMAGE")
    print("-" * 70)
    print("Width :", width)
    print("Height:", height)

    # --------------------------------------------------------
    # Axis detection
    # --------------------------------------------------------

    print()
    print("AXIS")
    print("-" * 70)

    detector = FFTAxisDetector(
        str(IMAGE_PATH)
    )

    result = detector.analyze()

    axis_y = result.x_axis_y

    print(
        "X Axis Y =",
        axis_y
    )

    if axis_y is None:

        print()
        print("ERROR:")
        print("X axis not detected.")

        return

    # --------------------------------------------------------
    # Red mask
    # --------------------------------------------------------

    print()
    print("RED MASK")
    print("-" * 70)

    mask = detect_red_mask(
        image
    )

    red_pixels_before = int(
        np.count_nonzero(mask)
    )

    print(
        "Red pixels:",
        red_pixels_before
    )

    # --------------------------------------------------------
    # Remove tiny components
    # --------------------------------------------------------

    mask = remove_small_components(
        mask
    )

    red_pixels_after = int(
        np.count_nonzero(mask)
    )

    print(
        "After cleanup:",
        red_pixels_after
    )

    # Save mask for visual inspection.
    cv2.imwrite(
        str(MASK_OUTPUT_PATH),
        mask
    )

    print(
        "Mask saved:",
        MASK_OUTPUT_PATH
    )

    # --------------------------------------------------------
    # Candidates
    # --------------------------------------------------------

    print()
    print("CANDIDATES")
    print("-" * 70)

    candidates = get_column_candidates(
        mask,
        axis_y
    )

    print(
        "Columns with candidates:",
        len(candidates)
    )

    if len(candidates) < 10:

        print()
        print("ERROR:")
        print("Not enough curve candidates.")

        return

    # --------------------------------------------------------
    # Track curve
    # --------------------------------------------------------

    print()
    print("CURVE TRACKING")
    print("-" * 70)

    x, y = track_curve(
        candidates
    )

    print(
        "Tracked points:",
        len(x)
    )

    if len(x) < 10:

        print()
        print("ERROR:")
        print("Curve tracking failed.")

        return

    # --------------------------------------------------------
    # Remove accidental jumps
    # --------------------------------------------------------

    x, y = remove_large_jumps(
        x,
        y
    )

    print(
        "After jump filtering:",
        len(x)
    )

    # --------------------------------------------------------
    # Interpolate
    # --------------------------------------------------------

    x, y = interpolate_curve(
        x,
        y
    )

    print(
        "After interpolation:",
        len(x)
    )

    # --------------------------------------------------------
    # Smooth
    # --------------------------------------------------------

    y = smooth_curve(
        y
    )

    print(
        "After smoothing:",
        len(y)
    )

    # --------------------------------------------------------
    # Draw
    # --------------------------------------------------------

    debug = draw_result(
        image,
        x,
        y,
        axis_y
    )

    success = cv2.imwrite(
        str(OUTPUT_PATH),
        debug
    )

    if not success:

        print()
        print("ERROR:")
        print("Could not save output.")

        return

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    print()
    print("RESULT")
    print("-" * 70)

    print(
        "X range:",
        int(np.min(x)),
        "->",
        int(np.max(x))
    )

    print(
        "Y range:",
        int(np.min(y)),
        "->",
        int(np.max(y))
    )

    print()
    print(
        "Output:",
        OUTPUT_PATH
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print()

    print(
        "Open debug_curve_blue_v2.png"
    )

    print(
        "The BLUE line should stay on the RED FFT curve."
    )

    print()


if __name__ == "__main__":
    main()

