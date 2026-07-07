#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="Launchpad_X_performance"

DEST_1="/Users/bogusoff/Music/Ableton/User Library/Remote Scripts"
DEST_2="/Users/bogusoff/Yandex.Disk.localized/Studio/Ableton/User Library/Remote Scripts"

echo "Installing $SCRIPT_NAME..."

rm -rf "$DEST_1/$SCRIPT_NAME"
rm -rf "$DEST_2/$SCRIPT_NAME"

mkdir -p "$DEST_1"
mkdir -p "$DEST_2"

cp -R "$PROJECT_DIR/src/$SCRIPT_NAME" "$DEST_1/"
cp -R "$PROJECT_DIR/src/$SCRIPT_NAME" "$DEST_2/"

echo "Done."
echo "Restart Ableton Live."
