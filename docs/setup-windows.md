# Setting up StudyBuddy on Windows (week 1)

About 30–40 minutes the first time. Run every command in **PowerShell** (not as administrator),
from the project folder.

## 0. What you need

| Tool | Check | Install |
| --- | --- | --- |
| AWS CLI, signed in | `aws sts get-caller-identity` shows your account | Already done with `aws login` |
| Python 3.12 or newer | `py --version` | [python.org/downloads](https://www.python.org/downloads/) (tick "Add python.exe to PATH") |
| Node.js 20 or newer | `node --version` | [nodejs.org](https://nodejs.org/), LTS version (needed for the CDK tool) |
| Git | `git --version` | [git-scm.com](https://git-scm.com/downloads/win) |
| Telegram | | Phone app, Telegram Desktop, or web.telegram.org |

If `aws sts get-caller-identity` fails, your session expired: run `aws login` again.

## 1. Create the Telegram bot

1. In Telegram, open **@BotFather** (blue checkmark) and send `/newbot`.
2. Name: `StudyBuddy`. Username: something ending in `bot`, e.g. `ameni_studybuddy_bot`.
3. Copy the **token** BotFather gives you. Keep it secret: don't paste it in chats or code.
4. Message **@userinfobot** to get your **user ID** (a number).

## 2. Put the project on your PC

Unzip `studybuddy.zip` to `C:\Users\ameni\studybuddy`, then:

```powershell
cd $HOME\studybuddy
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

If PowerShell says *running scripts is disabled*, run this once, then retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Check that everything works locally

```powershell
pytest
```

All tests should pass (the infrastructure tests run here, because `aws-cdk-lib` is installed).

## 4. Deploy to AWS

```powershell
.\scripts\deploy.ps1 -AllowedUserIds 123456789 -BudgetEmail you@example.com
```

Replace the number with your Telegram user ID. The first run also "bootstraps" CDK in your account
(a one-time setup). It takes a few minutes. AWS sends a confirmation email for the budget alerts.

## 5. Store the bot token and connect Telegram

```powershell
.\scripts\set-token.ps1      # paste the BotFather token (hidden)
.\scripts\set-webhook.ps1    # tells Telegram where to send messages
```

## 6. Test it

Send your bot `/start`, then any text, a voice note and a photo. You should get:

- `/start` → the welcome message
- text → `You said: ...`
- voice / photo / file → a placeholder saying which week adds that feature

To watch what happens in AWS while you test:

```powershell
.\scripts\logs.ps1
```

## 7. Put it on GitHub

1. Create an empty **public** repository named `studybuddy` on GitHub (no README).
2. In the project folder:

```powershell
git init
git add .
git commit -m "Week 1: serverless Telegram pipeline on AWS"
git branch -M main
git remote add origin https://github.com/<your-username>/studybuddy.git
git push -u origin main
```

GitHub Actions runs the tests automatically on every push (the "Actions" tab).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Bot doesn't answer | Run `.\scripts\logs.ps1 -Function Webhook`. "bad secret token" → rerun `set-webhook.ps1`. "not on allowlist" → redeploy with the right user ID. |
| `ExpiredToken` / credential errors | `aws login` |
| `'charmap' codec` error | `$env:PYTHONUTF8=1`, then retry |
| `npx` not found | Install Node.js, then open a new PowerShell window |
| Deploy says a service isn't available on your plan | Send the error to Claude; some services need checking on the Free Plan |

## Stopping costs

```powershell
.\scripts\destroy.ps1
```
