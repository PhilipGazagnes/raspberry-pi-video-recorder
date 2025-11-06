#!/bin/bash
#
# Uninstall Script - Clean Environment
#
# Removes all installation artifacts to simulate a fresh system
# Use this to test the setup script from scratch
#
# Usage:
#   chmod +x UNINSTALL.sh
#   ./UNINSTALL.sh

echo "=========================================="
echo "Uninstall Script - Clean Environment"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will remove:"
echo "  - Virtual environment (.venv/)"
echo "  - System GPIO packages"
echo "  - User from gpio group"
echo "  - Generated files (logs, recordings)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

CURRENT_USER=$(whoami)

echo ""
echo "Step 1: Deactivating and removing virtual environment..."
echo "----------------------------------------"
# Deactivate if active (won't error if not active)
deactivate 2>/dev/null || true

if [ -d ".venv" ]; then
    rm -rf .venv
    echo "✓ Removed .venv/"
else
    echo "  (no .venv found)"
fi

echo ""
echo "Step 2: Removing system GPIO packages..."
echo "----------------------------------------"
sudo apt-get remove -y python3-lgpio python3-rpi-lgpio 2>/dev/null || echo "  (packages not installed)"
sudo apt-get autoremove -y 2>/dev/null

echo ""
echo "Step 3: Removing user from gpio group..."
echo "----------------------------------------"
sudo deluser $CURRENT_USER gpio 2>/dev/null && echo "✓ Removed $CURRENT_USER from gpio group" || echo "  (user not in gpio group)"

echo ""
echo "Step 4: Cleaning generated files..."
echo "----------------------------------------"

# Remove logs
if [ -f "recorder-service.log" ]; then
    rm -f recorder-service.log*
    echo "✓ Removed local log files"
fi

# Remove temp videos
if [ -d "temp_videos" ]; then
    rm -rf temp_videos
    echo "✓ Removed temp_videos/"
fi

# Remove credentials (optional - prompts first)
if [ -d "credentials" ]; then
    echo ""
    read -p "Remove credentials directory? (keeps client_secret.json safe) (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf credentials
        echo "✓ Removed credentials/"
    else
        # Only remove token.json, keep client_secret.json
        if [ -f "credentials/token.json" ]; then
            rm -f credentials/token.json
            echo "✓ Removed token.json (kept client_secret.json)"
        fi
    fi
fi

# Remove .env (optional - prompts first)
if [ -f ".env" ]; then
    echo ""
    read -p "Remove .env file? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f .env
        echo "✓ Removed .env"
    fi
fi

# Remove __pycache__ and .pyc files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "✓ Removed Python cache files"

echo ""
echo "Step 5: Verification..."
echo "----------------------------------------"

# Check virtual environment
if [ -d ".venv" ]; then
    echo "❌ .venv still exists"
else
    echo "✓ No virtual environment"
fi

# Check GPIO packages
if dpkg -l | grep -q python3-rpi-lgpio; then
    echo "⚠️  python3-rpi-lgpio still installed"
else
    echo "✓ GPIO packages removed"
fi

# Check group membership
if groups $CURRENT_USER | grep -q gpio; then
    echo "⚠️  $CURRENT_USER still in gpio group (reboot needed)"
else
    echo "✓ Not in gpio group"
fi

echo ""
echo "=========================================="
echo "✅ Uninstall Complete!"
echo "=========================================="
echo ""
echo "Your system is now in a clean state, similar to a fresh Pi."
echo ""
echo "To test the setup script:"
echo "  ./setup_pi5.sh"
echo ""
echo "⚠️  NOTE: If you were in the gpio group, you may need to"
echo "    log out and back in (or reboot) for the removal to"
echo "    fully take effect."
echo ""
