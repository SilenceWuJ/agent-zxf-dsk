#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证API模块
提供完整的用户认证、会话管理和历史记录API
"""

from flask import Blueprint, request, jsonify, session as flask_session
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, timedelta
import json
from functools import wraps

from models import db, User, UserSession, ChatHistory
from auth import authenticate_user, register_user, get_current_user_info
from session_manager import session_manager

# 创建蓝图
auth_bp = Blueprint('auth_api', __name__)

# ==================== 装饰器 ====================

def api_login_required(f):
    """API登录要求装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'message': '需要登录',
                'code': 'UNAUTHORIZED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def require_json(f):
    """要求JSON请求装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': '请求必须是JSON格式',
                'code': 'INVALID_REQUEST'
            }), 400
        return f(*args, **kwargs)
    return decorated_function

# ==================== 用户认证API ====================

@auth_bp.route('/api/auth/login', methods=['POST'])
@require_json
def api_login():
    """用户登录"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空',
            'code': 'MISSING_CREDENTIALS'
        }), 400
    
    # 验证用户
    result = authenticate_user(username, password, remember)
    
    if result['success']:
        # 记录登录日志
        user = User.query.filter_by(username=username).first()
        if user:
            user.update_last_login()
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': result['user'],
            'session_id': result['session_id'],
            'token': result['session_id']  # 兼容旧版本
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', '登录失败'),
            'code': 'INVALID_CREDENTIALS'
        }), 401

@auth_bp.route('/api/auth/register', methods=['POST'])
@require_json
def api_register():
    """用户注册"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    full_name = data.get('full_name', '').strip()
    
    # 验证输入
    if not username or not password:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空',
            'code': 'MISSING_CREDENTIALS'
        }), 400
    
    if len(username) < 3:
        return jsonify({
            'success': False,
            'message': '用户名至少3个字符',
            'code': 'INVALID_USERNAME'
        }), 400
    
    if len(password) < 6:
        return jsonify({
            'success': False,
            'message': '密码至少6个字符',
            'code': 'INVALID_PASSWORD'
        }), 400
    
    # 注册用户
    result = register_user(username, password, email, full_name)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user': result['user']
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', '注册失败'),
            'code': 'REGISTRATION_FAILED'
        }), 400

@auth_bp.route('/api/auth/logout', methods=['POST'])
@api_login_required
def api_logout():
    """用户登出"""
    session_id = request.headers.get('X-Session-ID') or request.json.get('session_id')
    
    if session_id:
        from auth import logout_user_session
        logout_user_session(session_id)
    
    logout_user()
    
    return jsonify({
        'success': True,
        'message': '登出成功'
    })

@auth_bp.route('/api/auth/me', methods=['GET'])
@api_login_required
def api_user_info():
    """获取当前用户信息"""
    user_info = get_current_user_info()
    
    if user_info:
        # 获取用户统计信息
        stats = session_manager.get_message_statistics(user_info['id'])
        
        return jsonify({
            'success': True,
            'user': user_info,
            'statistics': stats
        })
    else:
        return jsonify({
            'success': False,
            'message': '用户未登录',
            'code': 'NOT_LOGGED_IN'
        }), 401

@auth_bp.route('/api/auth/update-profile', methods=['PUT'])
@api_login_required
@require_json
def api_update_profile():
    """更新用户资料"""
    data = request.get_json()
    
    user = User.query.get(current_user.id)
    if not user:
        return jsonify({
            'success': False,
            'message': '用户不存在',
            'code': 'USER_NOT_FOUND'
        }), 404
    
    # 更新字段
    if 'email' in data:
        email = data['email'].strip()
        if email and email != user.email:
            # 检查邮箱是否已被使用
            existing = User.query.filter_by(email=email).first()
            if existing and existing.id != user.id:
                return jsonify({
                    'success': False,
                    'message': '邮箱已被使用',
                    'code': 'EMAIL_EXISTS'
                }), 400
            user.email = email
    
    if 'full_name' in data:
        user.full_name = data['full_name'].strip()
    
    if 'password' in data and data['password']:
        # 验证旧密码
        old_password = data.get('old_password')
        if not old_password or not user.check_password(old_password):
            return jsonify({
                'success': False,
                'message': '旧密码错误',
                'code': 'INVALID_PASSWORD'
            }), 400
        
        # 设置新密码
        user.set_password(data['password'])
    
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '资料更新成功',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name
        }
    })

# ==================== 会话管理API ====================

@auth_bp.route('/api/auth/sessions', methods=['GET'])
@api_login_required
def api_get_sessions():
    """获取用户的所有会话"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    sessions = session_manager.get_user_sessions(current_user.id, limit, offset)
    
    return jsonify({
        'success': True,
        'sessions': [
            {
                'session_id': sess.session_id,
                'created_at': sess.created_at.isoformat(),
                'expires_at': sess.expires_at.isoformat(),
                'ip_address': sess.ip_address,
                'user_agent': sess.user_agent,
                'is_active': sess.is_active,
                'message_count': ChatHistory.query.filter_by(session_id=sess.session_id).count()
            }
            for sess in sessions
        ],
        'total': UserSession.query.filter_by(user_id=current_user.id).count(),
        'limit': limit,
        'offset': offset
    })

