"""
语音分析服务
分析语音特征：语速、停顿、流畅度、紧张度等
"""
import re
from typing import Dict, Optional, List
from datetime import datetime


def analyze_speech(
    text: str,
    speech_data: Optional[Dict] = None
) -> Dict:
    """
    分析语音特征
    
    Args:
        text: 识别的文本
        speech_data: 语音数据（包含时间戳、置信度等）
            {
                "timestamps": [(word, start_time, end_time), ...],
                "confidence": float,
                "duration": float,  # 总时长（秒）
                "pauses": [pause_duration, ...],  # 停顿时长列表
                "interim_results": int  # 中间结果次数（修正次数）
            }
    
    Returns:
        {
            "speech_rate": float,  # 语速（字/分钟）
            "fluency": float,  # 流畅度 (0-1)
            "nervousness": float,  # 紧张度 (0-1)
            "pause_frequency": float,  # 停顿频率（次/分钟）
            "average_pause_duration": float,  # 平均停顿时长（秒）
            "confidence": float,  # 识别置信度
            "corrections": int,  # 修正次数
            "analysis": {
                "speech_rate_level": str,  # "slow", "normal", "fast"
                "fluency_level": str,  # "poor", "fair", "good", "excellent"
                "nervousness_level": str,  # "calm", "slightly_nervous", "nervous", "very_nervous"
                "recommendations": List[str]
            }
        }
    """
    # 基础文本分析
    char_count = len(text)
    word_count = len(text.split())
    
    # 检测重复和修正
    corrections = _count_corrections(text, speech_data)
    
    # 如果有语音数据，进行详细分析
    if speech_data:
        duration = speech_data.get("duration", 0)
        pauses = speech_data.get("pauses", [])
        confidence = speech_data.get("confidence", 0.8)
        timestamps = speech_data.get("timestamps", [])
        
        # 计算语速（字/分钟）
        if duration > 0:
            speech_rate = (char_count / duration) * 60
        else:
            # 如果没有时长数据，使用估算（平均语速约200字/分钟）
            speech_rate = 200
        
        # 计算停顿频率和平均停顿时长
        pause_frequency = (len(pauses) / duration * 60) if duration > 0 else 0
        avg_pause_duration = sum(pauses) / len(pauses) if pauses else 0
        
        # 计算流畅度
        fluency = _calculate_fluency(speech_rate, pause_frequency, avg_pause_duration, corrections)
        
        # 计算紧张度
        nervousness = _calculate_nervousness(speech_rate, pause_frequency, avg_pause_duration, corrections, confidence)
        
    else:
        # 仅基于文本的估算
        # 估算语速（假设正常语速）
        speech_rate = 200
        pause_frequency = 0
        avg_pause_duration = 0
        confidence = 0.8
        
        # 基于文本特征估算流畅度和紧张度
        fluency = _estimate_fluency_from_text(text, corrections)
        nervousness = _estimate_nervousness_from_text(text, corrections)
    
    # 生成分析结果
    analysis = _generate_analysis(speech_rate, fluency, nervousness, pause_frequency, avg_pause_duration)
    
    return {
        "speech_rate": round(speech_rate, 2),
        "fluency": round(fluency, 3),
        "nervousness": round(nervousness, 3),
        "pause_frequency": round(pause_frequency, 2),
        "average_pause_duration": round(avg_pause_duration, 3),
        "confidence": round(confidence, 3),
        "corrections": corrections,
        "analysis": analysis
    }


def _count_corrections(text: str, speech_data: Optional[Dict]) -> int:
    """统计修正次数"""
    if speech_data and "interim_results" in speech_data:
        return speech_data["interim_results"]
    
    # 基于文本特征检测修正
    # 检测重复词、填充词等
    corrections = 0
    
    # 检测明显的重复（如"那个那个"、"就是就是"）
    repeated_patterns = re.findall(r'(\S+)\s+\1', text)
    corrections += len(repeated_patterns)
    
    # 检测填充词（"嗯"、"啊"、"那个"等）
    fillers = ['嗯', '啊', '那个', '这个', '就是', '然后', '呃']
    for filler in fillers:
        # 连续出现多次填充词
        pattern = f'({filler}[，,。.\\s]*)+'
        matches = re.findall(pattern, text)
        if matches:
            corrections += len(matches)
    
    return min(corrections, 10)  # 限制最大修正次数


def _calculate_fluency(
    speech_rate: float,
    pause_frequency: float,
    avg_pause_duration: float,
    corrections: int
) -> float:
    """
    计算流畅度 (0-1)
    
    流畅度考虑因素：
    - 语速适中（150-250字/分钟为佳）
    - 停顿频率低
    - 停顿时长短
    - 修正次数少
    """
    # 语速得分（150-250为最佳）
    if 150 <= speech_rate <= 250:
        rate_score = 1.0
    elif 120 <= speech_rate < 150 or 250 < speech_rate <= 300:
        rate_score = 0.7
    elif 100 <= speech_rate < 120 or 300 < speech_rate <= 350:
        rate_score = 0.5
    else:
        rate_score = 0.3
    
    # 停顿得分（停顿频率低、时长短为佳）
    # 正常停顿频率约5-15次/分钟
    if pause_frequency <= 15:
        pause_freq_score = 1.0 - (pause_frequency / 15) * 0.3
    else:
        pause_freq_score = max(0.3, 1.0 - (pause_frequency / 30))
    
    # 平均停顿时长（0.5-1.5秒为正常）
    if avg_pause_duration <= 1.5:
        pause_dur_score = 1.0
    elif avg_pause_duration <= 2.5:
        pause_dur_score = 0.7
    elif avg_pause_duration <= 3.5:
        pause_dur_score = 0.5
    else:
        pause_dur_score = 0.3
    
    # 修正得分
    correction_score = max(0.0, 1.0 - (corrections / 10))
    
    # 加权平均
    fluency = (
        rate_score * 0.3 +
        pause_freq_score * 0.3 +
        pause_dur_score * 0.2 +
        correction_score * 0.2
    )
    
    return min(1.0, max(0.0, fluency))


