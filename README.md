# coding-pudding.exe

> A lightweight Python IDE for low-configuration laptops/PCs.

<p align="center">
  <img src="screenshots/light.PNG" width="45%" />
  <img src="screenshots/dark.PNG" width="45%" />
</p>

<p align="center">
  <img src="screenshots/find.PNG" width="45%" />
  <img src="screenshots/replace.PNG" width="45%" />
</p>

<p align="center">
  <img src="screenshots/go_to.PNG" width="45%" />
  <img src="screenshots/word_count.PNG" width="45%" />
</p>

<p align="center">
  <img src="screenshots/tabs.PNG" width="45%" />
</p>

---

## Features

- **Tabs** — Open multiple files in one window.
- **Dark mode** — Protect your eyes during long coding sessions.
- **Automatical indentation** — Automatically indent after `:` (no more typing 4 spaces manually).
- **Bracket matching** — Automatically close opening brackets `()`, `[]`, `{}`, `<>`, `""`, `''`.
- **Smart bracket deletion** — Delete matching bracket pairs intelligently.
- **Tear-off tabs** — Drag a tab out to create a new window with that file.
- **Automatically scrolling** — Middle-click to create an anchor and scroll automatically.
- **Toggle comment** — `Ctrl + /` to comment/uncomment selected lines.
- **Line numbers** — Easily locate your code by line number.
- **Find/Replace/Go To** — Full search, replace, and navigation support.
- **Automatically saving settings** — Remembers your theme (dark/light) and window size.
- **"Open with coding-pudding"** — Right-click any file to open it directly.

---

## Installation

### Option 1: Download coding-pudding.exe (Recommended)

1. Download `coding-pudding.exe` from [**Releases**](../../releases).
2. Run the file (no Python installation required).
3. Right-click any file --> **"Open with coding-pudding"**.

### Option 2: Run from source code (coding-pudding.py)

```bash
# Clone repository
git clone https://github.com/caoductri698/coding-pudding.git
cd coding-pudding

# Install dependencies
pip install PyQt5

# Run app
py coding-pudding.py
```

### Option 3: Build coding-pudding.exe by yourself

```bash
# Clone repository
git clone https://github.com/caoductri698/coding-pudding.git

# Install PyInstaller
pip install pyinstaller

# Build
py -m PyInstaller --onefile --windowed --icon=icon.ico --add-data="icon.ico;." --name coding-pudding coding-pudding.py

# File .exe is ready in dist/coding-pudding.exe
```

---

## Requirements

- **Operating System**: Windows 7/8/10/11
- **RAM**: at least 2GB (for best performance)
- **Python version** (if running from source code): 3.8+

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + N` | New file |
| `Ctrl + T` | New tab |
| `Ctrl + O` | Open file |
| `Ctrl + S` | Save |
| `Ctrl + Shift + S` | Save as |
| `Ctrl + W` | Close tab |
| `Ctrl + Q` | Exit |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` | Redo |
| `Ctrl + F` | Find |
| `Ctrl + H` | Replace |
| `Ctrl + G` | Go To |
| `Ctrl + /` | Toggle comment |
| `Ctrl + Tab` | Next tab |
| `Ctrl + Shift + Tab` | Previous tab |
| `F5` | Time/Date |
| `Tab` | 1 indentation (line start)/4 spaces |
| `Shift + Tab` | Unindent |
| `Ctrl + Shift + W` | Word count |

---

## How to use

### Open a file

- **Option 1**: `Ctrl + O` --> Choose file
- **Option 2**: Right-click file --> **"Open with coding-pudding"**
- **Option 3**: Drag file into the app window

### Tear-off tab

- Click and hold a tab
- Drag it outside the tab bar
--> A new window appears with that file

### Automatically scrolling

- Middle-click anywhere in the editor --> An anchor appears
- Move mouse up/down --> The page scrolls automatically
- The further from the anchor, the faster it scrolls
- Middle-click again to disable

### Register context menu

- **Automatically**: Run the app once --> it registers automatically
- **Manually**: Help --> Register 'Open with' Menu
- **Removing**: Help --> Unregister 'Open with' Menu

---

## Built with

- **Python 3.14** — Programming language
- **PyQt5** — GUI framework
- **PyInstaller** — Packaging tool
- **winreg** — Windows Registry integration

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request (PR)

---

## Bug reports

If you find a bug, please create an [Issue](../../issues) with:
- Description of the bug
- Steps to reproduce
- Screenshots (if possible)
- Windows version

---

## Contact

- **GitHub**: [@caoductri698](https://github.com/caoductri698)
- **Gmail**: caoductri698@gmail.com
- **TikTok**: [tdwc208](https://tiktok.com/@tdwc208)
- **Instagram**: [tdwc208](https://instagram.com/tdwc208)
- **Hotline**: 0342513045
- **Facebook**: [tri6462 (Trii Dwck)](https://facebook.com/tri6462)

---

## ⭐ If you find this application useful, please give me a star, that will be a lot to me!

[![Star](https://img.shields.io/github/stars/caoductri698/coding-pudding?style=social)](https://github.com/caoductri698/coding-pudding)

---

## Stats

![GitHub release](https://img.shields.io/github/v/release/caoductri698/coding-pudding)
![GitHub downloads](https://img.shields.io/github/downloads/caoductri698/coding-pudding/total)
![GitHub stars](https://img.shields.io/github/stars/caoductri698/coding-pudding)
![GitHub forks](https://img.shields.io/github/forks/caoductri698/coding-pudding)
![GitHub issues](https://img.shields.io/github/issues/caoductri698/coding-pudding)
![License](https://img.shields.io/github/license/caoductri698/coding-pudding)

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for more details.

You are free to:
- Use commercially
- Modify
- Distribute
- Use privately

Just include the original copyright notice and license text.