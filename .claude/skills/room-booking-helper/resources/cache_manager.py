#!/usr/bin/env python3
"""
会议室预订 Skill 缓存管理模块

功能:
  - 缓存城市、建筑、楼层列表数据
  - 缓存其他条件列表 (设备、容量、窗户等)
  - 自动检测缓存是否存在
  - 支持手动清除缓存
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

class CacheManager:
    # 缓存文件路径
    CACHE_DIR = Path(__file__).parent / "cache"
    BUILDINGS_CACHE_FILE = CACHE_DIR / "buildings_cache.json"
    CONDITIONS_CACHE_FILE = CACHE_DIR / "conditions_cache.json"
    
    # 缓存过期时间 (单位: 天)
    CACHE_EXPIRY_DAYS = 7
    
    def __init__(self):
        """初始化缓存管理器"""
        self.CACHE_DIR.mkdir(exist_ok=True)
    
    @staticmethod
    def _get_cache_expiry_time():
        """获取缓存过期时间戳"""
        return int((datetime.now() - timedelta(days=CacheManager.CACHE_EXPIRY_DAYS)).timestamp() * 1000)
    
    def is_buildings_cache_valid(self):
        """检查建筑缓存是否有效"""
        if not self.BUILDINGS_CACHE_FILE.exists():
            return False
        
        try:
            with open(self.BUILDINGS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cached_at = cache_data.get('cached_at', 0)
                return cached_at > self._get_cache_expiry_time()
        except:
            return False
    
    def is_conditions_cache_valid(self):
        """检查条件缓存是否有效"""
        if not self.CONDITIONS_CACHE_FILE.exists():
            return False
        
        try:
            with open(self.CONDITIONS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cached_at = cache_data.get('cached_at', 0)
                return cached_at > self._get_cache_expiry_time()
        except:
            return False
    
    def get_buildings_cache(self):
        """获取建筑缓存数据"""
        if not self.is_buildings_cache_valid():
            return None
        
        try:
            with open(self.BUILDINGS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('data')
        except:
            return None
    
    def get_conditions_cache(self):
        """获取条件缓存数据"""
        if not self.is_conditions_cache_valid():
            return None
        
        try:
            with open(self.CONDITIONS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('data')
        except:
            return None
    
    def save_buildings_cache(self, data):
        """保存建筑缓存数据"""
        try:
            cache_data = {
                'cached_at': int(datetime.now().timestamp() * 1000),
                'data': data
            }
            with open(self.BUILDINGS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存建筑缓存失败: {e}")
            return False
    
    def save_conditions_cache(self, data):
        """保存条件缓存数据"""
        try:
            cache_data = {
                'cached_at': int(datetime.now().timestamp() * 1000),
                'data': data
            }
            with open(self.CONDITIONS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存条件缓存失败: {e}")
            return False
    
    def clear_buildings_cache(self):
        """清除建筑缓存"""
        try:
            if self.BUILDINGS_CACHE_FILE.exists():
                self.BUILDINGS_CACHE_FILE.unlink()
            return True
        except Exception as e:
            print(f"❌ 清除建筑缓存失败: {e}")
            return False
    
    def clear_conditions_cache(self):
        """清除条件缓存"""
        try:
            if self.CONDITIONS_CACHE_FILE.exists():
                self.CONDITIONS_CACHE_FILE.unlink()
            return True
        except Exception as e:
            print(f"❌ 清除条件缓存失败: {e}")
            return False
    
    def clear_all_cache(self):
        """清除所有缓存"""
        self.clear_buildings_cache()
        self.clear_conditions_cache()
        return True
    
    def get_cache_status(self):
        """获取缓存状态"""
        buildings_valid = self.is_buildings_cache_valid()
        conditions_valid = self.is_conditions_cache_valid()
        
        status = {
            'buildings': {
                'valid': buildings_valid,
                'exists': self.BUILDINGS_CACHE_FILE.exists(),
                'path': str(self.BUILDINGS_CACHE_FILE)
            },
            'conditions': {
                'valid': conditions_valid,
                'exists': self.CONDITIONS_CACHE_FILE.exists(),
                'path': str(self.CONDITIONS_CACHE_FILE)
            },
            'expiry_days': self.CACHE_EXPIRY_DAYS
        }
        
        return status


if __name__ == '__main__':
    cache = CacheManager()
    print(json.dumps(cache.get_cache_status(), indent=2, ensure_ascii=False))
