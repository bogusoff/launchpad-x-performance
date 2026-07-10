#!/bin/bash
set -euo pipefail

SCRIPT_NAME="Launchpad_X_performance"
STANDARD_USER_LIBRARY="$HOME/Music/Ableton/User Library"

echo
echo "Launchpad X Performance uninstaller"
echo "==================================="
echo

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

echo "Choose User Library location:"
echo
echo "1) Standard Ableton User Library:"
echo "   $STANDARD_USER_LIBRARY"
echo
echo "2) Select another User Library folder"
echo

read -r -p "Enter 1 or 2 [1]: " choice
choice="${choice:-1}"

case "$choice" in
    1)
        USER_LIBRARY="$STANDARD_USER_LIBRARY"
        ;;
    2)
        USER_LIBRARY="$(choose_user_library)"

        if [ -z "$USER_LIBRARY" ]; then
            echo "Uninstall cancelled."
            exit 1
        fi

        USER_LIBRARY="${USER_LIBRARY%/}"
        ;;
    *)
        echo "Error: enter 1 or 2."
        exit 1
        ;;
esac

DESTINATION="$USER_LIBRARY/Remote Scripts/$SCRIPT_NAME"

case "$DESTINATION" in
    /Applications/*|*/Ableton\ Live*.app/*)
        echo "Error: unsafe destination:"
        echo "$DESTINATION"
        exit 1
        ;;
esac

if [ ! -d "$DESTINATION" ]; then
    echo
    echo "Launchpad X Performance is not installed at:"
    echo "$DESTINATION"
    exit 0
fi

echo
echo "Removing:"
echo "$DESTINATION"
echo

rm -rf "$DESTINATION"

echo "Uninstall complete."
echo "Restart Ableton Live."
echo