def _calculate_nervousness(
    speech_rate: float,
    pause_frequency: float,
    avg_pause_duration: float,
    corrections: int,
    confidence: float
) -> float:
    """
    计算紧张度 (0-1)
    
    紧张度指标：
    - 语速过快或过慢
    - 停顿频率高
    - 停顿时长长
    - 修正次数多
    - 识别置信度低（可能因为声音颤抖）
    """
    nervousness = 0.0
    
    # 语速异常（过快或过慢都可能是紧张）
    if speech_rate > 300 or speech_rate < 100:
        nervousness += 0.3
    elif speech_rate > 250 or speech_rate < 120:
        nervousness += 0.15
    
    # 停顿频率高
    if pause_frequency > 20:
        nervousness += 0.25
    elif pause_frequency > 15:
        nervousness += 0.15
    
    # 停顿时长长
    if avg_pause_duration > 2.5:
        nervousness += 0.2
    elif avg_pause_duration > 1.5:
        nervousness += 0.1
    
    # 修正次数多
    if corrections > 5:
        nervousness += 0.15
    elif corrections > 2:
        nervousness += 0.1
    
    # 识别置信度低
    if confidence < 0.6:
        nervousness += 0.1
    
    return min(1.0, nervousness)


def _estimate_fluency_from_text(text: str, corrections: int) -> float:
    """基于文本估算流畅度"""
    # 检测句子结构
    sentence_count = len(re.split(r'[。！？.!?]', text))
    if sentence_count == 0:
        sentence_count = 1
    
    avg_sentence_length = len(text) / sentence_count
    
    # 正常句子长度约20-50字
    if 20 <= avg_sentence_length <= 50:
        structure_score = 1.0
    else:
        structure_score = 0.7
    
    # 修正次数影响
    correction_score = max(0.0, 1.0 - (corrections / 10))
    
    return (structure_score * 0.6 + correction_score * 0.4)


def _estimate_nervousness_from_text(text: str, corrections: int) -> float:
    """基于文本估算紧张度"""
    nervousness = 0.0
    
    # 检测填充词频率
    fillers = ['嗯', '啊', '那个', '这个', '就是', '然后', '呃']
    filler_count = sum(text.count(filler) for filler in fillers)
    text_length = len(text)
    
    if text_length > 0:
        filler_ratio = filler_count / text_length
        if filler_ratio > 0.1:
            nervousness += 0.3
        elif filler_ratio > 0.05:
            nervousness += 0.15
    
    # 修正次数
    if corrections > 5:
        nervousness += 0.3
    elif corrections > 2:
        nervousness += 0.15
    
    # 检测重复模式
    repeated = len(re.findall(r'(\S+)\s+\1', text))
    if repeated > 3:
        nervousness += 0.2
    elif repeated > 1:
        nervousness += 0.1
    
    return min(1.0, nervousness)


def _generate_analysis(
    speech_rate: float,
    fluency: float,
    nervousness: float,
    pause_frequency: float,
    avg_pause_duration: float
) -> Dict:
    """生成分析结果和建议"""
    # 语速等级
    if speech_rate < 120:
        speech_rate_level = "slow"
        speech_rate_desc = "语速较慢"
    elif speech_rate <= 250:
        speech_rate_level = "normal"
        speech_rate_desc = "语速正常"
    else:
        speech_rate_level = "fast"
        speech_rate_desc = "语速较快"
    
    # 流畅度等级
    if fluency >= 0.8:
        fluency_level = "excellent"
        fluency_desc = "非常流畅"
    elif fluency >= 0.6:
        fluency_level = "good"
        fluency_desc = "较为流畅"
    elif fluency >= 0.4:
        fluency_level = "fair"
        fluency_desc = "基本流畅"
    else:
        fluency_level = "poor"
        fluency_desc = "不够流畅"
    
    # 紧张度等级
    if nervousness < 0.3:
        nervousness_level = "calm"
        nervousness_desc = "表现自然"
    elif nervousness < 0.5:
        nervousness_level = "slightly_nervous"
        nervousness_desc = "略显紧张"
    elif nervousness < 0.7:
        nervousness_level = "nervous"
        nervousness_desc = "较为紧张"
    else:
        nervousness_level = "very_nervous"
        nervousness_desc = "非常紧张"
    
    # 生成建议
    recommendations = []
    
    if speech_rate < 120:
        recommendations.append("建议适当提高语速，保持自然节奏")
    elif speech_rate > 300:
        recommendations.append("语速过快可能影响表达清晰度，建议适当放慢")
    
    if pause_frequency > 20:
        recommendations.append("停顿频率较高，建议减少不必要的停顿")
    
    if avg_pause_duration > 2.5:
        recommendations.append("停顿时间较长，建议缩短思考时间")
    
    if fluency < 0.5:
        recommendations.append("表达流畅度有待提升，建议多练习口语表达")
    
    if nervousness > 0.5:
        recommendations.append("建议放松心态，保持自信，深呼吸有助于缓解紧张")
    
    if not recommendations:
        recommendations.append("语音表达良好，继续保持")
    
    return {
        "speech_rate_level": speech_rate_level,
        "speech_rate_desc": speech_rate_desc,
        "fluency_level": fluency_level,
        "fluency_desc": fluency_desc,
        "nervousness_level": nervousness_level,
        "nervousness_desc": nervousness_desc,
        "recommendations": recommendations
    }

