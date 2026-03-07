#!/bin/bash
# KG Session Context Hook
# Injects knowledge graph context summary at session start.
# Remove or comment out the settings.json entry to disable.

# Ensure kg and system commands are available
export PATH="$HOME/.pyenv/shims:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Read stdin (required by Claude Code hook protocol)
cat > /dev/null

# Check if kg command is available
if ! command -v kg &> /dev/null; then
    exit 0
fi

# Check if the database exists
DB_PATH="${HOME}/.claude-conversation-kg/graph.db"
if [ ! -e "$DB_PATH" ]; then
    exit 0
fi

# Generate context and output as additionalContext for the session
CONTEXT=$(kg context --plain --top 5 --days 7 2>/dev/null)
if [ -n "$CONTEXT" ]; then
    # Escape for JSON
    ESCAPED=$(echo "$CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
    echo "{\"additionalContext\": ${ESCAPED}}"
fi

exit 0
