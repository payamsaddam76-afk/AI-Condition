import glob
import os
import re
import subprocess
import pandas as pd

# ۱. تعیین مسیر پوشه پروژه
project_dir = os.path.dirname(os.path.abspath(__file__))

print("🚀 شروع فرآیند استخراج و مرتب‌سازی کامل دیتابیس پایش وضعیت...\n")

# ۲. پیدا کردن فایل .sdf در پوشه پروژه
sdf_files = glob.glob(os.path.join(project_dir, "*.sdf"))
if not sdf_files:
    print("❌ هیچ فایل .sdf در پوشه پروژه پیدا نشد!")
    print(
        "لطفاً فایل اصلی دیتابیس (مثل EIDBB.sdf) را در پوشه پروژه کپی کنید."
    )
    exit()

sdf_path = sdf_files[0]
sdf_name = os.path.basename(sdf_path)
print(f"📁 فایل دیتابیس شناسایی شد: {sdf_name}")

# ایجاد پوشه موقت برای ذخیره داده‌های خام
output_dir = os.path.join(project_dir, "extracted_tables")
os.makedirs(output_dir, exist_ok=True)

# ۳. استخراج خودکار جداول خام از دیتابیس SDF
print(
    "⏳ در حال متصل شدن به دیتابیس و استخراج داده‌ها (لطفاً کمی شکیبا باشید)..."
)
ps_script = f"""
$sdfPath = "{sdf_path}"
$outputFolder = "{output_dir}"

$providers = @("Microsoft.SQLSERVER.CE.OLEDB.4.0", "Microsoft.SQLSERVER.CE.OLEDB.3.5")
$conn = $null

foreach ($p in $providers) {{
    try {{
        $c = New-Object System.Data.OleDb.OleDbConnection("Provider=$p;Data Source='$sdfPath';")
        $c.Open()
        $conn = $c
        break
    }} catch {{}}
}}

if ($conn -eq $null) {{
    exit 1
}}

$tables = $conn.GetSchema("Tables")
foreach ($row in $tables.Rows) {{
    $tableName = $row["TABLE_NAME"]
    try {{
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT * FROM [$tableName]"
        $adapter = New-Object System.Data.OleDb.OleDbDataAdapter($cmd)
        $dt = New-Object System.Data.DataTable
        $adapter.Fill($dt) | Out-Null
        if ($dt.Rows.Count -gt 0) {{
            $csvPath = Join-Path $outputFolder "$tableName.csv"
            $dt | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        }}
    }} catch {{}}
}}
$conn.Close()
"""

ps_file = os.path.join(project_dir, "temp_extractor.ps1")
with open(ps_file, "w", encoding="utf-8") as f:
    f.write(ps_script)

ps_executors = [
    "powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

for ps_exe in ps_executors:
    try:
        subprocess.run(
            [ps_exe, "-ExecutionPolicy", "Bypass", "-File", ps_file],
            capture_output=True,
            text=True,
        )
        break
    except Exception:
        pass

if os.path.exists(ps_file):
    os.remove(ps_file)

# ۴. خواندن شناسه ماشین‌آلات برای جایگزینی کدهای نامفهوم با نام واقعی تجهیز
machines_file = os.path.join(output_dir, "Machines.csv")
machines_dict = {}

if os.path.exists(machines_file):
    try:
        df_m = pd.read_csv(machines_file)
        for _, row in df_m.iterrows():
            code = str(row.get("Code", "")).strip()
            name = str(row.get("Name", "نامشخص")).strip()
            area = str(row.get("Area", "نامشخص")).strip()
            company = str(row.get("Company", "")).strip()
            machines_dict[code] = {
                "Machine_Name": name,
                "Area": area,
                "Company": company,
            }
    except Exception as e:
        print(f"⚠️ خطایی در خواندن جدول مشخصات ماشین‌آلات رخ داد: {e}")

# ۵. یکپارچه‌سازی تمام جداول در یک ساختار واحد
print("🔄 در حال مرتب‌سازی داده‌ها و درج نام واقعی تجهیزات...")
master_list = []
csv_files = glob.glob(os.path.join(output_dir, "M__*.csv"))

for file_path in csv_files:
    file_name = os.path.basename(file_path)

    match = re.search(r"M__(\d+)__(.+)\.csv", file_name)
    if not match:
        match = re.search(r"M__(\d+)_(.+)\.csv", file_name)

    if match:
        m_code = match.group(1)
        point_idx = match.group(2)

        m_info = machines_dict.get(
            m_code,
            {
                "Machine_Name": f"دستگاه کد {m_code}",
                "Area": "-",
                "Company": "-",
            },
        )

        try:
            df_data = pd.read_csv(file_path)
            if not df_data.empty:
                # درج مشخصات تجهیز در ستون‌های اول
                df_data.insert(0, "کد دستگاه", m_code)
                df_data.insert(1, "نام تجهیز / ماشین", m_info["Machine_Name"])
                df_data.insert(2, "بخش / واحد", m_info["Area"])
                df_data.insert(3, "شماره/نوع نقطه", point_idx)

                master_list.append(df_data)
        except Exception:
            pass

# ۶. خروجی نهایی در قالب اکسل مرتب
if master_list:
    df_consolidated = pd.concat(master_list, ignore_index=True)
    df_consolidated.sort_values(
        by=["بخش / واحد", "نام تجهیز / ماشین", "کد دستگاه"], inplace=True
    )

    output_excel = "گزارش_منظم_پایش_وضعیت.xlsx"

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df_consolidated.to_excel(
            writer, sheet_name="داده‌های جامع ارتعاشات", index=False
        )
        if os.path.exists(machines_file):
            pd.read_csv(machines_file).to_excel(
                writer, sheet_name="شناسنامه ماشین‌آلات", index=False
            )

    print("\n🎉 عملیات با موفقیت انجام شد!")
    print(f"📄 فایل اکسل نهایی ساخته شد: {output_excel}")
    print(f"📊 مجموعاً {len(df_consolidated):,} سطر داده در ۱ شیت اصلی مرتب شدند.")
else:
    print(
        "❌ مشکلی در استخراج داده‌ها رخ داد. مطمئن شوید فایل .sdf در همین پوشه قرار دارد."
    )