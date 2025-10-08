#!/bin/bash
cd /home/kavia/workspace/code-generation/nutrition-connect-platform-172674-172685/backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

