import glob
import os
import re
import subprocess
import pandas as pd

# بررسی امکان استفاده از matplotlib
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

project_dir = os.path.dirname(os.path.abspath(__file__))
print("🚀 اجرای اسکریپت جامع پایش وضعیت و رمزگشایی باینری...\n")

sdf_files = glob.glob(os.path.join(project_dir, "*.sdf"))
if not sdf_files:
    print("❌ هیچ فایل .sdf پیدا نشد!")
    exit()

sdf_path = sdf_files[0]
output_dir = os.path.join(project_dir, "extracted_tables")
os.makedirs(output_dir, exist_ok=True)

# اسکریپت پاورشل مجزا بدون تداخل f-string
ps_content = r"""
param([string]$sdfPath, [string]$outputFolder)

$dll35 = "C:\Program Files (x86)\Microsoft SQL Server Compact Edition\v3.5\Desktop\System.Data.SqlServerCe.dll"
$dll40 = "C:\Program Files\Microsoft SQL Server Compact Edition\v4.0\Desktop\System.Data.SqlServerCe.dll"

$conn = $null

if (Test-Path $dll35) {
    try { Add-Type -Path $dll35; $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';"); $conn.Open() } catch {}
}
if ($conn -eq $null -and (Test-Path $dll40)) {
    try { Add-Type -Path $dll40; $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';"); $conn.Open() } catch {}
}

if ($conn -eq $null) {
    $providers = @("Microsoft.SQLSERVER.CE.OLEDB.4.0", "Microsoft.SQLSERVER.CE.OLEDB.3.5")
    foreach ($p in $providers) {
        try {
            $conn = New-Object System.Data.OleDb.OleDbConnection("Provider=$p;Data Source='$sdfPath';")
            $conn.Open()
            break
        } catch {}
    }
}

if ($conn -eq $null) { exit 1 }

# استخراج جداول اصلی
$tables = @('Machines', 'Points', 'Machine_Stats', 'Notes', 'points_current_values', 'points_current_rms_values', 'Temperature')
foreach ($t in $tables) {
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT * FROM [$t]"
        $dt = New-Object System.Data.DataTable
        if ($conn -is [System.Data.OleDb.OleDbConnection]) {
            $adp = New-Object System.Data.OleDb.OleDbDataAdapter($cmd)
            $adp.Fill($dt) | Out-Null
        } else {
            $adp = New-Object System.Data.SqlServerCe.SqlCeDataAdapter($cmd)
            $adp.Fill($dt) | Out-Null
        }

        if ($dt.Rows.Count -gt 0) {
            foreach ($col in @('Image_File', 'File3D')) {
                if ($dt.Columns.Contains($col)) { $dt.Columns.Remove($col) }
            }
            $csvPath = Join-Path $outputFolder "$t.csv"
            $dt | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        }
    } catch {}
}

# استخراج جداول M_ و تبدیل داده‌های باینری
try {
    $cmdM = $conn.CreateCommand()
    $cmdM.CommandText = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'M_%'"
    $reader = $cmdM.ExecuteReader()
    $mTables = @()
    while ($reader.Read()) { $mTables += $reader.GetString(0) }
    $reader.Close()

    foreach ($tName in $mTables) {
        try {
            $cmdData = $conn.CreateCommand()
            $cmdData.CommandText = "SELECT * FROM [$tName]"
            $dtM = New-Object System.Data.DataTable
            if ($conn -is [System.Data.OleDb.OleDbConnection]) {
                $adpM = New-Object System.Data.OleDb.OleDbDataAdapter($cmdData)
                $adpM.Fill($dtM) | Out-Null
            } else {
                $adpM = New-Object System.Data.SqlServerCe.SqlCeDataAdapter($cmdData)
                $adpM.Fill($dtM) | Out-Null
            }

            if ($dtM.Rows.Count -gt 0) {
                if ($tName.EndsWith("_o") -or $tName.EndsWith("_f")) {
                    if ($dtM.Columns.Contains("This_File")) {
                        $newCol = $dtM.Columns.Add("Decoded_Signal", [string])
                        foreach ($row in $dtM.Rows) {
                            if ($row["This_File"] -is [byte[]]) {
                                $bytes = [byte[]]$row["This_File"]
                                $floats = New-Object System.Collections.Generic.List[single]
                                for ($i = 0; $i -le ($bytes.Length - 4); $i += 4) {
                                    $floats.Add([System.BitConverter]::ToSingle($bytes, $i))
                                }
                                $row["Decoded_Signal"] = ($floats -join ",")
                            }
                        }
                        $dtM.Columns.Remove("This_File")
                    }
                }
                $csvPathM = Join-Path $outputFolder "$tName.csv"
                $dtM | Export-Csv -Path $csvPathM -NoTypeInformation -Encoding UTF8
            }
        } catch {}
    }
} catch {}

$conn.Close()
"""

