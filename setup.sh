#!/bin/bash
# setup.sh - Altin Blok Dashboard kurulumu ve çalıştırma

echo "🔹 Sanal ortam kuruluyor..."
python3 -m venv venv

echo "🔹 Sanal ortam aktif ediliyor..."
source venv/bin/activate

echo "🔹 Pip güncelleniyor..."
python3 -m pip install --upgrade pip

echo "🔹 Gerekli paketler yükleniyor..."
python3 -m pip install streamlit pandas matplotlib

echo "🔹 Dashboard başlatılıyor..."
streamlit run voice_dashboard.py
