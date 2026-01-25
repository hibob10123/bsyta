@echo off
echo ======================================================================
echo CLEARING ICON CACHE
echo ======================================================================
echo.
echo This will delete all cached icons in data\assets\icons\
echo Press Ctrl+C to cancel, or
pause
echo.
echo Deleting icons...
del /Q data\assets\icons\*.png 2>nul
del /Q data\assets\icons\*.jpg 2>nul
del /Q data\assets\icons\*.jpeg 2>nul
echo.
echo Done! Icon cache cleared.
echo Next run will download fresh icons with improved search queries.
echo.
pause
