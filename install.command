#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="Launchpad_X_performance"
SOURCE_DIR="$PROJECT_DIR/src/$SCRIPT_NAME"

STANDARD_LIBRARY="$HOME/Music/Ableton/User Library"
STANDARD_REMOTE_SCRIPTS="$STANDARD_LIBRARY/Remote Scripts"

echo
echo "Launchpad X Performance installer"
echo "================================="
echo

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: source directory not found:"
    echo "$SOURCE_DIR"
    exit 1
fi

choose_user_library() {
    osascript <<'APPLESCRIPT'
try
    set selectedFolder to choose folder with prompt "Select your Ableton User Library folder"
    return POSIX path of selectedFolder
on error number -128
    return ""
end try
APPLESCRIPT
}

echo "Choose installation location:"
echo
echo "1) Standard Ableton User Library:"
echo "   $STANDARD_LIBRARY"
echo
echo "2) Select another User Library folder"
echo

USER_LIBRARY=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --user-library)
            if [ "$#" -lt 2 ]; then
                echo "Error: --user-library requires a path."
                exit 1
            fi

            USER_LIBRARY="${2%/}"
            shift 2
            ;;
        *)
            echo "Error: unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$USER_LIBRARY" ]; then
    read -r -p "Enter 1 or 2 [1]: " choice
    choice="${choice:-1}"

    case "$choice" in
        1)
            USER_LIBRARY="$STANDARD_LIBRARY"
            ;;
        2)
            USER_LIBRARY="$(choose_user_library)"

            if [ -z "$USER_LIBRARY" ]; then
                echo "Installation cancelled."
                exit 1
            fi

            USER_LIBRARY="${USER_LIBRARY%/}"
            ;;
        *)
            echo "Error: enter 1 or 2."
            exit 1
            ;;
    esac
fi

REMOTE_SCRIPTS_DIR="$USER_LIBRARY/Remote Scripts"
DESTINATION="$REMOTE_SCRIPTS_DIR/$SCRIPT_NAME"

# Safety check: never install inside Ableton Live.app.
case "$DESTINATION" in
    /Applications/*|*/Ableton\ Live*.app/*)
        echo "Error: unsafe destination:"
        echo "$DESTINATION"
        exit 1
        ;;
esac

echo
echo "Installing to:"
echo "$DESTINATION"
echo

mkdir -p "$REMOTE_SCRIPTS_DIR"
rm -rf "$DESTINATION"
cp -R "$SOURCE_DIR" "$DESTINATION"

find "$DESTINATION" -name ".DS_Store" -delete 2>/dev/null || true
find "$DESTINATION" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo
echo "Installation complete."
echo
echo "Restart Ableton Live and select:"
echo "Control Surface: $SCRIPT_NAME"
echo "Input: Launchpad X DAW In"
echo "Output: Launchpad X DAW Out"
echo
