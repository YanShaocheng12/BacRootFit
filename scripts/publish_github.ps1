param(
    [string]$Repository = 'YanShaocheng12/BacRootFit',
    [string]$AssetsDirectory = (Join-Path $PSScriptRoot '..\..\assets'),
    [ValidateSet('public','private')][string]$Visibility = 'public'
)
$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$assetsRoot = [System.IO.Path]::GetFullPath($AssetsDirectory)
if ($Repository -notmatch '^YanShaocheng12/[A-Za-z0-9_.-]+$') { throw 'Expected an explicitly configured YanShaocheng12 repository.' }
Get-Command git,gh -ErrorAction Stop | Out-Null
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Authenticate GitHub CLI before publishing. Do not put a token in this script.' }
$login = (& gh api user --jq .login).Trim()
if ($login -cne 'YanShaocheng12') { throw "Authenticated account is $login; expected YanShaocheng12." }
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot 'release_manifest.json') -Raw | ConvertFrom-Json
foreach ($asset in $manifest.assets) {
    $path = Join-Path $assetsRoot $asset.filename
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset.sha256) { throw "Asset checksum mismatch: $path" }
}
Push-Location -LiteralPath $repoRoot
try {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.git'))) {
        & git init -b main
        if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
    }
    & git add --all
    if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        & git -c user.name='Shaocheng Yan' -c user.email='YanShaocheng12@users.noreply.github.com' commit -m 'Prepare BacRootFit v1.0.0 publication resource'
        if ($LASTEXITCODE -ne 0) { throw 'git commit failed' }
    }
    & gh repo view $Repository --json name 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & gh repo create $Repository "--$Visibility" --description 'Experimental bacterial root-colonization evidence and frozen ProtT5 prediction' --source . --remote origin
        if ($LASTEXITCODE -ne 0) { throw 'Repository creation failed' }
    }
    $remote = (& git remote get-url origin 2>$null)
    $expected = "https://github.com/$Repository.git"
    if (-not $remote) { & git remote add origin $expected }
    elseif ($remote.TrimEnd('/') -ne $expected -and $remote.TrimEnd('/') -ne $expected.Replace('.git','')) { throw 'Existing origin differs; no remote was changed.' }
    & git push -u origin main
    if ($LASTEXITCODE -ne 0) { throw 'Push failed; no force-push was attempted.' }
    & gh release view v1.0.0 --repo $Repository 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { throw 'Release v1.0.0 already exists; it was not overwritten.' }
    $assetPaths = @($manifest.assets | ForEach-Object { Join-Path $assetsRoot $_.filename })
    & gh release create v1.0.0 @assetPaths --repo $Repository --draft --title 'BacRootFit v1.0.0' --notes-file (Join-Path $repoRoot 'RELEASE_NOTES.md')
    if ($LASTEXITCODE -ne 0) { throw 'Draft release upload failed' }
} finally { Pop-Location }
