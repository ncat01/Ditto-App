$ErrorActionPreference = 'Stop'
$privateDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../.ditto-private'))
New-Item -ItemType Directory -Path $privateDirectory -Force | Out-Null
$key = Read-Host 'Paste the Google Cloud Vision API key (input is hidden)' -AsSecureString
if ($key.Length -eq 0) { throw 'No key entered.' }
$key | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $privateDirectory 'google-vision-key.dpapi')
Write-Host 'Vision key saved privately with Windows encryption. Reply saved privately; never paste the key in chat.'
