from pathlib import Path

import cv2
import numpy as np

from engine.axis_detector import FFTAxisDetector


IMAGE_PATH = Path("test_fft.png")
OUTPUT_PATH = Path("debug_continuous_trace.png")


# ============================================================
# SETTINGS
# ============================================================

MIN_RUN_HEIGHT = 1

# حداکثر جابه‌جایی مجاز مسیر بین دو ستون
MAX_Y_JUMP = 12

# حداکثر فاصله‌ای که اجازه می‌دهیم یک مسیر قطع شود
MAX_GAP = 5

# تعداد ستون‌هایی که یک مسیر باید حداقل داشته باشد
MIN_TRACK_LENGTH = 20

# فاصله از محور X
AXIS_MARGIN = 5


# ============================================================
# RED MASK
# ============================================================

def detect_red_mask(image):

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
# FIND VERTICAL RUNS
# ============================================================

def get_vertical_runs(mask, x, axis_y):

    column = mask[:, x] > 0

    # حذف قسمت محور X و پایین آن
    limit = max(
        0,
        int(axis_y) - AXIS_MARGIN
    )

    column[limit:] = False

    runs = []

    start = None

    for y, value in enumerate(column):

        if value and start is None:
            start = y

        elif not value and start is not None:

            end = y - 1

            if end - start + 1 >= MIN_RUN_HEIGHT:

                runs.append(
                    {
                        "y1": start,
                        "y2": end,
                        "center": (start + end) / 2.0,
                        "height": end - start + 1
                    }
                )

            start = None

    if start is not None:

        end = len(column) - 1

        if end - start + 1 >= MIN_RUN_HEIGHT:

            runs.append(
                {
                    "y1": start,
                    "y2": end,
                    "center": (start + end) / 2.0,
                    "height": end - start + 1
                }
            )

    return runs


# ============================================================
# ALL RUNS
# ============================================================

def collect_runs(mask, axis_y):

    height, width = mask.shape

    all_runs = []

    for x in range(width):

        runs = get_vertical_runs(
            mask,
            x,
            axis_y
        )

        all_runs.append(runs)

    return all_runs


# ============================================================
# TRACK
# ============================================================

def track_continuous_paths(all_runs):

    tracks = []

    active = []

    for x, runs in enumerate(all_runs):

        used_run_indices = set()

        # ----------------------------------------------------
        # Try to extend existing tracks
        # ----------------------------------------------------

        for track in active:

            best_index = None
            best_distance = None

            last_y = track["points"][-1]["y"]

            for i, run in enumerate(runs):

                if i in used_run_indices:
                    continue

                distance = abs(
                    run["center"] - last_y
                )

                if distance > MAX_Y_JUMP:
                    continue

                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_distance = distance
                    best_index = i

            if best_index is not None:

                run = runs[best_index]

                track["points"].append(
                    {
                        "x": x,
                        "y": run["center"],
                        "height": run["height"]
                    }
                )

                track["last_x"] = x
                track["gap"] = 0

                used_run_indices.add(
                    best_index
                )

            else:

                track["gap"] += 1

        # ----------------------------------------------------
        # Remove dead tracks
        # ----------------------------------------------------

        still_active = []

        for track in active:

            if track["gap"] <= MAX_GAP:

                still_active.append(track)

            else:

                tracks.append(track)

        active = still_active

        # ----------------------------------------------------
        # Start new tracks
        # ----------------------------------------------------

        for i, run in enumerate(runs):

            if i in used_run_indices:
                continue

            active.append(
                {
                    "points": [
                        {
                            "x": x,
                            "y": run["center"],
                            "height": run["height"]
                        }
                    ],
                    "last_x": x,
                    "gap": 0
                }
            )

    # پایان مسیرهای فعال
    tracks.extend(active)

    # --------------------------------------------------------
    # Filter
    # --------------------------------------------------------

    filtered = []

    for track in tracks:

        if len(track["points"]) >= MIN_TRACK_LENGTH:

            filtered.append(track)

    filtered.sort(
        key=lambda t: len(t["points"]),
        reverse=True
    )

    return filtered


# ============================================================
# SELECT BEST TRACE
# ============================================================

