#!/usr/bin/env python3
"""
Generate main system architecture diagram for the paper.
Includes: Agentic PDA loop + Three-layer architecture + Key modules.
Output: architecture.png (for paper inclusion)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import matplotlib.lines as mlines

fig, ax = plt.subplots(1, 1, figsize=(12, 10))
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')

# Colors
C_PDA = '#E3F2FD'      # Perceive-Decide-Act - light blue
C_UI = '#E8F5E9'       # Presentation - light green
C_LOGIC = '#FFF3E0'    # Business logic - light orange
C_DATA = '#F3E5F5'     # Data - light purple
C_ARROW = '#455A64'
C_TEXT = '#263238'

def draw_box(ax, x, y, w, h, text, color, fontsize=8, bold=False):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                         facecolor=color, edgecolor='#37474F', linewidth=1)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=C_TEXT, fontweight=weight, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color=C_ARROW, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.5))

# ========== TOP: Agentic PDA Loop ==========
ax.text(6, 9.5, 'Agentic Workflow (Perceive–Decide–Act)', fontsize=11, fontweight='bold',
        ha='center', color=C_TEXT)

# PDA boxes
pda_boxes = [
    ('Perceive\nScores, missing points,\nhistory, resume', 1.2, 7.8, 2.4, 1.4),
    ('Decide\nFollow-up? Next Q?\nTerminate?', 4.8, 7.8, 2.4, 1.4),
    ('Act\nPresent Q, follow-up,\nor report', 8.4, 7.8, 2.4, 1.4),
]
for text, x, y, w, h in pda_boxes:
    draw_box(ax, x, y, w, h, text, C_PDA, fontsize=7)

# PDA arrows (loop)
draw_arrow(ax, 3.6, 8.5, 4.8, 8.5)
draw_arrow(ax, 7.2, 8.5, 8.4, 8.5)
draw_arrow(ax, 10.8, 8.5, 11.8, 8.5)
draw_arrow(ax, 11.8, 7.8, 11.8, 6.5)
draw_arrow(ax, 11.8, 6.5, 1.2, 6.5)
draw_arrow(ax, 1.2, 6.5, 1.2, 7.8)

# ========== MIDDLE: Three Layers ==========
ax.text(6, 6.0, 'System Architecture (Three Layers)', fontsize=10, fontweight='bold',
        ha='center', color=C_TEXT)

# Presentation Layer
draw_box(ax, 0.5, 5.0, 11, 0.7, 'Presentation Layer: Streamlit (Auth, Resume, QuestionBank, Interview, Report)', C_UI, fontsize=8)

# Business Logic Layer - main modules
logic_items = [
    ('Adaptive Interview Engine\n(RQ1: calibration)', 0.5, 3.6, 2.8, 1.0),
    ('Question Selector\n(RQ2: multi-priority)', 3.5, 3.6, 2.8, 1.0),
    ('Evaluation Engine\n(RQ3: rule+LLM)', 6.5, 3.6, 2.8, 1.0),
    ('Resume Parser', 0.5, 2.4, 1.8, 0.7),
    ('Speech Analyzer', 2.5, 2.4, 1.8, 0.7),
    ('Report Generator', 4.5, 2.4, 1.8, 0.7),
]
for text, x, y, w, h in logic_items:
    draw_box(ax, x, y, w, h, text, C_LOGIC, fontsize=7)

# Data Layer
draw_box(ax, 0.5, 0.8, 11, 1.2, 'Data Layer: SQLAlchemy ORM (User, Resume, QuestionBank, InterviewSession, Evaluation) | MySQL / SQLite', C_DATA, fontsize=8)

# Arrows between layers
draw_arrow(ax, 6, 5.0, 6, 4.6)
draw_arrow(ax, 6, 3.6, 6, 2.0)
draw_arrow(ax, 6, 1.2, 6, 0.8)

# PDA to Presentation
draw_arrow(ax, 6, 7.8, 6, 5.7)

plt.tight_layout()
plt.savefig('architecture.png', bbox_inches='tight', dpi=300, facecolor='white')
plt.savefig('architecture.pdf', bbox_inches='tight', facecolor='white')
print('Saved architecture.png and architecture.pdf')
plt.close()
