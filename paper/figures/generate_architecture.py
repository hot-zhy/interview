#!/usr/bin/env python3
"""
Generate the main architecture diagram: Problems -> Solutions (Modules) -> Results
Output: architecture.pdf (vector) and architecture.png (raster)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Figure setup
fig, ax = plt.subplots(1, 1, figsize=(14, 9))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis('off')

# Colors (professional palette)
C_PROBLEM = '#E8D5D5'   # light red
C_SOLUTION = '#D5E8E8'  # light teal
C_MODULE = '#E8E8D5'    # light yellow
C_RESULT = '#D5E8D5'    # light green
C_ARROW = '#555555'
C_TEXT = '#333333'

def draw_box(ax, x, y, w, h, text, color, fontsize=9, bold=False):
    """Draw a rounded box with text."""
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                         facecolor=color, edgecolor='#444', linewidth=1.2)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=C_TEXT, fontweight=weight, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color=C_ARROW):
    """Draw arrow from (x1,y1) to (x2,y2)."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2))

# === SECTION 1: Problems (存在问题) ===
ax.text(2, 8.5, 'Problems', fontsize=12, fontweight='bold', color=C_TEXT)
problems = [
    ('P1: Inconsistent\nDifficulty Calibration', 0.5, 6.8, 2.8, 1.2),
    ('P2: Ineffective\nQuestion Selection', 0.5, 5.2, 2.8, 1.2),
    ('P3: Reliability–Nuance\nTrade-off in Evaluation', 0.5, 3.6, 2.8, 1.2),
]
for text, x, y, w, h in problems:
    draw_box(ax, x, y, w, h, text, C_PROBLEM, fontsize=8)

# === SECTION 2: Solutions / Modules (我们的实现方案) ===
ax.text(7, 8.5, 'Our Solutions (Modules)', fontsize=12, fontweight='bold', color=C_TEXT)
solutions = [
    ('RQ1: Adaptive Interview Engine\n• Sliding-window calibration\n• Target-score control\n• Adaptive termination', 3.8, 6.2, 3.2, 2.0),
    ('RQ2: Question Selector\n• Multi-priority (P1/P2/P3)\n• IRT + Fisher + UCB\n• Resume personalization', 3.8, 3.8, 3.2, 2.0),
    ('RQ3: Evaluation Engine\n• 5-dim rule-based scoring\n• LLM augmentation\n• Automatic fallback', 3.8, 1.4, 3.2, 2.0),
]
for text, x, y, w, h in solutions:
    draw_box(ax, x, y, w, h, text, C_SOLUTION, fontsize=8)

# Supporting modules
support = [
    ('Resume Parser', 7.2, 5.8, 1.6, 0.6),
    ('Speech Analyzer', 7.2, 5.0, 1.6, 0.6),
    ('Follow-up Generator', 7.2, 4.2, 1.6, 0.6),
    ('Report Generator', 7.2, 3.4, 1.6, 0.6),
]
for text, x, y, w, h in support:
    draw_box(ax, x, y, w, h, text, C_MODULE, fontsize=7)

# === SECTION 3: Results (最后的结果) ===
ax.text(11.5, 8.5, 'Results', fontsize=12, fontweight='bold', color=C_TEXT)
results = [
    ('87.3%\nCalibration Accuracy', 9.2, 6.6, 2.2, 0.9),
    ('73.8% Gap Targeting\n85.2% Coverage', 9.2, 5.4, 2.2, 0.9),
    ('84.7% Human Agreement\n99.2% Uptime', 9.2, 4.2, 2.2, 0.9),
    ('4.2 Q Convergence\n68.4% Personalization', 9.2, 3.0, 2.2, 0.9),
]
for text, x, y, w, h in results:
    draw_box(ax, x, y, w, h, text, C_RESULT, fontsize=8)

# === Arrows: Problems -> Solutions -> Results ===
# P1 -> RQ1
draw_arrow(ax, 3.3, 7.4, 3.8, 7.2)
# P2 -> RQ2
draw_arrow(ax, 3.3, 5.8, 3.8, 4.8)
# P3 -> RQ3
draw_arrow(ax, 3.3, 4.2, 3.8, 2.4)

# Solutions -> Results
draw_arrow(ax, 7.0, 7.2, 9.2, 7.05)
draw_arrow(ax, 7.0, 4.8, 9.2, 5.85)
draw_arrow(ax, 7.0, 2.4, 9.2, 4.65)

# Supporting modules arrows (to RQ2, RQ3)
draw_arrow(ax, 7.2, 5.5, 7.0, 4.8)
draw_arrow(ax, 7.2, 4.2, 7.0, 2.4)

# Section dividers (vertical lines)
ax.axvline(x=3.5, color='#ccc', linestyle='--', linewidth=0.8)
ax.axvline(x=9.0, color='#ccc', linestyle='--', linewidth=0.8)

plt.tight_layout()
plt.savefig('architecture.pdf', bbox_inches='tight', dpi=300)
plt.savefig('architecture.png', bbox_inches='tight', dpi=300)
print('Saved architecture.pdf and architecture.png')
plt.close()
