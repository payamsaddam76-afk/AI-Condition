import streamlit as st
from PIL import Image
from google import genai
import pandas as pd
from io import BytesIO

# تنظیمات ظاهر صفحه
st.set_page_config(page_title="AI Vibration Cloud Analyzer", layout="wide")

st.title("🎛️ سامانه ابری و هوشمند تحلیل ارتعاشات ماشین‌آلات")
st.markdown("این ابزار اسکرین‌شاتِ نمودار FFT را تحلیل کرده، گزارش مهندسی می‌سازد و خروجی اکسل ارائه می‌دهد.")

# دریافت کلید API (در فضای ابری می‌توان آن را امن‌تر هم ذخیره کرد، فعلاً از سشن/سایدبار می‌گیریم)
st.sidebar.header("تنظیمات اتصال")
api_key = st.sidebar.text_input("Google Gemini API Key:", type="password", value="")

if 'history' not in st.session_state:
    st.session_state.history = []

if api_key:
    client = genai.Client(api_key=api_key)

    uploaded_file = st.file_uploader("تصویر اسکرین‌شات (FFT یا گزارش ماشین) را انتخاب کنید...",
                                     type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, caption='تصویر آپلود شده', width='stretch')

        with col2:
            st.subheader("وضعیت پردازش")
            machine_name_input = st.text_input("نام یا کد تجهیز:", value="موتور/پمپ 01")

            if st.button("🚀 تحلیل هوشمند و ثبت در گزارش"):
                with st.spinner("هوش مصنوعی در حال بررسی پیک‌ها و عیب‌یابی است..."):
                    try:
                        prompt = """
                        تو یک مهندس ارشد ارتعاشات هستی. این تصویر مربوط به گراف یا گزارش ارتعاشی یک ماشین صنعتی است.
                        لطفاً با دیدگاه مهندسی موارد زیر را استخراج کن و به صورت ساختاریافته بنویس:
                        1. وضعیت کلی شدت ارتعاش و سطح هشدار (عادی، هشدار، بحرانی).
                        2. فرکانس‌ها و دامنه‌های پیک اصلی (Peaks / 1X / 2X).
                        3. عیب‌یابی احتمالی (مثل Unbalance، Misalignment یا Bearing Fault).
                        """

                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[prompt, image]
                        )
                        analysis_result = response.text

                        st.success("تحلیل با موفقیت انجام شد!")
                        st.markdown("### 📊 نتیجه تحلیل:")
                        st.markdown(analysis_result)

                        st.session_state.history.append({
                            "نام تجهیز": machine_name_input,
                            "نام فایل": uploaded_file.name,
                            "تحلیل هوش مصنوعی": analysis_result
                        })

                    except Exception as e:
                        st.error(f"خطا در پردازش تصویر: {e}")

    if st.session_state.history:
        st.markdown("---")
        st.subheader("📁 تاریخچه تحلیل‌ها و دانلود گزارش اکسل")

        df_history = pd.DataFrame(st.session_state.history)
        st.dataframe(df_history, width='stretch')

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_history.to_excel(writer, index=False, sheet_name='Vibration_Cloud_Report')
        processed_data = output.getvalue()

        st.download_button(
            label="📥 دانلود فایل اکسل گزارش‌ها (Excel)",
            data=processed_data,
            file_name="Vibration_Cloud_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("🗑️ پاک کردن تاریخچه"):
            st.session_state.history = []
            st.rerun()

else:
    st.warning("⚠️ لطفاً کلید API جمینای خود را از منوی سمت چپ وارد کنید تا برنامه فعال شود.")