#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证和授权相关功能
"""

from flask import request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import uuid
from models import db, User, UserSession, ChatHistory, VerificationCode
from services.sms_service import send_code, verify_code
from utils.logger import logger

# 创建登录管理器
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    return User.query.get(int(user_id))

def init_auth(app):
    """初始化认证系统"""
    login_manager.init_app(app)
    return login_manager

def authenticate_user(username, password, remember=False):
    """验证用户登录"""
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password) and user.is_active:
        # 更新最后登录时间
        user.update_last_login()
        
        # 创建用户会话
        user_session = create_user_session(user.id, request)
        
        # 登录用户
        login_user(user, remember=remember)
        
        return {
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            },
            'session_id': user_session.session_id
        }
    
    return {'success': False, 'message': '用户名或密码错误'}

def create_user_session(user_id, request_obj=None):
    """创建用户会话"""
    # 清理过期的会话
    expired_sessions = UserSession.query.filter(
        UserSession.expires_at < datetime.utcnow()
    ).all()
    for sess in expired_sessions:
        sess.is_active = False
    db.session.commit()
    
    # 创建新会话
    user_session = UserSession(
        user_id=user_id,
        ip_address=request_obj.remote_addr if request_obj else None,
        user_agent=request_obj.user_agent.string if request_obj and request_obj.user_agent else None
    )
    
    db.session.add(user_session)
    db.session.commit()
    
    return user_session

def get_user_session(session_id):
    """获取用户会话"""
    if not session_id:
        return None
    
    user_session = UserSession.query.filter_by(
        session_id=session_id,
        is_active=True
    ).first()
    
    if user_session and not user_session.is_expired():
        return user_session
    
    return None

def save_chat_message(user_id, session_id, message_type, content, context=None, response_time=None):
    """保存聊天消息"""
    chat_message = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        message_type=message_type,
        content=content,
        context=context,
        response_time=response_time
    )
    
    db.session.add(chat_message)
    db.session.commit()
    
    return chat_message

def get_chat_history(user_id, session_id=None, limit=50):
    """获取聊天历史"""
    query = ChatHistory.query.filter_by(user_id=user_id)
    
    if session_id:
        query = query.filter_by(session_id=session_id)
    
    return query.order_by(ChatHistory.created_at.desc()).limit(limit).all()

def get_user_sessions(user_id, limit=20):
    """获取用户的所有会话"""
    return UserSession.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(UserSession.created_at.desc()).limit(limit).all()

def logout_user_session(session_id):
    """登出用户会话"""
    user_session = UserSession.query.filter_by(session_id=session_id).first()
    if user_session:
        user_session.is_active = False
        user_session.expires_at = datetime.utcnow()
        db.session.commit()
        return True
    return False

def register_user(username, password, email=None, full_name=None):
    """注册新用户"""
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return {'success': False, 'message': '用户名已存在'}
    
    # 检查邮箱是否已存在
    if email and User.query.filter_by(email=email).first():
        return {'success': False, 'message': '邮箱已存在'}
    
    # 创建新用户
    user = User(
        username=username,
        email=email,
        full_name=full_name
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return {
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name
        }
    }

def get_current_user_info():
    """获取当前用户信息"""
    if current_user.is_authenticated:
        return {
            'id': current_user.id,
            'username': current_user.username,
            'phone_number': current_user.phone_number,
            'email': current_user.email,
            'full_name': current_user.full_name,
            'last_login': current_user.last_login.isoformat() if current_user.last_login else None
        }
    return None


# ==================== 手机验证码登录 ====================

def send_verification_code(phone: str) -> dict:
    """
    发送手机验证码
    
    返回: {"success": bool, "message": str, "code": str (dev)}
    """
    return send_code(phone)


def login_by_phone(phone: str, code: str, remember: bool = False) -> dict:
    """
    通过手机验证码登录
    如果手机号不存在则自动注册
    
    返回: {"success": bool, "message": str, "user": dict, "session_id": str}
    """
    # 验证验证码
    verify_result = verify_code(phone, code)
    if not verify_result.get("valid"):
        return {"success": False, "message": verify_result.get("message", "验证失败")}
    
    # 查找用户（手机号登录）
    user = User.query.filter_by(phone_number=phone).first()
    
    # 如果手机号不存在，自动注册新用户
    if not user:
        # 生成用户名：phone_后4位
        username = f"user_{phone[-4:]}"
        base_username = username
        suffix = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{suffix}"
            suffix += 1
        
        user = User(
            username=username,
            phone_number=phone,
            full_name=f"用户{phone[-4:]}",
            password_hash=""  # 手机号注册用户无需密码
        )
        db.session.add(user)
        db.session.commit()
        logger.info(f"新用户通过手机号自动注册: {phone} -> {username}")
    
    # 确保用户激活
    if not user.is_active:
        return {"success": False, "message": "该账号已被禁用"}
    
    # 更新最后登录时间
    user.update_last_login()
    
    # 创建用户会话
    user_session = create_user_session(user.id, request)
    
    # 登录用户
    login_user(user, remember=remember)
    
    return {
        'success': True,
        'message': '登录成功',
        'user': {
            'id': user.id,
            'username': user.username,
            'phone_number': user.phone_number,
            'email': user.email,
            'full_name': user.full_name
        },
        'session_id': user_session.session_id
    }


def bind_phone(user_id: int, phone: str) -> dict:
    """为已有用户绑定手机号"""
    # 检查手机号是否已被绑定
    existing = User.query.filter_by(phone_number=phone).first()
    if existing and existing.id != user_id:
        return {"success": False, "message": "该手机号已被其他账号绑定"}
    
    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": "用户不存在"}
    
    user.phone_number = phone
    db.session.commit()
    
    return {"success": True, "message": "手机号绑定成功"}


def get_user_by_phone(phone: str) -> User:
    """通过手机号查找用户"""
    return User.query.filter_by(phone_number=phone).first()