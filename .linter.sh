#!/bin/bash
cd /home/kavia/workspace/code-generation/reactfasttictactoe-115041-5617829c/tic_tac_toe_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

