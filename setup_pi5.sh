#!/bin/bash
#
# Raspberry Pi 5 Setup Script
#
# Automates installation of GPIO dependencies and permissions
# for Raspberry Pi Video Recorder on Raspberry Pi 5
#
# Usage:
#   chmod +x setup_pi5.sh
#   ./setup_pi5.sh

set -e  # Exit on any error

echo "=========================================="
echo "Raspberry Pi 5 Setup Script"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi 5
PI_MODEL=$(cat /proc/cpuinfo | grep Model | head -n 1)
echo "Detected: $PI_MODEL"
echo ""

if [[ ! "$PI_MODEL" =~ "Raspberry Pi 5" ]]; then
    echo "⚠️  WARNING: This script is designed for Raspberry Pi 5"
    echo "   Your model may not need these specific steps"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Step 1: Installing GPIO libraries for Raspberry Pi 5..."
echo "----------------------------------------"
# Pi 5 requires lgpio, not RPi.GPIO
sudo apt-get update
sudo apt-get install -y python3-lgpio python3-rpi-lgpio

echo ""
echo "Step 2: Adding user to GPIO group..."
echo "----------------------------------------"
# Add current user to gpio group for GPIO access without sudo
CURRENT_USER=$(whoami)
sudo usermod -a -G gpio $CURRENT_USER

echo ""
echo "Step 3: Installing other system dependencies..."
echo "----------------------------------------"
# FFmpeg for video recording
sudo apt-get install -y ffmpeg v4l-utils

echo ""
echo "Step 4: Setting up Python virtual environment..."
echo "----------------------------------------"
# Check if venv exists
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists"
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
    else
        echo "Skipping venv creation"
        echo ""
        echo "=========================================="
        echo "⚠️  IMPORTANT: Recreate venv manually with:"
        echo "   rm -rf .venv"
        echo "   python3 -m venv .venv --system-site-packages"
        echo "=========================================="
    fi
fi

if [ ! -d ".venv" ]; then
    # Create venv WITH system site packages (required for GPIO libs)
    python3 -m venv .venv --system-site-packages
    echo "✓ Virtual environment created with system package access"
fi

echo ""
echo "Step 5: Installing Python dependencies..."
echo "----------------------------------------"
source .venv/bin/activate
pip install --upgrade pip

# Install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Installed dependencies from requirements.txt"
else
    echo "⚠️  No requirements.txt found, skipping pip install"
fi

echo ""
echo "Step 6: Testing GPIO access..."
echo "----------------------------------------"
python -c "import RPi.GPIO; print('✓ RPi.GPIO (rpi-lgpio) imported successfully')" || {
    echo "❌ GPIO import failed"
    exit 1
}

echo ""
echo "Step 7: YouTube Authentication Setup..."
echo "----------------------------------------"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from .env.example"
    else
        cat > .env << 'EOF'
# YouTube OAuth Configuration
YOUTUBE_CLIENT_SECRET_PATH=credentials/client_secret.json
YOUTUBE_TOKEN_PATH=credentials/token.json
YOUTUBE_PLAYLIST_ID=
EOF
        echo "✓ Created .env file with defaults"
    fi
else
    echo "✓ .env file already exists"
fi

# Create credentials directory
mkdir -p credentials

# Check if client_secret.json exists
if [ ! -f "credentials/client_secret.json" ]; then
    echo ""
    echo "⚠️  YouTube authentication not configured!"
    echo ""
    echo "To enable YouTube uploads, you need to:"
    echo "1. Download client_secret.json from Google Cloud Console"
    echo "2. Place it in: credentials/client_secret.json"
    echo "3. Run: python setup_youtube_auth.py"
    echo ""
    read -p "Do you have client_secret.json ready now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Please place client_secret.json in credentials/ directory"
        read -p "Press Enter when ready to continue..."

        if [ -f "credentials/client_secret.json" ]; then
            echo "✓ Found client_secret.json"
            echo ""
            echo "Running YouTube authentication setup..."
            python setup_youtube_auth.py || {
                echo "⚠️  Authentication setup failed or was skipped"
                echo "You can run it later with: python setup_youtube_auth.py"
            }
        else
            echo "⚠️  client_secret.json not found"
            echo "You can set this up later with: python setup_youtube_auth.py"
        fi
    else
        echo ""
        echo "Skipping YouTube setup for now."
        echo "Run later with: python setup_youtube_auth.py"
    fi
else
    echo "✓ client_secret.json found"

    # Check if token.json exists
    if [ ! -f "credentials/token.json" ]; then
        echo ""
        echo "Running YouTube authentication (will open browser)..."
        python setup_youtube_auth.py || {
            echo "⚠️  Authentication setup failed or was skipped"
            echo "You can run it later with: python setup_youtube_auth.py"
        }
    else
        echo "✓ YouTube authentication already configured (token.json exists)"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT: You must log out and back in (or reboot)"
echo "for GPIO group membership to take effect!"
echo ""
echo "After reboot:"
echo "  cd /opt/raspberry-pi-video-recorder"
echo "  source .venv/bin/activate"
echo "  python recorder_service.py"
echo ""

if [ ! -f "credentials/token.json" ]; then
    echo "⚠️  Remember to setup YouTube authentication:"
    echo "  python setup_youtube_auth.py"
    echo ""
fi

echo "Would you like to reboot now? (recommended)"
read -p "Reboot? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi
