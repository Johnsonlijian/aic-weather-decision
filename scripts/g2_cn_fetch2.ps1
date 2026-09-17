param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [string]$Referer = "",
    [int]$TimeoutSec = 90,
    [string]$Encoding = "",
    [int]$ExtractChars = 200000
)
$ErrorActionPreference = "Continue"
$root = "R:\IMUT_WORKPOOL\01_PROJECTS\NAS_DRIVE\IMUT\2026-AiC-Weather-Decision\AiC_Weather_Decision_Project_v1"
$outdir = Join-Path $root "sources\raw\g2_cn"
$txtdir = Join-Path $root "sources\extracted\g2_cn"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
New-Item -ItemType Directory -Force -Path $txtdir | Out-Null
$outpath = Join-Path $outdir $OutFile
$txtpath = Join-Path $txtdir ([System.IO.Path]::GetFileNameWithoutExtension($OutFile) + ".txt")

$headers = @{
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    "Accept" = "text/html,application/xhtml+xml,application/xml,application/pdf,*/*;q=0.8"
    "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8"
}
if ($Referer -ne "") { $headers["Referer"] = $Referer }

$log = [ordered]@{
    url = $Url
    outfile = $outpath
    extracted = $txtpath
    fetched_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    referer = $Referer
}

$bytes = $null
try {
    $resp = Invoke-WebRequest -Uri $Url -Headers $headers -TimeoutSec $TimeoutSec -MaximumRedirection 8 -UseBasicParsing
    $log.status = [int]$resp.StatusCode
    $log.content_type = [string]$resp.Headers["Content-Type"]
    $log.content_length = $resp.RawContentLength
    try { $log.final_uri = $resp.BaseResponse.ResponseUri.AbsoluteUri } catch { $log.final_uri = $Url }
    $bytes = $resp.Content
    [System.IO.File]::WriteAllBytes($outpath, $bytes)
    $log.saved_bytes = (Get-Item $outpath).Length
    $log.error = $null
} catch {
    $log.status = $null
    $log.error = $_.Exception.Message
    try { if ($_.Exception.Response) { $log.status = [int]$_.Exception.Response.StatusCode } } catch {}
    try {
        $s = $_.Exception.Response.GetResponseStream()
        if ($s) {
            $ms = New-Object System.IO.MemoryStream
            $s.CopyTo($ms)
            $bytes = $ms.ToArray()
            [System.IO.File]::WriteAllBytes($outpath, $bytes)
            $log.saved_bytes = $bytes.Length
        }
    } catch {}
}

# Decode to text if it is not a PDF
$isPdf = $false
if ($bytes -and $bytes.Length -gt 4) {
    $isPdf = ($bytes[0] -eq 0x25 -and $bytes[1] -eq 0x50 -and $bytes[2] -eq 0x44 -and $bytes[3] -eq 0x46)
}
$log.is_pdf = $isPdf

if ($bytes -and -not $isPdf) {
    $text = $null
    if ($Encoding -ne "") {
        try { $text = [System.Text.Encoding]::GetEncoding($Encoding).GetString($bytes) } catch { $text = $null }
    }
    if (-not $text) {
        # sniff charset from raw bytes
        $latin = [System.Text.Encoding]::GetEncoding(28591).GetString($bytes[0..([Math]::Min(4000,$bytes.Length-1))])
        if ($latin -match "(?i)charset\s*=\s*[\x22']?([\w\-]+)") {
            $cs = $Matches[1]
            $map = @{ "gb2312"="gb2312"; "gbk"="gb2312"; "gb18030"="gb18030"; "utf-8"="utf-8"; "utf8"="utf-8"; "big5"="big5" }
            if ($map.ContainsKey($cs.ToLower())) {
                try { $text = [System.Text.Encoding]::GetEncoding($map[$cs.ToLower()]).GetString($bytes) } catch { $text = $null }
            }
        }
    }
    if (-not $text) {
        # try utf8 strict, then gb18030
        try {
            $strict = New-Object System.Text.UTF8Encoding($false, $true)
            $text = $strict.GetString($bytes)
        } catch {
            $text = [System.Text.Encoding]::GetEncoding("gb18030").GetString($bytes)
        }
    }
    # strip script/style for readability
    $clean = $text -replace "(?is)<script.*?</script>", " " -replace "(?is)<style.*?</style>", " "
    $clean = $clean -replace "(?is)<br\s*/?>", "`n" -replace "(?is)</(p|div|tr|li|h[1-6]|table)>", "`n"
    $clean = $clean -replace "(?is)<[^>]+>", " "
    $clean = $clean -replace "&nbsp;", " " -replace "&amp;", "&" -replace "&lt;", "<" -replace "&gt;", ">" -replace "&quot;", '"'
    $clean = $clean -replace "[ \t]+", " "
    $clean = $clean -replace "(\r?\n\s*){3,}", "`n`n"
    if ($clean.Length -gt $ExtractChars) { $clean = $clean.Substring(0, $ExtractChars) }
    [System.IO.File]::WriteAllText($txtpath, $clean, (New-Object System.Text.UTF8Encoding($false)))
    $log.text_chars = $clean.Length
}

$log | ConvertTo-Json -Depth 4
