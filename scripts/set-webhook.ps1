# Tell Telegram to send your bot's messages to the AWS webhook.
#
# Usage: .\scripts\set-webhook.ps1
# Run it again after redeploying if the webhook URL changed.

param([string]$Region = "eu-north-1")

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_outputs.ps1"

$outputs = Get-StackOutputs -Region $Region
$secret = Get-TelegramSecret -SecretArn $outputs["TelegramSecretArn"] -Region $Region
if ($secret.bot_token -eq "REPLACE_ME") { throw "Run .\scripts\set-token.ps1 first." }

$body = @{
    url                  = $outputs["WebhookUrl"]
    secret_token         = $secret.webhook_secret
    allowed_updates      = @("message")
    drop_pending_updates = $true
} | ConvertTo-Json

$api = "https://api.telegram.org/bot$($secret.bot_token)"
$result = Invoke-RestMethod -Method Post -Uri "$api/setWebhook" -ContentType "application/json" -Body $body
if (-not $result.ok) { throw "Telegram refused the webhook: $($result.description)" }

$info = Invoke-RestMethod -Uri "$api/getWebhookInfo"
Write-Host "Webhook set to $($info.result.url)" -ForegroundColor Green
Write-Host "Now open Telegram and send a message to your bot."
