from __future__ import annotations

import os
import time
import requests  
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class LLMGenerator:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        base = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
        self.base_url = base.rstrip("/")
        self.model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")
        self.timeout = int(os.getenv("LLM_TIMEOUT", "20"))

    def generate(self, query: str, context: List[Dict[str, Any]]) -> str:
        # --- Mock / 降级检查 ---
        # 如果 Key 是空的，或者包含 mock 字样，直接跳过网络请求
        if not self.api_key or "mock" in self.api_key.lower():
            return self._mock_generate(context, error_msg="未配置API Key")

        # --- 构建 Prompt ---
        docs_str = ""
        for i, item in enumerate(context):
            q_text = item.get("question", "")
            a_text = item.get("answer", "")
            docs_str += f"【资料{i+1}】\n问题：{q_text}\n答案：{a_text}\n\n"

        system_prompt = (
            "你是一个专业的企业HR智能助手。请严格基于【参考资料】回答用户问题。\n"
            "规则：\n"
            "1. 必须基于提供的资料回答，严禁编造。\n"
            "2) 若资料不足以完全回答，也请基于最相关资料给出“最接近的制度流程/建议”（如事假/年假/病假），并提醒以HR解释为准；只有当资料与问题完全无关时，才回复“当前制度库中未找到相关规定，建议咨询HR”。"
            "3. 回答要条理清晰、语气亲切专业。\n"
            "4. 回答末尾必须标注引用的资料编号，格式如：[引用: 资料1]。"
        )
        
        user_prompt = f"【参考资料】：\n{docs_str}\n【用户问题】：{query}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
            "stream": False
        }

        try:
            t0 = time.time()
            # 这里直接请求 /chat/completions 接口
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            elapsed = time.time() - t0
            
            # 检查 HTTP 状态码
            if response.status_code != 200:
                print(f"[LLM Error] HTTP {response.status_code}: {response.text}")
                return self._mock_generate(context, error_msg=f"服务报错 {response.status_code}")

            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            
            print(f"[LLM Call] Model: {self.model}, Cost: {elapsed:.2f}s")
            return content

        except Exception as e:
            print(f"[LLM Exception] {e}")
            return self._mock_generate(context, error_msg="网络请求超时")

    def _mock_generate(self, context: List[Dict[str, Any]], error_msg: str = "") -> str:
        """兜底生成"""
        if not context:
            return "抱歉，未找到相关制度，建议咨询 HR。"
        
        best = context[0]
        prefix = f"（{error_msg}，已切换至基础模式）" if error_msg else ""
        
        return (
            f"{prefix}根据现有制度规定：\n"
            f"{best.get('answer', '')}\n"
            f"\n[引用: 资料1 (自动匹配)]"
        )

# 单例导出
llm_generator = LLMGenerator()