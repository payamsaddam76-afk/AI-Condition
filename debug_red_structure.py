from pathlib import Path

import cv2
import numpy as np


IMAGE_PATH = Path("test_fft.png")

OUTPUT_PATH = Path("debug_red_structure.png")
PROFILE_PATH = Path("debug_red_profile.png")


# ============================================================
# SETTINGS
# ============================================================

# Ignore red pixels very close to the X axis.
AXIS_MARGIN = 4

# Keep even a single red pixel.
MIN_RED_PIXELS_PER_COLUMN = 1

# IMPORTANT:
# Do not remove small red components.
# We want to preserve small FFT peaks.
MIN_COMPONENT_AREA = 1

# Maximum vertical gap between red pixels
# for considering them part of the same group.
MAX_VERTICAL_GAP = 2


# ============================================================
# RED MASK
# ============================================================

def detect_red_mask(image):

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

    # --------------------------------------------------------
    # Red range 1
    # --------------------------------------------------------

    lower_red_1 = np.array(
        [0, 100, 80],
        dtype=np.uint8
    )

    upper_red_1 = np.array(
        [10, 255, 255],
        dtype=np.uint8
    )

    # --------------------------------------------------------
    # Red range 2
    # --------------------------------------------------------

    lower_red_2 = np.array(
        [170, 100, 80],
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

    # --------------------------------------------------------
    # Combine red ranges
    # --------------------------------------------------------

    mask = cv2.bitwise_or(
        mask1,
        mask2
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # No MORPH_OPEN here.
    #
    # We intentionally do not remove thin structures because
    # a real FFT peak may be only a few pixels wide.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Connected components
    #
    # We keep ALL components because:
    #
    # small component != necessarily noise
    #
    # It can be a real small FFT peak.
    # --------------------------------------------------------

    num_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            mask,
            connectivity=8
        )
    )

    cleaned_mask = np.zeros_like(mask)

    for i in range(1, num_labels):

        area = stats[
            i,
            cv2.CC_STAT_AREA
        ]

        if area >= MIN_COMPONENT_AREA:

            cleaned_mask[
                labels == i
            ] = 255

    return cleaned_mask


# ============================================================
# COLUMN PROFILE
# ============================================================

def build_column_profile(mask, axis_y):

    height, width = mask.shape

    profile = []

    for x in range(width):

        # ----------------------------------------------------
        # Get ALL red pixels in this column
        # ----------------------------------------------------

        ys = np.where(
            mask[:, x] > 0
        )[0]

        # ----------------------------------------------------
        # Ignore X axis and everything below it
        # ----------------------------------------------------

        ys = ys[
            ys < int(axis_y) - AXIS_MARGIN
        ]

        if len(ys) < MIN_RED_PIXELS_PER_COLUMN:

            profile.append(
                {
                    "x": x,
                    "count": 0,
                    "min_y": None,
                    "max_y": None,
                    "center_y": None,
                    "median_y": None,
                    "groups": []
                }
            )

            continue

        # ----------------------------------------------------
        # Find ALL independent vertical groups
        # ----------------------------------------------------

        groups = []

        start = int(ys[0])
        previous = int(ys[0])

        for y in ys[1:]:

            y = int(y)

            # New group if vertical gap is too large.
            if (
                y - previous
                > MAX_VERTICAL_GAP
            ):

                groups.append(
                    {
                        "min_y": start,
                        "max_y": previous
                    }
                )

                start = y

            previous = y

        # ----------------------------------------------------
        # Add final group
        # ----------------------------------------------------

        groups.append(
            {
                "min_y": start,
                "max_y": previous
            }
        )

        # ----------------------------------------------------
        # Calculate information for EVERY group
        # ----------------------------------------------------

        for group in groups:

            group_min = group["min_y"]
            group_max = group["max_y"]

            group_pixels = ys[
                (ys >= group_min)
                &
                (ys <= group_max)
            ]

            group["count"] = int(
                len(group_pixels)
            )

            group["height"] = int(
                group_max
                - group_min
                + 1
            )

            group["center_y"] = float(
                np.mean(group_pixels)
            )

            group["median_y"] = float(
                np.median(group_pixels)
            )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # ALL groups are preserved.
        #
        # Nothing is selected or discarded here.
        # ----------------------------------------------------

        profile.append(
            {
                "x": x,

                "count": int(
                    len(ys)
                ),

                "min_y": int(
                    np.min(ys)
                ),

                "max_y": int(
                    np.max(ys)
                ),

                "center_y": float(
                    np.mean(ys)
                ),

                "median_y": float(
                    np.median(ys)
                ),

                "groups": groups
            }
        )

    return profile


