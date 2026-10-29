# Helper: read the StudyBuddy stack outputs into a hashtable.
function Get-StackOutputs {
    param([string]$Region = "eu-north-1")
    $json = aws cloudformation describe-stacks --stack-name StudyBuddy --region $Region `
        --query "Stacks[0].Outputs" --output json
    if ($LASTEXITCODE -ne 0) { throw "Stack StudyBuddy not found. Run .\scripts\deploy.ps1 first." }
    $outputs = @{}
    foreach ($o in ($json | ConvertFrom-Json)) { $outputs[$o.OutputKey] = $o.OutputValue }
    return $outputs
}

function Get-TelegramSecret {
    param([string]$SecretArn, [string]$Region = "eu-north-1")
    $raw = aws secretsmanager get-secret-value --secret-id $SecretArn --region $Region `
        --query SecretString --output text
    if ($LASTEXITCODE -ne 0) { throw "Could not read the Telegram secret" }
    return ($raw | ConvertFrom-Json)
}
