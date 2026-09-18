import glob
import os
import re
import subprocess
import pandas as pd

# جهت رسم نمودارها
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ۱. تنظیمات اولیه مسیر
project_dir = os.path.dirname(os.path.abspath(__file__))

print("🚀 شروع پردازش جامع دیتابیس Digivibe و تولید گزارشات...\n")

# ۲. یافتن فایل .sdf
sdf_files = glob.glob(os.path.join(project_dir, "*.sdf"))
if not sdf_files:
    print("❌ هیچ فایل .sdf پیدا نشد!")
    exit()

sdf_path = sdf_files[0]
output_dir = os.path.join(project_dir, "extracted_tables")
os.makedirs(output_dir, exist_ok=True)

# ۳. اسکریپت پاورشل جامع جهت استخراج تمام جداول (ثابت و M_...)
ps_content = f"""
$sdfPath = "{sdf_path}"
$outputFolder = "{output_dir}"

$dll35 = "C:\\Program Files (x86)\\Microsoft SQL Server Compact Edition\\v3.5\\Desktop\\System.Data.SqlServerCe.dll"
$dll40 = "C:\\Program Files\\Microsoft SQL Server Compact Edition\\v4.0\\Desktop\\System.Data.SqlServerCe.dll"

$conn = $null

if (Test-Path $dll35) {{
    try {{
        Add-Type -Path $dll35
        $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';")
        $conn.Open()
    }} catch {{ $conn = $null }}
}}

if ($conn -eq $null -and (Test-Path $dll40)) {{
    try {{
        Add-Type -Path $dll40
        $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';")
        $conn.Open()
    }} catch {{ $conn = $null }}
}}

if ($conn -eq $null) {{
    $providers = @("Microsoft.SQLSERVER.CE.OLEDB.4.0", "Microsoft.SQLSERVER.CE.OLEDB.3.5")
    foreach ($p in $providers) {{
        try {{
            $conn = New-Object System.Data.OleDb.OleDbConnection("Provider=$p;Data Source='$sdfPath';")
            $conn.Open()
            break
        }} catch {{}}
    }}
}}

if ($conn -eq $null) {{
    Write-Host "ERROR_NO_CONNECTION"
    exit 1
}}

# ۱. استخراج جداول پایه
$tables = @('Machines', 'Points', 'Machine_Stats', 'Notes', 'points_current_values', 'points_current_rms_values', 'Temperature')
foreach ($t in $tables) {{
    try {{
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT * FROM [$t]"
        $adapter = New-Object System.Data.DataTable
        if ($conn -is [System.Data.OleDb.OleDbConnection]) {{
            $adp = New-Object System.Data.OleDb.OleDbDataAdapter($cmd)
            $adp.Fill($adapter) | Out-Null
        }} else {{
            $adp = New-Object System.Data.SqlServerCe.SqlCeDataAdapter($cmd)
            $adp.Fill($adapter) | Out-Null
        }}

        if ($adapter.Rows.Count -gt 0) {{
            foreach ($col in @('Image_File', 'File3D')) {{
                if ($adapter.Columns.Contains($col)) {{ $adapter.Columns.Remove($col) }}
            }}
            $csvPath = Join-Path $outputFolder "$t.csv"
            $adapter | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        }}
    }} catch {{}}
}}

# ۲. استخراج جداول M_
try {{
    $cmdM = $conn.CreateCommand()
    $cmdM.CommandText = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'M_%'"
    $reader = $cmdM.ExecuteReader()
    while ($reader.Read()) {{
        $tName = $reader.GetString(0)
        try {{
            $cmdData = $conn.CreateCommand()
            $cmdData.CommandText = "SELECT * FROM [$tName]"
            $dtM = New-Object System.Data.DataTable
            if ($conn -is [System.Data.OleDb.OleDbConnection]) {{
                $adpM = New-Object System.Data.OleDb.OleDbDataAdapter($cmdData)
                $adpM.Fill($dtM) | Out-Null
            }} else {{
                $adpM = New-Object System.Data.SqlServerCe.SqlCeDataAdapter($cmdData)
                $adpM.Fill($dtM) | Out-Null
            }}

            if ($dtM.Rows.Count -gt 0) {{
                $csvPathM = Join-Path $outputFolder "$tName.csv"
                $dtM | Export-Csv -Path $csvPathM -NoTypeInformation -Encoding UTF8
            }}
        }} catch {{}}
    }}
    $reader.Close()
}} catch {{}}

$conn.Close()
"""

