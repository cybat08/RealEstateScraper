@echo off
echo Real Estate Scraper - Installer
echo ==============================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Step 1: Installing required Python packages...
echo.
pip install streamlit pandas beautifulsoup4 plotly trafilatura cairosvg

REM Create directory structure if it doesn't exist
echo.
echo Step 2: Setting up directories...
if not exist "%USERPROFILE%\RealEstateScraper" mkdir "%USERPROFILE%\RealEstateScraper"
if not exist "%USERPROFILE%\RealEstateScraper\.streamlit" mkdir "%USERPROFILE%\RealEstateScraper\.streamlit"
if not exist "%USERPROFILE%\RealEstateScraper\.streamlit\static" mkdir "%USERPROFILE%\RealEstateScraper\.streamlit\static"

REM Copy all necessary files
echo.
echo Step 3: Copying application files...
xcopy /Y "*.py" "%USERPROFILE%\RealEstateScraper\"
xcopy /Y "icon.svg" "%USERPROFILE%\RealEstateScraper\"
xcopy /Y "generated-icon.png" "%USERPROFILE%\RealEstateScraper\"
xcopy /Y "icon.svg" "%USERPROFILE%\RealEstateScraper\.streamlit\static\"

REM Create launcher script
echo.
echo Step 4: Creating executable launcher...
echo @echo off > "%USERPROFILE%\RealEstateScraper\launch.bat"
echo cd /d "%%~dp0" >> "%USERPROFILE%\RealEstateScraper\launch.bat"
echo start "" streamlit run app.py --server.port 8501 >> "%USERPROFILE%\RealEstateScraper\launch.bat"

REM Create desktop shortcut
echo.
echo Step 5: Creating desktop shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Real Estate Scraper.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%USERPROFILE%\RealEstateScraper\launch.bat" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%USERPROFILE%\RealEstateScraper" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "%USERPROFILE%\RealEstateScraper\generated-icon.png" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "Real Estate Scraper Application" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

REM Create start menu shortcut
echo.
echo Step 6: Creating Start Menu shortcut...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Real Estate Scraper" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Real Estate Scraper"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateStartShortcut.vbs"
echo sLinkFile = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Real Estate Scraper\Real Estate Scraper.lnk" >> "%TEMP%\CreateStartShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.TargetPath = "%USERPROFILE%\RealEstateScraper\launch.bat" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.WorkingDirectory = "%USERPROFILE%\RealEstateScraper" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.IconLocation = "%USERPROFILE%\RealEstateScraper\generated-icon.png" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Description = "Real Estate Scraper Application" >> "%TEMP%\CreateStartShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateStartShortcut.vbs"
cscript //nologo "%TEMP%\CreateStartShortcut.vbs"
del "%TEMP%\CreateStartShortcut.vbs"

REM Create uninstaller
echo.
echo Step 7: Creating uninstaller...
echo @echo off > "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo Uninstalling Real Estate Scraper... >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo. >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo Removing desktop shortcut... >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo del "%USERPROFILE%\Desktop\Real Estate Scraper.lnk" >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo Removing Start Menu shortcuts... >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Real Estate Scraper" >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo. >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo The application files are located at: >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo %USERPROFILE%\RealEstateScraper >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo. >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo echo You can delete this folder manually if you want to completely remove the application. >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"
echo pause >> "%USERPROFILE%\RealEstateScraper\uninstall.bat"

echo.
echo ==============================
echo Installation completed successfully!
echo.
echo The Real Estate Scraper has been installed to:
echo %USERPROFILE%\RealEstateScraper
echo.
echo Shortcuts have been created on your desktop and in the Start Menu.
echo.
echo To uninstall, run the uninstall.bat file in the installation directory.
echo.
pause