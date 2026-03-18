"""
表情分析服务
识别被面试者面部表情，分析情绪状态（紧张、自信、专注等）
"""
import base64
import tempfile
import os
from typing import Dict, Optional, Union


def analyze_expression(
    image_data: Union[bytes, str, None],
    enforce_detection: bool = False
) -> Optional[Dict]:
    """
    分析面部表情，识别情绪状态。
    
    Args:
        image_data: 图像数据，支持：
            - bytes: 原始图像字节
            - str: base64 编码字符串，或图像文件路径
        enforce_detection: 若为 True，未检测到人脸时抛出异常；False 时返回 None
    
    Returns:
        {
            "dominant_emotion": str,      # 主导情绪: angry, disgust, fear, happy, sad, surprise, neutral
            "emotion_scores": Dict,       # 各情绪得分 0-1
            "confidence": float,          # 检测置信度
            "detected_face": bool,
            "interview_relevance": {      # 面试场景相关解读
                "nervousness": float,     # 紧张度 0-1（基于 fear, sad, surprise 等）
                "confidence_level": str,  # 自信程度
                "engagement": str,        # 投入度
                "recommendations": List[str]
            }
        }
        或 None（未检测到人脸或分析失败）
    """
    if image_data is None:
        return None
    
    img_path = None
    try:
        if isinstance(image_data, bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(image_data)
                img_path = tmp.name
        elif isinstance(image_data, str):
            if len(image_data) < 260 and os.path.isfile(image_data):
                img_path = image_data
            else:
                # 假定为 base64
                raw = base64.b64decode(image_data)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(raw)
                    img_path = tmp.name
        
        if not img_path or not os.path.exists(img_path):
            return None
        
        result = _analyze_with_deepface(img_path, enforce_detection)
        if result:
            result["interview_relevance"] = _compute_interview_relevance(result)
        return result
        
    except Exception as e:
        if os.environ.get("DEBUG"):
            import traceback
            traceback.print_exc()
        return None
    finally:
        if img_path and img_path != image_data and os.path.exists(img_path):
            try:
                os.unlink(img_path)
            except OSError:
                pass


def _analyze_with_deepface(img_path: str, enforce_detection: bool) -> Optional[Dict]:
    """使用 DeepFace 进行情绪分析。"""
    try:
        from deepface import DeepFace
    except ImportError:
        return None
    
    try:
        analyses = DeepFace.analyze(
            img_path=img_path,
            actions=["emotion"],
            enforce_detection=enforce_detection,
            silent=True
        )
        
        if not analyses:
            return None
        
        # 可能返回单条或多条（多人脸）
        item = analyses[0] if isinstance(analyses, list) else analyses
        emotions = item.get("emotion", {})
        
        if not emotions:
            return None
        
        dominant = item.get("dominant_emotion", max(emotions, key=emotions.get))
        total = sum(emotions.values()) or 1
        emotion_scores = {k: round(v / total, 4) for k, v in emotions.items()}
        
        return {
            "dominant_emotion": dominant,
            "emotion_scores": emotion_scores,
            "confidence": 1.0,
            "detected_face": True,
        }
    except Exception:
        return None


def _compute_interview_relevance(emotion_result: Dict) -> Dict:
    """
    将情绪结果映射到面试场景：紧张度、自信度、投入度。
    """
    scores = emotion_result.get("emotion_scores", {})
    dominant = emotion_result.get("dominant_emotion", "neutral")
    
    # 紧张度：fear, sad, disgust 等负面情绪权重高
    nervousness = (
        scores.get("fear", 0) * 0.4 +
        scores.get("sad", 0) * 0.25 +
        scores.get("disgust", 0) * 0.15 +
        scores.get("angry", 0) * 0.1 +
        scores.get("surprise", 0) * 0.1  # 惊讶可能表示意外/紧张
    )
    nervousness = min(1.0, nervousness * 1.5)  # 适当放大
    
    # 自信度：happy, neutral 表示相对放松
    confidence_score = scores.get("happy", 0) * 0.5 + scores.get("neutral", 0) * 0.5
    if confidence_score >= 0.6:
        confidence_level = "confident"
        confidence_desc = "表现自信"
    elif confidence_score >= 0.4:
        confidence_level = "moderate"
        confidence_desc = "表现较为自然"
    elif nervousness < 0.5:
        confidence_level = "moderate"
        confidence_desc = "表现较为自然"
    else:
        confidence_level = "nervous"
        confidence_desc = "略显紧张"
    
    # 投入度：neutral + 低 fear 表示专注
    engagement = "focused" if scores.get("neutral", 0) >= 0.5 and scores.get("fear", 0) < 0.3 else "engaged"
    engagement_desc = "专注投入" if engagement == "focused" else "正常投入"
    
    # 建议
    recommendations = []
    if nervousness > 0.5:
        recommendations.append("表情显示略有紧张，建议深呼吸、保持微笑有助于放松")
    if scores.get("fear", 0) > 0.3:
        recommendations.append("面部表情略显紧绷，可尝试放松肩颈、保持眼神交流")
    if scores.get("happy", 0) >= 0.3:
        recommendations.append("表情自然放松，保持当前状态")
    if not recommendations:
        recommendations.append("表情自然，继续保持")
    
    return {
        "nervousness": round(nervousness, 3),
        "confidence_level": confidence_level,
        "confidence_desc": confidence_desc,
        "engagement": engagement,
        "engagement_desc": engagement_desc,
        "recommendations": recommendations[:3],
    }
