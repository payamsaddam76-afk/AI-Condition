import os
import json

base_dir = "database"
os.makedirs(base_dir, exist_ok=True)

fault_database_structured = {
    "fault_diagnostics_database": {
        "turbine_faults.json": {
            "equipment": "توربین (Turbine - Siemens, Mapna, Zorya, Nuovo Pignone)",
            "standards_ref": "ISO 10816-4, API 616, Mobius Vibration Category III/IV",
            "faults": [
                {
                    "fault_code": "TURB_UNB_01",
                    "fault_name": "نابالانسی روتور (Rotor Unbalance)",
                    "dominant_frequency": "1X RPM (پیک اصلی در فرکانس دورانی)",
                    "key_direction": "شعاعی (H & V) - بیشترین شدت در نقاط بیرینگ DE و NDE",
                    "description": "افزایش خطی دامنه ارتعاش با مجذور سرعت. در توربین‌های مپنا و زیمنس معمولاً ناشی از رسوب‌گذاری روی پره‌های توربین یا تنش‌های حرارتی روتور است."
                },
                {
                    "fault_code": "TURB_MIS_02",
                    "fault_name": "ناهم‌محوری (Misalignment)",
                    "dominant_frequency": "1X, 2X, 3X RPM",
                    "key_direction": "محوری (A) بالا (بیش از 50% ارتعاش شعاعی)",
                    "description": "خطای اتصالات فلنجی صلب یا کوپلینگ‌ها. در توربین‌های زاریا یا نواپینیون به دلیل انبساط حرارتی زیاد بسیار رایج است."
                },
                {
                    "fault_code": "TURB_BPF_03",
                    "fault_name": "فرکانس عبور پره (Blade Pass Frequency - BPF)",
                    "dominant_frequency": "Number of Blades × RPM همراه با سایدبندهای 1X",
                    "key_direction": "شعاعی و محوری",
                    "description": "برخورد جریان گاز با پره‌ها؛ ظاهر شدن هارمونیک‌های BPF نشانه دفرمگی یا اعوجاج نازل‌ها و پره‌هاست."
                },
                {
                    "fault_code": "TURB_OIL_04",
                    "fault_name": "ناپایداری فیلم روغن (Oil Whirl / Oil Whip)",
                    "dominant_frequency": "0.42 تا 0.48 از فرکانس دورانی (Sub-synchronous)",
                    "key_direction": "شعاعی (H & V) در بیرینگ‌های لغزشی (Journal Bearings)",
                    "description": "مخصوص توربین‌های سنگین مجهز به بیرینگ لغزشی. پدیده‌ای بسیار مخرب که با عبور فرکانس از سرعت بحرانی به Oil Whip تبدیل شده و نیازمند توقف فوری است."
                }
            ]
        },
        "compressor_faults.json": {
            "equipment": "کمپرسورهای هوا و اینتگرال (Air & Integrally Geared Compressors - Atlas Copco ZH)",
            "standards_ref": "API 617, ISO 10816-3",
            "faults": [
                {
                    "fault_code": "COMP_GMF_01",
                    "fault_name": "خطاهای درگیری چرخ‌دنده (Gear Mesh Frequency - GMF)",
                    "dominant_frequency": "GMF = (Number of Teeth) × RPM با سایدبندهای سرعت دورانی پینیون",
                    "key_direction": "شعاعی روی محفظه گیربکس اینتگرال",
                    "description": "در کمپرسورهای اطلس کپکو سری ZH، وجود سایدبندهای دورانی دور فرکانس GMF نشان‌دهنده سایش، ناهم‌راستایی دنده‌ها یا بک‌لاش نامناسب است."
                },
                {
                    "fault_code": "COMP_SURGE_02",
                    "fault_name": "پدیده‌های ناپایداری آیرودینامیکی (Surge & Rotating Stall)",
                    "dominant_frequency": "فرکانس‌های پهن‌باند تصادفی (Broadband Sub-synchronous)",
                    "key_direction": "محوری و مکش (Inlet / Axial)",
                    "description": "جریان معکوس یا نوسانات شدید فشار در اثر افت دبی؛ با صداهای ناگهانی و ارتعاشات شدید در ورودی ایمپلر همراه است."
                }
            ]
        }
    }
}

# ذخیره در دیتابیس
fault_dir = os.path.join(base_dir, "fault_knowledge_base")
os.makedirs(fault_dir, exist_ok=True)

for filename, content in fault_database_structured["fault_diagnostics_database"].items():
    file_path = os.path.join(fault_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

print("✅ پایگاه دانش تخصصی عیب‌یابی ارتعاشی همراه با رفرنس‌های استاندارد API و ISO با موفقیت در دیتابیس ثبت شد!")