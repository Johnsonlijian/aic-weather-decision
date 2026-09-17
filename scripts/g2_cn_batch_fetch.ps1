param(
    [Parameter(Mandatory=$true)][string]$ListFile,
    [int]$TimeoutSec = 90
)
$ErrorActionPreference = "Continue"
$root = "R:\IMUT_WORKPOOL\01_PROJECTS\NAS_DRIVE\IMUT\2026-AiC-Weather-Decision\AiC_Weather_Decision_Project_v1"
$outdir = Join-Path $root "sources\raw\g2_cn"
$txtdir = Join-Path $root "sources\extracted\g2_cn"
$logdir = Join-Path $root "outputs\gates"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
New-Item -ItemType Directory -Force -Path $txtdir | Out-Null
New-Item -ItemType Directory -Force -Path $logdir | Out-Null

$items = Get-Content $ListFile -Encoding UTF8 | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }
$results = @()
foreach ($line in $items) {
    $parts = $line -split "\|"
    $url = $parts[0].Trim()
    $name = $parts[1].Trim()
    $referer = ""
    if ($parts.Count -ge 3) { $referer = $parts[2].Trim() }

    $outpath = Join-Path $outdir $name
    $txtpath = Join-Path $txtdir ([System.IO.Path]::GetFileNameWithoutExtension($name) + ".txt")

    $headers = @{
        "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        "Accept" = "text/html,application/xhtml+xml,application/xml,application/pdf,*/*;q=0.8"
        "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8"
    }
    if ($referer -ne "") { $headers["Referer"] = $referer }

    $rec = [ordered]@{
        name = $name; url = $url; referer = $referer
        fetched_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
        status = $null; content_type = ""; final_uri = ""; saved_bytes = 0; is_pdf = $false; text_chars = 0; error = ""
    }
    $bytes = $null
    try {
        $resp = Invoke-WebRequest -Uri $url -Headers $headers -TimeoutSec $TimeoutSec -MaximumRedirection 8 -UseBasicParsing
        $rec.status = [int]$resp.StatusCode
        $rec.content_type = [string]$resp.Headers["Content-Type"]
        try { $rec.final_uri = $resp.BaseResponse.ResponseUri.AbsoluteUri } catch { $rec.final_uri = $url }
        $bytes = $resp.Content
    } catch {
        $rec.error = $_.Exception.Message
        try { if ($_.Exception.Response) { $rec.status = [int]$_.Exception.Response.StatusCode } } catch {}
        try { if ($_.Exception.Response) { $rec.final_uri = $_.Exception.Response.ResponseUri.AbsoluteUri } } catch {}
        try {
            $s = $_.Exception.Response.GetResponseStream()
            if ($s) { $ms = New-Object System.IO.MemoryStream; $s.CopyTo($ms); $bytes = $ms.ToArray() }
        } catch {}
    }

    if ($bytes -and $bytes.Length -gt 0) {
        [System.IO.File]::WriteAllBytes($outpath, $bytes)
        $rec.saved_bytes = $bytes.Length
        $isPdf = ($bytes.Length -gt 4 -and $bytes[0] -eq 0x25 -and $bytes[1] -eq 0x50 -and $bytes[2] -eq 0x44 -and $bytes[3] -eq 0x46)
        $rec.is_pdf = $isPdf
        if ($isPdf) {
            # extract via pdftotext -enc UTF-8
            $pt = "C:\Users\renli\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftotext.exe"
            & $pt -enc UTF-8 -layout $outpath $txtpath 2>$null | Out-Null
            if (Test-Path $txtpath) { $rec.text_chars = (Get-Item $txtpath).Length }
        } else {
            $text = $null
            $latin = [System.Text.Encoding]::GetEncoding(28591).GetString($bytes[0..([Math]::Min(4000,$bytes.Length-1))])
            if ($latin -match "(?i)charset\s*=\s*[\x22']?([\w\-]+)") {
                $cs = $Matches[1].ToLower()
                $map = @{ "gb2312"="gb2312"; "gbk"="gb2312"; "gb18030"="gb18030"; "utf-8"="utf-8"; "utf8"="utf-8"; "big5"="big5" }
                if ($map.ContainsKey($cs)) { try { $text = [System.Text.Encoding]::GetEncoding($map[$cs]).GetString($bytes) } catch {} }
            }
            if (-not $text) {
                try { $strict = New-Object System.Text.UTF8Encoding($false, $true); $text = $strict.GetString($bytes) }
                catch { $text = [System.Text.Encoding]::GetEncoding("gb18030").GetString($bytes) }
            }
            $clean = $text -replace "(?is)<script.*?</script>", " " -replace "(?is)<style.*?</style>", " "
            $clean = $clean -replace "(?is)<br\s*/?>", "`n" -replace "(?is)</(p|div|tr|li|h[1-6]|table)>", "`n"
            $clean = $clean -replace "(?is)<[^>]+>", " "
            $clean = $clean -replace "&nbsp;", " " -replace "&amp;", "&" -replace "&lt;", "<" -replace "&gt;", ">" -replace "&quot;", '"'
            $clean = $clean -replace "[ \t]+", " " -replace "(\r?\n\s*){3,}", "`n`n"
            [System.IO.File]::WriteAllText($txtpath, $clean, (New-Object System.Text.UTF8Encoding($false)))
            $rec.text_chars = $clean.Length
        }
    }
    $results += [pscustomobject]$rec
    Write-Output ("[{0}] {1} -> {2} bytes={3} pdf={4} txt={5} {6}" -f $rec.status, $name, $rec.content_type, $rec.saved_bytes, $rec.is_pdf, $rec.text_chars, $rec.error)
}
$results | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $logdir "G2_fetch_log.json") -Encoding UTF8
Write-Output "DONE"
