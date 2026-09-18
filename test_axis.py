from engine.fft_image import FFTImageExtractor
from engine.axis_detector import UniversalAxisDetector


IMAGE_PATH = "test_fft.png"


print()
print("==============================")
print("UNIVERSAL AXIS DETECTOR TEST")
print("==============================")


extractor = FFTImageExtractor(
    IMAGE_PATH
)


image = extractor.image


detector = UniversalAxisDetector(
    image
)


result = detector.analyze()


print()
print("X Axis Y:")
print(
    result.x_axis_y
)


print()
print("Detected Unit:")
print(
    result.unit
)


print()
print("X Axis Labels:")
print(
    "------------------------------"
)


for label in result.x_labels:

    print(
        f"text={label.text!r}"
        f" | value={label.value}"
        f" | x={label.x:.1f}"
        f" | y={label.y:.1f}"
        f" | confidence={label.confidence:.1f}"
    )


print()
print("Calibration:")
print(
    "------------------------------"
)

print(
    "Pixel X1:",
    result.pixel_x1
)

print(
    "Value X1:",
    result.value_x1
)

print(
    "Pixel X2:",
    result.pixel_x2
)

print(
    "Value X2:",
    result.value_x2
)


print()
print("Confidence:")
print(
    f"{result.confidence * 100:.1f}%"
)


print()
print("Warnings:")

for warning in result.warnings:
    print(
        "-",
        warning
    )