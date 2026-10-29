# Follow the live logs of a function while you test the bot.
#
# Usage: .\scripts\logs.ps1            (worker)
#        .\scripts\logs.ps1 -Function Webhook

param(
    [ValidateSet("Worker", "Webhook")][string]$Function = "Worker",
    [string]$Region = "eu-north-1"
)

$name = aws cloudformation describe-stack-resources --stack-name StudyBuddy --region $Region `
    --query "StackResources[?ResourceType=='AWS::Lambda::Function' && starts_with(LogicalResourceId, '$($Function)Function')].PhysicalResourceId" `
    --output text
if (-not $name) { throw "Function not found. Is the stack deployed?" }
aws logs tail "/aws/lambda/$name" --follow --format short --region $Region
