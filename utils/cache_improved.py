#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的缓存模块
支持Redis和内存缓存两种模式，自动降级
"""

import json
import time
import threading
from typing import Any, Optional, Dict
import pickle

from utils.logger import logger

# 尝试导入Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis模块未安装，将使用内存缓存")

# 配置
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_TIMEOUT = 5  # 连接超时时间（秒）

# 内存缓存配置
MEMORY_CACHE_MAX_SIZE = 1000  # 最大缓存条目数
MEMORY_CACHE_CLEANUP_THRESHOLD = 0.8  # 清理阈值（当达到80%时清理过期条目）


class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                # 检查是否过期
                if entry['expire'] > 0 and time.time() > entry['expire']:
                    del self.cache[key]
                    self.miss_count += 1
                    return None
                
                self.hit_count += 1
                return entry['value']
            
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存值"""
        with self.lock:
            # 如果缓存已满，清理过期条目
            if len(self.cache) >= MEMORY_CACHE_MAX_SIZE * MEMORY_CACHE_CLEANUP_THRESHOLD:
                self._cleanup()
            
            # 如果仍然满，删除最旧的条目
            if len(self.cache) >= MEMORY_CACHE_MAX_SIZE:
                self._remove_oldest()
            
            expire_time = time.time() + expire if expire > 0 else 0
            self.cache[key] = {
                'value': value,
                'expire': expire_time,
                'timestamp': time.time()
            }
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> int:
        """清空缓存"""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            return count
    
    def _cleanup(self):
        """清理过期条目"""
        current_time = time.time()
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            if entry['expire'] > 0 and current_time > entry['expire']:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
        
        if keys_to_delete:
            logger.debug(f"内存缓存清理了 {len(keys_to_delete)} 个过期条目")
    
    def _remove_oldest(self):
        """删除最旧的条目"""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.items(), key=lambda x: x[1]['timestamp'])[0]
        del self.cache[oldest_key]
        logger.debug(f"内存缓存删除了最旧的条目: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total * 100 if total > 0 else 0
            
            # 计算有效条目数
            valid_count = 0
            current_time = time.time()
            for entry in self.cache.values():
                if entry['expire'] == 0 or current_time <= entry['expire']:
                    valid_count += 1
            
            return {
                'size': len(self.cache),
                'valid_entries': valid_count,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'max_size': MEMORY_CACHE_MAX_SIZE
            }


class HybridCache:
    """混合缓存：优先使用Redis，失败时降级到内存缓存"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = MemoryCache()
        self.use_redis = False
        self._init_redis()
        
    def _init_redis(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            logger.info("Redis模块不可用，使用内存缓存")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                socket_timeout=REDIS_TIMEOUT,
                socket_connect_timeout=REDIS_TIMEOUT,
                decode_responses=False  # 不自动解码，以便处理二进制数据
            )
            
            # 测试连接
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis连接成功，使用Redis缓存")
            
        except Exception as e:
            self.redis_client = None
            self.use_redis = False
            logger.warning(f"Redis连接失败，降级到内存缓存: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 先尝试Redis
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    try:
                        # 尝试JSON解码
                        return json.loads(value.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # 如果JSON解码失败，尝试pickle解码
                        try:
                            return pickle.loads(value)
                        except:
                            # 如果都失败，返回原始字节
                            return value
                return None
            except Exception as e:
                logger.warning(f"Redis获取失败，降级到内存缓存: {e}")
                self.use_redis = False
        
        # 降级到内存缓存
        return self.memory_cache.get(key)
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存值"""
        # 先尝试Redis
        if self.use_redis and self.redis_client:
            try:
                # 根据值类型选择序列化方式
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    serialized = json.dumps(value, ensure_ascii=False).encode('utf-8')
                else:
                    # 对于其他类型（如bytes），使用pickle
                    serialized = pickle.dumps(value)
                
                if expire > 0:
                    self.redis_client.setex(key, expire, serialized)
                else:
                    self.redis_client.set(key, serialized)
                
                # 同时更新内存缓存（作为本地缓存）
                self.memory_cache.set(key, value, min(expire, 300))  # 内存缓存最多5分钟
                return True
            except Exception as e:
                logger.warning(f"Redis设置失败，降级到内存缓存: {e}")
                self.use_redis = False
        
        # 降级到内存缓存
        return self.memory_cache.set(key, value, expire)
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        success = False
        
        # 删除Redis中的缓存
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
                success = True
            except Exception as e:
                logger.warning(f"Redis删除失败: {e}")
        
        # 删除内存中的缓存
        memory_success = self.memory_cache.delete(key)
        
        return success or memory_success
    
    def clear(self, prefix: str = None) -> Dict[str, int]:
        """清空缓存"""
        result = {'redis': 0, 'memory': 0}
        
        # 清空Redis缓存
        if self.use_redis and self.redis_client:
            try:
                if prefix:
                    # 删除指定前缀的键
                    keys = self.redis_client.keys(f"{prefix}*")
                    if keys:
                        self.redis_client.delete(*keys)
                        result['redis'] = len(keys)
                else:
                    # 清空整个数据库
                    self.redis_client.flushdb()
                    result['redis'] = -1  # 表示清空了整个数据库
            except Exception as e:
                logger.warning(f"Redis清空失败: {e}")
        
        # 清空内存缓存
        if prefix:
            # 删除指定前缀的键
            keys_to_delete = []
            with self.memory_cache.lock:
                for key in list(self.memory_cache.cache.keys()):
                    if key.startswith(prefix):
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del self.memory_cache.cache[key]
                
                result['memory'] = len(keys_to_delete)
        else:
            result['memory'] = self.memory_cache.clear()
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            'mode': 'redis' if self.use_redis else 'memory',
            'redis_available': self.use_redis
        }
        
        # 添加内存缓存统计
        memory_stats = self.memory_cache.get_stats()
        stats.update({'memory_' + k: v for k, v in memory_stats.items()})
        
        # 添加Redis统计（如果可用）
        if self.use_redis and self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats['redis'] = {
                    'used_memory': redis_info.get('used_memory_human', 'N/A'),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0)
                }
            except Exception as e:
                stats['redis_error'] = str(e)
        
        return stats


# 创建全局缓存实例
cache = HybridCache()


# 兼容旧接口的函数
def get_cache(key: str) -> Optional[Any]:
    """获取缓存值（兼容旧接口）"""
    return cache.get(key)


def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """设置缓存值（兼容旧接口）"""
    return cache.set(key, value, expire)


def delete_cache(key: str) -> bool:
    """删除缓存值"""
    return cache.delete(key)


def clear_cache(prefix: str = None) -> Dict[str, int]:
    """清空缓存"""
    return cache.clear(prefix)


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return cache.get_stats()


if __name__ == "__main__":
    # 测试缓存功能
    print("测试缓存功能...")
    
    # 测试设置和获取
    test_key = "test:key"
    test_value = {"name": "测试", "value": 123}
    
    print(f"设置缓存: {test_key} = {test_value}")
    set_cache(test_key, test_value, expire=60)
    
    print(f"获取缓存: {test_key}")
    cached_value = get_cache(test_key)
    print(f"获取结果: {cached_value}")
    
    # 测试统计信息
    stats = get_cache_stats()
    print(f"\n缓存统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")