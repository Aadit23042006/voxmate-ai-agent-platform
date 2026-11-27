# VoxMate GitHub secret cleanup
# Run from the repository root in PowerShell.
# IMPORTANT: rotate/restrict the exposed Google API key in Google Cloud/Firebase first.

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
  throw "Run this script from the Git repository root."
}

# Ensure the detected secret file is not tracked.
git rm --cached --ignore-unmatch "mobile/google-services.json"

# Remove the previously exposed local copy from the repository working tree.
# Download a fresh file again later if you need it for an Android build.
if (Test-Path "mobile/google-services.json") {
  Remove-Item "mobile/google-services.json" -Force
}

# Make sure local secret files remain ignored.
$gitignore = ".gitignore"
$ignoreText = if (Test-Path $gitignore) { Get-Content $gitignore -Raw } else { "" }
if ($ignoreText -notmatch "(?m)^mobile/google-services\.json$") {
  Add-Content -Path $gitignore -Value "`nmobile/google-services.json"
}
if ($ignoreText -notmatch "(?m)^\*\*/google-services\.json$") {
  Add-Content -Path $gitignore -Value "**/google-services.json"
}

# Confirm the current working tree no longer contains the detected key pattern.
$matches = Get-ChildItem -Recurse -File -Force |
  Where-Object { $_.FullName -notmatch "\\.git\\" -and $_.FullName -notmatch "\\node_modules\\" } |
  Select-String -Pattern 'AIza[0-9A-Za-z_-]{20,}' -ErrorAction SilentlyContinue

if ($matches) {
  throw "Potential Google API key still exists in working-tree files. Remove/rotate it before continuing."
}

git add -A
git commit -m "Remove exposed Google API credential"
Write-Host "Working tree cleaned. Because the secret was in an existing commit, the remote history must also be rewritten."

# This repository currently contains a single initial commit. Create a fresh clean root commit.
git checkout --orphan clean-main
git add -A
git commit -m "Clean initial commit"
git branch -M main

# Force-with-lease replaces the remote main history with the cleaned history.
git push --force-with-lease origin main

Write-Host ""
Write-Host "DONE: remote main now points to the clean history."
Write-Host "After GitHub processes the push, review Secret scanning / Security alerts."
Write-Host "If the old alert remains, resolve it there only after the leaked key has been revoked/rotated."
