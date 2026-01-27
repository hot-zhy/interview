"""Resume parser service."""
import pdfplumber
from docx import Document
from typing import Dict, Any, Optional
import re


def parse_resume(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Parse resume from PDF or DOCX file.
    
    Returns structured information:
    {
        "education": [...],
        "experience": [...],
        "projects": [...],
        "skills": [...],
        "raw_text": "..."
    }
    """
    raw_text = ""
    
    # Extract text based on file type
    if filename.lower().endswith('.pdf'):
        raw_text = extract_text_from_pdf(file_path)
    elif filename.lower().endswith(('.docx', '.doc')):
        raw_text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {filename}")
    
    # Parse structured information
    parsed = {
        "education": extract_education(raw_text),
        "experience": extract_experience(raw_text),
        "projects": extract_projects(raw_text),
        "skills": extract_skills(raw_text),
        "raw_text": raw_text
    }
    
    return parsed


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")


def extract_education(text: str) -> list:
    """Extract education information."""
    education = []
    # Simple pattern matching for education
    patterns = [
        r'(?:教育背景|Education|学历)[:：]?\s*(.*?)(?=\n\n|\n(?:工作|项目|技能))',
        r'(?:本科|学士|硕士|博士|Bachelor|Master|PhD)[^。]*',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            edu_text = match.group(0).strip()
            if edu_text and len(edu_text) > 10:
                education.append(edu_text)
    
    return education if education else ["未识别到教育背景"]


def extract_experience(text: str) -> list:
    """Extract work experience."""
    experience = []
    # Simple pattern matching for experience
    patterns = [
        r'(?:工作经历|Experience|工作)[:：]?\s*(.*?)(?=\n\n|\n(?:项目|技能|教育))',
        r'(?:公司|Company|职位|Position)[^。]*',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            exp_text = match.group(0).strip()
            if exp_text and len(exp_text) > 10:
                experience.append(exp_text)
    
    return experience if experience else ["未识别到工作经历"]


def extract_projects(text: str) -> list:
    """Extract project information."""
    projects = []
    # Simple pattern matching for projects
    patterns = [
        r'(?:项目经历|Projects|项目)[:：]?\s*(.*?)(?=\n\n|\n(?:技能|教育|工作))',
        r'(?:项目|Project)[^。]*',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            proj_text = match.group(0).strip()
            if proj_text and len(proj_text) > 10:
                projects.append(proj_text)
    
    return projects if projects else ["未识别到项目经历"]


def extract_skills(text: str) -> list:
    """Extract skills."""
    skills = []
    
    # Common skill keywords
    skill_keywords = [
        'Java', 'Python', 'JavaScript', 'TypeScript', 'Spring', 'Spring Boot',
        'MySQL', 'PostgreSQL', 'Redis', 'MongoDB', 'Docker', 'Kubernetes',
        'Git', 'Linux', 'AWS', 'Azure', '微服务', '分布式', '并发', 'JVM',
        '多线程', '设计模式', '算法', '数据结构'
    ]
    
    # Find skills in text
    found_skills = []
    for keyword in skill_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
            found_skills.append(keyword)
    
    # Also try to extract from skills section
    skill_patterns = [
        r'(?:技能|Skills|技术栈)[:：]?\s*(.*?)(?=\n\n|\n(?:教育|工作|项目))',
    ]
    
    for pattern in skill_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            skills_text = match.group(1).strip()
            # Extract individual skills
            skill_items = re.split(r'[,，、;；\n]', skills_text)
            for item in skill_items:
                item = item.strip()
                if item and len(item) > 1:
                    found_skills.append(item)
    
    return list(set(found_skills)) if found_skills else ["未识别到技能信息"]

