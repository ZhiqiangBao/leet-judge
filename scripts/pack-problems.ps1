param(
    [Parameter(Mandatory = $true)]
    [string[]] $Slug,
    [string] $Root = ""
)

$ErrorActionPreference = "Stop"
if (-not $Root) {
    $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$problems = Join-Path $Root "problems"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zip = Join-Path $env:TEMP "leet-hub-problems-$stamp.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, "Create")
try {
    foreach ($name in $Slug) {
        $dir = Join-Path $problems $name
        if (-not (Test-Path $dir -PathType Container)) {
            throw "missing problems/$name"
        }
        $prefix = (Resolve-Path $dir).Path
        Get-ChildItem -Path $dir -Recurse -File | ForEach-Object {
            $tail = $_.FullName.Substring($prefix.Length).TrimStart("\")
            $rel = ("problems/" + $name + "/" + $tail).Replace("\", "/")
            [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $_.FullName,
                $rel,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
        }
    }
} finally {
    $archive.Dispose()
}

Write-Output $zip
