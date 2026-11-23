# Deployment & Monetization Guide

This guide details how to publish the **Universal Multi-Media Downloader** to the internet as a live website, set up custom domains, and configure advertisements (Google AdSense, Adsterra, PropellerAds, or direct sponsor banners).

---

## 🚀 Option 1: Free / 1-Click Deployment on Render.com (Recommended)

[Render](https://render.com) provides free and affordable Docker and web service hosting.

1. **Push your repository to GitHub or GitLab**.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Web Service**.
4. Connect your GitHub repository.
5. In the configuration:
   - **Environment**: `Docker`
   - **Region**: Choose the closest to your target audience.
   - **Branch**: `main`
   - **Plan**: `Free` or `Starter`
6. Render will automatically detect the `Dockerfile`, install FFmpeg, build the image, and assign you a free `https://your-service.onrender.com` URL!

---

## 🚂 Option 2: Deploy on Railway.app

1. Sign up on [Railway.app](https://railway.app).
2. Click **New Project** > **Deploy from GitHub repo**.
3. Select this repository.
4. Railway will automatically detect the `Dockerfile` or `Procfile` and deploy it with zero configuration.
5. Go to **Settings** > **Networking** to generate a public domain (e.g., `media-downloader.up.railway.app`) or attach a custom domain.

---

## 🪂 Option 3: Deploy on Fly.io

1. Install the `flyctl` CLI (`powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"`).
2. Inside the `youtube-downloader` directory, run:
   ```bash
   fly launch
   ```
3. Follow the CLI prompts to deploy using the bundled `Dockerfile`.
4. Deploy updates anytime with:
   ```bash
   fly deploy
   ```

---

## 🐳 Option 4: Deploy on Any Linux VPS / Docker (DigitalOcean, Linode, AWS, Hetzner)

Run anywhere Docker is installed:

```bash
# Clone the repository
git clone <your-repo-url>
cd youtube-downloader

# Build and run in background with docker-compose
docker compose up -d --build
```

Your service will immediately be live on `http://YOUR_SERVER_IP:5000`. You can put **Nginx** or **Caddy** in front of it with an SSL certificate (`certbot` or automatic Let's Encrypt with Caddy).

---

## 💰 Monetization: Configuring Ads

The website is equipped with **4 high-converting ad units**:
1. **Top Leaderboard Banner** (`#topAdSlot`): 728x90 (Desktop) / 320x50 (Mobile).
2. **Mid-Page In-Content Banner** (`#midAdSlot`): High visibility between video inspection and download history.
3. **Download Progress & Ad Overlay Modal** (`#adModalBackdrop`): The primary conversion unit. When users click **Download**, this modal engages them with a dedicated sponsor ad while the live download progress bar fills from 0% to 100%.
4. **Sticky Bottom Banner** (`#stickyBottomAd`): Fixed footer sponsor banner with user close/minimize button.

### How to Add Real Google AdSense:

1. Open `templates/index.html`.
2. Locate the header tag around line 18:
   ```html
   <!-- Replace ca-pub-XXXXXXXXXXXXXXXX with your AdSense Publisher ID -->
   <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script>
   ```
3. In any of the ad slots (e.g. `#topAdSlot` or `#midAdSlot`), replace the `<a class="mock-ad-banner">` with your standard AdSense code:
   ```html
   <ins class="adsbygoogle"
        style="display:block"
        data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
        data-ad-slot="1234567890"
        data-ad-format="auto"
        data-full-width-responsive="true"></ins>
   <script>
        (adsbygoogle = window.adsbygoogle || []).push({});
   </script>
   ```

### How to Add Custom Sponsor Banners or Affiliate Deals:

In `templates/index.html`, locate the `AD_CONFIG` script block:
```javascript
const AD_CONFIG = {
  sponsors: [
    {
      name: "Your Brand / Affiliate",
      title: "Your Promotional Headline",
      desc: "Promotional description and offer details...",
      badge: "Sponsored Partner",
      cta: "Click Here / Claim Offer",
      url: "https://your-affiliate-link.com",
      bgImage: "https://url-to-your-banner-image.jpg"
    }
    // Add as many sponsors as you wish; the modal will rotate them!
  ]
};
```

---

## 🔒 Production Features Included

- **Automatic Disk Space Cleanup**: Temporary downloads older than 60 minutes are automatically pruned by a background thread so cloud servers never exhaust their disks.
- **Multithreaded Gunicorn Support**: Handles concurrent users and stream conversions simultaneously.
- **Cross-Platform FFmpeg Detection**: Bundled for both local Windows development and cloud Linux containers.
- **Graceful Local/Cloud Storage Handling**: Local users can open folders directly; cloud users receive direct browser file attachments automatically.