# ============================================================
# DRAW STRUCTURE
# ============================================================

def draw_structure(
    image,
    profile,
    axis_y
):

    output = image.copy()

    # --------------------------------------------------------
    # Draw X axis
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Draw ALL red groups
    # --------------------------------------------------------

    for item in profile:

        x = item["x"]

        if item["count"] == 0:
            continue

        groups = item.get(
            "groups",
            []
        )

        # ----------------------------------------------------
        # Every group is drawn separately
        # ----------------------------------------------------

        for group in groups:

            min_y = int(
                group["min_y"]
            )

            max_y = int(
                group["max_y"]
            )

            center_y = int(
                round(
                    group["center_y"]
                )
            )

            median_y = int(
                round(
                    group["median_y"]
                )
            )

            # ------------------------------------------------
            # GREEN
            # Full red group
            # ------------------------------------------------

            cv2.line(
                output,
                (x, min_y),
                (x, max_y),
                (0, 255, 0),
                1
            )

            # ------------------------------------------------
            # BLUE
            # Group center
            # ------------------------------------------------

            cv2.circle(
                output,
                (x, center_y),
                1,
                (255, 0, 0),
                -1
            )

            # ------------------------------------------------
            # YELLOW
            # Group median
            # ------------------------------------------------

            cv2.circle(
                output,
                (x, median_y),
                1,
                (0, 255, 255),
                -1
            )

    # --------------------------------------------------------
    # Legend
    # --------------------------------------------------------

    cv2.putText(
        output,
        "GREEN = ALL RED GROUPS",
        (30, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2
    )

    cv2.putText(
        output,
        "BLUE = GROUP CENTER",
        (30, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 0, 0),
        2
    )

    cv2.putText(
        output,
        "YELLOW = GROUP MEDIAN",
        (30, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 255),
        2
    )

    return output


# ============================================================
# DRAW PROFILE
# ============================================================

def draw_profile(profile):

    height = 500
    width = len(profile)

    canvas = np.ones(
        (height, width, 3),
        dtype=np.uint8
    ) * 255

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # This profile is ONLY a structural diagnostic.
    #
    # It is NOT used as the actual FFT amplitude.
    # --------------------------------------------------------

    counts = np.array(
        [
            item["count"]
            for item in profile
        ],
        dtype=float
    )

    if (
        len(counts) > 0
        and np.max(counts) > 0
    ):

        normalized = (
            counts
            / np.max(counts)
        )

        y_values = (
            height
            - 20
            - normalized
            * (height - 40)
        )

        points = np.column_stack(
            (
                np.arange(width),
                y_values.astype(
                    np.int32
                )
            )
        )

        cv2.polylines(
            canvas,
            [points],
            False,
            (0, 0, 255),
            2
        )

    cv2.putText(
        canvas,
        "RED STRUCTURE PER X COLUMN",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        2
    )

    cv2.putText(
        canvas,
        "NOT ACTUAL FFT AMPLITUDE",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        2
    )

    return canvas


# ============================================================
# PRINT INTERESTING COLUMNS
# ============================================================

def print_interesting_columns(profile):

    valid = [
        item
        for item in profile
        if item["count"] > 0
    ]

    if not valid:
        return

    # --------------------------------------------------------
    # Sort by total red pixels
    # --------------------------------------------------------

    strongest = sorted(
        valid,
        key=lambda item: item["count"],
        reverse=True
    )

    print()
    print(
        "COLUMNS WITH MOST RED PIXELS"
    )

    print(
        "-" * 105
    )

    print(
        f"{'X':<8}"
        f"{'Count':<10}"
        f"{'Groups':<10}"
        f"{'MinY':<10}"
        f"{'MaxY':<10}"
        f"{'Center':<12}"
        f"{'Median':<12}"
    )

    print(
        "-" * 105
    )

    for item in strongest[:30]:

        print(
            f"{item['x']:<8}"
            f"{item['count']:<10}"
            f"{len(item['groups']):<10}"
            f"{item['min_y']:<10}"
            f"{item['max_y']:<10}"
            f"{item['center_y']:<12.1f}"
            f"{item['median_y']:<12.1f}"
        )

        # ----------------------------------------------------
        # Print every group
        # ----------------------------------------------------

        for index, group in enumerate(
            item["groups"],
            start=1
        ):

            print(
                f"    Group {index}: "
                f"Y={group['min_y']}"
                f" -> "
                f"{group['max_y']} | "
                f"Count={group['count']} | "
                f"Height={group['height']} | "
                f"Center={group['center_y']:.1f}"
            )


# ============================================================
# STRUCTURE SUMMARY
# ============================================================

def print_summary(profile):

    total_groups = 0
    multi_group_columns = 0
    maximum_groups = 0

    for item in profile:

        group_count = len(
            item.get(
                "groups",
                []
            )
        )

        total_groups += group_count

        if group_count > 1:

            multi_group_columns += 1

        maximum_groups = max(
            maximum_groups,
            group_count
        )

    print()
    print(
        "STRUCTURE SUMMARY"
    )

    print(
        "-" * 75
    )

    print(
        "Total red groups:",
        total_groups
    )

    print(
        "Columns with multiple groups:",
        multi_group_columns
    )

    print(
        "Maximum groups in one column:",
        maximum_groups
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("FFT RED STRUCTURE ANALYSIS")
    print("=" * 75)

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    if not IMAGE_PATH.exists():

        print()
        print(
            "ERROR: test_fft.png not found."
        )

        return

    image = cv2.imread(
        str(IMAGE_PATH)
    )

    if image is None:

        print()
        print(
            "ERROR: Cannot read image."
        )

        return

    height, width = image.shape[:2]

    print()
    print("IMAGE")
    print("-" * 75)

    print(
        "Width :",
        width
    )

    print(
        "Height:",
        height
    )

    # --------------------------------------------------------
    # Detect X axis
    # --------------------------------------------------------

    from engine.axis_detector import FFTAxisDetector

    detector = FFTAxisDetector(
        str(IMAGE_PATH)
    )

    result = detector.analyze()

    axis_y = result.x_axis_y

    print()
    print("X AXIS")
    print("-" * 75)

    print(
        "X Axis Y =",
        axis_y
    )

    if axis_y is None:

        print()
        print(
            "ERROR: X axis not detected."
        )

        return

    # --------------------------------------------------------
    # Detect red mask
    # --------------------------------------------------------

    print()
    print("RED MASK")
    print("-" * 75)

    mask = detect_red_mask(
        image
    )

    total_red_pixels = int(
        np.count_nonzero(mask)
    )

    print(
        "Total red pixels:",
        total_red_pixels
    )

    # --------------------------------------------------------
    # Build profile
    # --------------------------------------------------------

    print()
    print("COLUMN PROFILE")
    print("-" * 75)

    profile = build_column_profile(
        mask,
        axis_y
    )

    valid_columns = sum(
        1
        for item in profile
        if item["count"] > 0
    )

    print(
        "Columns containing red:",
        valid_columns,
        "/",
        width
    )

    # --------------------------------------------------------
    # Print statistics
    # --------------------------------------------------------

    print_interesting_columns(
        profile
    )

    print_summary(
        profile
    )

    # --------------------------------------------------------
    # Draw structure
    # --------------------------------------------------------

    debug = draw_structure(
        image,
        profile,
        axis_y
    )

    cv2.imwrite(
        str(OUTPUT_PATH),
        debug
    )

    # --------------------------------------------------------
    # Draw diagnostic profile
    # --------------------------------------------------------

    profile_image = draw_profile(
        profile
    )

    cv2.imwrite(
        str(PROFILE_PATH),
        profile_image
    )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print("OUTPUT")
    print("-" * 75)

    print(
        "Structure:",
        OUTPUT_PATH
    )

    print(
        "Profile  :",
        PROFILE_PATH
    )

    print()
    print("=" * 75)
    print("DONE")
    print("=" * 75)
    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()