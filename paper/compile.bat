@echo off
REM Compile LaTeX paper to PDF
REM For Windows

echo Compiling LaTeX paper...

REM First pass
pdflatex -interaction=nonstopmode main.tex

REM Bibliography (if using bibtex)
REM bibtex main

REM Second pass
pdflatex -interaction=nonstopmode main.tex

REM Third pass (for references)
pdflatex -interaction=nonstopmode main.tex

echo.
echo Compilation complete! Check main.pdf
echo.
pause

