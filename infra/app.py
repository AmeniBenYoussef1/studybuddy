#!/usr/bin/env python3
"""CDK entry point.

Settings come from cdk.json "context" or the command line, e.g.:
    npx cdk deploy -c allowedUserIds=123456789 -c budgetEmail=you@example.com
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import aws_cdk as cdk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stacks.studybuddy_stack import StudyBuddyStack

app = cdk.App()

allowed = str(app.node.try_get_context("allowedUserIds") or "")
if not allowed.strip():
    raise SystemExit(
        "Set your Telegram user ID: npx cdk deploy -c allowedUserIds=123456789 "
        "(several IDs: comma-separated)"
    )

StudyBuddyStack(
    app,
    "StudyBuddy",
    allowed_user_ids=allowed,
    budget_email=app.node.try_get_context("budgetEmail"),
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "eu-north-1"),
    ),
)
cdk.Tags.of(app).add("project", "studybuddy")

app.synth()
