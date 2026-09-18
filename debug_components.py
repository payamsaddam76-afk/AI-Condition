
from pathlib import Path

import cv2
import numpy as np


IMAGE_PATH = Path("test_fft.png")
OUTPUT_PATH = Path("debug_components.png")
MASK_OUTPUT_PATH = Path("debug_components_mask.png")


# ============================================================
# SETTINGS
# ============================================================

MIN_COMPONENT_AREA = 5


# ============================================================
# RED MASK
# ============================================================

def detect_red_mask(image):

    hsv = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2HSV
    )

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

    # Same basic cleanup that produced the good mask.
    kernel = np.ones(
        (3, 3),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    return mask


# ============================================================
# COMPONENT ANALYSIS
# ============================================================

def analyze_components(mask):

    number_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            mask,
            connectivity=8
        )
    )

    components = []

    for label in range(1, number_labels):

        x = int(
            stats[label, cv2.CC_STAT_LEFT]
        )

        y = int(
            stats[label, cv2.CC_STAT_TOP]
        )

        w = int(
            stats[label, cv2.CC_STAT_WIDTH]
        )

        h = int(
            stats[label, cv2.CC_STAT_HEIGHT]
        )

        area = int(
            stats[label, cv2.CC_STAT_AREA]
        )

        cx = float(
            centroids[label][0]
        )

        cy = float(
            centroids[label][1]
        )

        if area < MIN_COMPONENT_AREA:
            continue

        components.append(
            {
                "label": label,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "area": area,
                "cx": cx,
                "cy": cy
            }
        )

    components.sort(
        key=lambda item: item["area"],
        reverse=True
    )

    return (
        labels,
        components
    )


# ============================================================
# DRAW COMPONENTS
# ============================================================

def draw_components(image, labels, components):

    output = image.copy()

    # Generate deterministic colors from component index.
    rng = np.random.default_rng(12345)

    for index, component in enumerate(components):

        label = component["label"]

        # Random visible color.
        color = tuple(
            int(v)
            for v in rng.integers(
                40,
                255,
                size=3
            )
        )

        component_mask = (
            labels == label
        ).astype(np.uint8) * 255

        # Paint component pixels.
        output[component_mask > 0] = color

        # Bounding box.
        x = component["x"]
        y = component["y"]
        w = component["w"]
        h = component["h"]

        cv2.rectangle(
            output,
            (x, y),
            (x + w, y + h),
            color,
            2
        )

        # Component number.
        text = (
            f"#{index + 1} "
            f"A={component['area']}"
        )

        text_y = max(
            20,
            y - 5
        )

        cv2.putText(
            output,
            text,
            (x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("FFT RED MASK - CONNECTED COMPONENT ANALYSIS")
    print("=" * 75)

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    if not IMAGE_PATH.exists():

        print()
        print("ERROR: test_fft.png not found.")
        return

    image = cv2.imread(
        str(IMAGE_PATH)
    )

    if image is None:

        print()
        print("ERROR: Cannot read image.")
        return

    height, width = image.shape[:2]

    print()
    print("IMAGE")
    print("-" * 75)
    print("Width :", width)
    print("Height:", height)

    # --------------------------------------------------------
    # Mask
    # --------------------------------------------------------

    print()
    print("RED MASK")
    print("-" * 75)

    mask = detect_red_mask(
        image
    )

    red_pixels = int(
        np.count_nonzero(mask)
    )

    print(
        "Red pixels:",
        red_pixels
    )

    cv2.imwrite(
        str(MASK_OUTPUT_PATH),
        mask
    )

    print(
        "Mask saved:",
        MASK_OUTPUT_PATH
    )

    # --------------------------------------------------------
    # Components
    # --------------------------------------------------------

    print()
    print("CONNECTED COMPONENTS")
    print("-" * 75)

    labels, components = analyze_components(
        mask
    )

    print(
        "Total components:",
        len(components)
    )

    print()

    print(
        f"{'No.':<6}"
        f"{'Area':<10}"
        f"{'X':<8}"
        f"{'Y':<8}"
        f"{'W':<8}"
        f"{'H':<8}"
        f"{'CX':<12}"
        f"{'CY':<12}"
    )

    print("-" * 75)

    for index, component in enumerate(
        components[:30],
        start=1
    ):

        print(
            f"{index:<6}"
            f"{component['area']:<10}"
            f"{component['x']:<8}"
            f"{component['y']:<8}"
            f"{component['w']:<8}"
            f"{component['h']:<8}"
            f"{component['cx']:<12.1f}"
            f"{component['cy']:<12.1f}"
        )

    # --------------------------------------------------------
    # Draw
    # --------------------------------------------------------

    print()
    print("DRAWING COMPONENTS")
    print("-" * 75)

    debug = draw_components(
        image,
        labels,
        components
    )

    cv2.imwrite(
        str(OUTPUT_PATH),
        debug
    )

    print(
        "Saved:",
        OUTPUT_PATH
    )

    # --------------------------------------------------------
    # Largest component
    # --------------------------------------------------------

    if components:

        largest = components[0]

        print()
        print("LARGEST COMPONENT")
        print("-" * 75)

        print(
            "Area       :",
            largest["area"]
        )

        print(
            "Bounding X :",
            largest["x"],
            "->",
            largest["x"] + largest["w"]
        )

        print(
            "Bounding Y :",
            largest["y"],
            "->",
            largest["y"] + largest["h"]
        )

        print(
            "Width      :",
            largest["w"]
        )

        print(
            "Height     :",
            largest["h"]
        )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print("=" * 75)
    print("DONE")
    print("=" * 75)
    print()

    print(
        "Open:",
        OUTPUT_PATH
    )

    print()
    print(
        "Each colored component is labeled #1, #2, #3, ..."
    )

    print(
        "We are looking for the component(s) containing the actual FFT curve."
    )

    print()


if __name__ == "__main__":
    main()
