#!/bin/bash
cd /workspaces/AnonXMusic || exit 1
if pgrep -f "python3 -m anony" > /dev/null; then
    exit 0
fi
nohup bash -c 'while true; do python3 -m anony; sleep 4; done' > /workspaces/AnonXMusic/bot.log 2>&1 &
