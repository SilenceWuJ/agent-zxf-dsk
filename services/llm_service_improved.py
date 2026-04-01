#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改进的LLM服务
- 优化的提示词
- 更好的错误处理
- 性能优化
"""

import requests
import time
import json
from typing import List, Dict, Any, Optional
from config import DEEPSEEK_API_KEY, DEEPSEEK_URL
from utils.logger import logger
from utils.performance import time_it


class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_URL
        self.timeout = 20  # 超时时间（秒）
        self.max_retries = 2  # 最大重试次数
        self.max_tokens = 800  # 最大生成token数
        
        # 优化的系统提示词
        self.system_prompt = """你是AI张老师，基于张雪峰风格的高考与考研志愿规划专家。

核心特点：
1. **直接务实**：以就业为导向，帮助考生找到有专业壁垒、适合普通家庭投入的方向
2. **幽默风趣**：说话生动有趣，但不过度夸张
3. **案例丰富**：用具体案例和对比说明问题
4. **立场鲜明**：对普通家庭孩子要务实，对富裕家庭可以谈兴趣和长远发展

表达要求：
- 语气坚定，结论明确
- 常用"我跟你说啊"、"你记住"、"我告诉你"开头
- 适当使用东北口音词汇（如"整"、"老好了"）
- **禁止使用动作描述**（如拍桌子、扶眼镜、敲黑板、写白板等）
- **禁止使用括号描述动作**（如（一拍桌子）、（扶了扶眼镜）等）
- 只使用语言表达，不要描述肢体动作

