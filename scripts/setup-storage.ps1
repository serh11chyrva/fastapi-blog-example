# Provision local Garage storage before starting the API. Safe to run repeatedly.
param([string]$AccessKey = $env:GARAGE_ACCESS_KEY)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    if (-not $AccessKey) {
        $taskEnv = Join-Path $taskRoot '.env'
        $taskKeyLine = Get-Content -LiteralPath $taskEnv | Where-Object { $_ -match '^\s*GARAGE_ACCESS_KEY\s*=' } | Select-Object -Last 1
        if ($taskKeyLine) { $AccessKey = ($taskKeyLine -split '=', 2)[1].Trim().Trim('"').Trim("'") }
    }
    if (-not $AccessKey) { throw 'Set GARAGE_ACCESS_KEY in .env or pass -AccessKey.' }
    docker compose up -d --wait garage
    if ($LASTEXITCODE -ne 0) { throw 'Garage did not become ready.' }
    foreach ($taskBucket in @('blog-avatars', 'blog-publications')) {
        $taskBucketExists = $false
        try {
            docker compose exec -T garage /garage bucket info $taskBucket *> $null
            $taskBucketExists = $LASTEXITCODE -eq 0
        }
        catch { $taskBucketExists = $false }
        if (-not $taskBucketExists) {
            docker compose exec -T garage /garage bucket create $taskBucket
            if ($LASTEXITCODE -ne 0) { throw "Cannot create bucket $taskBucket." }
        }
        docker compose exec -T garage /garage bucket allow --read --write --owner $taskBucket --key $AccessKey
        if ($LASTEXITCODE -ne 0) { throw "Cannot grant permissions for $taskBucket." }
    }
    Get-Content -LiteralPath (Join-Path $taskRoot 'src/backend/storage/setup.py') -Raw |
        docker compose run --rm --no-deps -T api python -
    if ($LASTEXITCODE -ne 0) { throw 'Storage CORS configuration failed.' }
}
finally { Pop-Location }
