# Delete everything StudyBuddy created in AWS (stops all costs).
#
# Usage: .\scripts\destroy.ps1

param([string]$Region = "eu-north-1")

$ErrorActionPreference = "Stop"
$env:CDK_DEFAULT_REGION = $Region

$confirm = Read-Host "This deletes the StudyBuddy stack and its data. Type 'delete' to continue"
if ($confirm -ne "delete") { Write-Host "Cancelled."; exit 0 }

npx --yes aws-cdk@2 destroy StudyBuddy --force -c allowedUserIds=0
if ($LASTEXITCODE -ne 0) { throw "Destroy failed" }
Write-Host "StudyBuddy removed from AWS." -ForegroundColor Green