回答规则：
1. 基于提供的知识库信息回答
2. 如果知识库信息不足，基于自身知识回答
3. 保持回答简洁明了，重点突出
4. 每个回答控制在300-500字以内"""
    
    @time_it
    def ask_llm(self, question: str, context: str, history: List[Dict] = None) -> str:
        """
        调用LLM生成回答
        
        Args:
            question: 用户问题
            context: 知识库上下文
            history: 对话历史
            
        Returns:
            LLM生成的回答
        """
        if not self.api_key:
            logger.error("DeepSeek API密钥未配置")
            return "抱歉，AI张老师暂时无法回答。请检查API配置。"
        
        # 构建消息列表
        messages = self._build_messages(question, context, history)
        
        # 构建请求载荷
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"调用DeepSeek API (尝试 {attempt + 1}/{self.max_retries + 1}): {question[:50]}...")
                
                start_time = time.time()
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
                    
                    # 后处理：移除可能残留的动作描述
                    answer = self._post_process_answer(answer)
                    
                    logger.info(f"DeepSeek API调用成功: 耗时 {duration:.2f}s, 回答长度 {len(answer)}")
                    logger.debug(f"回答预览: {answer[:100]}...")
                    
                    return answer
                else:
                    logger.warning(f"DeepSeek API调用失败 (尝试 {attempt + 1}): HTTP {response.status_code}")
                    logger.debug(f"错误响应: {response.text[:200]}")
                    
                    if attempt == self.max_retries:
                        return self._get_fallback_answer(question)
                    
                    # 重试前等待
                    wait_time = 1 * (attempt + 1)
                    logger.info(f"等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    
            except requests.exceptions.Timeout:
                logger.warning(f"DeepSeek API调用超时 (尝试 {attempt + 1})")
                if attempt == self.max_retries:
                    return "抱歉，AI张老师思考时间太长了。请稍后再试或简化您的问题。"
                
                wait_time = 1 * (attempt + 1)
                logger.info(f"等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"DeepSeek API调用异常 (尝试 {attempt + 1}): {e}")
                if attempt == self.max_retries:
                    return self._get_fallback_answer(question)
                
                wait_time = 1 * (attempt + 1)
                logger.info(f"等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
        
        # 所有尝试都失败
        return self._get_fallback_answer(question)
    
    def _build_messages(self, question: str, context: str, history: List[Dict] = None) -> List[Dict]:
        """构建消息列表"""
        messages = []
        
        # 添加系统提示
        messages.append({"role": "system", "content": self.system_prompt})
        
        # 添加历史对话
        if history:
            # 只保留最近5轮对话，避免token过多
            recent_history = history[-10:]  # 最多10条消息
            messages.extend(recent_history)
        
        # 构建用户消息
        user_content = f"用户问题：{question}\n\n"
        
        if context and context.strip():
            user_content += f"相关参考信息：\n{context}\n\n"
            user_content += "请基于以上参考信息，用AI张老师的风格回答用户问题。"
        else:
            user_content += "请用AI张老师的风格回答用户问题。"
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    def _extract_answer(self, result: Dict[str, Any]) -> str:
        """从API响应中提取回答"""
        try:
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()
            
            # 尝试其他格式
            if "output" in result and "text" in result["output"]:
                return result["output"]["text"].strip()
            
            logger.warning(f"未知的响应格式: {json.dumps(result, ensure_ascii=False)[:200]}...")
            return "抱歉，AI张老师暂时无法生成回答。"
            
        except Exception as e:
            logger.error(f"提取回答失败: {e}")
            return "抱歉，AI张老师暂时无法生成回答。"
    
    def _post_process_answer(self, answer: str) -> str:
        """后处理回答，移除动作描述"""
        if not answer:
            return answer
        
        # 移除括号中的动作描述
        import re
        
        # 移除 (拍桌子)、(扶眼镜)、(敲黑板) 等动作描述
        answer = re.sub(r'\([^)]*(拍|扶|敲|写|站|坐|走|笑|看|说|指|拿|放)[^)]*\)', '', answer)
        
        # 移除其他常见动作描述
        action_patterns = [
            r'一拍桌子', r'扶了扶眼镜', r'敲了敲黑板', r'写在白板上',
            r'站起来说', r'坐下来说', r'笑着说', r'认真地说',
            r'指着说', r'拿着粉笔', r'放下手中的'
        ]
        
        for pattern in action_patterns:
            answer = answer.replace(pattern, '')
        
        # 移除多余的空格和换行
        answer = re.sub(r'\n\s*\n', '\n\n', answer)  # 多个空行合并为一个
        answer = answer.strip()
        
        return answer
    
    def _get_fallback_answer(self, question: str) -> str:
        """获取备用回答"""
        # 根据问题类型返回不同的备用回答
        if any(keyword in question for keyword in ["计算机", "软件", "编程", "代码"]):
            return "计算机专业是目前就业前景最好的方向之一。我跟你说啊，这行虽然竞争激烈，但机会也多。关键是得把技术学扎实，别光学理论不实践。"
        elif any(keyword in question for keyword in ["考研", "研究生", "硕士"]):
            return "考研这事儿得提前规划。你记住，选对专业和导师比考高分更重要。普通家庭的孩子更要考虑投入产出比。"
        elif any(keyword in question for keyword in ["就业", "工作", "薪资"]):
            return "就业前景得看行业趋势和个人能力。我告诉你，现在企业更看重实际技能，学历只是敲门砖。"
        else:
            return "这个问题问得好！我是专门帮助大家解决高考志愿、考研选择和职业规划问题的AI张老师。你有什么具体想了解的专业或院校吗？"
    
    def test_connection(self) -> bool:
        """测试API连接"""
        if not self.api_key:
            logger.error("DeepSeek API密钥未配置")
            return False
        
        try:
            test_payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个测试助手，请简单回复'测试成功'。"},
                    {"role": "user", "content": "你好，请回复'测试成功'"}
                ],
                "max_tokens": 10
            }
            
            response = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("DeepSeek API连接测试成功")
                return True
            else:
                logger.error(f"DeepSeek API连接测试失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"DeepSeek API连接测试异常: {e}")
            return False


# 创建全局实例
llm_service = LLMService()


# 兼容旧接口的函数
def ask_llm(question: str, context: str, history: List[Dict] = None) -> str:
    """调用LLM生成回答（兼容旧接口）"""
    return llm_service.ask_llm(question, context, history)


if __name__ == "__main__":
    # 测试LLM服务
    print("测试LLM服务...")
    
    # 测试连接
    print("测试API连接...")
    if llm_service.test_connection():
        print("✅ API连接成功")
    else:
        print("❌ API连接失败")
    
    # 测试生成
    test_cases = [
        {
            "question": "计算机专业就业前景怎么样？",
            "context": "计算机专业涉及软件开发、人工智能、数据分析等多个方向，就业前景广阔。",
            "history": []
        },
        {
            "question": "普通家庭学什么专业好？",
            "context": "",
            "history": []
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试生成:")
        print(f"   问题: {test_case['question']}")
        print(f"   上下文: {test_case['context'][:50]}..." if test_case['context'] else "   上下文: 无")
        
        start_time = time.time()
        answer = llm_service.ask_llm(
            test_case["question"],
            test_case["context"],
            test_case["history"]
        )
        duration = time.time() - start_time
        
        print(f"   耗时: {duration:.2f}s")
        print(f"   回答长度: {len(answer)} 字符")
        print(f"   回答预览: {answer[:100]}...")