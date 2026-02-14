"""
场景生成系统 - 核心生成引擎

实现递归式场景生成逻辑，包括：
- 初始节点生成
- 容器节点递归展开
- 并行处理优化
- 生成过程控制
"""

import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from models import (
    Scene, SceneContext, SceneNode, ItemNode, ContainerNode,
    NodeType, ContainerType, create_node_from_dict
)
from ai_client import SceneAIClient, AIConfig


@dataclass
class GeneratorConfig:
    """生成器配置"""
    max_depth: int = 5                    # 最大递归深度
    max_nodes_per_container: int = 20     # 每个容器最大节点数
    parallel_expansion: bool = True       # 是否启用并行展开
    parallel_batch_size: int = 5          # 并行批次大小
    verbose: bool = True                  # 是否输出详细日志


@dataclass
class GenerationStats:
    """生成统计信息"""
    total_ai_calls: int = 0
    total_nodes_generated: int = 0
    total_containers_expanded: int = 0
    generation_time: float = 0.0
    depth_reached: int = 0


class SceneGenerator:
    """
    场景生成器
    
    核心类，负责协调整个场景生成流程
    """
    
    def __init__(
        self,
        ai_config: Optional[AIConfig] = None,
        generator_config: Optional[GeneratorConfig] = None
    ):
        self.ai_client = SceneAIClient(ai_config)
        self.config = generator_config or GeneratorConfig()
        self.stats = GenerationStats()
        self._log_callback: Optional[Callable] = None
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """设置日志回调函数"""
        self._log_callback = callback
    
    def _log(self, message: str) -> None:
        """输出日志"""
        if self.config.verbose:
            print(f"[SceneGenerator] {message}")
            if self._log_callback:
                self._log_callback(message)
    
    def _generate_node_id(self) -> str:
        """生成节点ID"""
        return str(uuid.uuid4())[:8]
    
    def _create_node_from_ai_response(
        self, 
        node_data: Dict[str, Any],
        level: int = 0,
        parent_path: str = "",
        theme: str = ""
    ) -> SceneNode:
        """从AI响应创建节点对象"""
        node_type = NodeType(node_data.get("node_type", "item"))
        node_id = self._generate_node_id()
        created_at = datetime.now().isoformat()
        
        if node_type == NodeType.ITEM:
            attrs = node_data.get("attributes", {})
            return ItemNode(
                name=node_data.get("name", "未命名物品"),
                node_type=NodeType.ITEM,
                description=node_data.get("description", ""),
                level=level,
                parent_path=parent_path,
                theme=theme,
                position=node_data.get("position"),
                attributes=attrs,
                node_id=node_id,
                created_at=created_at,
                material=attrs.get("material", ""),
                color=attrs.get("color", ""),
                size=attrs.get("size", ""),
                condition=attrs.get("condition", "")
            )
        else:
            container_type_str = node_data.get("container_type", "physical")
            container_type = ContainerType(container_type_str)
            
            return ContainerNode(
                name=node_data.get("name", "未命名容器"),
                node_type=NodeType.CONTAINER,
                description=node_data.get("description", ""),
                level=level,
                parent_path=parent_path,
                theme=theme,
                position=node_data.get("position"),
                attributes=node_data.get("attributes", {}),
                node_id=node_id,
                created_at=created_at,
                container_type=container_type,
                is_expanded=False,
                max_depth=self.config.max_depth
            )
    
    def generate_scene(
        self,
        script: str,
        scene_requirement: str,
        era: str = "现代",
        location: str = "",
        atmosphere: str = "",
        style: str = ""
    ) -> Scene:
        """
        生成完整场景
        
        Args:
            script: 剧本内容
            scene_requirement: 场景需求描述
            era: 时代背景
            location: 地点
            atmosphere: 氛围
            style: 风格
        
        Returns:
            完整的Scene对象
        """
        start_time = datetime.now()
        self.stats = GenerationStats()
        
        # 创建场景上下文
        context = SceneContext(
            script=script,
            scene_requirement=scene_requirement,
            era=era,
            location=location,
            atmosphere=atmosphere,
            style=style
        )
        
        # 创建场景对象
        scene = Scene(
            scene_id=self._generate_node_id(),
            scene_name=f"场景_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            context=context
        )
        
        self._log(f"开始生成场景: {scene.scene_name}")
        self._log(f"剧本: {script[:50]}...")
        self._log(f"场景需求: {scene_requirement}")
        
        # 第一步：生成初始节点
        self._log("=== 第一阶段：生成初始节点 ===")
        initial_nodes = self._generate_initial_nodes(context)
        scene.root_nodes = initial_nodes
        self.stats.total_nodes_generated += len(initial_nodes)
        
        # 第二步：递归展开容器节点
        self._log("=== 第二阶段：递归展开容器节点 ===")
        self._expand_all_containers(scene, context)
        
        # 计算统计信息
        end_time = datetime.now()
        self.stats.generation_time = (end_time - start_time).total_seconds()
        scene.calculate_statistics()
        
        self._log(f"=== 场景生成完成 ===")
        self._log(f"总节点数: {self.stats.total_nodes_generated}")
        self._log(f"展开容器数: {self.stats.total_containers_expanded}")
        self._log(f"AI调用次数: {self.stats.total_ai_calls}")
        self._log(f"生成耗时: {self.stats.generation_time:.2f}秒")
        
        return scene
    
    async def generate_scene_async(
        self,
        script: str,
        scene_requirement: str,
        era: str = "现代",
        location: str = "",
        atmosphere: str = "",
        style: str = ""
    ) -> Scene:
        """异步生成完整场景"""
        start_time = datetime.now()
        self.stats = GenerationStats()
        
        # 创建场景上下文
        context = SceneContext(
            script=script,
            scene_requirement=scene_requirement,
            era=era,
            location=location,
            atmosphere=atmosphere,
            style=style
        )
        
        # 创建场景对象
        scene = Scene(
            scene_id=self._generate_node_id(),
            scene_name=f"场景_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            context=context
        )
        
        self._log(f"开始生成场景: {scene.scene_name}")
        
        # 第一步：异步生成初始节点
        self._log("=== 第一阶段：生成初始节点 ===")
        initial_nodes = await self._generate_initial_nodes_async(context)
        scene.root_nodes = initial_nodes
        self.stats.total_nodes_generated += len(initial_nodes)
        
        # 第二步：异步递归展开容器节点
        self._log("=== 第二阶段：递归展开容器节点 ===")
        await self._expand_all_containers_async(scene, context)
        
        # 计算统计信息
        end_time = datetime.now()
        self.stats.generation_time = (end_time - start_time).total_seconds()
        scene.calculate_statistics()
        
        self._log(f"=== 场景生成完成 ===")
        self._log(f"总节点数: {self.stats.total_nodes_generated}")
        self._log(f"展开容器数: {self.stats.total_containers_expanded}")
        self._log(f"AI调用次数: {self.stats.total_ai_calls}")
        self._log(f"生成耗时: {self.stats.generation_time:.2f}秒")
        
        return scene
    
    def _generate_initial_nodes(self, context: SceneContext) -> List[SceneNode]:
        """生成初始场景节点"""
        self._log("调用AI生成初始节点...")
        self.stats.total_ai_calls += 1
        
        try:
            response = self.ai_client.generate_initial_nodes(
                context.to_prompt_context()
            )
            
            nodes = []
            for node_data in response.get("nodes", []):
                # 检查是否应该展开
                should_expand = node_data.get("should_expand", True)
                node = self._create_node_from_ai_response(node_data)
                
                # 设置主题
                if isinstance(node, ContainerNode):
                    node.theme = f"{node.name}的内容"
                
                nodes.append(node)
            
            self._log(f"生成了 {len(nodes)} 个初始节点")
            return nodes
            
        except Exception as e:
            self._log(f"生成初始节点失败: {e}")
            return []
    
    async def _generate_initial_nodes_async(self, context: SceneContext) -> List[SceneNode]:
        """异步生成初始场景节点"""
        self._log("调用AI生成初始节点...")
        self.stats.total_ai_calls += 1
        
        try:
            response = await self.ai_client.generate_initial_nodes_async(
                context.to_prompt_context()
            )
            
            nodes = []
            for node_data in response.get("nodes", []):
                node = self._create_node_from_ai_response(node_data)
                if isinstance(node, ContainerNode):
                    node.theme = f"{node.name}的内容"
                nodes.append(node)
            
            self._log(f"生成了 {len(nodes)} 个初始节点")
            return nodes
            
        except Exception as e:
            self._log(f"生成初始节点失败: {e}")
            return []
    
    def _expand_all_containers(self, scene: Scene, context: SceneContext) -> None:
        """递归展开所有容器节点"""
        iteration = 0
        max_iterations = 20  # 防止无限循环
        
        while iteration < max_iterations:
            iteration += 1
            
            # 获取所有未展开的容器
            unexpanded = scene.get_all_unexpanded_containers()
            
            if not unexpanded:
                self._log("所有容器已展开完成")
                break
            
            self._log(f"--- 第 {iteration} 轮展开，待展开容器: {len(unexpanded)} 个 ---")
            
            # 检查深度限制
            valid_containers = [
                c for c in unexpanded 
                if c.level < self.config.max_depth
            ]
            
            if not valid_containers:
                self._log("达到最大深度限制，停止展开")
                break
            
            # 展开容器
            if self.config.parallel_expansion and len(valid_containers) > 1:
                self._expand_containers_batch(valid_containers, context)
            else:
                for container in valid_containers:
                    self._expand_single_container(container, context)
        
        if iteration >= max_iterations:
            self._log("达到最大迭代次数限制")
    
    async def _expand_all_containers_async(self, scene: Scene, context: SceneContext) -> None:
        """异步递归展开所有容器节点"""
        iteration = 0
        max_iterations = 20
        
        while iteration < max_iterations:
            iteration += 1
            
            unexpanded = scene.get_all_unexpanded_containers()
            
            if not unexpanded:
                self._log("所有容器已展开完成")
                break
            
            self._log(f"--- 第 {iteration} 轮展开，待展开容器: {len(unexpanded)} 个 ---")
            
            valid_containers = [
                c for c in unexpanded 
                if c.level < self.config.max_depth
            ]
            
            if not valid_containers:
                self._log("达到最大深度限制，停止展开")
                break
            
            if self.config.parallel_expansion and len(valid_containers) > 1:
                await self._expand_containers_batch_async(valid_containers, context)
            else:
                for container in valid_containers:
                    await self._expand_single_container_async(container, context)
    
    def _expand_single_container(
        self, 
        container: ContainerNode, 
        context: SceneContext
    ) -> None:
        """展开单个容器"""
        self._log(f"展开容器: {container.name} (层级: {container.level})")
        self.stats.total_ai_calls += 1
        
        try:
            response = self.ai_client.expand_container(
                container_name=container.name,
                container_type=container.container_type.value,
                container_description=container.description,
                parent_theme=container.theme,
                level=container.level,
                context=context.to_prompt_context()
            )
            
            nodes_data = response.get("nodes", [])
            
            for node_data in nodes_data[:self.config.max_nodes_per_container]:
                child = self._create_node_from_ai_response(
                    node_data,
                    level=container.level + 1,
                    parent_path=container.get_full_path(),
                    theme=f"{container.theme} > {node_data.get('name', '')}"
                )
                container.add_child(child)
                self.stats.total_nodes_generated += 1
            
            container.is_expanded = True
            self.stats.total_containers_expanded += 1
            
            self._log(f"  -> 添加了 {len(container.children)} 个子节点")
            
        except Exception as e:
            self._log(f"展开容器 {container.name} 失败: {e}")
            container.is_expanded = True  # 标记为已展开，避免重复尝试
    
    async def _expand_single_container_async(
        self, 
        container: ContainerNode, 
        context: SceneContext
    ) -> None:
        """异步展开单个容器"""
        self._log(f"展开容器: {container.name} (层级: {container.level})")
        self.stats.total_ai_calls += 1
        
        try:
            response = await self.ai_client.expand_container_async(
                container_name=container.name,
                container_type=container.container_type.value,
                container_description=container.description,
                parent_theme=container.theme,
                level=container.level,
                context=context.to_prompt_context()
            )
            
            nodes_data = response.get("nodes", [])
            
            for node_data in nodes_data[:self.config.max_nodes_per_container]:
                child = self._create_node_from_ai_response(
                    node_data,
                    level=container.level + 1,
                    parent_path=container.get_full_path(),
                    theme=f"{container.theme} > {node_data.get('name', '')}"
                )
                container.add_child(child)
                self.stats.total_nodes_generated += 1
            
            container.is_expanded = True
            self.stats.total_containers_expanded += 1
            
            self._log(f"  -> 添加了 {len(container.children)} 个子节点")
            
        except Exception as e:
            self._log(f"展开容器 {container.name} 失败: {e}")
            container.is_expanded = True
    
    def _expand_containers_batch(
        self, 
        containers: List[ContainerNode], 
        context: SceneContext
    ) -> None:
        """批量展开容器（模拟并行）"""
        batch_size = self.config.parallel_batch_size
        batches = [containers[i:i+batch_size] for i in range(0, len(containers), batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            self._log(f"处理批次 {batch_idx + 1}/{len(batches)}，共 {len(batch)} 个容器")
            
            for container in batch:
                self._expand_single_container(container, context)
    
    async def _expand_containers_batch_async(
        self, 
        containers: List[ContainerNode], 
        context: SceneContext
    ) -> None:
        """异步批量展开容器（真正的并行）"""
        batch_size = self.config.parallel_batch_size
        batches = [containers[i:i+batch_size] for i in range(0, len(containers), batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            self._log(f"并行处理批次 {batch_idx + 1}/{len(batches)}，共 {len(batch)} 个容器")
            
            # 并行展开
            tasks = [
                self._expand_single_container_async(container, context)
                for container in batch
            ]
            await asyncio.gather(*tasks)


class SceneVisualizer:
    """
    场景可视化工具
    
    提供场景结构的可视化输出
    """
    
    @staticmethod
    def print_tree(scene: Scene) -> None:
        """打印场景树形结构"""
        print(f"\n{'='*60}")
        print(f"场景: {scene.scene_name}")
        print(f"{'='*60}")
        
        if scene.context:
            print(f"\n上下文:")
            print(f"  剧本: {scene.context.script[:100]}...")
            print(f"  需求: {scene.context.scene_requirement}")
            print(f"  时代: {scene.context.era}")
        
        print(f"\n场景结构:")
        print("-" * 40)
        
        for node in scene.root_nodes:
            SceneVisualizer._print_node(node, "")
        
        print(f"\n统计信息:")
        print(f"  物品节点: {scene.total_items}")
        print(f"  容器节点: {scene.total_containers}")
        print(f"  最大深度: {scene.max_depth_reached}")
    
    @staticmethod
    def _print_node(node: SceneNode, prefix: str) -> None:
        """递归打印节点"""
        if isinstance(node, ItemNode):
            print(f"{prefix}📦 {node.name} [物品]")
            if node.description:
                print(f"{prefix}   └─ {node.description[:50]}...")
        elif isinstance(node, ContainerNode):
            type_icon = {
                ContainerType.PHYSICAL: "🗄️",
                ContainerType.CHARACTER: "👤",
                ContainerType.ABSTRACT: "💭"
            }.get(node.container_type, "📦")
            
            print(f"{prefix}{type_icon} {node.name} [容器-{node.container_type.value}]")
            if node.description:
                print(f"{prefix}   └─ {node.description[:50]}...")
            
            for i, child in enumerate(node.children):
                is_last = (i == len(node.children) - 1)
                child_prefix = prefix + ("    " if is_last else "│   ")
                SceneVisualizer._print_node(child, child_prefix)
    
    @staticmethod
    def to_markdown(scene: Scene) -> str:
        """将场景转换为Markdown格式"""
        lines = [
            f"# 场景: {scene.scene_name}",
            "",
            "## 场景上下文",
            "",
            f"- **剧本**: {scene.context.script if scene.context else 'N/A'}",
            f"- **需求**: {scene.context.scene_requirement if scene.context else 'N/A'}",
            f"- **时代**: {scene.context.era if scene.context else 'N/A'}",
            "",
            "## 场景结构",
            "",
        ]
        
        for node in scene.root_nodes:
            lines.extend(SceneVisualizer._node_to_markdown(node, 0))
        
        lines.extend([
            "",
            "## 统计信息",
            "",
            f"- 物品节点: {scene.total_items}",
            f"- 容器节点: {scene.total_containers}",
            f"- 最大深度: {scene.max_depth_reached}",
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def _node_to_markdown(node: SceneNode, level: int) -> List[str]:
        """将节点转换为Markdown"""
        indent = "  " * level
        lines = []
        
        if isinstance(node, ItemNode):
            lines.append(f"{indent}- **{node.name}** [物品]")
            if node.description:
                lines.append(f"{indent}  - 描述: {node.description}")
        elif isinstance(node, ContainerNode):
            lines.append(f"{indent}- **{node.name}** [容器-{node.container_type.value}]")
            if node.description:
                lines.append(f"{indent}  - 描述: {node.description}")
            for child in node.children:
                lines.extend(SceneVisualizer._node_to_markdown(child, level + 1))
        
        return lines
