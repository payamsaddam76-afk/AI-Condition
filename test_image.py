import cv2

from engine.fft_image import FFTImageExtractor


IMAGE_PATH = "test_fft.png"


extractor = FFTImageExtractor(
    IMAGE_PATH
)

print()
print("==========================")
print("UNIVERSAL FFT IMAGE TEST")
print("==========================")

print(
    "Image loaded successfully!"
)

print(
    "Width:",
    extractor.width
)

print(
    "Height:",
    extractor.height
)


# ---------------------------------------------------------
# AUTOMATIC ANALYSIS
# ---------------------------------------------------------

result = extractor.analyze()


print()
print("==========================")
print("AUTOMATIC GRAPH DETECTION")
print("==========================")

print(
    "Graph ROI:",
    result["graph_roi"]
)


candidates = result[
    "peak_candidates"
]


print()
print("==========================")
print("IMAGE PEAK CANDIDATES")
print("==========================")


for pixel_x, strength in candidates[:30]:

    print(
        f"Pixel={pixel_x:4d}"
        f"   Strength={strength:8.2f}"
    )


# ---------------------------------------------------------
# SAVE DEBUG IMAGE
# ---------------------------------------------------------

debug_image = (
    extractor.draw_peak_candidates(
        result["graph_image"],
        candidates
    )
)


cv2.imwrite(
    "fft_debug.png",
    debug_image
)


print()
print("==========================")
print("DEBUG")
print("==========================")

print(
    "Debug image saved:"
)

print(
    "fft_debug.png"
)

print()
print(
    "Number of candidates:",
    len(candidates)
)