ps_file = os.path.join(project_dir, "run_combined_extractor.ps1")
with open(ps_file, "w", encoding="utf-8") as f:
    f.write(ps_content)

print("⏳ در حال استخراج جامع تمامی جداول و سیگنال‌ها...")
subprocess.run(
    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_file],
    capture_output=True,
    text=True,
)

if os.path.exists(ps_file):
    os.remove(ps_file)

# ۴. بخش نگاشت اطلاعات Machines و Points
machines_file = os.path.join(output_dir, "Machines.csv")
points_file = os.path.join(output_dir, "Points.csv")

machines_by_id = {}
machines_by_code = {}

if os.path.exists(machines_file):
    try:
        df_m = pd.read_csv(machines_file, dtype=str)
        for _, row in df_m.iterrows():
            m_id = str(row.get("ID", "")).strip()
            m_code = str(row.get("Code", "")).strip()
            info = {
                "Company": str(row.get("Company", "")).strip(),
                "Area": str(row.get("Area", "")).strip(),
                "Name": str(row.get("Name", "")).strip(),
                "Code": m_code,
                "Coupling": str(row.get("Coupling", "")).strip(),
                "ISO_Class": str(row.get("ISO_Class", "")).strip(),
            }
            if m_id:
                machines_by_id[m_id] = info
            if m_code:
                machines_by_code[m_code] = info
    except Exception as e:
        print(f"⚠️ خطای خواندن Machines.csv: {e}")

tbl_to_machine = {}
if os.path.exists(points_file):
    try:
        df_p = pd.read_csv(points_file, dtype=str)
        for _, row in df_p.iterrows():
            tbl_code = str(
                row.get(
                    "Machine_Code", row.get("Code", row.get("Point_Code", ""))
                )
            ).strip()
            m_id = str(row.get("Machine_ID", row.get("ID_Machine", ""))).strip()
            m_code = str(row.get("Code", "")).strip()

            if tbl_code:
                if m_id in machines_by_id:
                    tbl_to_machine[tbl_code] = machines_by_id[m_id]
                elif m_code in machines_by_code:
                    tbl_to_machine[tbl_code] = machines_by_code[m_code]
    except Exception as e:
        print(f"⚠️ خطای خواندن Points.csv: {e}")

for code, info in machines_by_code.items():
    if code not in tbl_to_machine:
        tbl_to_machine[code] = info

# ۵. خواندن داده‌های اندازه‌گیری و ساخت اکسل
master_list = []
csv_files = glob.glob(os.path.join(output_dir, "M__*.csv"))
axis_map = {1: "H", 2: "V", 3: "A", "1": "H", "2": "V", "3": "A"}


def format_extra(row):
    amp = row.get("Max_Amp")
    freq = row.get("Max_Frec")
    if pd.notnull(amp) and pd.notnull(freq):
        try:
            return f"Max: {float(amp):.4f} - Max Freq:{int(float(freq))}"
        except Exception:
            return ""
    return ""


def sort_key_func(val):
    val_str = str(val)
    match = re.match(r"^(\d+)(.*)$", val_str)
    if match:
        return (0, int(match.group(1)), match.group(2))
    return (1, val_str, "")


