# Figures in the Paper

This document describes all figures included in the paper.

## Figure List

### Figure 1: System Architecture (fig:architecture)
- **Location**: Section 4.1 (System Implementation - Architecture Overview)
- **Type**: System architecture diagram
- **Content**: Three-layer architecture showing:
  - Presentation Layer (Streamlit UI)
  - Business Logic Layer (6 services: Adaptive Interview Engine, Question Selector, Evaluation Engine, Resume Parser, Speech Analyzer, Report Generator)
  - Data Layer (Database with SQLAlchemy ORM)
- **Format**: TikZ diagram with arrows showing data flow

### Figure 2: Difficulty Convergence Pattern (fig:convergence)
- **Location**: Section 9.1 (Results for RQ1)
- **Type**: Line chart showing convergence patterns
- **Content**: Shows how difficulty level adapts over question progression for different candidate ability levels
- **Features**:
  - Three example trajectories (high, medium-high, low ability)
  - Convergence zone highlighting
  - Question number on x-axis, difficulty level on y-axis
- **Format**: PGFPlots line chart

### Figure 3: Priority Distribution (fig:priority)
- **Location**: Section 9.2 (Results for RQ2)
- **Type**: Bar chart
- **Content**: Shows application rate and average questions per interview for each priority level
- **Features**:
  - Three bars for Priority 1, 2, and 3
  - Dual metrics: application rate (%) and average questions
- **Format**: PGFPlots bar chart

### Figure 4: Evaluation Agreement (fig:agreement)
- **Location**: Section 9.3 (Results for RQ3)
- **Type**: Grouped bar chart
- **Content**: Comparison of agreement percentages across five evaluation dimensions for three approaches (rule-based, LLM-enhanced, hybrid)
- **Features**:
  - Five dimensions: Correctness, Depth, Clarity, Practicality, Tradeoffs
  - Three approaches side-by-side comparison
  - Shows improvement from rule-based to hybrid
- **Format**: PGFPlots grouped bar chart

## Technical Details

All figures are generated using TikZ and PGFPlots, which are LaTeX-native packages. This ensures:
- High-quality vector graphics
- Consistent fonts with the document
- Easy customization
- No external dependencies

## Compilation

The figures will compile automatically when you compile the main.tex file, as long as you have:
- TikZ package (usually included in LaTeX distributions)
- PGFPlots package (usually included in LaTeX distributions)

If compilation fails, ensure these packages are installed:
```bash
# For TeX Live
tlmgr install pgfplots

# For MiKTeX
# Usually auto-installs on first use
```

## Customization

To modify figures:
1. Edit the TikZ/PGFPlots code in main.tex
2. Adjust colors, sizes, or data values
3. Recompile to see changes

## Notes

- All figures use consistent color schemes
- Figures are sized to fit within page margins
- Captions are descriptive and self-explanatory
- All figures are referenced in the text

