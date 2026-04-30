#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话历史管理器
提供完整的会话历史存储、检索和管理功能
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import desc, asc, and_, or_
from sqlalchemy.orm import joinedload
import json
from models import db, User, UserSession, ChatHistory


class SessionManager:
    """会话管理器"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        self.app = app
    
    # ==================== 会话管理 ====================
    
    def create_session(self, user_id: int, request_obj=None) -> UserSession:
        """创建新会话"""
        # 清理过期的会话
        self._cleanup_expired_sessions()
        
        # 创建新会话
        session = UserSession(
            user_id=user_id,
            ip_address=request_obj.remote_addr if request_obj else None,
            user_agent=request_obj.user_agent.string if request_obj and request_obj.user_agent else None
        )
        
        db.session.add(session)
        db.session.commit()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话"""
        return UserSession.query.filter_by(
            session_id=session_id,
            is_active=True
        ).first()
    
    def get_user_sessions(self, user_id: int, limit: int = 20, offset: int = 0) -> List[UserSession]:
        """获取用户的所有会话"""
        return UserSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(desc(UserSession.created_at)).limit(limit).offset(offset).all()
    
    def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """获取用户的活跃会话（未过期）"""
        return UserSession.query.filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).order_by(desc(UserSession.created_at)).all()
    
    def renew_session(self, session_id: str, days: int = 7) -> bool:
        """续约会话"""
        session = self.get_session(session_id)
        if session:
            session.renew(days)
            db.session.commit()
            return True
        return False
    
    def deactivate_session(self, session_id: str) -> bool:
        """停用会话"""
        session = UserSession.query.filter_by(session_id=session_id).first()
        if session:
            session.is_active = False
            session.expires_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    def deactivate_all_sessions(self, user_id: int) -> int:
        """停用用户的所有会话"""
        sessions = UserSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        count = 0
        for session in sessions:
            session.is_active = False
            session.expires_at = datetime.utcnow()
            count += 1
        
        if count > 0:
            db.session.commit()
        
        return count
    
    # ==================== 聊天历史管理 ====================
    
    def save_message(self, user_id: int, session_id: str, message_type: str, 
                    content: str, context: Optional[str] = None, 
                    response_time: Optional[float] = None, metadata: Optional[Dict] = None) -> ChatHistory:
        """保存聊天消息"""
        message = ChatHistory(
            user_id=user_id,
            session_id=session_id,
            message_type=message_type,
            content=content,
            context=context,
            response_time=response_time
        )
        
        # 如果有元数据，可以存储在context中
        if metadata:
            if context:
                try:
                    context_data = json.loads(context)
                    context_data['metadata'] = metadata
                    message.context = json.dumps(context_data, ensure_ascii=False)
                except:
                    # 如果解析失败，创建新的context
                    message.context = json.dumps({'metadata': metadata}, ensure_ascii=False)
            else:
                message.context = json.dumps({'metadata': metadata}, ensure_ascii=False)
        
        db.session.add(message)
        db.session.commit()
        
        return message
    
    def get_session_messages(self, session_id: str, limit: int = 100, 
                            offset: int = 0, message_type: Optional[str] = None) -> List[ChatHistory]:
        """获取会话的所有消息"""
        query = ChatHistory.query.filter_by(session_id=session_id)
        
        if message_type:
            query = query.filter_by(message_type=message_type)
        
        return query.order_by(asc(ChatHistory.created_at)).limit(limit).offset(offset).all()
    
    def get_user_messages(self, user_id: int, limit: int = 100, 
                         offset: int = 0, session_id: Optional[str] = None) -> List[ChatHistory]:
        """获取用户的所有消息"""
        query = ChatHistory.query.filter_by(user_id=user_id)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        return query.order_by(desc(ChatHistory.created_at)).limit(limit).offset(offset).all()
    
    def search_messages(self, user_id: int, query_text: str, limit: int = 50) -> List[ChatHistory]:
        """搜索用户的聊天消息"""
        return ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.content.like(f'%{query_text}%')
            )
        ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
    
    def get_message_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """获取用户的消息统计"""
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # 总消息数
        total_messages = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.created_at >= from_date
            )
        ).count()
        
        # 用户消息数
        user_messages = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.message_type == 'user',
                ChatHistory.created_at >= from_date
            )
        ).count()
        
        # 助手消息数
        assistant_messages = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.message_type == 'assistant',
                ChatHistory.created_at >= from_date
            )
        ).count()
        
        # 平均响应时间
        avg_response_time = db.session.query(
            db.func.avg(ChatHistory.response_time)
        ).filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.message_type == 'assistant',
                ChatHistory.response_time.isnot(None),
                ChatHistory.created_at >= from_date
            )
        ).scalar() or 0
        
        return {
            'total_messages': total_messages,
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'avg_response_time': round(avg_response_time, 2),
            'period_days': days
        }
    
    def delete_message(self, message_id: int, user_id: int) -> bool:
        """删除消息"""
        message = ChatHistory.query.filter_by(id=message_id, user_id=user_id).first()
        if message:
            db.session.delete(message)
            db.session.commit()
            return True
        return False
    
    def delete_session_messages(self, session_id: str, user_id: int) -> int:
        """删除会话的所有消息"""
        messages = ChatHistory.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).all()
        
        count = len(messages)
        for message in messages:
            db.session.delete(message)
        
        if count > 0:
            db.session.commit()
        
        return count
    
    # ==================== 导出和导入 ====================
    
    def export_session_data(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """导出会话数据"""
        session = self.get_session(session_id)
        if not session or session.user_id != user_id:
            return None
        
        messages = self.get_session_messages(session_id, limit=1000)
        
        return {
            'session': {
                'session_id': session.session_id,
                'created_at': session.created_at.isoformat(),
                'ip_address': session.ip_address,
                'user_agent': session.user_agent
            },
            'messages': [
                {
                    'id': msg.id,
                    'message_type': msg.message_type,
                    'content': msg.content,
                    'context': msg.context,
                    'response_time': msg.response_time,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in messages
            ],
            'exported_at': datetime.utcnow().isoformat(),
            'total_messages': len(messages)
        }
    
    def export_user_data(self, user_id: int, limit_sessions: int = 10) -> Dict[str, Any]:
        """导出用户数据"""
        sessions = self.get_user_sessions(user_id, limit=limit_sessions)
        
        data = {
            'user_id': user_id,
            'sessions': [],
            'exported_at': datetime.utcnow().isoformat()
        }
        
        for session in sessions:
            session_data = self.export_session_data(session.session_id, user_id)
            if session_data:
                data['sessions'].append(session_data)
        
        return data
    
    # ==================== 辅助方法 ====================
    
    def _cleanup_expired_sessions(self):
        """清理过期的会话"""
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
        
        if expired_sessions:
            db.session.commit()
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话摘要"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # 获取会话中的消息
        messages = self.get_session_messages(session_id, limit=10)
        
        # 计算统计信息
        total_messages = ChatHistory.query.filter_by(session_id=session_id).count()
        user_messages = ChatHistory.query.filter_by(
            session_id=session_id, 
            message_type='user'
        ).count()
        
        # 获取第一条和最后一条消息
        first_message = ChatHistory.query.filter_by(
            session_id=session_id
        ).order_by(asc(ChatHistory.created_at)).first()
        
        last_message = ChatHistory.query.filter_by(
            session_id=session_id
        ).order_by(desc(ChatHistory.created_at)).first()
        
        return {
            'session_id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'total_messages': total_messages,
            'user_messages': user_messages,
            'assistant_messages': total_messages - user_messages,
            'first_message_time': first_message.created_at.isoformat() if first_message else None,
            'last_message_time': last_message.created_at.isoformat() if last_message else None,
            'recent_messages': [
                {
                    'type': msg.message_type,
                    'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                    'time': msg.created_at.isoformat()
                }
                for msg in messages[:5]
            ]
        }


# 创建全局实例
session_manager = SessionManager()