for file_path in csv_files:
    file_name = os.path.basename(file_path)
    match = re.search(r"M__(\d+)[_]+([a-zA-Z0-9]+)\.csv", file_name)

    if match:
        tbl_code = str(match.group(1)).strip()
        point_idx = match.group(2)
        machine_info = tbl_to_machine.get(
            tbl_code,
            {
                "Company": "",
                "Area": "",
                "Name": tbl_code,
                "Code": tbl_code,
                "Coupling": "",
                "ISO_Class": "",
            },
        )

        try:
            df_data = pd.read_csv(file_path)
            if not df_data.empty and "Date_Time" in df_data.columns:
                df_meas = df_data[df_data["Date_Time"].notnull()].copy()
                if not df_meas.empty:
                    df_meas["Company"] = machine_info["Company"]
                    df_meas["Area"] = machine_info["Area"]
                    df_meas["Name"] = machine_info["Name"]
                    df_meas["Code"] = machine_info["Code"]
                    df_meas["Coupling"] = machine_info["Coupling"]
                    df_meas["ISO_Class"] = machine_info["ISO_Class"]
                    df_meas["P"] = point_idx
                    df_meas["A"] = df_meas["Axis"].map(
                        lambda x: axis_map.get(
                            x, str(x) if pd.notnull(x) else ""
                        )
                    )
                    df_meas["Date"] = df_meas["Date_Time"]
                    df_meas["mm/s"] = df_meas["Vel_RMS"].round(4)
                    df_meas["gE"] = df_meas["Env_RMS"].round(4)
                    df_meas["g"] = df_meas["Acc_RMS"].round(4)
                    df_meas["Temp"] = (
                        df_meas["Temperature"].fillna(0.0).round(1)
                    )
                    df_meas["Extra"] = df_meas.apply(format_extra, axis=1)

                    cols_order = [
                        "Company",
                        "Area",
                        "Name",
                        "Code",
                        "Coupling",
                        "ISO_Class",
                        "P",
                        "A",
                        "Date",
                        "mm/s",
                        "gE",
                        "g",
                        "Temp",
                        "Extra",
                    ]
                    master_list.append(df_meas[cols_order])
        except Exception:
            pass

# ۶. ساخت فایل اکسل جامع
if master_list:
    df_consolidated = pd.concat(master_list, ignore_index=True)
    df_consolidated["_sort"] = df_consolidated["Name"].apply(sort_key_func)
    df_consolidated.sort_values(
        by=["_sort", "P", "A"], inplace=True, ignore_index=True
    )
    df_consolidated.drop(columns=["_sort"], inplace=True)

    output_excel = os.path.join(
        project_dir, "گزارش_منظم_پایش_وضعیت.xlsx"
    )
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df_consolidated.to_excel(
            writer, sheet_name="داده‌های Digivibe", index=False
        )
    print(f"🎉 گزارش اکسل با موفقیت ذخیره شد:\n{output_excel}")

# ۷. رسم نمونه نمودار سیگنال در صورت نصب بودن matplotlib
if HAS_MATPLOTLIB:
    time_files = glob.glob(os.path.join(output_dir, "*_o.csv"))
    valid_time_files = [f for f in time_files if os.path.getsize(f) > 10]

    if valid_time_files:
        sample_time_file = valid_time_files[0]
        sample_fft_file = sample_time_file.replace("_o.csv", "_f.csv")

        df_time = pd.read_csv(sample_time_file)
        fig, axes = plt.subplots(2, 1, figsize=(10, 6))

        cols = df_time.columns.tolist()
        if len(cols) >= 2:
            axes[0].plot(
                df_time[cols[0]], df_time[cols[1]], color="blue", linewidth=0.8
            )
        else:
            axes[0].plot(df_time.iloc[:, 0], color="blue", linewidth=0.8)
        axes[0].set_title(
            f"Time Waveform - {os.path.basename(sample_time_file)}"
        )
        axes[0].grid(True)

        if os.path.exists(sample_fft_file):
            df_fft = pd.read_csv(sample_fft_file)
            fft_cols = df_fft.columns.tolist()
            if len(fft_cols) >= 2:
                axes[1].plot(
                    df_fft[fft_cols[0]],
                    df_fft[fft_cols[1]],
                    color="red",
                    linewidth=0.8,
                )
            else:
                axes[1].plot(df_fft.iloc[:, 0], color="red", linewidth=0.8)
            axes[1].set_title(
                f"FFT Spectrum - {os.path.basename(sample_fft_file)}"
            )
            axes[1].grid(True)

        plt.tight_layout()
        plot_path = os.path.join(project_dir, "Vibration_Plot.png")
        plt.savefig(plot_path)
        print(f"📈 نمودار سیگنال با موفقیت ذخیره شد: {plot_path}")
else:
    print(
        "⚠️ کتابخانه matplotlib نصب نیست. جهت رسم نمودار دستور 'pip install matplotlib' را در ترمینال بزنید."
    )