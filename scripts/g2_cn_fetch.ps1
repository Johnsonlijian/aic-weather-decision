param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [string]$Referer = "",
    [int]$TimeoutSec = 60
)
$ErrorActionPreference = "Continue"
$root = "R:\IMUT_WORKPOOL\01_PROJECTS\NAS_DRIVE\IMUT\2026-AiC-Weather-Decision\AiC_Weather_Decision_Project_v1"
$outdir = Join-Path $root "sources\raw\g2_cn"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
$outpath = Join-Path $outdir $OutFile

$headers = @{
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    "Accept" = "text/html,application/xhtml+xml,application/xml,application/pdf,*/*;q=0.8"
    "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8"
}
if ($Referer -ne "") { $headers["Referer"] = $Referer }

$log = [ordered]@{
    url = $Url
    outfile = $outpath
    fetched_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    referer = $Referer
}

try {
    $resp = Invoke-WebRequest -Uri $Url -Headers $headers -TimeoutSec $TimeoutSec -MaximumRedirection 8 -UseBasicParsing
    $log.status = [int]$resp.StatusCode
    $log.content_type = [string]$resp.Headers["Content-Type"]
    $log.content_length = $resp.RawContentLength
    $log.final_uri = $resp.BaseResponse.ResponseUri.AbsoluteUri
    [System.IO.File]::WriteAllBytes($outpath, $resp.Content)
    $log.saved_bytes = (Get-Item $outpath).Length
    $log.error = $null
} catch {
    $log.status = $null
    $log.error = $_.Exception.Message
    if ($_.Exception.Response) {
        try { $log.status = [int]$_.Exception.Response.StatusCode } catch {}
        try { $log.final_uri = $_.Exception.Response.ResponseUri.AbsoluteUri } catch {}
    }
    try {
        $s = $_.Exception.Response.GetResponseStream()
        if ($s) {
            $ms = New-Object System.IO.MemoryStream
            $s.CopyTo($ms)
            [System.IO.File]::WriteAllBytes($outpath, $ms.ToArray())
            $log.saved_bytes = (Get-Item $outpath).Length
        }
    } catch {}
}

$log | ConvertTo-Json -Depth 4
