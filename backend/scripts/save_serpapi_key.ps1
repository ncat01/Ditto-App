param([switch]$FromClipboard)
$ErrorActionPreference = 'Stop'
$privateDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../.ditto-private'))
New-Item -ItemType Directory -Path $privateDirectory -Force | Out-Null
if ($FromClipboard) {
    $keyText = (Get-Clipboard -Raw).Trim()
    if ($keyText -notmatch '^[a-fA-F0-9]{64}$') {
        throw 'The clipboard does not contain a complete SerpApi API key. Copy it using the Copy button on the SerpApi API-key page.'
    }
    $key = ConvertTo-SecureString -String $keyText -AsPlainText -Force
    $keyText = $null
} else {
    $key = Read-Host 'Paste the SerpApi API key (input is hidden)' -AsSecureString
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
    try {
        $keyText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer).Trim()
        if ($keyText -notmatch '^[a-fA-F0-9]{64}$') {
            throw 'A complete SerpApi API key was not entered. Use the -FromClipboard option after copying your key.'
        }
        $key = ConvertTo-SecureString -String $keyText -AsPlainText -Force
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        $keyText = $null
    }
}
$key | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $privateDirectory 'serpapi-key.dpapi')
Write-Host 'SerpApi key saved privately with Windows encryption. Reply saved privately; never paste the key in chat.'
