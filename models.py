#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义
使用SQLite作为临时数据库，后续可迁移到MySQL
"""

import os
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# 创建SQLAlchemy实例
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, index=True, nullable=True)
    email = db.Column(db.String(100), unique=True, index=True)
    full_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关系
    sessions = db.relationship('UserSession', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserSession(db.Model):
    """用户会话模型"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关系
    chat_history = db.relationship('ChatHistory', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=7)  # 7天后过期
    
    def is_expired(self):
        """检查会话是否过期"""
        return datetime.utcnow() > self.expires_at
    
    def renew(self, days=7):
        """续约会话"""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.is_active = True
    
    def __repr__(self):
        return f'<UserSession {self.session_id[:8]}...>'

class ChatHistory(db.Model):
    """聊天历史模型"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.String(100), db.ForeignKey('user_sessions.session_id'), nullable=False, index=True)
    message_type = db.Column(db.Enum('user', 'assistant', 'system', name='message_type_enum'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    context = db.Column(db.Text)
    response_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<ChatHistory {self.message_type}: {self.content[:50]}...>'

class VerificationCode(db.Model):
    """短信验证码模型"""
    __tablename__ = 'verification_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_expired(self):
        """检查验证码是否过期"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """检查验证码是否有效（未过期且未使用）"""
        return not self.used and not self.is_expired()
    
    def mark_used(self):
        """标记验证码为已使用"""
        self.used = True
        db.session.commit()
    
    def __repr__(self):
        return f'<VerificationCode {self.phone}:{self.code}>'


def init_db(app):
    """初始化数据库"""
    # 配置数据库 - 支持MySQL和SQLite
    db_uri = os.environ.get('DATABASE_URI')

    if db_uri:
        # 使用环境变量配置（生产环境MySQL）
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    elif os.environ.get('MYSQL_HOST'):
        # 使用MySQL配置
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_password = os.environ.get('MYSQL_PASSWORD', '')
        mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')
        mysql_database = os.environ.get('MYSQL_DATABASE', 'agent_db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4'
    else:
        # 默认使用SQLite（开发环境）
        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 初始化扩展
    db.init_app(app)

    # 创建表
    with app.app_context():
        # 仅SQLite需要启用外键约束
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            from sqlalchemy import event
            @event.listens_for(db.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        db.create_all()

        # 创建测试用户（如果不存在）
        if not User.query.filter_by(username='testuser').first():
            test_user = User(
                username='testuser',
                phone_number='13800138000',
                email='test@example.com',
                full_name='测试用户'
            )
            test_user.set_password('test123')
            db.session.add(test_user)

            admin_user = User(
                username='admin',
                phone_number='13900139000',
                email='admin@example.com',
                full_name='管理员'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)

            db.session.commit()
            print("✅ 测试用户创建成功:")
            print("  用户名: testuser, 密码: test123, 手机: 13800138000")
            print("  用户名: admin, 密码: admin123, 手机: 13900139000")

    return db