@auth_bp.route('/api/auth/sessions/<session_id>', methods=['GET'])
@api_login_required
def api_get_session(session_id):
    """获取特定会话"""
    session = session_manager.get_session(session_id)
    
    if not session or session.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': '会话不存在或无权访问',
            'code': 'SESSION_NOT_FOUND'
        }), 404
    
    summary = session_manager.get_session_summary(session_id)
    
    return jsonify({
        'success': True,
        'session': {
            'session_id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'expires_at': session.expires_at.isoformat(),
            'ip_address': session.ip_address,
            'user_agent': session.user_agent,
            'is_active': session.is_active
        },
        'summary': summary
    })

@auth_bp.route('/api/auth/sessions/<session_id>/messages', methods=['GET'])
@api_login_required
def api_get_session_messages(session_id):
    """获取会话的消息"""
    # 验证会话所有权
    session = UserSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.id
    ).first()
    
    if not session:
        return jsonify({
            'success': False,
            'message': '会话不存在或无权访问',
            'code': 'SESSION_NOT_FOUND'
        }), 404
    
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    message_type = request.args.get('type')
    
    messages = session_manager.get_session_messages(
        session_id, limit, offset, message_type
    )
    
    return jsonify({
        'success': True,
        'messages': [
            {
                'id': msg.id,
                'message_type': msg.message_type,
                'content': msg.content,
                'context': json.loads(msg.context) if msg.context else None,
                'response_time': msg.response_time,
                'created_at': msg.created_at.isoformat()
            }
            for msg in messages
        ],
        'total': ChatHistory.query.filter_by(session_id=session_id).count(),
        'limit': limit,
        'offset': offset
    })

@auth_bp.route('/api/auth/sessions/<session_id>/renew', methods=['POST'])
@api_login_required
def api_renew_session(session_id):
    """续约会话"""
    days = request.json.get('days', 7) if request.is_json else 7
    
    session = UserSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.id
    ).first()
    
    if not session:
        return jsonify({
            'success': False,
            'message': '会话不存在或无权访问',
            'code': 'SESSION_NOT_FOUND'
        }), 404
    
    if session_manager.renew_session(session_id, days):
        return jsonify({
            'success': True,
            'message': '会话续约成功',
            'expires_at': session.expires_at.isoformat()
        })
    else:
        return jsonify({
            'success': False,
            'message': '会话续约失败',
            'code': 'RENEWAL_FAILED'
        }), 400

