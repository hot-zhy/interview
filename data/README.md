# 数据目录

此目录用于存储：
- 数据库文件（interview.db）
- 上传的题库文件（question.xlsx）

## Excel 题库格式

请确保 `question.xlsx` 文件包含以下表头：

| id | question | correct_answer | difficulty | chapter |
|----|----------|----------------|------------|---------|
| Q1 | 题目内容 | 标准答案 | 1-5 | 章节名称 |

### 字段说明

- **id**: 题目唯一标识（字符串或数字）
- **question**: 题目内容
- **correct_answer**: 标准答案
- **difficulty**: 难度等级（1-5，1最简单，5最难）
- **chapter**: 章节/分类（如：Java基础、Spring、JVM等）

### 示例

| id | question | correct_answer | difficulty | chapter |
|----|----------|----------------|------------|---------|
| Q1 | 什么是Java？ | Java是一种面向对象的编程语言... | 1 | Java基础 |
| Q2 | Spring框架的核心特性？ | IoC容器、AOP、事务管理等... | 3 | Spring |

