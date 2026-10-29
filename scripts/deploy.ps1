# Deploy StudyBuddy to AWS.
#
# Usage (from the project folder):
#   .\scripts\deploy.ps1 -AllowedUserIds 123456789 -BudgetEmail you@example.com
#
# Several Telegram user IDs: -AllowedUserIds "123,456"

param(
    [Parameter(Mandatory = $true)][string]$AllowedUserIds,
    [string]$BudgetEmail = "",
    [string]$Region = "eu-north-1"
)

$ErrorActionPreference = "Stop"
$env:CDK_DEFAULT_REGION = $Region
$env:AWS_REGION = $Region

Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
$account = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0) { throw "Not signed in to AWS. Run: aws login" }
$env:CDK_DEFAULT_ACCOUNT = $account
Write-Host "Account $account, region $Region"

# The first deployment in an account/region needs a one-time CDK bootstrap.
$ErrorActionPreference = "Continue"  # a missing stack writes to stderr; that's expected here
aws cloudformation describe-stacks --stack-name CDKToolkit --region $Region 2>&1 | Out-Null
$needsBootstrap = ($LASTEXITCODE -ne 0)
$ErrorActionPreference = "Stop"
if ($needsBootstrap) {
    Write-Host "First deployment here: bootstrapping CDK (one time only)..." -ForegroundColor Cyan
    npx --yes aws-cdk@2 bootstrap "aws://$account/$Region" -c "allowedUserIds=$AllowedUserIds"
    if ($LASTEXITCODE -ne 0) { throw "CDK bootstrap failed" }
}

$cdkArgs = @("deploy", "StudyBuddy", "--require-approval", "never", "-c", "allowedUserIds=$AllowedUserIds")
if ($BudgetEmail) { $cdkArgs += @("-c", "budgetEmail=$BudgetEmail") }

Write-Host "Deploying (takes 2-4 minutes)..." -ForegroundColor Cyan
npx --yes aws-cdk@2 @cdkArgs
if ($LASTEXITCODE -ne 0) { throw "Deployment failed" }

Write-Host ""
Write-Host "Deployed. Next steps:" -ForegroundColor Green
Write-Host "  1. .\scripts\set-token.ps1     (store your BotFather token, once)"
Write-Host "  2. .\scripts\set-webhook.ps1   (connect Telegram to AWS)"