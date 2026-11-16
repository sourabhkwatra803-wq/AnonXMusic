#!/bin/bash
echo "🚀 Wavy All-in-One Bot Auto-Restore Shuru Ho Raha Hai..."
if command -v pkg >/dev/null 2>&1; then
    pkg update -y && pkg install -y python ffmpeg git unzip
fi
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi
pip install -U yt-dlp Pillow google-genai
echo "✅ Sab kuch install aur restore ho gaya hai! Bot start ho raha hai..."
python3 -m anony
