#!/bin/bash
# Compile LaTeX paper to PDF
# For Linux/macOS

echo "Compiling LaTeX paper..."

# First pass
pdflatex -interaction=nonstopmode main.tex

# Bibliography (if using bibtex)
# bibtex main

# Second pass
pdflatex -interaction=nonstopmode main.tex

# Third pass (for references)
pdflatex -interaction=nonstopmode main.tex

echo ""
echo "Compilation complete! Check main.pdf"
echo ""

# Clean up auxiliary files (optional)
# rm -f *.aux *.log *.out *.toc

