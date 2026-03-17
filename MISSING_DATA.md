# Missing Data and Materials for Reproducibility

**Paper:** Beyond One-Size-Fits-All: An Adaptive AI Interview System  
**Last updated:** 2025-02-26

This document lists all data files, annotation protocols, and materials required to reproduce the paper's experimental results. Until these are provided, numeric values in the paper must be treated as **illustrative** or **待补充** (to be supplemented).

---

## 1. Required Data Files

### 1.1 Participant and Session Data

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `participants.csv` | Participant roster | `participant_id`, `resume_available`, `experience_level`, `education_level`, `primary_language` | Demographics (Tab participants), resume availability (62.8%), personalization subset (n=98) |
| `sessions.csv` | Interview session metadata | `session_id`, `participant_id`, `track`, `duration_min`, `n_questions`, `initial_difficulty`, `termination_reason`, `termination_rounds` | System performance (28.5 min, 8.7 Q), interview outcomes (Tab interview_outcomes) |

### 1.2 Question and Selection Data

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `asked_questions.csv` | Per-session question sequence | `session_id`, `round`, `question_id`, `difficulty`, `chapter`, `priority_used` (P1/P2/P3) | Difficulty adjustment patterns, priority distribution (34.2/28.7/37.1%), selection metrics |
| `question_bank.csv` | Question bank | `question_id`, `difficulty`, `chapter`, `track` | Coverage denominator, question bank stats (Tab question_bank) |

### 1.3 Evaluation Data

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `evaluations.csv` | System evaluation scores | `session_id`, `round`, `question_id`, `correctness`, `depth`, `clarity`, `practicality`, `tradeoffs`, `overall_score`, `provenance` (rule/llm/hybrid), `missing_points` | Calibration, agreement, fallback rate (17.6%) |
| `human_evaluations.csv` | Human rubric scores (30% sample) | `response_id`, `evaluator_id`, `correctness`, `depth`, `clarity`, `practicality`, `tradeoffs`, `overall_score` | Agreement (84.7%), κ, ICC |
| `evaluation_timing_log.csv` | Evaluation latency | `eval_id`, `mode` (rule/llm), `latency_sec` | Response times (1.2s rule, 3.8s LLM) |

### 1.4 External Labels (Critical for Calibration)

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `ability_labels.csv` | External ability proxy | `participant_id` or `session_id`, `ability_label`, `source` (exam/expert/course) | Calibration accuracy (87.3%); **must NOT be system-internal** |

### 1.5 Gap Targeting and Coverage

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `missing_concepts.csv` | Human-annotated missing concepts | `session_id`, `round`, `concept_id`, `chapter`, `queried_within_k` (boolean) | Gap targeting (73.8%); k value must be specified |
| `chapter_coverage.csv` or derived | Required chapter set per track | `track`, `required_chapters` | Coverage denominator (85.2%) |

### 1.6 Expert Ratings (Optional but Referenced)

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `expert_relevance_ratings.csv` | Expert relevance ratings (n=50) | `session_id`, `evaluator_id`, `relevance` (ordinal/binary) | 88% vs 45% vs 62% (ours/random/template) |

### 1.7 System Logs

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `evaluation_provenance_log.csv` | LLM vs rule usage | `eval_id`, `provenance`, `llm_available`, `fallback_triggered` | Uptime (99.2%), fallback rate (17.6%) |
| `termination_log.csv` | Termination reasons | `session_id`, `reason`, `rounds` | Tab interview_outcomes |

### 1.8 Survey Data

| File | Description | Required Fields | Purpose |
|------|-------------|-----------------|---------|
| `survey_responses.csv` | Post-interview survey | `session_id`, `satisfaction` (1–5) | User satisfaction (4.3/5.0) |

---

## 2. Annotation Protocols

| Protocol | Description | Required for |
|----------|-------------|--------------|
| **Missing concept annotation** | How "missing concept/chapter" is identified (human label vs. system extraction) | Gap targeting |
| **Relevance rubric** | Binary or ordinal rubric for "question relevant to resume" | Personalization (68.4%) |
| **Coverage chapter list** | Source of required chapters per track (curriculum? expert? fixed list?) | Coverage (85.2%) |
| **Ability label protocol** | How external ability is obtained (exam score, expert rating, course grade) | Calibration accuracy |
| **Human evaluation rubric** | Five-dimension rubric for human evaluators | Agreement, κ, ICC |

---

## 3. Code and Configuration

| Item | Description |
|------|-------------|
| **Commit hash** | Git commit of code used for experiments |
| **Random seed** | Seed for any stochastic components (selection, sampling) |
| **Config snapshot** | `target_score`, `difficulty_kp`, `difficulty_kd`, `window_size`, `personalized_exploration_rate`, termination thresholds (0.85, 0.4, 0.15) |
| **LLM config** | Model name, version, temperature, max tokens, schema validation rules |

---

## 4. Statistical Assumptions to Document

| Item | Description |
|------|-------------|
| **ICC form** | Shrout & Fleiss ICC(1), ICC(2,1), or ICC(3,k) |
| **CI algorithm** | Bootstrap (resamples, seed) or analytical |
| **Multiple comparison correction** | Bonferroni vs. Benjamini-Hochberg |
| **Mixed-effects structure** | Fixed/random effects for agreement models |

---

## 5. Uptime Definition

To recompute 99.2% uptime, specify:

- **Observation window**: e.g., total evaluation requests during study
- **Denominator**: total requests or total minutes
- **Failure definition**: LLM timeout? API error? Schema validation failure?
- **Fallback = success?**: Yes—if fallback to rule-based succeeds, count as uptime

---

## 6. Evaluation Plan and Export

See `paper/EVALUATION_PLAN.md` for the full evaluation plan (real user data + module-level technical evaluation).

**Export database to CSV:**

```bash
python scripts/export_db.py --output data/
```

**Or generate synthetic raw data** (no database required):

```bash
python scripts/generate_raw_data.py --output data/ --n-sessions 60 --n-participants 15
```

This produces: `participants.csv`, `sessions.csv`, `asked_questions.csv`, `evaluations.csv`, `turns.csv`, `question_bank.csv`, `resumes.csv`.

**Module-level evaluation** (see `reproduce_results/eval_modules/`):

- `run_calibration_sim.py` — calibration simulation (no external data)
- `eval_rule_scorer.py`, `eval_llm_scorer.py` — require `human_evaluations.csv`
- `eval_resume_parser.py` — ResumeBench or labeled JSON
- `eval_speech_analyzer.py` — annotated audio
- `eval_expression_fer.py` — FER2013

---

## 7. Next Steps for Authors

1. Run `python scripts/export_db.py --output data/` to export DB tables.
2. Complete manual annotation: `ability_labels.csv`, `missing_concepts.csv`, `human_evaluations.csv`, `expert_relevance_ratings.csv`.
3. Run `reproduce_results/reproduce.py` with data paths; update paper tables from output CSVs.
4. Add "Generated by script: reproduce_results/reproduce.py [commit] [date] [seed]" to table captions.
5. Run module evaluations (e.g. `eval_modules/run_calibration_sim.py`) for Appendix results.
6. Update this document when data is released or shared under restricted access.
