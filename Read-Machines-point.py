import glob
import os
import subprocess
import pandas as pd

project_dir = os.path.dirname(os.path.abspath(__file__))

print("🚀 شروع استخراج جامع جداول فایل .sdf...\n")

# ۱. یافتن فایل SDF
sdf_files = glob.glob(os.path.join(project_dir, "*.sdf"))
if not sdf_files:
    print("❌ فایل .sdf پیدا نشد!")
    exit()

sdf_path = sdf_files[0]
output_dir = os.path.join(project_dir, "extracted_tables")
os.makedirs(output_dir, exist_ok=True)

# ۲. ساخت اسکریپت پاورشل
ps_content = """param([string]$sdfPath, [string]$outputFolder)

$dll35 = "C:\\Program Files (x86)\\Microsoft SQL Server Compact Edition\\v3.5\\Desktop\\System.Data.SqlServerCe.dll"
$dll40 = "C:\\Program Files\\Microsoft SQL Server Compact Edition\\v4.0\\Desktop\\System.Data.SqlServerCe.dll"

$conn = $null

if (Test-Path $dll35) {
    try {
        Add-Type -Path $dll35
        $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';")
        $conn.Open()
        Write-Host "CONNECTED_35"
    } catch { $conn = $null }
}

if ($conn -eq $null -and (Test-Path $dll40)) {
    try {
        Add-Type -Path $dll40
        $conn = New-Object System.Data.SqlServerCe.SqlCeConnection("Data Source='$sdfPath';")
        $conn.Open()
        Write-Host "CONNECTED_40"
    } catch { $conn = $null }
}

if ($conn -eq $null) {
    Write-Host "ERROR_NO_CONNECTION"
    exit 1
}

$tables = @('Machines', 'Points', 'Machine_Stats', 'Notes', 'points_current_values', 'points_current_rms_values', 'Temperature')

foreach ($t in $tables) {
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT * FROM [$t]"
        $adapter = New-Object System.Data.SqlServerCe.SqlCeDataAdapter($cmd)

        $dt = New-Object System.Data.DataTable
        $adapter.Fill($dt) | Out-Null

        # اگر جدول ردیف داشت خروجی CSV بگیر
        if ($dt.Rows.Count -gt 0) {
            foreach ($col in @('Image_File', 'File3D')) {
                if ($dt.Columns.Contains($col)) {
                    $dt.Columns.Remove($col)
                }
            }
            $csvPath = Join-Path $outputFolder "$t.csv"
            $dt | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
            Write-Host "SUCCESS: $t - Rows: $($dt.Rows.Count)"
        } else {
            Write-Host "SKIP: $t is empty."
        }
    } catch {
        Write-Host "FAIL: $t"
    }
}

$conn.Close()
"""

ps_file = os.path.join(project_dir, "run_extractor.ps1")
with open(ps_file, "w", encoding="utf-8") as f:
    f.write(ps_content)

# ۳. اجرای پاورشل
print("⏳ در حال پردازش دیتابیس...")
cmd = [
    "powershell.exe",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    ps_file,
    "-sdfPath",
    sdf_path,
    "-outputFolder",
    output_dir,
]

res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)

if os.path.exists(ps_file):
    os.remove(ps_file)

# ۴. ذخیره جداول پر شده در اکسل
output_excel = os.path.join(project_dir, "گزارش_جامع_Machines_و_Points.xlsx")

extracted_files = glob.glob(os.path.join(output_dir, "*.csv"))

if extracted_files:
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        for csv_p in extracted_files:
            tbl_name = os.path.basename(csv_p).replace(".csv", "")
            try:
                df = pd.read_csv(csv_p)
                if not df.empty:
                    df.to_excel(writer, sheet_name=tbl_name[:31], index=False)
                    print(
                        f"✅ شیت '{tbl_name}' با {len(df)} ردیف اضافه شد."
                    )
            except Exception as e:
                print(f"⚠️ خطای خواندن {tbl_name}: {e}")

    print("\n" + "=" * 50)
    print(f"🎉 تمامی جداول با موفقیت در فایل اکسل ذخیره شدند:\n{output_excel}")
else:
    print("❌ هیچ فایل CSV حاوی دیتایی یافت نشد.")