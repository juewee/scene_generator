"""
场景生成系统 - AI客户端模块

封装DeepSeek API调用，提供场景生成所需的AI能力
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx


@dataclass
class AIConfig:
    """AI配置"""
    api_key: str = "sk-41b5fa62f0a445bea376f5852ed686c2"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0


class AIClient:
    """
    DeepSeek AI客户端
    
    封装API调用，支持同步和异步模式
    """
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig()
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_request_body(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求体"""
        return {
            "model": kwargs.get("model", self.config.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取JSON块
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    return json.loads(content[start:end].strip())
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    return json.loads(content[start:end].strip())
            
            # 尝试找到JSON对象
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
            
            raise ValueError(f"无法解析JSON响应: {content[:200]}...")
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步调用AI对话
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数（model, temperature, max_tokens等）
        
        Returns:
            解析后的JSON响应
        """
        url = f"{self.config.base_url}/v1/chat/completions"
        body = self._build_request_body(messages, **kwargs)
        
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(url, headers=self.headers, json=body)
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        return self._parse_json_response(content)
    
    async def chat_async(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        异步调用AI对话
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数
        
        Returns:
            解析后的JSON响应
        """
        url = f"{self.config.base_url}/v1/chat/completions"
        body = self._build_request_body(messages, **kwargs)
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, headers=self.headers, json=body)
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        return self._parse_json_response(content)


class SceneAIPrompts:
    """
    场景生成AI提示词模板
    
    提供各种场景生成任务的提示词模板
    """
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return """你是一个专业的场景设计师，负责根据剧本和场景需求生成详细的场景元素。

你的任务是根据给定的上下文信息，生成场景中的物品和容器节点。

## 节点类型说明

1. **物品节点 (item)**: 末端节点，不可再分的基础元素
   - 例如：苹果、杯子、书本、钥匙、手机、钱包等
   - 这些物品通常不会再包含其他物品

2. **容器节点 (container)**: 可包含其他节点的元素
   - **物理容器**: 桌子、抽屉、房间、柜子、箱子、书架等
   - **人物容器**: 人物可以携带物品、穿着衣物、持有道具
   - **抽象容器**: 想法、计划、系统、概念等

## 判断规则

1. 如果一个元素可能包含其他物品，则标记为容器节点
2. 人物默认可以作为容器节点（可以携带物品、穿着衣物）
3. 家具类（桌子、柜子、床等）通常是容器节点
4. 小型物品（杯子、笔、手机等）通常是物品节点
5. 根据场景主题判断是否需要展开容器

## 输出格式

请严格按照JSON格式输出，不要添加任何额外文字。

```json
{
  "nodes": [
    {
      "name": "节点名称",
      "node_type": "item 或 container",
      "container_type": "physical/character/abstract（仅容器节点需要）",
      "description": "详细描述",
      "position": "位置描述",
      "attributes": {
        "material": "材质",
        "color": "颜色",
        "size": "大小",
        "condition": "状态"
      },
      "should_expand": true/false（容器节点是否需要展开）
    }
  ],
  "reasoning": "生成这些节点的理由"
}
```"""

    @staticmethod
    def get_initial_generation_prompt(context: str) -> str:
        """获取初始生成提示词"""
        return f"""请根据以下场景上下文，生成场景中的主要元素节点。

{context}

请生成场景中的主要物品和容器节点。注意：
1. 根据场景需求合理分配物品和容器
2. 考虑时代背景和场景氛围
3. 人物可以作为容器节点
4. 标记容器节点是否需要进一步展开

请直接输出JSON格式的结果。"""

    @staticmethod
    def get_container_expansion_prompt(
        container_name: str,
        container_type: str,
        container_description: str,
        parent_theme: str,
        level: int,
        context: str
    ) -> str:
        """获取容器展开提示词"""
        return f"""请展开以下容器节点的内部内容。

## 容器信息
- 名称: {container_name}
- 类型: {container_type}
- 描述: {container_description}
- 当前层级: {level}
- 父级主题: {parent_theme}

## 场景上下文
{context}

## 展开规则
1. 层级深度为 {level}，最大深度建议不超过5层
2. 根据容器类型和主题决定展开内容
3. 如果层级较深（>=4），尽量生成物品节点而非容器
4. 内容要符合场景的时代背景和氛围
5. 如果容器内容对场景不重要，可以返回空节点列表

请生成该容器内部的物品和容器节点，直接输出JSON格式。"""

    @staticmethod
    def get_parallel_expansion_prompt(
        containers: List[Dict[str, Any]],
        context: str
    ) -> str:
        """获取并行展开提示词（批量处理多个容器）"""
        containers_info = "\n".join([
            f"- {c['name']} (类型: {c['container_type']}, 层级: {c['level']}, 主题: {c['theme']})"
            for c in containers
        ])
        
        return f"""请批量展开以下容器节点的内部内容。

## 待展开容器列表
{containers_info}

## 场景上下文
{context}

## 输出格式
请为每个容器生成内部节点，输出格式如下：

```json
{{
  "expansions": [
    {{
      "container_name": "容器名称",
      "nodes": [
        {{
          "name": "节点名称",
          "node_type": "item 或 container",
          ...
        }}
      ]
    }}
  ]
}}
请直接输出JSON格式的结果。"""

    @staticmethod
    def get_round_summary_prompt(
        round_num: int,
        current_nodes: List[Dict[str, Any]],
        context: str,
        previous_summary: str = ""
    ) -> str:
        """获取轮次总结提示词"""
        
        # 格式化当前节点结构
        nodes_summary = []
        for node in current_nodes:
            node_type_display = "📦 容器" if node.get('node_type') == 'container' else "📄 物品"
            container_type = f"({node.get('container_type', 'physical')})" if node.get('node_type') == 'container' else ""
            nodes_summary.append(f"- {node_type_display} {node['name']} {container_type} [层级:{node.get('level',0)}]")
        
        nodes_text = "\n".join(nodes_summary) if nodes_summary else "  暂无节点"
        
        return f"""你是一个专业的场景设计师，负责对场景生成过程进行质量控制和优化。
当前状态
轮次: 第 {round_num} 轮

场景上下文: {context}

当前已生成的节点
{nodes_text}

上一轮总结
{previous_summary if previous_summary else "这是第一轮，尚无总结"}

你的任务
请分析当前场景的节点，并回答以下问题：

完整性检查：当前节点是否完整覆盖了场景需求？还缺少哪些关键元素？

合理性检查：节点的层次关系是否合理？是否有节点应该合并或拆分？

冗余检查：哪些节点是多余的、不必要的？（请尽量精简，删除冗余节点）

深度控制：哪些容器应该继续展开（下一轮展开）？哪些应该停止？

优化建议：需要增加什么节点？删除什么节点？修改什么节点？

输出格式
请严格按照JSON格式输出：
```json
{{
  "summary": "本轮总结，简要描述场景生成状态",
  "completeness_score": 0-100的完整性评分,
  "issues_found": [
    "问题1",
    "问题2"
  ],
  "optimization_suggestions": [
    {{
      "action": "add/remove/modify",
      "target_node": "节点名称",
      "suggestion": "具体建议",
      "node_data": {{}}  # 如果是add或modify，提供新的节点数据
    }}
  ],
  "containers_to_expand_next": [
    {{
      "name": "容器名称",
      "reason": "展开理由",
      "priority": 1-5的优先级（5最高）
    }}
  ],
  "containers_to_stop": [
    {{
      "name": "容器名称",
      "reason": "停止理由"
    }}
  ],
  "next_round_focus": "下一轮应该重点关注的方向"
}}
```"""

    @staticmethod
    def get_optimization_prompt(
        optimization_suggestions: List[Dict[str, Any]],
        current_nodes: List[Dict[str, Any]],
        context: str
    ) -> str:
        """获取节点优化提示词"""
        
        suggestions_text = "\n".join([
            f"- {s['action']} {s.get('target_node', '')}: {s['suggestion']}"
            for s in optimization_suggestions
        ])
        
        return f"""请根据优化建议，调整当前场景的节点。

## 场景上下文
{context}

## 优化建议
{suggestions_text}

## 当前节点
{json.dumps(current_nodes, ensure_ascii=False, indent=2)}

## 任务
请根据优化建议，生成调整后的节点列表。可以直接添加新节点、修改现有节点或删除不必要的节点。

## 输出格式
```json
{{
  "updated_nodes": [
    {{
      "name": "节点名称",
      "node_type": "item/container",
      "container_type": "physical/character/abstract（容器需要）",
      "description": "描述",
      "position": "位置",
      "attributes": {{}},
      "should_expand": true/false
    }}
  ]
}}
```"""


class SceneAIClient:
    """
    场景生成专用AI客户端
    
    封装场景生成相关的AI调用
    """
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.client = AIClient(config)
        self.prompts = SceneAIPrompts()
    
    def generate_initial_nodes(self, context: str) -> Dict[str, Any]:
        """
        生成初始场景节点
        
        Args:
            context: 场景上下文描述
        
        Returns:
            包含节点列表的字典
        """
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_initial_generation_prompt(context)}
        ]
        
        return self.client.chat(messages)
    
    async def generate_initial_nodes_async(self, context: str) -> Dict[str, Any]:
        """异步生成初始场景节点"""
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_initial_generation_prompt(context)}
        ]
        
        return await self.client.chat_async(messages)
    
    def expand_container(
        self,
        container_name: str,
        container_type: str,
        container_description: str,
        parent_theme: str,
        level: int,
        context: str
    ) -> Dict[str, Any]:
        """
        展开容器节点
        
        Args:
            container_name: 容器名称
            container_type: 容器类型
            container_description: 容器描述
            parent_theme: 父级主题
            level: 当前层级
            context: 场景上下文
        
        Returns:
            包含子节点列表的字典
        """
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_container_expansion_prompt(
                container_name, container_type, container_description,
                parent_theme, level, context
            )}
        ]
        
        return self.client.chat(messages)
    
    async def expand_container_async(
        self,
        container_name: str,
        container_type: str,
        container_description: str,
        parent_theme: str,
        level: int,
        context: str
    ) -> Dict[str, Any]:
        """异步展开容器节点"""
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_container_expansion_prompt(
                container_name, container_type, container_description,
                parent_theme, level, context
            )}
        ]
        
        return await self.client.chat_async(messages)
    
    async def expand_containers_parallel_async(
        self,
        containers: List[Dict[str, Any]],
        context: str
    ) -> Dict[str, Any]:
        """
        并行展开多个容器节点
        
        Args:
            containers: 容器信息列表
            context: 场景上下文
        
        Returns:
            包含所有展开结果的字典
        """
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_parallel_expansion_prompt(containers, context)}
        ]
        
        return await self.client.chat_async(messages)
    
    def expand_containers_parallel(
        self,
        containers: List[Dict[str, Any]],
        context: str
    ) -> Dict[str, Any]:
        """同步并行展开多个容器节点"""
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_parallel_expansion_prompt(containers, context)}
        ]
        
        return self.client.chat(messages)
    
    def analyze_round(
        self,
        round_num: int,
        current_nodes: List[Dict[str, Any]],
        context: str,
        previous_summary: str = ""
    ) -> Dict[str, Any]:
        """
        分析当前轮次的结果
        
        Args:
            round_num: 当前轮次
            current_nodes: 当前所有节点（字典格式）
            context: 场景上下文
            previous_summary: 上一轮总结
        
        Returns:
            包含总结和建议的字典
        """
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_round_summary_prompt(
                round_num, current_nodes, context, previous_summary
            )}
        ]
        
        return self.client.chat(messages)
    
    async def analyze_round_async(
        self,
        round_num: int,
        current_nodes: List[Dict[str, Any]],
        context: str,
        previous_summary: str = ""
    ) -> Dict[str, Any]:
        """异步分析当前轮次的结果"""
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_round_summary_prompt(
                round_num, current_nodes, context, previous_summary
            )}
        ]
        
        return await self.client.chat_async(messages)
    
    def optimize_nodes(
        self,
        optimization_suggestions: List[Dict[str, Any]],
        current_nodes: List[Dict[str, Any]],
        context: str
    ) -> Dict[str, Any]:
        """
        根据建议优化节点
        """
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_optimization_prompt(
                optimization_suggestions, current_nodes, context
            )}
        ]
        
        return self.client.chat(messages)
    
    async def optimize_nodes_async(
        self,
        optimization_suggestions: List[Dict[str, Any]],
        current_nodes: List[Dict[str, Any]],
        context: str
    ) -> Dict[str, Any]:
        """异步优化节点"""
        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": self.prompts.get_optimization_prompt(
                optimization_suggestions, current_nodes, context
            )}
        ]
        
        return await self.client.chat_async(messages)