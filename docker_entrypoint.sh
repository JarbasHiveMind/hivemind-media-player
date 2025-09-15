#!/bin/bash

# Install plugins via pip command when a setup.py exists
player_list=~/.config/hivemind/player.list
player_list_state=~/.local/state/hivemind/player.state

if test -f "$player_list"; then
    if ! diff -q -B <(grep -vE '^\s*(#|$)' "$player_list") <(grep -vE '^\s*(#|$)' "$player_list_state" 2>/dev/null) &>/dev/null; then
        if pip3 install --no-cache-dir -r "$player_list"; then
            cp "$player_list" "$player_list_state"
        else
            echo "Error: Failed to install packages from $player_list"
            exit 1
        fi
    fi
fi

# Run hivemind-core
if ! hivemind-core listen; then
    echo "Error: Failed to start hivemind-core"
    exit 1
fi
