"""
This script will create an executable version of the Real Estate Scraper application.
This script is meant to be used with PyInstaller.
"""

import os
import sys
import shutil
from pathlib import Path

# Instructions for users
print("=" * 60)
print("Real Estate Scraper - Executable Creator")
print("=" * 60)
print("\nThis script will help you create an executable version of the application.")
print("Requirements:")
print("1. PyInstaller must be installed (pip install pyinstaller)")
print("2. All dependencies must be installed (pip install -r requirements.txt)")
print("\nThe process may take a few minutes to complete.")
print("=" * 60)

try:
    import PyInstaller
except ImportError:
    print("\nError: PyInstaller is not installed.")
    print("Please install it using: pip install pyinstaller")
    sys.exit(1)

# Create a requirements.txt file to ensure all dependencies are installed
with open("requirements.txt", "w") as f:
    f.write("""streamlit>=1.12.0
pandas>=1.3.0
beautifulsoup4>=4.9.3
plotly>=5.3.1
trafilatura>=1.4.0
cairosvg>=2.5.2
""")

print("\nStep 1: Creating requirements.txt file...")
print("Done.")

# Create a simple launcher script
with open("launcher.py", "w") as f:
    f.write("""import os
import subprocess
import sys

def main():
    # Get the directory where the executable is located
    base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Change to that directory
    os.chdir(base_path)
    
    # Launch Streamlit
    cmd = ["streamlit", "run", "app.py", "--server.port", "8501"]
    subprocess.Popen(cmd)

if __name__ == "__main__":
    main()
""")

print("Step 2: Creating launcher script...")
print("Done.")

# Create PyInstaller spec file
spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['launcher.py'],
             pathex=[],
             binaries=[],
             datas=[
                ('app.py', '.'),
                ('scraper.py', '.'),
                ('data_processor.py', '.'),
                ('utils.py', '.'),
                ('web_content.py', '.'),
                ('icon.svg', '.'),
                ('generated-icon.png', '.')
             ],
             hiddenimports=['streamlit', 'pandas', 'plotly', 'beautifulsoup4', 'trafilatura'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='RealEstateScraper',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='generated-icon.png')
"""

with open("RealEstateScraper.spec", "w") as f:
    f.write(spec_content)

print("Step 3: Creating PyInstaller spec file...")
print("Done.")

# Create a batch file to run PyInstaller
with open("build_exe.bat", "w") as f:
    f.write("""@echo off
echo Building Real Estate Scraper executable...
echo This may take a few minutes.
echo.

REM Install required packages
pip install -r requirements.txt

REM Run PyInstaller
pyinstaller --noconfirm RealEstateScraper.spec

echo.
if %errorlevel% equ 0 (
    echo Build completed successfully!
    echo The executable is located in the dist folder.
    echo.
    
    REM Create desktop shortcut
    echo Creating desktop shortcut...
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
    echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Real Estate Scraper.lnk" >> "%TEMP%\CreateShortcut.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.TargetPath = "%CD%\dist\RealEstateScraper.exe" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.WorkingDirectory = "%CD%\dist" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.IconLocation = "%CD%\generated-icon.png" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Description = "Real Estate Scraper Application" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
    cscript //nologo "%TEMP%\CreateShortcut.vbs"
    del "%TEMP%\CreateShortcut.vbs"
    
    echo.
    echo Desktop shortcut created!
) else (
    echo Build failed. Please check the error messages above.
)

pause
""")

print("Step 4: Creating build script...")
print("Done.")

print("\nSetup Complete!")
print("=" * 60)
print("To build the executable:")
print("1. Open a command prompt")
print("2. Navigate to this directory")
print("3. Run build_exe.bat")
print("=" * 60)
print("\nThe executable will be created in the 'dist' folder")
print("A shortcut will be created on your desktop automatically.")
print("\nNote: The build process may take several minutes to complete.")