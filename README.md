# Multi-Media Downloader — Publishable Web Edition

A high-performance universal media downloader web application powered by **Python**, **Flask**, **yt-dlp**, bundled **FFmpeg**, and production **Gunicorn** server.

Ready for local use or 1-click cloud deployment with **monetization ads** and **synchronized live download progress bar while users watch ads**.

---

## ✨ Features

- 🌐 **Publishable & Cloud-Ready**: Complete with Dockerfile, Procfile, docker-compose, and Render configuration for instant hosting.
- 💰 **Built-in Monetization System**:
  - Top Responsive Leaderboard Ad (728x90 / 320x50)
  - Mid-Page In-Content Sponsor Banner
  - Sticky Bottom Banner with dismiss toggle
  - **Exclusive Ad-Watching & Live Progress Overlay**: Users watch an interactive sponsor ad while the real-time download progress bar fills from 0% to 100%, followed by an automatic browser file download trigger.
  - Ready for Google AdSense, Adsterra, PropellerAds, or custom sponsors.
- 🔍 **Auto-Detects Virtually Any Platform**:
  - 🔴 **YouTube** (Videos, Shorts, Playlists, MP3)
  - 🎵 **TikTok** (Watermark-free MP4 & Audio)
  - 📸 **Instagram** (Reels, Posts, Stories)
  - 🐦 **X / Twitter** (Videos & GIFs)
  - 📘 **Facebook** (Reels & Public Videos)
  - 🤖 **Reddit** (v.redd.it with audio)
  - 🟣 **Twitch** (Clips & VODs)
  - 🔷 **Vimeo** & 🟠 **SoundCloud**
  - 🌐 **1,000+ other supported websites**
- ✂️ **Integrated Video Trimming / Clipping**:
  - Embedded player preview (YouTube iframe & HTML5 video).
  - Quick-mark "Set as Start" and "Set as End" buttons directly from current playback position.
  - "Test Clip" previewer.
  - Precision keyframe cutting on download.
- 🎛️ **Quality & Format Selector**:
  - Best Available Quality (Auto up to 4K / 1080p)
  - 1080p Full HD, 720p HD, 480p SD, 360p Low
  - Audio extraction to high-quality MP3 (192 kbps)
- 🧹 **Automatic Server Cleanup**: Background worker cleans files older than 60 minutes to prevent disk exhaustion on public servers.
- ⚡ **Concurrent & Fast**: Multi-threaded architecture supports multiple simultaneous user sessions.

---

## 🚀 How to Run Locally

1. Double-click `start.bat` in this folder.
2. The server will start and automatically open `http://127.0.0.1:5000` in your web browser.

---

## 🌐 How to Publish to the Web

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions for:
- **Render.com** (1-click Docker deployment with free SSL)
- **Railway.app**
- **Fly.io**
- **Docker / Linux VPS** (DigitalOcean, AWS, Linode)
