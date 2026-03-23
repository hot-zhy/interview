"""Resume-track matching: check if resume skills align with selected job track."""
from typing import List, Tuple, Optional

# Track -> skill keywords that indicate a match (resume should have at least MIN_MATCH_COUNT)
TRACK_SKILL_KEYWORDS = {
    "Java Backend": [
        "Java", "Spring", "Spring Boot", "SpringBoot",
        "MySQL", "PostgreSQL", "Redis", "MongoDB",
        "并发", "多线程", "JVM", "微服务", "分布式",
        "集合", "数据结构", "设计模式",
    ],
    "Java Concurrency": [
        "Java", "并发", "多线程", "JVM",
        "微服务", "分布式", "锁", "线程",
    ],
    "JVM & Performance": [
        "Java", "JVM", "并发", "多线程",
        "微服务", "分布式", "性能", "调优",
    ],
    "Spring & Microservices": [
        "Java", "Spring", "Spring Boot", "SpringBoot",
        "微服务", "分布式", "MySQL", "Redis",
        "Docker", "Kubernetes", "K8s",
    ],
}

# Placeholder from resume parser when no skills detected
UNKNOWN_SKILL_PLACEHOLDER = "未识别到技能信息"

# Minimum number of matching skills required
MIN_MATCH_COUNT = 1


def check_resume_track_match(
    resume_skills: Optional[List[str]],
    track: str,
) -> Tuple[bool, str]:
    """
    Check if resume skills match the selected job track.

    Args:
        resume_skills: List of skills from resume parsed_json["skills"]
        track: Selected track name (e.g. "Java Backend")

    Returns:
        (match: bool, reason: str)
    """
    if not resume_skills:
        return False, "no_skills"

    # Filter out placeholder / empty
    skills = [
        s.strip() for s in resume_skills
        if s and s.strip() and s.strip() != UNKNOWN_SKILL_PLACEHOLDER
    ]
    if not skills:
        return False, "no_valid_skills"

    keywords = TRACK_SKILL_KEYWORDS.get(track, [])
    if not keywords:
        return True, "ok"  # Unknown track, allow

    # Normalize for comparison (case-insensitive, partial match)
    skills_lower = [s.lower() for s in skills]
    keywords_lower = [k.lower() for k in keywords]

    match_count = 0
    for sk in skills_lower:
        for kw in keywords_lower:
            if kw in sk or sk in kw:
                match_count += 1
                break

    if match_count >= MIN_MATCH_COUNT:
        return True, "ok"
    return False, "mismatch"
