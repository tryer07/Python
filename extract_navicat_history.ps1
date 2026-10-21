$files = Get-ChildItem "C:\Users\ASUS\Documents\Navicat\Premium\logs\history\*.log" | Sort-Object Name
$out = "D:\Python\navicat_history_extract.txt"
$errOut = "D:\Python\navicat_error_extract.txt"
$skipPattern = '^(SHOW (VARIABLES|CHARACTER SET|COLLATION|FULL TABLES|TABLE STATUS|CREATE|INDEX|GRANTS|DATABASES|TABLES|COLUMNS|ENGINES)|SELECT (SCHEMA_NAME|@@|TABLE_SCHEMA|DISTINCT ROUTINE_SCHEMA|DATABASE\(\)|\* FROM .LIMIT 0,1000)|SELECT .*FROM information_schema|SELECT COUNT\(\*\) FROM information_schema|SELECT .* WHERE .* LIMIT 1$|SET |/\*|BEGIN;|COMMIT;|RENAME TO|ALTER TABLE .* MODIFY COLUMN .* CHARACTER SET)'
$queries = New-Object System.Collections.ArrayList
$errors = New-Object System.Collections.ArrayList
foreach ($f in $files) {
    $text = (Get-Content $f.FullName -Encoding UTF8 -Raw) -replace "[\r\n]+", " "
    $segments = [regex]::Split($text, '(?=LOG_TIME=)', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    Write-Host "file=$($f.Name) segments=$($segments.Count)"
    $qhit = 0
    foreach ($seg in $segments) {
        $time = ''
        if ($seg -match 'LOG_TIME=([\d\- :\.]+)') { $time = $Matches[1] }
        $level = ''
        if ($seg -match 'LOG_LEVEL=(\w+)') { $level = $Matches[1] }
        if ($seg -match 'QUERY=(.+)\|\s*$') {
            $qhit++
            $q = ($Matches[1] -replace '\s+', ' ').Trim()
            if ($q -notmatch $skipPattern -and $q.Length -gt 3) {
                $queries.Add(("{0} :: {1}" -f $time, $q)) | Out-Null
            }
        }
        if ($level -eq 'Error' -and $seg -match 'ERROR=(.+?) \|') {
            $errors.Add(("{0} :: {1}" -f $time, $Matches[1].Trim())) | Out-Null
        }
    }
    Write-Host "  qhit=$qhit"
}
$queries | Set-Content $out -Encoding UTF8
$errors | Set-Content $errOut -Encoding UTF8
Write-Host "queries=$($queries.Count) errors=$($errors.Count)"
