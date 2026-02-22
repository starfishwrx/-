param(
  [string]$ReportDate = "",
  [string]$DateMode = "today", # today | yesterday
  [string]$ConfigPath = "",
  [int]$MaxRetries = 3,
  [int]$RetryDelaySeconds = 300,
  [switch]$NoPushFeishuDoc,
  [switch]$VerifyFeishuContent,
  [switch]$SkipAuthCheck
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
  $ConfigPath = Join-Path $RootDir "config.yaml"
}

$PythonBin = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonBin)) {
  $PythonBin = "python"
}

$LogDir = Join-Path $RootDir "output\scheduler_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if ([string]::IsNullOrWhiteSpace($ReportDate)) {
  if ($DateMode -eq "yesterday") {
    $ReportDate = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
  } else {
    $ReportDate = (Get-Date).ToString("yyyy-MM-dd")
  }
}

$Now = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "daily_$Now.log"

function Write-Log {
  param([string]$Text)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Text
  Write-Output $line
  Add-Content -Path $LogFile -Value $line
}

Write-Log "start daily report, date=$ReportDate"
Write-Log "root=$RootDir"
Write-Log "config=$ConfigPath"

if (-not $SkipAuthCheck) {
  Write-Log "auth precheck..."
  & $PythonBin (Join-Path $RootDir "generate_daily_report.py") --config $ConfigPath --check-extra-auth --date $ReportDate 2>&1 | Tee-Object -FilePath $LogFile -Append
  if ($LASTEXITCODE -ne 0) {
    throw "auth precheck failed"
  }
}

$attempt = 1
while ($attempt -le $MaxRetries) {
  Write-Log "run attempt $attempt/$MaxRetries"
  $cmd = @(
    (Join-Path $RootDir "generate_daily_report.py"),
    "--config", $ConfigPath,
    "--date", $ReportDate,
    "--with-extra-metrics"
  )
  if ($NoPushFeishuDoc) {
    $cmd += "--no-push-feishu-doc"
  }
  if ($VerifyFeishuContent) {
    $cmd += "--verify-feishu-content"
  }
  & $PythonBin @cmd 2>&1 | Tee-Object -FilePath $LogFile -Append
  if ($LASTEXITCODE -eq 0) {
    Write-Log "success"
    exit 0
  }
  if ($attempt -lt $MaxRetries) {
    Write-Log "failed, sleep ${RetryDelaySeconds}s then retry"
    Start-Sleep -Seconds $RetryDelaySeconds
  }
  $attempt += 1
}

throw "all retries failed"
