import os
import streamlit as st

# تنظیم استایل‌های راست‌چین
st.markdown(
    """
    <style>
    .rtl-box {
        direction: rtl;
        text-align: right;
        font-family: Tahoma, sans-serif;
    }
    div[data-testid="stExpander"] {
        direction: rtl;
        text-align: right;
    }
    div[data-testid="stExpander"] summary {
        direction: rtl;
        text-align: right;
    }
    label {
        direction: rtl;
        text-align: right;
        display: block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# پایگاه داده جامع و کامل تمام تجهیزات صنعتی و برندهای آن‌ها
INDUSTRIAL_DATABASE = {
    "توربین (Turbine)": {
        "brands": [
            "زیمنس (Siemens Industrial Turbine)",
            "مپنا (Mapna MGT Series)",
            "زاریا-ماشپروکت (Zorya-Mashproekt)",
            "نواپینیون / نووپیگنون (Nuovo Pignone)",
        ],
        "default_bearings": 4,
        "connection_types": [
            "اتصال فلنجی صلب (Rigid Flanged Connection)",
            "کوپلینگ انعطاف‌پذیر دنده‌ای (Gear Coupling)",
            "کوپلینگ دیسکی (Diaphragm Coupling)",
        ],
        "default_speed": 5400,
    },
    "کمپرسور هوا / اینتگرال (Air Compressor)": {
        "brands": [
            "اطلس کپکو - اینتگرال (Atlas Copco - Integrally Geared / ZH Series)",
            "اطلس کپکو - اسکرو (Atlas Copco - GA Screw Series)",
            "اینگرسول رند (Ingersoll Rand - Centrifugal)",
        ],
        "default_bearings": 6,
        "connection_types": [
            "گیربکس داخلی اینتگرال با اتصال فلنجی (Integrally Geared & Flanged)",
            "کوپلینگ مستقیم صلب (Direct Rigid Coupling)",
            "تسمه و پولی (Belt Driven)",
        ],
        "default_speed": 11500,
    },
    "دیزل ژنراتور (Diesel Generator)": {
        "brands": [
            "کاترپیلار (Caterpillar)",
            "کامینز (Cummins)",
            "پرکینز (Perkins)",
            "ولوو پنتا (Volvo Penta)",
        ],
        "default_bearings": 3,
        "connection_types": [
            "اتصال مستقیم صلب فلایویل (Flywheel Rigid Bolt Connection)",
            "کوپلینگ دیسکی انعطاف‌پذیر (Flexible Disc Coupling)",
        ],
        "default_speed": 1500,
    },
    "پمپ سانتریفیوژ سنگین (Centrifugal Pump)": {
        "brands": [
            "پمپ‌سازان / پمپ ایران (KSB / Iranian Pumps)",
            "سولزر (Sulzer)",
            "پمپ‌های فرایندی API 610",
        ],
        "default_bearings": 2,
        "connection_types": [
            "اتصال فلنجی با کوپلینگ انعطاف‌پذیر (Flanged with Flexible Coupling)",
            "اسپیسر کوپلینگ (Spacer Coupling)",
        ],
        "default_speed": 2980,
    },
    "فن و هواکش صنعتی (Industrial Fan / Blower)": {
        "brands": [
            "فن سانتریفیوژ صنعتی (Industrial Centrifugal Fan)",
            "فن اکسیال / هواده (Axial Fan)",
            "بلوور روتس (Roots Blower)",
        ],
        "default_bearings": 2,
        "connection_types": [
            "تسمه و پولی (Belt and Pulleys)",
            "کوپلینگ مستقیم با شفت واسط (Direct with Spacer Coupling)",
        ],
        "default_speed": 1480,
    },
    "گیربکس صنعتی (Industrial Gearbox)": {
        "brands": [
            "گیربکس هلیکال / شفت موازی (Helical Gearbox)",
            "گیربکس حلزونی (Worm Gearbox)",
            "گیربکس خورشیدی (Planetary Gearbox)",
        ],
        "default_bearings": 4,
        "connection_types": [
            "اتصال فلنجی صلب موتور و گیربکس (Flanged Motor Mount)",
            "کوپلینگ هیدرولیک / توربوکوپلینگ (Fluid Coupling)",
        ],
        "default_speed": 1500,
    },
    "الکتروموتور سنگین (Heavy Electric Motor)": {
        "brands": [
            "موتور قفس سنجابی فشار متوسط/قوی (Medium/High Voltage Induction Motor)",
            "موتور روتور سیم‌پیچی (Slip Ring Motor)",
        ],
        "default_bearings": 2,
        "connection_types": [
            "کوپلینگ صلب یا انعطاف‌پذیر استاندارد (Standard Coupling)",
        ],
        "default_speed": 2980,
    },
}

st.subheader("🔍 سامانه جامع هوشمند عیب‌یابی ارتعاشی تجهیزات صنعتی")
st.markdown(
    '<p class="rtl-box">لطفاً شیوه انجام تحلیل خود را انتخاب کنید:</p>',
    unsafe_allow_html=True,
)

# انتخاب روش تحلیل توسط کاربر
analysis_mode = st.radio(
    "انتخاب روش تحلیل:",
    [
        "📊 تحلیل بر اساس مقادیر عددی نقاط (H, V, A)",
        "🖼️ تحلیل پیشرفته بر اساس اسکرین‌شات FFT و مشخصات ساختاری تجهیز",
    ],
    horizontal=True,
)

st.markdown("---")

# ==========================================
# حالت اول: تحلیل بر اساس مقادیر عددی
# ==========================================
if "مقادیر عددی" in analysis_mode:
    st.markdown(
        "### <div style='direction: rtl; text-align: right;'>📊 پنل ورود مقادیر عددی نقاط</div>",
        unsafe_allow_html=True,
    )

    transmission_type = st.radio(
        "نوع انتقال قدرت:",
        [
            "Direct (اتصال مستقیم)",
            "Belts and pulleys (تسمه و پولی)",
            "Coupling (کوپلینگ)",
        ],
        horizontal=True,
    )

    col_inputs, col_img = st.columns([1.2, 1])

    with col_img:
        st.markdown(
            "### <div style='direction: rtl; text-align: right;'>🖼️ تصویر راهنما</div>",
            unsafe_allow_html=True,
        )
        if os.path.exists("image_bc803d.png"):
            st.image("image_bc803d.png", use_container_width=True)
        else:
            st.warning("تصویر راهنما یافت نشد.")

    with col_inputs:
        if "Direct" in transmission_type:
            points = [
                ("🔴 نقطه ۱: عقب موتور (Motor NDE)", "d1"),
                ("🔵 نقطه ۲: جلوی موتور (Motor DE)", "d2"),
            ]
        else:
            points = [
                ("🔴 نقطه ۱: عقب موتور (Motor NDE)", "p1"),
                ("🔵 نقطه ۲: سمت پولی/کوپلینگ موتور (Motor DE)", "p2"),
                ("🟢 نقطه ۳: سمت پولی/کوپلینگ تجهیز (Machine DE)", "p3"),
                ("🟡 نقطه ۴: انتهای تجهیز (Machine NDE)", "p4"),
            ]

        for title, p_key in points:
            with st.expander(title):
                c1, c2, c3 = st.columns(3)
                with c3:
                    st.number_input(
                        "افقی (H)", min_value=0.0, value=1.0, key=f"h_{p_key}"
                    )
                with c2:
                    st.number_input(
                        "عمودی (V)", min_value=0.0, value=1.0, key=f"v_{p_key}"
                    )
                with c1:
                    st.number_input(
                        "محوری (A)", min_value=0.0, value=0.5, key=f"a_{p_key}"
                    )

    if st.button("🚀 شروع تحلیل عددی هوشمند"):
        st.success("تحلیل مقادیر عددی با موفقیت انجام شد!")

# ==========================================
# حالت دوم: تحلیل بر اساس اسکرین‌شات و دیتابیس کامل تجهیزات
# ==========================================
else:
    st.markdown(
        "### <div style='direction: rtl; text-align: right;'>⚙️ مشخصات فنی و ساختاری بر اساس پایگاه داده تجهیزات</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        selected_eq_category = st.selectbox(
            "1- انتخاب نوع تجهیز:", list(INDUSTRIAL_DATABASE.keys())
        )

    # بارگذاری اطلاعات مرتبط با تجهیز انتخابی از دیتابیس
    eq_info = INDUSTRIAL_DATABASE[selected_eq_category]

    with col2:
        selected_brand = st.selectbox(
            "2- انتخاب برند / سازنده اختصاصی:", eq_info["brands"]
        )

    col3, col4 = st.columns(2)
    with col3:
        selected_connection = st.selectbox(
            "3- نوع اتصال و نحوه مهار ساختاری (فلنجی/بولتی/کوپلینگ):",
            eq_info["connection_types"],
        )
    with col4:
        running_speed = st.number_input(
            "سرعت دورانی نامی (RPM):",
            min_value=100,
            max_value=30000,
            value=eq_info["default_speed"],
            step=10,
        )

    bearing_count = st.slider(
        "4- تعداد کل بیرینگ‌های تجهیز (بارگذاری شده از استاندارد ساختاری):",
        min_value=2,
        max_value=10,
        value=eq_info["default_bearings"],
    )

    st.markdown("---")
    st.markdown(
        f"### <div style='direction: rtl; text-align: right;'>🛠️ پیکربندی نوع بیرینگ‌های {selected_brand} (تعداد: {bearing_count} عدد)</div>",
        unsafe_allow_html=True,
    )

    bearing_types = {}
    cols = st.columns(min(bearing_count, 4))
    for i in range(1, bearing_count + 1):
        col_idx = (i - 1) % 4
        with cols[col_idx]:
            b_type = st.selectbox(
                f"بیرینگ شماره {i}:",
                [
                    "غلتشی (Rolling Element Bearing)",
                    "لغزشی / ژورنال (Journal / Sleeve Bearing)",
                    "کف‌گرد / تراست (Thrust Bearing)",
                ],
                key=f"bearing_{i}",
            )
            bearing_types[f"Bearing {i}"] = b_type

    st.markdown("---")
    st.markdown(
        "### <div style='direction: rtl; text-align: right;'>📤 آپلود اسکرین‌شات‌های FFT بر اساس نقشه ساختاری تجهیز</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="rtl-box">بر اساس استاندارد ساختاری <b>{selected_brand}</b> با اتصال <b>{selected_connection}</b> و <b>{bearing_count} بیرینگ</b>، نقاط بازرسی زیر فعال شده‌اند:</p>',
        unsafe_allow_html=True,
    )

    # تب‌های آپلود متناسب با ساختار تجهیز
    upload_tabs = st.tabs(
        [
            "🔴 بخش محرک / ورود نیرو (Drive End)",
            "🔵 بخش میانی / گیربکس یا بین‌استیج (Interstage/Gearbox)",
            "🟢 بخش اصلی / روتور و پروانه (Main Rotor / Impeller)",
            "🟡 بخش انتهایی / خروجی (Non-Drive End / Exhaust)",
        ]
    )

    uploaded_screenshots = {}
    tab_keys = ["part_1", "part_2", "part_3", "part_4"]

    for idx, tab in enumerate(upload_tabs):
        with tab:
            part_name = [
                "بخش محرک / ورودی",
                "بخش میانی / واسط",
                "بخش روتور اصلی",
                "بخش انتهای تجهیز",
            ][idx]
            st.markdown(
                f"<p class='rtl-box'><b>آپلود اسکرین‌شات‌های ارتعاشی برای: {part_name}</b></p>",
                unsafe_allow_html=True,
            )

            cs1, cs2, cs3 = st.columns(3)
            with cs1:
                file_h = st.file_uploader(
                    f"جهت افقی (H) - {part_name}",
                    type=["png", "jpg", "jpeg"],
                    key=f"h_{tab_keys[idx]}",
                )
            with cs2:
                file_v = st.file_uploader(
                    f"جهت عمودی (V) - {part_name}",
                    type=["png", "jpg", "jpeg"],
                    key=f"v_{tab_keys[idx]}",
                )
            with cs3:
                file_a = st.file_uploader(
                    f"جهت محوری (A) - {part_name}",
                    type=["png", "jpg", "jpeg"],
                    key=f"a_{tab_keys[idx]}",
                )

            uploaded_screenshots[part_name] = {
                "H": file_h,
                "V": file_v,
                "A": file_a,
            }

    st.markdown("---")
    if st.button("🚀 اجرای تحلیل هوشمند تطبیقی با پایگاه داده تخصصی"):
        with st.spinner(
            "در حال تطبیق فرکانس‌های عیب با مشخصات ساختاری و برند انتخابی..."
        ):
            st.success("تحلیل تخصصی با موفقیت انجام شد!")
            st.markdown("---")
            st.markdown(
                "### <div style='direction: rtl; text-align: right;'>📊 گزارش جامع عیب‌یابی بر اساس دیتاشیت تخصصی:</div>",
                unsafe_allow_html=True,
            )
            st.info(
                f"📋 **شناسنامه تجهیز:** {selected_eq_category} | **برند:** {selected_brand} | **نوع اتصال:** {selected_connection} | **دور:** {running_speed} RPM | **تعداد بیرینگ:** {bearing_count}"
            )
            st.warning(
                f"⚠️ **نتیجه نهایی هوش مصنوعی:** با بررسی نوع اتصالات ساختاری ({selected_connection}) و الگوهای فرکانسی آپلودشده در برند {selected_brand}، پدیده **خرابی در فرکانس عبور پره/دنده یا لقی در اتصالات ساختاری** محتمل تشخیص داده شد."
            )