@auth_bp.route('/api/auth/sessions/<session_id>', methods=['DELETE'])
@api_login_required
def api_delete_session(session_id):
    """删除会话"""
    session = UserSession.query.filter_by(
        session_id=session_id,
        user_id=current_user.id
    ).first()
    
    if not session:
        return jsonify({
            'success': False,
            'message': '会话不存在或无权访问',
            'code': 'SESSION_NOT_FOUND'
        }), 404
    
    # 删除会话消息
    message_count = session_manager.delete_session_messages(session_id, current_user.id)
    
    # 删除会话
    db.session.delete(session)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'会话删除成功，共删除{message_count}条消息',
        'deleted_messages': message_count
    })

# ==================== 消息管理API ====================

@auth_bp.route('/api/auth/messages', methods=['GET'])
@api_login_required
def api_get_messages():
    """获取用户的所有消息"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    session_id = request.args.get('session_id')
    
    messages = session_manager.get_user_messages(
        current_user.id, limit, offset, session_id
    )
    
    return jsonify({
        'success': True,
        'messages': [
            {
                'id': msg.id,
                'session_id': msg.session_id,
                'message_type': msg.message_type,
                'content': msg.content[:200] + '...' if len(msg.content) > 200 else msg.content,
                'created_at': msg.created_at.isoformat()
            }
            for msg in messages
        ],
        'total': ChatHistory.query.filter_by(user_id=current_user.id).count(),
        'limit': limit,
        'offset': offset
    })

@auth_bp.route('/api/auth/messages/search', methods=['GET'])
@api_login_required
def api_search_messages():
    """搜索消息"""
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify({
            'success': False,
            'message': '搜索关键词至少2个字符',
            'code': 'INVALID_QUERY'
        }), 400
    
    limit = request.args.get('limit', 50, type=int)
    
    messages = session_manager.search_messages(current_user.id, query, limit)
    
    return jsonify({
        'success': True,
        'query': query,
        'messages': [
            {
                'id': msg.id,
                'session_id': msg.session_id,
                'message_type': msg.message_type,
                'content': msg.content,
                'created_at': msg.created_at.isoformat()
            }
            for msg in messages
        ],
        'total': len(messages)
    })

@auth_bp.route('/api/auth/messages/<int:message_id>', methods=['DELETE'])
@api_login_required
def api_delete_message(message_id):
    """删除消息"""
    if session_manager.delete_message(message_id, current_user.id):
        return jsonify({
            'success': True,
            'message': '消息删除成功'
        })
    else:
        return jsonify({
            'success': False,
            'message': '消息不存在或无权删除',
            'code': 'MESSAGE_NOT_FOUND'
        }), 404

# ==================== 数据导出API ====================

@auth_bp.route('/api/auth/export/session/<session_id>', methods=['GET'])
@api_login_required
def api_export_session(session_id):
    """导出会话数据"""
    data = session_manager.export_session_data(session_id, current_user.id)
    
    if data:
        return jsonify({
            'success': True,
            'data': data,
            'format': 'json'
        })
    else:
        return jsonify({
            'success': False,
            'message': '会话不存在或无权访问',
            'code': 'SESSION_NOT_FOUND'
        }), 404

@auth_bp.route('/api/auth/export/user', methods=['GET'])
@api_login_required
def api_export_user_data():
    """导出用户数据"""
    limit_sessions = request.args.get('limit_sessions', 10, type=int)
    
    data = session_manager.export_user_data(current_user.id, limit_sessions)
    
    return jsonify({
        'success': True,
        'data': data,
        'format': 'json'
    })

# ==================== 统计API ====================

@auth_bp.route('/api/auth/statistics', methods=['GET'])
@api_login_required
def api_get_statistics():
    """获取用户统计信息"""
    days = request.args.get('days', 30, type=int)
    
    stats = session_manager.get_message_statistics(current_user.id, days)
    
    # 获取活跃会话数
    active_sessions = len(session_manager.get_active_sessions(current_user.id))
    
    stats['active_sessions'] = active_sessions
    stats['total_sessions'] = UserSession.query.filter_by(user_id=current_user.id).count()
    
    return jsonify({
        'success': True,
        'statistics': stats
    })

# ==================== 健康检查 ====================

@auth_bp.route('/api/auth/health', methods=['GET'])
def api_health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })