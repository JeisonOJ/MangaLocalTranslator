# Reproduce only the small CRF compatibility environment, not the manga ML stack.
param([switch]$Offline)
$ErrorActionPreference = 'Stop'
$crfWorkspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$crfAudit = Join-Path $crfWorkspace 'evaluation\crf-binary-audit'
$crfMamba = Join-Path $crfAudit 'micromamba.exe'
$crfPrefix = Join-Path $crfWorkspace 'evaluation\envs\crf312-reproduced'
$crfRoot = Join-Path $crfWorkspace 'evaluation\mamba-root'
$crfConfig = Join-Path $crfAudit 'mambarc.yaml'
$crfLock = Join-Path $crfAudit 'crf312-explicit-lock.txt'
if (Test-Path -LiteralPath $crfPrefix) { throw "Refusing to overwrite existing environment: $crfPrefix" }
if (-not (Test-Path -LiteralPath $crfMamba)) { throw 'Missing audited micromamba executable.' }

# Micromamba registers prefixes in a text file even without shell initialization.
# Remove only the new registration afterward; preserve any preexisting entries.
$crfRegistration = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.conda\environments.txt'
$crfRegistrationExisted = Test-Path -LiteralPath $crfRegistration
$crfPriorLines = if ($crfRegistrationExisted) { @(Get-Content -LiteralPath $crfRegistration) } else { @() }
$crfArgs = @('create', '--rc-file', $crfConfig, '--no-env', '--root-prefix', $crfRoot,
    '--prefix', $crfPrefix, '--file', $crfLock, '--skip-run-link-scripts',
    '--no-shortcuts', '--no-pyc', '--always-copy', '--lock-timeout', '5', '--yes')
if ($Offline) { $crfArgs += '--offline' }
try {
    & $crfMamba @crfArgs
    if ($LASTEXITCODE -ne 0) { throw "Environment installation failed: $LASTEXITCODE" }
} finally {
    if ((Test-Path -LiteralPath $crfRegistration) -and ($crfPriorLines -notcontains $crfPrefix)) {
        $crfCurrentLines = @(Get-Content -LiteralPath $crfRegistration)
        $crfRemaining = @($crfCurrentLines | Where-Object { $_.TrimEnd('\', '/') -ne $crfPrefix.TrimEnd('\', '/') })
        if ($crfRemaining.Count -eq 0 -and -not $crfRegistrationExisted) {
            Remove-Item -LiteralPath $crfRegistration
        } elseif ($crfRemaining.Count -ne $crfCurrentLines.Count) {
            $crfRemaining | Set-Content -LiteralPath $crfRegistration -Encoding utf8
        }
    }
}
& (Join-Path $crfPrefix 'python.exe') -I (Join-Path $PSScriptRoot 'validate_crf_api.py')
if ($LASTEXITCODE -ne 0) { throw 'CRF compatibility validation failed.' }
& (Join-Path $crfPrefix 'python.exe') -I -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Package consistency check failed.' }
