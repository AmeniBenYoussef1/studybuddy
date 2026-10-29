# Store your BotFather token in AWS Secrets Manager (never in code or Git).
#
# Usage: .\scripts\set-token.ps1
# The token is typed hidden and never printed or saved on disk.

param([string]$Region = "eu-north-1")

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_outputs.ps1"

$outputs = Get-StackOutputs -Region $Region
$secretArn = $outputs["TelegramSecretArn"]
$secret = Get-TelegramSecret -SecretArn $secretArn -Region $Region

$secure = Read-Host "Paste your BotFather token (input hidden)" -AsSecureString
$token = [System.Net.NetworkCredential]::new("", $secure).Password.Trim()
if ($token -notmatch '^\d+:[A-Za-z0-9_-]{30,}$') {
    throw "That doesn't look like a bot token (expected something like 123456:ABC-...)."
}

$secret.bot_token = $token
$tmp = New-TemporaryFile
try {
    # Write to a temp file so the token never appears in the command line or history.
    ($secret | ConvertTo-Json -Compress) | Set-Content -Path $tmp -NoNewline -Encoding ascii
    aws secretsmanager put-secret-value --secret-id $secretArn --region $Region `
        --secret-string "file://$tmp" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not update the secret" }
}
finally {
    Remove-Item $tmp -Force
}

Write-Host "Token stored in AWS Secrets Manager." -ForegroundColor Green
Write-Host "Next: .\scripts\set-webhook.ps1"
