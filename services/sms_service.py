#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短信验证码服务
开发环境：验证码打印到控制台
生产环境：可对接阿里云/腾讯云短信API
"""

import random
import string
from datetime import datetime, timedelta

from models import db, VerificationCode
from utils.logger import logger


# ==================== 配置 ====================

SMS_CODE_EXPIRE_MINUTES = 5  # 验证码有效期（分钟）
SMS_CODE_LENGTH = 6          # 验证码长度
SMS_RESEND_INTERVAL = 60     # 重发间隔（秒）


def generate_code(length: int = SMS_CODE_LENGTH) -> str:
    """生成随机数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_code(phone: str) -> dict:
    """
    发送验证码
    开发环境：打印到控制台 + 存入数据库
    生产环境：对接短信API
    
    返回: {"success": bool, "message": str, "code": str (仅dev环境)}
    """
    # 检查重发频率（同一手机号60秒内不能重复发送）
    recent_code = VerificationCode.query.filter_by(
        phone=phone,
        used=False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if recent_code and not recent_code.is_expired():
        elapsed = (datetime.utcnow() - recent_code.created_at).total_seconds()
        if elapsed < SMS_RESEND_INTERVAL:
            remain = int(SMS_RESEND_INTERVAL - elapsed)
            logger.warning(f"验证码发送过于频繁，手机: {phone}，剩余等待: {remain}秒")
            return {
                "success": False,
                "message": f"发送过于频繁，请{remain}秒后再试"
            }
    
    # 生成验证码
    code = generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=SMS_CODE_EXPIRE_MINUTES)
    
    # 存入数据库
    vc = VerificationCode(
        phone=phone,
        code=code,
        expires_at=expires_at
    )
    db.session.add(vc)
    db.session.commit()
    
    # 开发环境：打印到控制台
    logger.info(f"📱 [短信验证码] 手机: {phone}，验证码: {code}，有效期: {SMS_CODE_EXPIRE_MINUTES}分钟")
    print(f"\n{'='*50}")
    print(f"  📱 手机验证码")
    print(f"  手机号: {phone}")
    print(f"  验证码: \033[1;32m{code}\033[0m")
    print(f"  有效期: {SMS_CODE_EXPIRE_MINUTES}分钟")
    print(f"{'='*50}\n")
    
    return {
        "success": True,
        "message": "验证码已发送",
        "code": code  # 开发环境返回验证码方便测试
    }


def verify_code(phone: str, code: str) -> dict:
    """
    验证验证码
    
    返回: {"success": bool, "message": str, "valid": bool}
    """
    if not phone or not code:
        return {"success": False, "message": "手机号和验证码不能为空", "valid": False}
    
    # 查找最新的未使用验证码
    vc = VerificationCode.query.filter_by(
        phone=phone,
        code=code,
        used=False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not vc:
        return {"success": False, "message": "验证码错误", "valid": False}
    
    if vc.is_expired():
        return {"success": False, "message": "验证码已过期，请重新获取", "valid": False}
    
    # 标记为已使用
    vc.mark_used()
    
    return {"success": True, "message": "验证成功", "valid": True}


def cleanup_expired_codes():
    """清理过期的验证码（可定时调用）"""
    expired = VerificationCode.query.filter(
        VerificationCode.expires_at < datetime.utcnow()
    ).all()
    count = len(expired)
    for vc in expired:
        db.session.delete(vc)
    db.session.commit()
    if count > 0:
        logger.info(f"已清理 {count} 条过期验证码")
    return count
