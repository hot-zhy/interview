# Results Audit: Traceability and Verifiability

**Paper:** Beyond One-Size-Fits-All: An Adaptive AI Interview System with Lightweight Calibration, Multi-Priority Selection, and Hybrid LLM Evaluation  
**Audit date:** 2025-02-26  
**Status:** Raw data files not found in repository; many claims marked UNVERIFIABLE.

---

## Summary

| Status | Count |
|--------|-------|
| Verifiable (data + script exist) | 0 |
| Unverifiable (no data) | 68 |
| Definition needed | 12 |

---

## Audit Table

| Claim ID | Location | Reported value | Definition needed? | Source data file | Recompute script | Recomputed value | Match? | Fix action |
|----------|----------|----------------|--------------------|------------------|------------------|------------------|--------|------------|
| C001 | Abstract | 156 participants | Yes (sample definition) | — | — | — | — | Replace with "N participants" or provide participant roster; add to MISSING_DATA |
| C002 | Abstract | 87.3% calibration accuracy | Yes (ability label source) | — | — | — | — | See Metrics section; mark illustrative until data provided |
| C003 | Abstract | 73.8% gap-targeting | Yes (k, annotation source) | — | — | — | — | Define in Metrics; mark illustrative |
| C004 | Abstract | 85.2% coverage | Yes (chapter set, threshold) | — | — | — | — | Define in Metrics; mark illustrative |
| C005 | Abstract | 84.7% agreement | Yes (accuracy vs κ vs ICC) | — | — | — | — | Specify metric; mark illustrative |
| C006 | Abstract | 99.2% uptime | Yes (window, denominator) | — | — | — | — | Define in Metrics; mark illustrative |
| C007 | Sec 3, Tab system_comparison | 4.2 Q convergence | — | — | — | — | — | Mark illustrative; link to tab_calibration |
| C008 | Sec 3, Tab system_comparison | 87.3% calibration | — | — | — | — | — | Mark illustrative |
| C009 | Sec 7.2 | 62.8% resume available | — | — | — | — | — | Require participants.csv with resume_flag |
| C010 | Sec 7.3 | 30% responses human-evaluated | — | — | — | — | — | Require evaluation_sample_log.csv |
| C011 | Sec 7.3 | ICC=0.85 (evaluators) | Yes (ICC form) | — | — | — | — | Specify ICC(2,1) or ICC(3,k); add to Metrics |
| C012 | Sec 10.1, Tab calibration | 91.2, 85.6, 79.3, 88.7, 87.9, 86.2, 84.5, 89.1, 92.3 (by ability×init) | Yes (ability label) | — | reproduce_results/calc_calibration.py | — | — | Require ability_labels.csv; mark illustrative |
| C013 | Sec 10.1, Tab calibration | 87.3 overall calibration | — | — | — | — | — | Mark illustrative |
| C014 | Sec 10.1, Tab calibration | 4.2 avg convergence (Q) | Yes (convergence def) | — | — | — | — | Define: first Q where \|d-d_prev\|<ε for 2 consecutive |
| C015 | Sec 10.1, Tab calibration | 78.5% stability rate | Yes | — | — | — | — | Define stability; mark illustrative |
| C016 | Sec 10.1 | 78.5% within 5 Q | — | — | — | — | — | Mark illustrative |
| C017 | Sec 10.1, Tab difficulty_adjustment | 32.4%, 45.8%, 21.8% (inc/maint/dec) | — | — | reproduce_results/calc_difficulty_patterns.py | — | — | Require asked_questions + evaluations |
| C018 | Sec 10.1, Tab difficulty_adjustment | 1,358 total adjustments | — | — | — | — | — | Verify df matches N interviews × rounds |
| C019 | Sec 10.1, Tab ablation_difficulty | 86.9% vs 87.3%, t(310)=0.8, p=0.42, d=0.09 | — | — | — | — | — | Verify df=310; mark illustrative |
| C020 | Sec 10.1, Tab ablation_difficulty | 3.8 vs 4.2 Q, t(310)=3.2, p=0.001, d=0.36 | — | — | — | — | — | Mark illustrative |
| C021 | Sec 10.1 | +2.1% / -3.8% sensitivity (target 0.75) | — | — | — | — | — | Mark illustrative |
| C022 | Sec 10.2 | 73.8% gap targeting | — | — | — | — | — | Mark illustrative |
| C023 | Sec 10.2 | 85.2% coverage | — | — | — | — | — | Mark illustrative |
| C024 | Sec 10.2 | 68.4% personalization | — | — | — | — | — | Mark illustrative |
| C025 | Sec 10.2, Tab selection | 73.8, 85.2, 68.4, 0.76 (ours) | — | — | — | — | — | Mark illustrative |
| C026 | Sec 10.2, Tab selection | 31.5, 82.1, 32.7, 0.48 (random) | — | — | — | — | — | Require baseline runs; mark illustrative |
| C027 | Sec 10.2, Tab selection | 55.2, 66.6, 39.5, 0.54 (template) | — | — | — | — | — | Mark illustrative |
| C028 | Sec 10.2, Tab selection | 28.9, 78.3, 25.1, 0.44 (diff-only) | — | — | — | — | — | Mark illustrative |
| C029 | Sec 10.2, Tab priority_distribution | 34.2, 28.7, 37.1 (%) | — | — | — | — | — | Require selection_log with priority_used |
| C030 | Sec 10.2 | F(3,620)=156.8, p<0.001, η²=0.43 | — | — | — | — | — | Verify df; mark illustrative |
| C031 | Sec 10.2 | t(310)=18.2, p<0.001, d=1.03 (coverage) | — | — | — | — | — | Mark illustrative |
| C032 | Sec 10.2 | t(196)=15.3, p<0.001, d=1.54 (personalization) | — | — | — | — | — | Explain n=196 (resume subset); mark illustrative |
| C033 | Sec 10.2 | r=0.52, p<0.01 | — | — | — | — | — | Mark illustrative |
| C034 | Sec 10.2 | χ²(2)=2.1, p=0.35 | — | — | — | — | — | Mark illustrative |
| C035 | Sec 10.2 | 88% vs 45% vs 62% (expert relevance) | — | — | — | — | — | Require expert_ratings.csv; mark illustrative |
| C036 | Sec 10.2 | ICC=0.82 (expert agreement) | Yes (ICC form) | — | — | — | — | Mark illustrative |
| C037 | Sec 10.2, Tab ablation_selection | 74.1 vs 73.8, 84.8 vs 85.2, 71.2 vs 68.4 | — | — | — | — | — | Mark illustrative |
| C038 | Sec 10.2 | t(310)=2.8, p=0.005, d=0.32 | — | — | — | — | — | Mark illustrative |
| C039 | Sec 10.2 | 2.1% improvement (thompson_context) | — | — | — | — | — | Mark illustrative |
| C040 | Sec 10.2 | 3.2% (recent_chapter k=3 vs k=2) | — | — | — | — | — | Mark illustrative |
| C041 | Sec 10.3 | 84.7% agreement (hybrid) | — | — | — | — | — | Mark illustrative |
| C042 | Sec 10.3 | 76.3% rule-based, 88.2% LLM | — | — | — | — | — | Mark illustrative |
| C043 | Sec 10.3, Tab evaluation | 82.5–89.1 by dimension | — | — | — | — | — | Mark illustrative |
| C044 | Sec 10.3, Tab evaluation_reliability | κ 0.58–0.78, ICC 0.68–0.85 | Yes (ICC form) | — | — | — | — | Specify ICC(2,1) or (3,k); mark illustrative |
| C045 | Sec 10.3 | 84.7% (95% CI [83.2, 86.2]) | — | — | — | — | — | Mark illustrative |
| C046 | Sec 10.3 | t(468)=8.9, p<0.001, d=0.82 | — | — | — | — | — | Verify df=468 (responses); mark illustrative |
| C047 | Sec 10.3 | 99.2% uptime (95% CI [98.7, 99.6]) | Yes | — | — | — | — | Define: successful_evals/total_evals; mark illustrative |
| C048 | Sec 10.3 | 82.4% LLM applied | — | — | — | — | — | Require evaluation_log with provenance |
| C049 | Sec 10.3 | 1.2s rule, 3.8s LLM (SD 0.3, 1.1) | — | — | — | — | — | Require timing logs; mark illustrative |
| C050 | Sec 10.3, Tab ablation_evaluation | 17.6% fallback rate | — | — | — | — | — | Require provenance field; mark illustrative |
| C051 | Sec 10.4 | indirect effect=0.16, CI [0.11,0.22], p<0.001 | — | — | — | — | — | Mark illustrative |
| C052 | Sec 10.4 | β=0.18, p<0.05 (interaction) | — | — | — | — | — | Mark illustrative |
| C053 | Sec 10.4 | S=0.153 (15.3% synergy) | — | — | — | — | — | Mark illustrative |
| C054 | Sec 10.4, Tab system_performance | 28.5 min, [27.2,29.8] | — | — | — | — | — | Require session_log; mark illustrative |
| C055 | Sec 10.4, Tab system_performance | 8.7 Q, [8.3,9.1] | — | — | — | — | — | Mark illustrative |
| C056 | Sec 10.4, Tab system_performance | 76.2% relevance, [74.5,77.9] | — | — | — | — | — | Mark illustrative |
| C057 | Sec 10.4, Tab system_performance | 1.8s response, [1.6,2.0] | — | — | — | — | — | Mark illustrative |
| C058 | Sec 10.4, Tab system_performance | 4.3/5.0 satisfaction, [4.1,4.5] | — | — | — | — | — | Require survey_responses; mark illustrative |
| C059 | Sec 10.4 | r=0.68, p<0.001 (duration vs questions) | — | — | — | — | — | Mark illustrative |
| C060 | Sec 10.4 | 78.5% within 30 min | — | — | — | — | — | Mark illustrative |
| C061 | Sec 10.4 | β=0.42, 0.38, -0.15 (satisfaction) | — | — | — | — | — | Mark illustrative |
| C062 | Sec 10.4 | F(3,152)=1.2, p=0.31 (Levene) | — | — | — | — | — | Verify df; mark illustrative |
| C063 | Sec 10.4, Tab interview_outcomes | 23, 18, 89, 26 (counts) | — | — | — | — | — | Require termination_reasons; mark illustrative |
| C064 | Sec 10.4, Tab interview_outcomes | 14.7%, 11.5%, 57.1%, 16.7% | — | — | — | — | — | Mark illustrative |
| C065 | Sec 10.4, Tab interview_outcomes | 6.8, 5.2, 9.3, 15.0 avg rounds | — | — | — | — | — | Mark illustrative |
| C066 | Sec 10.4, Tab interview_outcomes | 156 total, 8.7 avg rounds | — | — | — | — | — | Mark illustrative |

---

## Required Data Files (see MISSING_DATA.md)

- `participants.csv`: id, resume_available, experience_level, ...
- `sessions.csv`: session_id, duration_min, n_questions, track, ...
- `asked_questions.csv`: session_id, question_id, difficulty, chapter, priority_used, ...
- `evaluations.csv`: session_id, question_id, overall_score, dim_scores, provenance (rule|llm|hybrid), ...
- `ability_labels.csv`: session_id or participant_id, external_ability_label (source: exam|expert|course)
- `human_evaluations.csv`: response_id, evaluator_id, dim_scores, ...
- `termination_log.csv`: session_id, reason, rounds, ...
- `evaluation_timing_log.csv`: eval_id, mode, latency_sec, ...

---

## Recompute Scripts (stubs in reproduce_results/)

1. `calc_calibration.py` — calibration accuracy, convergence, stability
2. `calc_selection.py` — gap targeting, coverage, personalization
3. `calc_evaluation.py` — agreement, κ, ICC, fallback rate
4. `calc_system_performance.py` — duration, uptime, satisfaction
5. `reproduce.py` — orchestrator; outputs tab_*.csv