ps_file = os.path.join(project_dir, "run_extract.ps1")
with open(ps_file, "w", encoding="utf-8") as f:
    f.write(ps_content)

print("⏳ در حال استخراج دیتابیس و تبدیل هوشمند باینری‌ها...")
subprocess.run(
    [
        "powershell.exe",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ps_file,
        "-sdfPath",
        sdf_path,
        "-outputFolder",
        output_dir,
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

if os.path.exists(ps_file):
    os.remove(ps_file)

# نگاشت متادیتا
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
    except Exception:
        pass

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
    except Exception:
        pass

for code, info in machines_by_code.items():
    if code not in tbl_to_machine:
        tbl_to_machine[code] = info

# استخراج داده‌های پایش وضعیت
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

    if match and not (file_name.endswith("_o.csv") or file_name.endswith("_f.csv")):
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
                    df_meas["mm/s"] = (
                        df_meas["Vel_RMS"].astype(float).round(4)
                        if "Vel_RMS" in df_meas
                        else 0
                    )
                    df_meas["gE"] = (
                        df_meas["Env_RMS"].astype(float).round(4)
                        if "Env_RMS" in df_meas
                        else 0
                    )
                    df_meas["g"] = (
                        df_meas["Acc_RMS"].astype(float).round(4)
                        if "Acc_RMS" in df_meas
                        else 0
                    )
                    df_meas["Temp"] = (
                        df_meas["Temperature"]
                        .fillna(0.0)
                        .astype(float)
                        .round(1)
                        if "Temperature" in df_meas
                        else 0.0
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

# ساخت فایل اکسل
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
    print(f"🎉 فایل اکسل جامع با موفقیت ساخته شد:\n{output_excel}")

# رسم نمودار از داده باینری بازشده
decoded_files = glob.glob(os.path.join(output_dir, "*_o.csv"))
if decoded_files and HAS_MATPLOTLIB:
    for d_file in decoded_files:
        try:
            df_sig = pd.read_csv(d_file)
            if "Decoded_Signal" in df_sig.columns and not df_sig.empty:
                raw_str = str(df_sig["Decoded_Signal"].iloc[0])
                signal_values = [
                    float(x) for x in raw_str.split(",") if x.strip()
                ]

                if signal_values:
                    plt.figure(figsize=(10, 4))
                    plt.plot(signal_values, color="blue", linewidth=0.8)
                    plt.title(
                        f"Decoded Time Waveform Signal - {os.path.basename(d_file)}"
                    )
                    plt.xlabel("Sample Index")
                    plt.ylabel("Amplitude")
                    plt.grid(True, linestyle="--", alpha=0.6)
                    plt.tight_layout()

                    plot_out = os.path.join(
                        project_dir, "Decoded_Signal_Plot.png"
                    )
                    plt.savefig(plot_out, dpi=300)
                    print(f"📈 نمودار سیگنال باینری بازشده ذخیره شد: {plot_out}")
                    break
        except Exception:
            pass