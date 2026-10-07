$ErrorActionPreference = 'Stop'
$privateDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../.ditto-private'))
New-Item -ItemType Directory -Path $privateDirectory -Force | Out-Null
$password = Read-Host 'Paste the Google App Password for Ditto (input is hidden)' -AsSecureString
if ($password.Length -eq 0) { throw 'No password entered.' }
$password | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $privateDirectory 'gmail-password.dpapi')
Write-Host 'Saved privately with Windows encryption. Do not attach this file to chat.'
