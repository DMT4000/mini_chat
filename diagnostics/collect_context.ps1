$ErrorActionPreference = 'Stop'

# Resolve paths and OneDrive state
$projectPath = (Get-Location).Path
$oneDrivePath = $env:OneDrive
$underOneDrive = $false
if ($oneDrivePath) {
    $underOneDrive = $projectPath.ToLower().StartsWith($oneDrivePath.ToLower())
}

# Enumerate attributes and detect cloud-only files (U attribute)
$attribLines = & cmd /c attrib /s /d "*"
$cloudMatches = @($attribLines | Select-String ' U ')
$cloudOnlyCount = $cloudMatches.Count
$cloudOnlySample = @($cloudMatches | Select-Object -First 10 | ForEach-Object { $_.ToString() })

# File count for sanity
$filesTotal = (Get-ChildItem -Recurse -File | Measure-Object).Count

# Assemble JSON diagnostics
$data = [pscustomobject]@{
    oneDrivePath     = $oneDrivePath
    projectPath      = $projectPath
    underOneDrive    = $underOneDrive
    filesTotal       = $filesTotal
    cloudOnlyCount   = $cloudOnlyCount
    cloudOnlySample  = $cloudOnlySample
}

New-Item -ItemType Directory -Force -Path diagnostics | Out-Null
$data | ConvertTo-Json -Depth 4 | Set-Content -Path 'diagnostics/context_results.json' -Encoding UTF8
Write-Output 'Wrote diagnostics/context_results.json'

