# Academic Paper: Adaptive AI-Powered Interview System

This directory contains the LaTeX source files for the academic paper describing the adaptive AI-powered interview system.

## File Structure

- `main.tex`: Main LaTeX document with complete paper content
- `README.md`: This file

## Paper Overview

The paper presents:
1. **System Architecture**: Modular design with UI, business logic, and data layers
2. **Core Algorithms**: 
   - Adaptive difficulty adjustment using sliding-window weighted averaging
   - Intelligent question selection with multi-priority strategy
   - Follow-up question decision algorithm
   - Intelligent interview termination based on multi-dimensional metrics
3. **Evaluation Framework**: Rule-based scoring with optional LLM enhancement
4. **Data Collection**: Question bank, resume parsing, interview data collection
5. **Analysis Methods**: Performance analysis and speech analysis

## Compilation

### Prerequisites

Install a LaTeX distribution:
- **Windows**: MiKTeX or TeX Live
- **macOS**: MacTeX
- **Linux**: TeX Live

### Compile the Paper

```bash
# Compile to PDF
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex

# Or use latexmk (recommended)
latexmk -pdf main.tex
```

## Sections to Complete

The paper template includes placeholders that need to be filled with actual data:

1. **Section 6 (Experimental Results)**:
   - Dataset statistics
   - Evaluation metrics
   - Actual experimental results
   - Comparison with baseline methods

2. **Author Information**:
   - Update author names and affiliations
   - Add corresponding author email

3. **Journal Information**:
   - Update journal name in `\journal{Journal Name}`

4. **References**:
   - Add more relevant citations
   - Ensure all citations are properly formatted

## Key Algorithms Documented

### 1. Adaptive Difficulty Adjustment
- Sliding window size: 3 (configurable)
- Weighted averaging with linear weights
- Trend analysis based on recent performance

### 2. Question Selection
- Priority 1: Missing knowledge chapters
- Priority 2: Resume-based matching (70% similarity threshold)
- Priority 3: Weighted random selection

### 3. Evaluation
- Five dimensions: Correctness, Depth, Clarity, Practicality, Tradeoffs
- Weighted combination: 30% + 25% + 20% + 15% + 10%
- Optional LLM enhancement via GLM-4-Flash

### 4. Interview Termination
- Multi-dimensional assessment
- Early termination for excellent/poor performance
- Normal termination based on stability and coverage

## Mathematical Formulations

All key algorithms are presented with mathematical formulations:
- Weighted average calculation
- Difficulty adjustment function
- Similarity matching
- Follow-up decision logic
- Termination conditions
- Evaluation score computation

## Next Steps

1. **Collect Experimental Data**:
   - Run interviews with test candidates
   - Collect performance metrics
   - Compare with baseline methods

2. **Add Results**:
   - Fill Section 6 with actual results
   - Include tables and figures
   - Statistical analysis

3. **Enhance References**:
   - Add more citations to related work
   - Include recent papers on AI interview systems
   - Cite adaptive testing literature

4. **Create Figures**:
   - System architecture diagram
   - Algorithm flowcharts
   - Experimental results charts
   - Performance comparison graphs

## Notes

- The paper follows Elsevier article format (elsarticle class)
- All algorithms are documented with mathematical formulations
- The system supports both text and audio input modalities
- Evaluation combines rule-based and LLM-enhanced methods
- The architecture is modular and extensible

## Contact

For questions about the paper or system, please contact the authors.

