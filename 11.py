"""
FFT Peak Detector (نسخه‌ی بهبودیافته)
------------------
این اسکریپت یک پنجره‌ی انتخاب فایل باز می‌کند تا عکس نمودار FFT را انتخاب کنید.
سپس:
    1) از شما می‌خواهد با کشیدن یک مستطیل، فقط ناحیه‌ی داخل محورها را انتخاب کنید
       (تا برچسب محور، عنوان و اعداد وارد پردازش نشوند).
    2) از شما می‌خواهد روی خود خط منحنی کلیک کنید تا رنگ آن به‌صورت خودکار
       شناسایی شود (به‌جای آستانه‌گذاری خام که با خطوط شبکه/گرید اشتباه می‌شود).
    3) خطوط شبکه (grid) را حذف می‌کند و سیگنال یک‌بعدی را استخراج می‌کند.
    4) پیک‌ها را تشخیص می‌دهد و نتیجه را نمایش/ذخیره می‌کند.

نیازمندی‌ها (یک‌بار نصب کنید):
    pip install opencv-python numpy scipy matplotlib

اجرا:
    python fft_peak_detector.py

خروجی:
    - نموداری که پیک‌های تشخیص داده‌شده را روی سیگنال استخراج‌شده نشان می‌دهد
    - یک فایل CSV با موقعیت و ارتفاع پیک‌ها در همان پوشه‌ی عکس ورودی
"""

import os
import sys
import csv
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt


def choose_image():
    """پنجره‌ی انتخاب فایل را باز می‌کند و مسیر عکس انتخاب‌شده را برمی‌گرداند."""
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="عکس نمودار FFT را انتخاب کنید",
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
    )
    root.destroy()
    return path


def select_plot_area(img):
    """
    با کشیدن ماوس، کاربر فقط ناحیه‌ی داخل محورها (بدون برچسب/عنوان) را انتخاب می‌کند.
    اگر چیزی انتخاب نشود، کل عکس استفاده می‌شود.
    """
    print("یک مستطیل دور ناحیه‌ی داخل نمودار (بدون محورها و برچسب‌ها) بکش، سپس ENTER یا SPACE بزن.")
    print("برای لغو، ESC بزن.")
    roi = cv2.selectROI("ناحیه نمودار را انتخاب کنید - سپس Enter", img, showCrosshair=True)
    cv2.destroyAllWindows()
    x, y, w, h = roi
    if w == 0 or h == 0:
        return img, (0, 0)
    cropped = img[y:y + h, x:x + w]
    return cropped, (x, y)


def pick_curve_color(img):
    """
    کاربر روی خط منحنی کلیک می‌کند تا رنگ آن (در فضای HSV) استخراج شود.
    اگر کلیک نشود، حالت پیش‌فرض (خط تیره روی پس‌زمینه روشن) استفاده می‌شود.
    """
    picked = {"color": None}

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            picked["color"] = img[y, x].copy()  # BGR

    win = "روی خط منحنی کلیک کن (سپس یک کلید بزن) - برای رد شدن فقط کلید بزن"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_click)
    cv2.imshow(win, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return picked["color"]


def remove_grid_lines(mask):
    """
    خطوط افقی و عمودی بلند (شبکه/محور) را از ماسک باینری حذف می‌کند،
    چون این خطوط معمولاً طولانی و صاف هستند برخلاف منحنی سیگنال.
    """
    h, w = mask.shape
    horizontal = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 15, 15), 1))
    )
    vertical = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 15, 15)))
    )
    grid = cv2.bitwise_or(horizontal, vertical)
    cleaned = cv2.bitwise_and(mask, cv2.bitwise_not(grid))
    return cleaned


def build_mask(img, curve_color_bgr, color_tolerance=25):
    """
    اگر رنگ خط مشخص شده باشد، بر اساس نزدیکی رنگ در فضای HSV ماسک می‌سازد.
    در غیر این صورت، از آستانه‌گذاری Otsu روی تصویر خاکستری استفاده می‌کند.
    """
    if curve_color_bgr is not None:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        target = cv2.cvtColor(
            np.uint8([[curve_color_bgr]]), cv2.COLOR_BGR2HSV
        )[0][0]
        lower = np.array([
            max(int(target[0]) - color_tolerance, 0),
            max(int(target[1]) - 60, 0),
            max(int(target[2]) - 60, 0),
        ])
        upper = np.array([
            min(int(target[0]) + color_tolerance, 179),
            min(int(target[1]) + 60, 255),
            min(int(target[2]) + 60, 255),
        ])
        mask = cv2.inRange(hsv, lower, upper)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    mask = remove_grid_lines(mask)

    # ضخیم‌تر کردن جزئی خط برای پرکردن شکاف‌های کوچک (مثلاً نقطه‌چین)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return mask


