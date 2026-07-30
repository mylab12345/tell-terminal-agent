<#
Add this repo folder to the current user's PATH and ensure the package is installed.
Run from the repository root with:
  .\install_tell.ps1
#>

$repoRoot = (Get-Location).Path
$repoRoot = Resolve-Path $repoRoot | Select-Object -ExpandProperty Path
$pythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { $null }

if (-not $pythonCmd) {
    Write-Error 'Python is not installed or not on PATH. Install Python first.'
    exit 1
}

Write-Host "Ensuring editable install for repo: $repoRoot"
& $pythonCmd -m pip install -e "$repoRoot"
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Failed to install package. Check pip output above.'
    exit $LASTEXITCODE
}

$pathValue = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($pathValue -notlike "*${repoRoot}*") {
    $newPath = "$pathValue;$repoRoot"
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Host "Added $repoRoot to user PATH."
} else {
    Write-Host "Repository root is already in user PATH."
}

Write-Host 'Done. Restart your terminal or open a new PowerShell session to use tell globally.'
