@echo off
title AI NEWS LETTER — Push to GitHub
color 0A
cls
echo ====================================================================
echo         AI NEWS LETTER — PUSH TO GITHUB REPOSITORY
echo ====================================================================
echo.
echo Target Repository: https://github.com/yasarsiddiqui03/ai-news-letter
echo.
echo Uploading latest code to GitHub master branch...
echo (If a browser window pops up, click "Sign in with your browser" to authorize).
echo.
git push -u origin master
echo.
if %ERRORLEVEL% EQU 0 (
    echo ====================================================================
    echo [SUCCESS] Congratulations! Code is now live on GitHub!
    echo Repository Link: https://github.com/yasarsiddiqui03/ai-news-letter
    echo ====================================================================
) else (
    echo ====================================================================
    echo [NOTE] If it prompted for login, please complete the GitHub sign-in.
    echo ====================================================================
)
echo.
pause