def select_best_trace(tracks, image_height):

    if not tracks:
        return None

    scored = []

    for track in tracks:

        points = track["points"]

        length = len(points)

        xs = np.array(
            [p["x"] for p in points],
            dtype=float
        )

        ys = np.array(
            [p["y"] for p in points],
            dtype=float
        )

        # ----------------------------------------------------
        # Coverage
        # ----------------------------------------------------

        if len(xs) > 1:

            coverage = (
                xs[-1] - xs[0]
            )

        else:

            coverage = 0

        # ----------------------------------------------------
        # Smoothness
        # ----------------------------------------------------

        if len(ys) >= 3:

            dy = np.diff(ys)

            smoothness = float(
                np.mean(np.abs(dy))
            )

        else:

            smoothness = 999

        # ----------------------------------------------------
        # Prefer traces above X axis
        # but do not force them to top
        # ----------------------------------------------------

        mean_y = float(
            np.mean(ys)
        )

        # Score
        score = (
            coverage * 3.0
            + length * 1.0
            - smoothness * 20.0
            - mean_y * 0.02
        )

        scored.append(
            (
                score,
                track
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return scored[0][1]


# ============================================================
# DRAW ALL TRACKS
# ============================================================

def draw_tracks(
    image,
    tracks,
    best_track,
    axis_y
):

    output = image.copy()

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

    # --------------------------------------------------------
    # Draw all candidate tracks in thin colors
    # --------------------------------------------------------

    rng = np.random.default_rng(123)

    for index, track in enumerate(tracks):

        if track is best_track:
            continue

        color = tuple(
            int(v)
            for v in rng.integers(
                80,
                230,
                size=3
            )
        )

        points = np.array(
            [
                [
                    int(p["x"]),
                    int(round(p["y"]))
                ]
                for p in track["points"]
            ],
            dtype=np.int32
        )

        if len(points) >= 2:

            cv2.polylines(
                output,
                [points],
                False,
                color,
                1
            )

    # --------------------------------------------------------
    # Best track
    # --------------------------------------------------------

    if best_track is not None:

        points = np.array(
            [
                [
                    int(p["x"]),
                    int(round(p["y"]))
                ]
                for p in best_track["points"]
            ],
            dtype=np.int32
        )

        if len(points) >= 2:

            cv2.polylines(
                output,
                [points],
                False,
                (255, 0, 255),
                3
            )

        for p in best_track["points"]:

            cv2.circle(
                output,
                (
                    int(p["x"]),
                    int(round(p["y"]))
                ),
                2,
                (0, 255, 255),
                -1
            )

    # --------------------------------------------------------
    # Text
    # --------------------------------------------------------

    cv2.putText(
        output,
        "MAGENTA = BEST CONTINUOUS TRACE",
        (30, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 0, 255),
        2
    )

    cv2.putText(
        output,
        f"TRACKS = {len(tracks)}",
        (30, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("FFT CONTINUOUS TRACE DEBUG")
    print("=" * 75)

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
    # Axis
    # --------------------------------------------------------

    detector = FFTAxisDetector(
        str(IMAGE_PATH)
    )

    axis_result = detector.analyze()

    axis_y = axis_result.x_axis_y

    print()
    print("X AXIS")
    print("-" * 75)
    print("X Axis Y =", axis_y)

    if axis_y is None:

        print()
        print("ERROR: X axis not detected.")
        return

    # --------------------------------------------------------
    # Mask
    # --------------------------------------------------------

    print()
    print("RED MASK")
    print("-" * 75)

    mask = detect_red_mask(
        image
    )

    print(
        "Red pixels:",
        int(np.count_nonzero(mask))
    )

    # --------------------------------------------------------
    # Runs
    # --------------------------------------------------------

    print()
    print("VERTICAL RUNS")
    print("-" * 75)

    all_runs = collect_runs(
        mask,
        axis_y
    )

    total_runs = sum(
        len(runs)
        for runs in all_runs
    )

    print(
        "Total vertical runs:",
        total_runs
    )

    # --------------------------------------------------------
    # Tracking
    # --------------------------------------------------------

    print()
    print("TRACKING")
    print("-" * 75)

    tracks = track_continuous_paths(
        all_runs
    )

    print(
        "Valid tracks:",
        len(tracks)
    )

    print()

    print(
        f"{'Track':<10}"
        f"{'Points':<10}"
        f"{'X Start':<10}"
        f"{'X End':<10}"
        f"{'Coverage':<12}"
    )

    print("-" * 55)

    for index, track in enumerate(
        tracks[:20],
        start=1
    ):

        points = track["points"]

        x_start = points[0]["x"]
        x_end = points[-1]["x"]

        print(
            f"{index:<10}"
            f"{len(points):<10}"
            f"{x_start:<10}"
            f"{x_end:<10}"
            f"{x_end - x_start:<12}"
        )

    # --------------------------------------------------------
    # Best
    # --------------------------------------------------------

    best_track = select_best_trace(
        tracks,
        height
    )

    print()
    print("BEST TRACE")
    print("-" * 75)

    if best_track is None:

        print(
            "No suitable continuous trace found."
        )

    else:

        points = best_track["points"]

        print(
            "Points  :",
            len(points)
        )

        print(
            "X start :",
            points[0]["x"]
        )

        print(
            "X end   :",
            points[-1]["x"]
        )

        print(
            "Coverage:",
            points[-1]["x"]
            - points[0]["x"]
        )

    # --------------------------------------------------------
    # Draw
    # --------------------------------------------------------

    debug = draw_tracks(
        image,
        tracks,
        best_track,
        axis_y
    )

    cv2.imwrite(
        str(OUTPUT_PATH),
        debug
    )

    print()
    print("OUTPUT")
    print("-" * 75)
    print(
        "Saved:",
        OUTPUT_PATH
    )

    print()
    print("=" * 75)
    print("DONE")
    print("=" * 75)
    print()


if __name__ == "__main__":
    main()