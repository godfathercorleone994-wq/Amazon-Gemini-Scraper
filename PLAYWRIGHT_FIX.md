# Playwright Installation Fix for Debian Trixie

## Problem

When building the Docker image on Railway, Playwright's automatic dependency installation was failing with the error:

```
E: Package 'ttf-unifont' has no installation candidate
E: Package 'ttf-ubuntu-font-family' has no installation candidate
Failed to install browser dependencies
Error: Installation process exited with code: 100
```

This occurred because:
1. The base image `python:3.11-slim` uses Debian Trixie
2. Playwright tries to install system dependencies when running `playwright install chromium`
3. Some font packages have been renamed or obsoleted in Debian Trixie:
   - `ttf-unifont` → `fonts-unifont`
   - `ttf-ubuntu-font-family` → removed (no direct replacement needed)
   - `libvpx7` → `libvpx9`

## Solution

The fix involves pre-installing all required Chromium dependencies manually in the Dockerfile before running `playwright install chromium`. This prevents Playwright from attempting its own automatic dependency installation.

### Changes Made

Added comprehensive list of Chromium/Playwright dependencies to the Dockerfile:
- Font packages: `fonts-unifont` (compatible with Debian Trixie)
- X11 libraries: `libx11-6`, `libx11-xcb1`, `libxcb1`, `libxext6`, `libxrender1`, `libxtst6`, `libxi6`
- Rendering libraries: `libpangocairo-1.0-0`, `libpango-1.0-0`, `libcairo2`
- System libraries: `libdbus-1-3`, `libglib2.0-0`, `libegl1`, `libnotify4`
- Media libraries: `libgstreamer1.0-0`, `libgstreamer-plugins-base1.0-0`, `libopus0`, `libwoff1`
- Additional dependencies: `libharfbuzz-icu0`, `libhyphen0`, `libmanette-0.2-0`, `libgles2`
- GStreamer plugins: `gstreamer1.0-libav`, `gstreamer1.0-plugins-bad`, `gstreamer1.0-plugins-base`, `gstreamer1.0-plugins-good`
- Other libraries: `libenchant-2-2`, `libsecret-1-0`, `libvpx9`, `libevdev2`, `libxkbfile1`

### Why This Works

1. **Debian Trixie Compatible**: All packages use the correct names for Debian Trixie
2. **Complete Dependencies**: Provides all libraries Chromium needs to run
3. **No Automatic Installation**: Playwright only downloads the browser binary without attempting system package installation
4. **Railway Compatible**: Works in Railway's build environment which uses similar base images

## Testing

The package list has been verified to install successfully on `python:3.11-slim` (Debian Trixie).

## Deployment

When deploying to Railway or any platform using Debian Trixie:
1. The Docker build will now complete successfully
2. Playwright will be able to launch Chromium without dependency errors
3. The scraper will function as expected
