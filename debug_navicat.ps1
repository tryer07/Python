$fs = Get-ChildItem "C:\Users\ASUS\Documents\Navicat\Premium\logs\history\*.log" | Sort-Object Name
Write-Host "files=$($fs.Count)"
$t = Get-Content $fs[0].FullName -Encoding UTF8 -Raw
Write-Host "len=$($t.Length)"
$t2 = $t -replace "[\r\n]+", " "
$s = [regex]::Split($t2, "(?=LOG_TIME=)")
Write-Host "segments=$($s.Count)"
Write-Host "queryhits=$(([regex]::Matches($t2, 'QUERY=')).Count)"
$hit = 0
foreach ($seg in $s) { if ($seg -match "QUERY=(.+)\|\s*$") { $hit++ } }
Write-Host "segmatch=$hit"
foreach ($seg in $s) {
    if ($seg -match "QUERY=") { Write-Host ("SAMPLE>>>" + $seg.Substring(0, [Math]::Min(260, $seg.Length))); break }
}
