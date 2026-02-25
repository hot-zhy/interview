# Figures and Tables to Add

This document lists suggested figures and tables to enhance the paper.

## Suggested Figures

### 1. System Architecture Diagram
- **Location**: Section 3
- **Content**: 
  - Three-layer architecture (UI, Business Logic, Data)
  - Component relationships
  - Data flow

### 2. Adaptive Difficulty Adjustment Flowchart
- **Location**: Section 4.1
- **Content**:
  - Algorithm flow
  - Decision points
  - Difficulty adjustment logic

### 3. Question Selection Algorithm Flowchart
- **Location**: Section 4.2
- **Content**:
  - Priority-based selection
  - Fuzzy matching process
  - Fallback mechanisms

### 4. Evaluation Framework Diagram
- **Location**: Section 4.5
- **Content**:
  - Five evaluation dimensions
  - Weighted combination
  - LLM enhancement flow

### 5. Interview Termination Decision Tree
- **Location**: Section 4.4
- **Content**:
  - Multi-dimensional assessment
  - Termination conditions
  - Decision paths

### 6. Experimental Results
- **Location**: Section 6
- **Content**:
  - Performance comparison charts
  - Difficulty adjustment effectiveness
  - Evaluation accuracy metrics
  - User experience metrics

## Suggested Tables

### Table 1: System Components
- **Location**: Section 3.2
- **Content**: List of core services and their functions

### Table 2: Algorithm Parameters
- **Location**: Section 4
- **Content**: 
  - Window size
  - Similarity thresholds
  - Score thresholds
  - Termination conditions

### Table 3: Evaluation Dimensions
- **Location**: Section 4.5
- **Content**: 
  - Dimension names
  - Calculation methods
  - Weights

### Table 4: Dataset Statistics
- **Location**: Section 6.1
- **Content**:
  - Number of interviews
  - Question bank size
  - Average metrics

### Table 5: Experimental Results
- **Location**: Section 6.2
- **Content**:
  - Performance metrics
  - Comparison with baselines
  - Statistical significance

### Table 6: Ablation Study
- **Location**: Section 6.2
- **Content**:
  - Component contributions
  - Feature importance
  - Algorithm variants

## LaTeX Code Templates

### Figure Template
```latex
\begin{figure}[h]
\centering
\includegraphics[width=0.8\textwidth]{figures/architecture.pdf}
\caption{System architecture showing three-layer design}
\label{fig:architecture}
\end{figure}
```

### Table Template
```latex
\begin{table}[h]
\centering
\caption{Algorithm parameters and default values}
\label{tab:parameters}
\begin{tabular}{lcc}
\toprule
Parameter & Default Value & Description \\
\midrule
Window Size & 3 & Sliding window size \\
Similarity Threshold & 70\% & Fuzzy matching threshold \\
Min Rounds & 5 & Minimum interview rounds \\
Max Rounds & 15 & Maximum interview rounds \\
\bottomrule
\end{tabular}
\end{table}
```

## Tools for Creating Figures

- **Architecture Diagrams**: draw.io, Lucidchart, or TikZ (LaTeX)
- **Flowcharts**: draw.io, TikZ, or PlantUML
- **Charts**: Python (matplotlib, seaborn), R, or Excel
- **Diagrams**: TikZ for LaTeX-native diagrams

## Notes

- All figures should be in vector format (PDF, EPS) for best quality
- Use consistent color schemes and fonts
- Ensure figures are readable when printed in grayscale
- Include figure captions that are self-explanatory
- Reference all figures in the text

