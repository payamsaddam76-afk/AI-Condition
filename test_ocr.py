import cv2
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

IMAGE_PATH = "test_fft.png"

print()
print("==============================")
print("OCR DIAGNOSTIC TEST")
print("==============================")

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise ValueError("تصویر پیدا نشد یا قابل خواندن نیست.")

print("Image:", image.shape)

gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY
)

print()
print("------------------------------")
print("TEST 1 - ORIGINAL")
print("------------------------------")

text = pytesseract.image_to_string(
    gray,
    config="--psm 11"
)

print(text)

print()
print("------------------------------")
print("TEST 2 - UPSCALE")
print("------------------------------")

upscaled = cv2.resize(
    gray,
    None,
    fx=3,
    fy=3,
    interpolation=cv2.INTER_CUBIC
)

text = pytesseract.image_to_string(
    upscaled,
    config="--psm 11"
)

print(text)

print()
print("------------------------------")
print("TEST 3 - THRESHOLD")
print("------------------------------")

threshold = cv2.adaptiveThreshold(
    upscaled,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31,
    11
)

text = pytesseract.image_to_string(
    threshold,
    config="--psm 11"
)

print(text)

cv2.imwrite(
    "ocr_debug.png",
    threshold
)

print()
print("==============================")
print("OCR DEBUG IMAGE")
print("==============================")

print("Saved: ocr_debug.png")