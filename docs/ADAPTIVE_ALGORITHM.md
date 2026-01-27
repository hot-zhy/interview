# 自适应面试算法设计文档

## 1. 概述

本系统实现了一个基于自适应算法的智能面试系统，能够根据候选人的实时表现动态调整题目难度、决定是否追问、以及智能判断面试结束时机。

## 2. 核心算法

### 2.1 自适应难度调整算法

**算法名称**: 基于滑动窗口的加权难度调整算法

**核心思想**:
- 使用滑动窗口（默认3次）分析最近的表现
- 采用加权平均，越近的表现权重越大
- 结合趋势分析（最近两次的分数差异）

**算法流程**:
```
1. 获取最近N次（window_size=3）的评估结果
2. 计算加权平均分: weighted_avg = Σ(score_i × weight_i) / Σ(weight_i)
   - 权重: [1, 2, 3] (越近权重越大)
3. 计算趋势: trend = score_last - score_second_last
4. 根据加权平均分和趋势调整难度:
   - weighted_avg ≥ 0.8 且 trend > 0.1 → 提高难度
   - weighted_avg ≥ 0.75 → 保持难度
   - 0.6 ≤ weighted_avg < 0.75 → 根据趋势微调
   - weighted_avg < 0.6 → 降低难度
```

**数学公式**:
```
weighted_avg = (Σ(i=1 to n) score_i × i) / (Σ(i=1 to n) i)
trend = score_n - score_{n-1}
new_difficulty = f(weighted_avg, trend, current_difficulty)
```

### 2.2 智能追问判断算法

**算法名称**: 基于表现和缺失点的追问决策算法

**核心思想**:
- 限制每个问题最多追问2次
- 检查是否已问过类似问题（避免重复）
- 根据分数和缺失点决定是否追问

**决策规则**:
```
1. 检查追问次数限制:
   - 如果 followup_count >= 2 → 不追问
   
2. 检查相似问题:
   - 如果已问过相似问题（相似度>70%）→ 不追问
   
3. 追问条件:
   - 条件1: score < 0.6 且 missing_points > 0 → 追问
   - 条件2: 0.6 ≤ score < 0.7 且 missing_points > 0 且 followup_count < 1 → 首次追问
```

**相似度计算**:
使用 RapidFuzz 库的 `partial_ratio` 函数计算文本相似度:
```
similarity = fuzz.partial_ratio(text1.lower(), text2.lower())
if similarity > 70:  # 70% 相似度阈值
    return True
```

### 2.3 智能结束判断算法

**算法名称**: 多维度综合评估的结束决策算法

**核心思想**:
- 综合考虑平均分、稳定性、难度覆盖、章节覆盖
- 设置最少轮次（5轮）和最大轮次（15轮）
- 根据表现提前结束或延长面试

**评估指标**:

1. **平均分 (avg_score)**:
   ```
   avg_score = Σ(score_i) / n
   ```

2. **最近表现 (recent_avg)**:
   ```
   recent_avg = Σ(score_i) / k  (k = min(window_size, n))
   ```

3. **稳定性 (std_dev)**:
   ```
   variance = Σ(score_i - avg_score)² / n
   std_dev = √variance
   ```

4. **难度覆盖 (difficulty_range)**:
   ```
   difficulty_range = max(difficulties) - min(difficulties)
   ```

5. **章节覆盖 (chapter_coverage)**:
   ```
   chapter_coverage = |unique_chapters|
   ```

**结束条件**:

| 条件 | 判断标准 | 说明 |
|------|---------|------|
| 提前结束（优秀） | avg_score ≥ 0.85 且 recent_avg ≥ 0.85 且 std_dev < 0.15 且 rounds ≥ min_rounds+2 | 表现优秀且稳定，提前结束 |
| 提前结束（较差） | avg_score < 0.4 且 recent_avg < 0.4 且 rounds ≥ min_rounds | 表现较差且无改善，结束面试 |
| 正常结束 | std_dev < 0.2 且 difficulty_range ≥ 2 且 chapter_coverage ≥ 3 且 recent_avg ≥ 0.7 | 表现稳定，覆盖充分 |
| 强制结束 | rounds ≥ max_rounds | 达到最大轮次 |

### 2.4 智能题目选择算法

**算法名称**: 基于章节权重和知识缺口的题目选择算法

**核心思想**:
- 优先选择缺失章节的题目
- 考虑简历技能匹配
- 避免重复章节
- 使用模糊匹配处理章节名称变化

**选择优先级**:
```
1. 缺失章节 (missing_chapters)
   - 优先选择候选人在这些章节表现较差的题目
   
2. 简历技能匹配 (resume_skills)
   - 如果简历中有相关技能，优先选择对应章节
   - 避免最近2轮问过的章节
   
3. 加权随机选择 (track_chapters)
   - 根据配置的章节权重随机选择
   - 避免最近2轮问过的章节
```

**模糊匹配算法**:
```
for chapter in track_chapters:
    similarity = fuzz.partial_ratio(chapter.lower(), target.lower())
    if similarity > 70:  # 70% 相似度阈值
        return chapter
```

## 3. 算法参数

### 3.1 可调参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `followup_limit` | 2 | 每个问题最多追问次数 |
| `min_rounds` | 5 | 最少面试轮次 |
| `max_rounds` | 15 | 最多面试轮次 |
| `window_size` | 3 | 滑动窗口大小 |
| `similarity_threshold` | 70% | 文本相似度阈值 |
| `excellent_score` | 0.85 | 优秀分数阈值 |
| `poor_score` | 0.4 | 较差分数阈值 |
| `stability_threshold` | 0.15 | 稳定性阈值（标准差） |

### 3.2 难度调整阈值

| 加权平均分 | 趋势 | 动作 |
|-----------|------|------|
| ≥ 0.8 | > 0.1 | 提高难度 |
| ≥ 0.75 | - | 保持难度 |
| 0.6-0.75 | > 0.05 | 提高难度 |
| 0.6-0.75 | < -0.05 | 降低难度 |
| < 0.6 | - | 降低难度 |

## 4. 算法优势

1. **自适应性**: 根据实时表现动态调整，而非固定流程
2. **多维度评估**: 综合考虑分数、稳定性、覆盖度等多个指标
3. **防止无限追问**: 通过次数限制和相似度检查避免重复
4. **智能结束**: 根据表现提前结束或延长，提高效率
5. **可解释性**: 每个决策都有明确的理由和依据

## 5. 实验建议

### 5.1 评估指标

- **面试效率**: 平均面试时长、轮次
- **评估准确性**: 与人工评估的一致性
- **用户体验**: 面试流畅度、问题相关性
- **算法性能**: 决策时间、资源消耗

### 5.2 对比实验

1. **固定难度 vs 自适应难度**
2. **无追问限制 vs 有追问限制**
3. **固定轮次 vs 智能结束**
4. **随机选择 vs 智能选择**

### 5.3 参数调优

- 滑动窗口大小的影响
- 追问次数限制的影响
- 相似度阈值的影响
- 结束条件阈值的影响

## 6. 参考文献建议

1. Adaptive Testing / Computerized Adaptive Testing (CAT)
2. Item Response Theory (IRT)
3. Multi-Armed Bandit Problem
4. Reinforcement Learning in Education
5. Intelligent Tutoring Systems

## 7. 代码实现位置

- **核心算法**: `backend/services/adaptive_interview.py`
- **集成逻辑**: `backend/services/interview_engine.py`
- **题目选择**: `backend/services/question_selector.py`

