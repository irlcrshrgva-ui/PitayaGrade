param(
  [Parameter(Mandatory = $true)][string]$KeystorePath,
  [Parameter(Mandatory = $true)][string]$KeyAlias,
  [Parameter(Mandatory = $true)][string]$OutputAudit,
  [string]$SdkRoot = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'Android/Sdk' }),
  [string]$JavaHome = $env:JAVA_HOME
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$auditPath = [System.IO.Path]::GetFullPath($OutputAudit)
$keyPath = [System.IO.Path]::GetFullPath($KeystorePath)
if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) { throw 'The release keystore file does not exist.' }
if (Test-Path -LiteralPath $auditPath) { throw 'The release audit already exists; choose a new path.' }
if (-not $env:PITAYAGRADE_STORE_PASSWORD -or -not $env:PITAYAGRADE_KEY_PASSWORD) {
  throw 'Set PITAYAGRADE_STORE_PASSWORD and PITAYAGRADE_KEY_PASSWORD for this terminal session.'
}
if (-not $JavaHome -or -not (Test-Path (Join-Path $JavaHome 'bin/java.exe'))) {
  throw 'Provide -JavaHome pointing to a Java 21 installation.'
}
if (-not (Test-Path (Join-Path $SdkRoot 'platforms/android-36/android.jar'))) {
  throw 'Android SDK platform 36 is missing.'
}
$buildTools = Get-ChildItem -LiteralPath (Join-Path $SdkRoot 'build-tools') -Directory |
  Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
$apksigner = if ($buildTools) { Join-Path $buildTools.FullName 'apksigner.bat' } else { $null }
if (-not $apksigner -or -not (Test-Path -LiteralPath $apksigner)) { throw 'Android apksigner was not found.' }

Push-Location $projectRoot
$originalJavaHome = $env:JAVA_HOME
$originalKeystore = $env:PITAYAGRADE_KEYSTORE_PATH
$originalAlias = $env:PITAYAGRADE_KEY_ALIAS
try {
  if (git status --porcelain) { throw 'Commit or stash project changes before producing the signed release.' }
  $sourceCommit = (git rev-parse HEAD).Trim()
  $env:JAVA_HOME = $JavaHome
  $env:PITAYAGRADE_KEYSTORE_PATH = $keyPath
  $env:PITAYAGRADE_KEY_ALIAS = $KeyAlias
  & node scripts/sync-web.js
  if ($LASTEXITCODE -ne 0) { throw 'Web asset synchronization failed.' }
  & node --test tests/*.test.js
  if ($LASTEXITCODE -ne 0) { throw 'App regression tests failed.' }
  & node node_modules/@capacitor/cli/bin/capacitor sync android
  if ($LASTEXITCODE -ne 0) { throw 'Capacitor synchronization failed.' }
  $sdkPath = (Resolve-Path -LiteralPath $SdkRoot).Path.Replace('\', '/').Replace(':', '\:')
  Set-Content -LiteralPath android/local.properties -Value "sdk.dir=$sdkPath" -Encoding ascii
  Push-Location android
  try {
    ./gradlew.bat assembleRelease lintRelease --console=plain
    if ($LASTEXITCODE -ne 0) { throw 'Signed Android release build or lint failed.' }
  } finally { Pop-Location }

  $apk = Join-Path $projectRoot 'android/app/build/outputs/apk/release/app-release.apk'
  if (-not (Test-Path -LiteralPath $apk -PathType Leaf)) { throw 'The signed release APK was not produced.' }
  $verification = (& $apksigner verify --verbose --print-certs $apk 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0 -or $verification -notmatch '(?m)^Verifies\s*$') { throw 'APK signature verification failed.' }
  $certificateMatch = [regex]::Match($verification, 'certificate SHA-256 digest:\s*([0-9A-Fa-f:]+)')
  if (-not $certificateMatch.Success) { throw 'Could not read the signing certificate SHA-256 digest.' }
  $certificateSha = $certificateMatch.Groups[1].Value.Replace(':', '').ToLowerInvariant()
  $apkSha = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
  $gradle = Get-Content -LiteralPath android/app/build.gradle -Raw
  $versionName = [regex]::Match($gradle, 'versionName\s+"([^"]+)"').Groups[1].Value
  $versionCode = [int][regex]::Match($gradle, 'versionCode\s+(\d+)').Groups[1].Value
  $audit = [ordered]@{
    generatedAt = [DateTimeOffset]::UtcNow.ToString('o')
    status = 'signed-release-verified'
    sourceCommit = $sourceCommit
    apkPath = [System.IO.Path]::GetFullPath($apk)
    apkSha256 = $apkSha
    certificateSha256 = $certificateSha
    signatureVerified = $true
    versionName = $versionName
    versionCode = $versionCode
    verificationTool = [System.IO.Path]::GetFullPath($apksigner)
  }
  $parent = Split-Path $auditPath -Parent
  if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
  $audit | ConvertTo-Json | Set-Content -LiteralPath $auditPath -Encoding utf8 -NoNewline
  $audit | ConvertTo-Json
} finally {
  $env:JAVA_HOME = $originalJavaHome
  $env:PITAYAGRADE_KEYSTORE_PATH = $originalKeystore
  $env:PITAYAGRADE_KEY_ALIAS = $originalAlias
  Pop-Location
}
