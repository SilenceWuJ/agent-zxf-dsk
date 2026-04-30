#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速LLM服务 - 优化版本
- 减少响应时间
- 优化提示词
- 快速降级
"""

import requests
import time
import json
from typing import List, Dict, Any
from config import DEEPSEEK_API_KEY, DEEPSEEK_URL
from utils.logger import logger


class FastLLMService:
    """快速LLM服务类"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_URL
        self.timeout = 12  # 超时时间（秒）
        self.max_tokens = 400  # 减少生成token数
        
        # 优化的系统提示词 - 更简洁
        self.system_prompt = """你是AI张老师，高考与考研志愿规划专家。

核心特点：
1. 直接务实，以就业为导向
2. 幽默风趣，但不夸张
3. 用具体案例说明问题

表达要求：
- 语气坚定，结论明确
- 常用"我跟你说啊"、"你记住"开头
- **禁止使用动作描述**（如拍桌子、扶眼镜等）
- **禁止使用括号描述动作**
- 回答简洁，控制在200-300字内"""
    
    def ask_llm(self, question: str, context: str, history: List[Dict] = None) -> str:
        """
        快速调用LLM生成回答
        
        Args:
            question: 用户问题
            context: 知识库上下文
            history: 对话历史
            
        Returns:
            LLM生成的回答（快速返回）
        """
        if not self.api_key:
            logger.error("DeepSeek API密钥未配置")
            return self._get_fallback_answer(question)
        
        start_time = time.time()
        
        try:
            logger.info(f"快速调用DeepSeek: {question[:30]}...")
            
            # 构建简洁的消息
            messages = self._build_concise_messages(question, context, history)
            
            payload = {
                "model": "deepseek-v4-pro",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = self._extract_answer(result)
                
                # 后处理：确保没有动作描述
                answer = self._clean_answer(answer)
                
                logger.info(f"DeepSeek调用成功: 耗时 {duration:.2f}s, 长度 {len(answer)}")
                
                # 如果响应时间过长，记录警告
                if duration > 8:
                    logger.warning(f"DeepSeek响应时间较长: {duration:.2f}s")
                
                return answer
            else:
                logger.warning(f"DeepSeek调用失败: HTTP {response.status_code}, 耗时 {duration:.2f}s")
                return self._get_fallback_answer(question)
                
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            logger.warning(f"DeepSeek调用超时: 耗时 {duration:.2f}s")
            return "我跟你说啊，这个问题需要点时间思考。要不你先问问别的？"
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"DeepSeek调用异常: {e}, 耗时 {duration:.2f}s")
            return self._get_fallback_answer(question)
    
    def _build_concise_messages(self, question: str, context: str, history: List[Dict] = None) -> List[Dict]:
        """构建简洁的消息列表"""
        messages = []
        
        # 添加系统提示
        messages.append({"role": "system", "content": self.system_prompt})
        
        # 添加有限的历史（最多3轮）
        if history:
            recent_history = history[-6:]  # 最多6条消息（3轮对话）
            messages.extend(recent_history)
        
        # 构建简洁的用户消息
        user_content = f"问题：{question}\n"
        
        if context and context.strip():
            # 截断上下文，避免过长
            short_context = context[:300] + "..." if len(context) > 300 else context
            user_content += f"\n参考信息：{short_context}\n"
            user_content += "请基于参考信息回答。"
        else:
            user_content += "请直接回答。"
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    def _extract_answer(self, result: Dict[str, Any]) -> str:
        """从API响应中提取回答"""
        try:
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
            
            return "抱歉，暂时无法生成回答。"
            
        except Exception as e:
            logger.error(f"提取回答失败: {e}")
            return "抱歉，暂时无法生成回答。"
    
    def _clean_answer(self, answer: str) -> str:
        """清理回答，移除动作描述"""
        if not answer:
            return answer
        
        import re
        
        # 移除括号中的动作描述
        answer = re.sub(r'\([^)]*(拍|扶|敲|写|站|坐|走|笑|看|说|指)[^)]*\)', '', answer)
        
        # 移除常见动作描述
        actions = [
            '一拍桌子', '扶了扶眼镜', '敲了敲黑板', '写在白板上',
            '站起来说', '坐下来说', '笑着说', '认真地说',
            '指着说', '拿着粉笔', '放下手中的'
        ]
        
        for action in actions:
            answer = answer.replace(action, '')
        
        # 移除多余的空格和换行
        answer = re.sub(r'\s+', ' ', answer)
        answer = answer.strip()
        
        return answer
    
    def _get_fallback_answer(self, question: str) -> str:
        """获取快速备用回答"""
        # 更简洁的备用回答
        if any(keyword in question for keyword in ["计算机", "软件", "编程"]):
            return "计算机专业就业前景很好，但竞争也激烈。关键要把技术学扎实。"
        elif any(keyword in question for keyword in ["考研", "研究生"]):
            return "考研要提前规划，选对专业和导师很重要。"
        elif any(keyword in question for keyword in ["就业", "工作"]):
            return "就业要看行业趋势和个人技能，学历只是敲门砖。"
        else:
            return "我是AI张老师，专门解答高考志愿和考研问题。有什么具体想了解的吗？"
    
    def quick_ask(self, question: str, context: str = "", history: List[Dict] = None) -> str:
        """
        超快速提问 - 8秒内必须返回
        
        Args:
            question: 用户问题
            context: 知识库上下文
            history: 对话历史
            
        Returns:
            快速回答
        """
        start_time = time.time()
        
        try:
            # 设置更短的超时
            original_timeout = self.timeout
            self.timeout = 8
            
            result = self.ask_llm(question, context, history)
            
            duration = time.time() - start_time
            if duration > 7.5:
                logger.warning(f"快速提问接近超时: {duration:.2f}s")
            
            # 恢复原始超时设置
            self.timeout = original_timeout
            
            return result
            
        except Exception as e:
            logger.error(f"快速提问异常: {e}")
            return "问题有点复杂，让我再想想。"


# 创建全局实例
fast_llm_service = FastLLMService()


# 兼容接口
def ask_llm(question: str, context: str, history: List[Dict] = None) -> str:
    """调用LLM生成回答（兼容接口）"""
    return fast_llm_service.ask_llm(question, context, history)


def quick_ask(question: str, context: str = "", history: List[Dict] = None) -> str:
    """快速调用LLM生成回答"""
    return fast_llm_service.quick_ask(question, context, history)


if __name__ == "__main__":
    # 测试快速LLM服务
    print("测试快速LLM服务...")
    
    test_cases = [
        {
            "question": "计算机专业就业前景怎么样？",
            "context": "计算机专业涉及多个方向，就业前景广阔。",
            "history": []
        },
        {
            "question": "普通家庭学什么专业好？",
            "context": "",
            "history": []
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试:")
        print(f"   问题: {test_case['question']}")
        
        # 测试快速提问
        print("   1. 快速提问测试:")
        start_time = time.time()
        answer = quick_ask(test_case["question"], test_case["context"], test_case["history"])
        duration = time.time() - start_time
        
        print(f"     耗时: {duration:.2f}s")
        print(f"     回答: {answer[:80]}...")
        
        # 测试普通提问
        print("   2. 普通提问测试:")
        start_time = time.time()
        answer = ask_llm(test_case["question"], test_case["context"], test_case["history"])
        duration = time.time() - start_time
        
        print(f"     耗时: {duration:.2f}s")
        print(f"     回答长度: {len(answer)} 字符")