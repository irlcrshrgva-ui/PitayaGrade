param(
  [string]$SdkRoot = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'Android/Sdk' }),
  [string]$JavaHome = $env:JAVA_HOME
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $JavaHome -or -not (Test-Path (Join-Path $JavaHome 'bin/java.exe'))) {
  throw 'Provide -JavaHome pointing to a Java 21 installation (Android Studio jbr can be used).'
}
if (-not (Test-Path (Join-Path $SdkRoot 'platforms/android-36/android.jar'))) {
  throw 'Android SDK platform 36 is missing. Install it using Android Studio SDK Manager.'
}
$originalJavaHome = $env:JAVA_HOME
try {
  $env:JAVA_HOME = $JavaHome
  Push-Location $projectRoot
  try {
    node scripts/sync-web.js
    if ($LASTEXITCODE -ne 0) { throw 'Web asset synchronization failed.' }
    node --test tests/*.test.js
    if ($LASTEXITCODE -ne 0) { throw 'App regression tests failed.' }
    node node_modules/@capacitor/cli/bin/capacitor sync android
    if ($LASTEXITCODE -ne 0) { throw 'Capacitor synchronization failed.' }
    $sdkPath = (Resolve-Path -LiteralPath $SdkRoot).Path.Replace('\', '/').Replace(':', '\:')
    Set-Content -LiteralPath android/local.properties -Value "sdk.dir=$sdkPath" -Encoding ascii
    Push-Location android
    try {
      ./gradlew.bat assembleDebug lintDebug --console=plain
      if ($LASTEXITCODE -ne 0) { throw 'Android build or lint failed.' }
    } finally { Pop-Location }
    $apk = Join-Path $projectRoot 'android/app/build/outputs/apk/debug/app-debug.apk'
    Get-Item -LiteralPath $apk | Select-Object FullName, Length, LastWriteTime
    Write-Output ('APK SHA256: ' + (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash)
  } finally { Pop-Location }
} finally { $env:JAVA_HOME = $originalJavaHome }
