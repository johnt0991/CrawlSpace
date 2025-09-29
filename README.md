# CrawlSpace

CrawlSpace is a desktop application for auditing and searching Slack export data.  
It provides an intuitive UI for loading exported JSON files, browsing conversations,  
and searching for specific keywords, phrases, or deleted messages.  

Built with **Python** and **Tkinter**, packaged as standalone apps for **macOS** and **Windows**.

---

## ✨ Features

- 📂 Load a Slack export folder (`.json` files, including `users.json`)
- 🔍 Search across all conversations using keywords or phrases
- 🗨️ Display chat history in a clean, threaded view
- 🕵️ Detect and display deleted or edited messages
- 🎨 Color-coded usernames for easy identification
- 📊 Progress tracking while scanning large exports
- 🖥️ Packaged as native `.app` (macOS) or `.exe` (Windows)

---

## 🚀 Installation

### macOS
1. Download the latest `.dmg` from the [Releases](../../releases) page.
2. Open the DMG and drag **CrawlSpace.app** into your **Applications** folder.
3. Launch CrawlSpace from Applications.

> **Note:** If macOS blocks the app as "unverified,"  
> right-click the app → **Open** → confirm once. After that, it will launch normally.

### Windows
1. Download the latest `.zip` or `.exe` installer from the [Releases](../../releases) page.
2. If a `.zip`, extract the contents to a folder of your choice.
3. Double-click **CrawlSpace.exe** to run the application.

> **Note:** On first launch, you may see a Windows SmartScreen warning.  
> Click **More info** → **Run anyway** to start the app.

---

## 🛠️ Build from Source

If you want to build CrawlSpace yourself:

### Requirements
- Python 3.11+
- [PyInstaller](https://pyinstaller.org/)
- Tkinter (included in most Python distributions)

### Build (macOS)

pyinstaller \
  --windowed \
  --name "CrawlSpace" \
  --icon icon.icns \
  --osx-bundle-identifier com.johntotaro.crawlspace \
  --collect-submodules=tkinter \
  --collect-data=tkinter \
  --collect-binaries=tkinter \
  --add-data "crawl.ico:." \
  CrawlSpace.py

### Build (Windows)

pyinstaller ^
  --windowed ^
  --name "CrawlSpace" ^
  --icon crawl.ico ^
  --collect-submodules=tkinter ^
  --collect-data=tkinter ^
  --collect-binaries=tkinter ^
  CrawlSpace.py
