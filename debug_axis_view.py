from pathlib import Path
import cv2

from engine.axis_detector import FFTAxisDetector


# ============================================
# تنظیمات
# ============================================

IMAGE_PATH = Path("test_fft.png")


# ============================================
# Main
# ============================================

def main():

    print()
    print("=" * 70)
    print("FFT AXIS DEBUG VIEW")
    print("=" * 70)


    # ----------------------------
    # Load image
    # ----------------------------

    if not IMAGE_PATH.exists():

        print(
            "ERROR: Image not found"
        )
        return


    image = cv2.imread(
        str(IMAGE_PATH)
    )


    if image is None:

        print(
            "ERROR: Cannot read image"
        )
        return


    height, width = image.shape[:2]


    print()
    print("IMAGE")
    print("-" * 70)
    print("Width :", width)
    print("Height:", height)


    # ----------------------------
    # Detect axis
    # ----------------------------

    detector = FFTAxisDetector(
        str(IMAGE_PATH)
    )


    result = detector.analyze()


    axis_y = result.x_axis_y


    print()
    print("DETECTED AXIS")
    print("-" * 70)
    print(
        "X Axis Y =",
        axis_y
    )


    # ----------------------------
    # Draw blue line
    # ----------------------------

    debug = image.copy()


    cv2.line(
        debug,
        (0, int(axis_y)),
        (width, int(axis_y)),
        (255,0,0),
        5
    )


    cv2.putText(
        debug,
        f"X AXIS Y={axis_y}",
        (50, max(50, int(axis_y)-30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255,0,0),
        3
    )


    output = "debug_axis_blue.png"


    cv2.imwrite(
        output,
        debug
    )


    print()
    print("OUTPUT")
    print("-" * 70)
    print(
        "Saved:",
        output
    )


    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)



if __name__ == "__main__":
    main()