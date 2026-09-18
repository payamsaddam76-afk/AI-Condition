import cv2
import pytesseract
import re


IMAGE_PATH = "test_fft.png"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def normalize_text(text):
    text = text.replace(",", "")
    text = text.replace("٬", "")
    text = text.replace("٫", ".")
    return text


def extract_numbers(text):
    text = normalize_text(text)

    matches = re.findall(
        r"\b\d+(?:\.\d+)?\b",
        text
    )

    numbers = []

    for item in matches:
        try:
            numbers.append(float(item))
        except ValueError:
            pass

    return numbers


print()
print("==============================")
print("AXIS OCR NUMERIC TEST")
print("==============================")


image = cv2.imread(IMAGE_PATH)

if image is None:
    raise ValueError("Image not found.")

print("Image:", image.shape)


gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY
)


# --------------------------------
# OCR
# --------------------------------

data = pytesseract.image_to_data(
    gray,
    config="--psm 11",
    output_type=pytesseract.Output.DICT
)


print()
print("------------------------------")
print("OCR NUMERIC TOKENS")
print("------------------------------")


for i, text in enumerate(data["text"]):

    text = text.strip()

    if not text:
        continue

    numbers = extract_numbers(text)

    if not numbers:
        continue

    try:
        confidence = float(data["conf"][i])
    except:
        confidence = 0

    x = data["left"][i]
    y = data["top"][i]
    w = data["width"][i]
    h = data["height"][i]

    print(
        f"text={text!r}"
        f" | numbers={numbers}"
        f" | x={x}"
        f" | y={y}"
        f" | w={w}"
        f" | h={h}"
        f" | conf={confidence:.1f}"
    )


print()
print("==============================")
print("DONE")
print("==============================")