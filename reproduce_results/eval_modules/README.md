# Module-Level Technical Evaluation

Each script evaluates a specific component independently:

| Script | Purpose | Data |
|--------|---------|------|
| `run_calibration_sim.py` | Difficulty calibration simulation | None (synthetic) |
| `eval_rule_scorer.py` | Rule-based scorer vs human | human_evaluations.csv |
| `eval_llm_scorer.py` | LLM scorer vs human | human_evaluations.csv |
| `eval_resume_parser.py` | Resume extraction F1 | ResumeBench / labeled JSON |
| `eval_speech_analyzer.py` | Speech tension/fluency | Annotated audio |
| `eval_expression_fer.py` | DeepFace emotion accuracy | FER2013 |

Run from project root:

```bash
cd reproduce_results
python eval_modules/run_calibration_sim.py --seed 42
python eval_modules/eval_expression_fer.py --data-dir ../data/fer2013
# etc.
```

Outputs go to `reproduce_results/output/`.