def extract_signal_from_image(cropped_img, curve_color_bgr):
    """
    از ناحیه‌ی برش‌خورده‌ی نمودار، خط منحنی را جدا کرده
    و آن را به یک سیگنال یک‌بعدی (برای هر ستون پیکسل، یک مقدار y) تبدیل می‌کند.
    """
    mask = build_mask(cropped_img, curve_color_bgr)
    h, w = mask.shape
    signal = np.full(w, np.nan)

    for x in range(w):
        col_pixels = np.where(mask[:, x] > 0)[0]
        if len(col_pixels) > 0:
            # اگر چند نقطه در یک ستون باشد (مثلاً برخورد با نویز)، نزدیک‌ترین خوشه به بالا را ترجیح می‌دهیم
            signal[x] = col_pixels.mean()

    nan_mask = np.isnan(signal)
    if nan_mask.all():
        raise ValueError(
            "هیچ خطی تشخیص داده نشد. یا ناحیه‌ی اشتباهی انتخاب شده، یا رنگ خط درست پیک نشده.\n"
            "دوباره اجرا کن و روی خودِ خط منحنی کلیک کن."
        )
    if nan_mask.any():
        signal[nan_mask] = np.interp(
            np.flatnonzero(nan_mask),
            np.flatnonzero(~nan_mask),
            signal[~nan_mask]
        )

    signal = h - signal  # معکوس‌کردن محور y چون مبدأ تصویر از بالاست
    return signal, mask


def detect_peaks(signal, prominence_ratio=0.08, min_distance=15):
    """
    تشخیص هوشمند پیک‌ها با نرمال‌سازی نسبت به دامنه‌ی سیگنال،
    تا روی عکس‌های مختلف با مقیاس‌های متفاوت هم درست کار کند.
    """
    sig_range = signal.max() - signal.min()
    prominence = max(sig_range * prominence_ratio, 1e-6)

    peaks, properties = find_peaks(
        signal,
        prominence=prominence,
        distance=min_distance
    )
    return peaks, properties


def save_results_csv(image_path, peaks, signal, properties):
    """نتایج را در کنار عکس ورودی به‌صورت CSV ذخیره می‌کند."""
    base, _ = os.path.splitext(image_path)
    out_path = base + "_peaks.csv"

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["peak_index", "pixel_x", "pixel_y_value", "prominence"])
        prominences = properties.get("prominences", [None] * len(peaks))
        for i, (p, prom) in enumerate(zip(peaks, prominences)):
            writer.writerow([i + 1, int(p), float(signal[p]), float(prom) if prom is not None else ""])

    return out_path


def plot_results(signal, peaks, mask):
    """نمودار سیگنال استخراج‌شده، ماسک تشخیص خط، و پیک‌های یافت‌شده را نمایش می‌دهد."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    axes[0].imshow(mask, cmap="gray", aspect="auto")
    axes[0].set_title("ماسک تشخیص‌داده‌شده از خط منحنی (برای بررسی درستی تشخیص)")
    axes[0].set_xlabel("پیکسل x")
    axes[0].set_ylabel("پیکسل y")

    axes[1].plot(signal, label="سیگنال استخراج‌شده از عکس", linewidth=1.2)
    axes[1].plot(peaks, signal[peaks], "rx", markersize=10, markeredgewidth=2, label="پیک‌های تشخیص داده‌شده")
    axes[1].set_xlabel("موقعیت پیکسل (محور x)")
    axes[1].set_ylabel("دامنه (پیکسل، معکوس‌شده)")
    axes[1].set_title(f"تشخیص پیک از روی FFT — تعداد پیک‌ها: {len(peaks)}")
    axes[1].legend()

    plt.tight_layout()
    plt.show()


def main():
    image_path = choose_image()
    if not image_path:
        print("هیچ فایلی انتخاب نشد. برنامه بسته می‌شود.")
        return

    try:
        full_img = cv2.imread(image_path)
        if full_img is None:
            raise ValueError("عکس خوانده نشد. مسیر یا فرمت فایل را بررسی کنید.")

        cropped_img, _ = select_plot_area(full_img)
        curve_color = pick_curve_color(cropped_img)

        signal, mask = extract_signal_from_image(cropped_img, curve_color)
        peaks, properties = detect_peaks(signal, prominence_ratio=0.08, min_distance=15)

        if len(peaks) == 0:
            messagebox.showwarning("نتیجه", "هیچ پیکی با تنظیمات فعلی پیدا نشد.\nاگر نمودار پیک واضحی دارد، مقدار prominence_ratio را در کد کمتر کنید.")
        else:
            csv_path = save_results_csv(image_path, peaks, signal, properties)
            print(f"تعداد پیک‌های یافت‌شده: {len(peaks)}")
            print(f"موقعیت پیک‌ها (پیکسل x): {peaks.tolist()}")
            print(f"فایل نتایج ذخیره شد در: {csv_path}")
            messagebox.showinfo(
                "نتیجه",
                f"تعداد پیک‌های یافت‌شده: {len(peaks)}\nفایل CSV ذخیره شد:\n{csv_path}"
            )

        plot_results(signal, peaks, mask)

    except Exception as e:
        messagebox.showerror("خطا", str(e))
        print(f"خطا: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()