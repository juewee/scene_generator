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
from typing import List, Dict, Any, Optional, Callable, Tuple
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
    verbose: bool = True                   # 是否输出详细日志
    
    # 新增：成本控制参数
    cost_control: bool = True               # 是否启用成本控制
    max_total_nodes: int = 200               # 最大总节点数
    min_description_length: int = 10         # 最小描述长度
    aggressive_pruning: bool = True          # 是否激进剪枝（删除更多节点）
    importance_threshold: float = 0.3        # 重要性阈值（低于此值的节点可能被删除）


@dataclass
class GenerationStats:
    """生成统计信息"""
    total_ai_calls: int = 0
    total_nodes_generated: int = 0
    total_containers_expanded: int = 0
    generation_time: float = 0.0
    depth_reached: int = 0


@dataclass
class RoundInfo:
    """轮次信息"""
    round_number: int
    expanded_containers: List[str]  # 本轮展开的容器
    new_nodes_count: int
    summary: str = ""
    completeness_score: int = 0
    issues: List[str] = field(default_factory=list)
    optimization_suggestions: List[Dict[str, Any]] = field(default_factory=list)


class SceneGenerator:
    """
    场景生成器
    
    核心类，负责协调整个场景生成流程
    """
    
    # 类变量：日志文件路径
    _log_file_path: str = "/data/log/scene_generator.log"
    
    def __init__(
        self,
        ai_config: Optional[AIConfig] = None,
        generator_config: Optional[GeneratorConfig] = None
    ):
        self.ai_client = SceneAIClient(ai_config)
        self.config = generator_config or GeneratorConfig()
        self.stats = GenerationStats()
        self._log_callback: Optional[Callable] = None
        self.round_history: List[RoundInfo] = []
        self.previous_summary: str = ""
        self.max_concurrent: int = 30  # 默认最大并发数
        
        # 初始化日志文件
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件"""
        import os
        os.makedirs(os.path.dirname(self._log_file_path), exist_ok=True)
        with open(self._log_file_path, "w", encoding="utf-8") as f:
            f.write(f"=== 场景生成日志 {datetime.now().isoformat()} ===\n")
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """设置日志回调函数"""
        self._log_callback = callback
    
    def _log(self, message: str) -> None:
        """输出日志（同时输出到控制台和文件）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        
        if self.config.verbose:
            print(log_line)
            
        # 写入日志文件
        with open(self._log_file_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
            f.flush()  # 立即刷新，确保实时写入
            
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
    
    async def generate_scene_async_with_rounds(
        self,
        script: str,
        scene_requirement: str,
        era: str = "现代",
        location: str = "",
        atmosphere: str = "",
        style: str = "",
        max_rounds: int = 5,  # 最大轮次数
        completeness_threshold: int = 90,  # 完整性阈值，达到后停止
        min_new_nodes_per_round: int = 3  # 每轮最少新增节点数，低于此值停止
    ) -> Scene:
        """
        带轮次总结的异步场景生成
        
        Args:
            script: 剧本内容
            scene_requirement: 场景需求
            era: 时代
            location: 地点
            atmosphere: 氛围
            style: 风格
            max_rounds: 最大轮次数
            completeness_threshold: 完整性阈值（0-100），达到后停止
            min_new_nodes_per_round: 每轮最少新增节点数，低于此值停止
        
        Returns:
            生成的场景
        """
        start_time = datetime.now()
        self.stats = GenerationStats()
        self.round_history = []
        self.previous_summary = ""
        
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
        
        # 第0轮：生成初始节点
        self._log("=== 第0轮：生成初始节点 ===")
        initial_nodes = await self._generate_initial_nodes_async(context)
        scene.root_nodes = initial_nodes
        self.stats.total_nodes_generated += len(initial_nodes)
        
        # 记录初始轮次
        initial_round = RoundInfo(
            round_number=0,
            expanded_containers=[],
            new_nodes_count=len(initial_nodes)
        )
        self.round_history.append(initial_round)
        
        # 开始多轮迭代
        for round_num in range(1, max_rounds + 1):
            self._log(f"\n{'='*60}")
            self._log(f"=== 第 {round_num} 轮开始 ===")
            self._log(f"{'='*60}")
            
            # 获取当前所有节点（用于分析）
            current_nodes_dict = self._scene_to_node_dicts(scene)
            
            # 1. 分析当前轮次
            self._log("▶ 分析当前场景状态...")
            self.stats.total_ai_calls += 1
            
            analysis = await self.ai_client.analyze_round_async(
                round_num=round_num,
                current_nodes=current_nodes_dict,
                context=context.to_prompt_context(),
                previous_summary=self.previous_summary
            )
            
            # 保存总结
            self.previous_summary = analysis.get("summary", "")
            completeness = analysis.get("completeness_score", 0)
            issues = analysis.get("issues_found", [])
            suggestions = analysis.get("optimization_suggestions", [])
            
            self._log(f"完整性评分: {completeness}/100")
            if issues:
                self._log("发现问题:")
                for issue in issues:
                    self._log(f"  - {issue}")
            
            # 2. 根据建议优化节点
            if suggestions:
                self._log("▶ 优化现有节点...")
                self.stats.total_ai_calls += 1
                
                optimization_result = await self.ai_client.optimize_nodes_async(
                    optimization_suggestions=suggestions,
                    current_nodes=current_nodes_dict,
                    context=context.to_prompt_context()
                )
                
                # 更新节点
                updated_nodes = optimization_result.get("updated_nodes", [])
                if updated_nodes:
                    self._apply_node_updates(scene, updated_nodes)
                    self._log(f"已根据建议更新节点")
            
            # 每两轮执行一次激进剪枝
            if self.config.aggressive_pruning and round_num % 2 == 0:
                self._aggressive_pruning(scene)
            
            # 3. 获取本轮要展开的容器
            containers_to_expand = analysis.get("containers_to_expand_next", [])
            containers_to_stop = analysis.get("containers_to_stop", [])
            
            if not containers_to_expand:
                self._log("▶ AI建议本轮无需展开新容器")
                
                # 检查停止条件
                if completeness >= completeness_threshold:
                    self._log(f"✅ 场景完整性已达 {completeness}%，停止生成")
                    break
                
                # 检查新增节点数
                last_round = self.round_history[-1]
                if last_round.new_nodes_count < min_new_nodes_per_round:
                    self._log(f"⚠️ 上一轮新增节点数({last_round.new_nodes_count})低于阈值({min_new_nodes_per_round})，停止生成")
                    break
                
                continue
            
            self._log(f"▶ 本轮计划展开 {len(containers_to_expand)} 个容器")
            
            # 按优先级排序
            containers_to_expand.sort(key=lambda x: x.get("priority", 1), reverse=True)
            
            # 4. 并行展开容器
            expanded_containers_names = []
            new_nodes_added = 0
            
            # 找出要展开的容器对象
            containers_to_process = []
            for container_info in containers_to_expand:
                container_name = container_info["name"]
                container = self._find_container_by_name(scene, container_name)
                if container:
                    # 检查深度限制
                    if container.level < self.config.max_depth:
                        containers_to_process.append(container)
                        expanded_containers_names.append(container_name)
                    else:
                        self._log(f"   ⚠️ {container_name} 已达最大深度，跳过展开")
                else:
                    self._log(f"   ⚠️ 找不到容器: {container_name}")
            
            if containers_to_process:
                self._log(f"▶ 并行展开 {len(containers_to_process)} 个容器...")
                
                # 创建展开任务（限制并发数）
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def expand_with_semaphore(container):
                    async with semaphore:
                        return await self._expand_single_container_async(container, context)
                
                tasks = [expand_with_semaphore(c) for c in containers_to_process]
                
                # 等待所有展开完成
                results = await asyncio.gather(*tasks)
                
                # 统计新增节点
                for container in containers_to_process:
                    new_nodes_added += len(container.children)
            
            # 5. 记录本轮信息
            round_info = RoundInfo(
                round_number=round_num,
                expanded_containers=expanded_containers_names,
                new_nodes_count=new_nodes_added,
                summary=analysis.get("summary", ""),
                completeness_score=completeness,
                issues=issues,
                optimization_suggestions=suggestions
            )
            self.round_history.append(round_info)
            
            self._log(f"\n=== 第 {round_num} 轮完成 ===")
            self._log(f"展开容器: {len(expanded_containers_names)} 个")
            self._log(f"新增节点: {new_nodes_added} 个")
            self._log(f"当前完整性: {completeness}%")
            self._log(f"下一轮重点: {analysis.get('next_round_focus', '无')}")
            
            # 6. 检查是否应该停止
            if completeness >= completeness_threshold:
                self._log(f"✅ 场景完整性已达 {completeness}%，停止生成")
                break
            
            if new_nodes_added < min_new_nodes_per_round and round_num > 1:
                self._log(f"⚠️ 本轮新增节点数({new_nodes_added})低于阈值({min_new_nodes_per_round})，停止生成")
                break
            
            if self.stats.total_nodes_generated >= self.config.max_total_nodes:
                self._log(f"⚠️ 已达到最大节点数限制({self.config.max_total_nodes})，停止生成")
                break
        
        # 计算最终统计
        end_time = datetime.now()
        self.stats.generation_time = (end_time - start_time).total_seconds()
        scene.calculate_statistics()
        
        # 输出轮次总结
        self._print_round_summary()
        
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
            
            self._log(f"并行展开 {len(valid_containers)} 个容器")
            
            # 创建所有容器的异步任务
            tasks = [
                self._expand_single_container_async(container, context)
                for container in valid_containers
            ]
            
            # 等待所有任务完成（真正并发）
            await asyncio.gather(*tasks)
    
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
            
            added_count = 0
            for node_data in nodes_data[:self.config.max_nodes_per_container]:
                # 成本控制：检查是否应该添加
                if self._should_add_node(node_data):
                    child = self._create_node_from_ai_response(
                        node_data,
                        level=container.level + 1,
                        parent_path=container.get_full_path(),
                        theme=f"{container.theme} > {node_data.get('name', '')}"
                    )
                    container.add_child(child)
                    self.stats.total_nodes_generated += 1
                    added_count += 1
                else:
                    self._log(f"   ⏭️ 跳过添加（成本控制）: {node_data.get('name', '未知')}")
            
            container.is_expanded = True
            self.stats.total_containers_expanded += 1
            
            self._log(f"  -> 添加了 {added_count} 个子节点（跳过 {len(nodes_data) - added_count} 个）")
            
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
            
            added_count = 0
            for node_data in nodes_data[:self.config.max_nodes_per_container]:
                # 成本控制：检查是否应该添加
                if self._should_add_node(node_data):
                    child = self._create_node_from_ai_response(
                        node_data,
                        level=container.level + 1,
                        parent_path=container.get_full_path(),
                        theme=f"{container.theme} > {node_data.get('name', '')}"
                    )
                    container.add_child(child)
                    self.stats.total_nodes_generated += 1
                    added_count += 1
                else:
                    self._log(f"   ⏭️ 跳过添加（成本控制）: {node_data.get('name', '未知')}")
            
            container.is_expanded = True
            self.stats.total_containers_expanded += 1
            
            self._log(f"  -> 添加了 {added_count} 个子节点（跳过 {len(nodes_data) - added_count} 个）")
            
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
    
    def _scene_to_node_dicts(self, scene: Scene) -> List[Dict[str, Any]]:
        """将场景节点转换为字典列表（用于AI分析）"""
        nodes = []
        
        def collect_nodes(node):
            node_dict = {
                "name": node.name,
                "node_type": node.node_type.value,
                "level": node.level,
                "description": node.description[:100] if node.description else "",
            }
            if isinstance(node, ContainerNode):
                node_dict["container_type"] = node.container_type.value
                node_dict["children_count"] = len(node.children)
            nodes.append(node_dict)
            
            if isinstance(node, ContainerNode):
                for child in node.children:
                    collect_nodes(child)
        
        for root in scene.root_nodes:
            collect_nodes(root)
        
        return nodes
    
    def _find_container_by_name(self, scene: Scene, name: str) -> Optional[ContainerNode]:
        """根据名称查找容器节点"""
        def search(node):
            if isinstance(node, ContainerNode) and node.name == name:
                return node
            if isinstance(node, ContainerNode):
                for child in node.children:
                    result = search(child)
                    if result:
                        return result
            return None
        
        for root in scene.root_nodes:
            result = search(root)
            if result:
                return result
        return None
    
    def _find_node_by_name(self, scene: Scene, name: str) -> Optional[SceneNode]:
        """根据名称查找节点"""
        def search(node):
            if node.name == name:
                return node
            if isinstance(node, ContainerNode):
                for child in node.children:
                    result = search(child)
                    if result:
                        return result
            return None
        
        for root in scene.root_nodes:
            result = search(root)
            if result:
                return result
        return None
    
    def _apply_node_updates(self, scene: Scene, updated_nodes: List[Dict[str, Any]]):
        """
        应用节点更新 - 优化版：偏向精简和删除
        
        更新规则：
        1. 如果节点在updated_nodes中但不在当前场景 -> 添加（谨慎添加）
        2. 如果节点在当前场景但不在updated_nodes中 -> 删除（精简）
        3. 如果节点两者都在，但类型/属性变化 -> 更新
        """
        self._log("🔍 执行节点优化...")
        
        # 获取当前所有节点的名称集合
        current_nodes_dict = {}
        def collect_nodes(node):
            current_nodes_dict[node.name] = node
            if isinstance(node, ContainerNode):
                for child in node.children:
                    collect_nodes(child)
        
        for root in scene.root_nodes:
            collect_nodes(root)
        
        # 获取优化建议中的节点名称
        updated_names = {node.get("name") for node in updated_nodes if node.get("name")}
        
        # 1. 找出要删除的节点（在场景中但不在优化建议中）
        nodes_to_delete = set(current_nodes_dict.keys()) - updated_names
        
        if nodes_to_delete:
            self._log(f"🗑️ 删除 {len(nodes_to_delete)} 个冗余节点:")
            for node_name in list(nodes_to_delete)[:10]:  # 只显示前10个
                self._log(f"   - {node_name}")
            
            if len(nodes_to_delete) > 10:
                self._log(f"   ... 等 {len(nodes_to_delete)} 个节点")
            
            # 从场景中删除节点
            for node_name in nodes_to_delete:
                node_to_delete = current_nodes_dict[node_name]
                self._remove_node_from_scene(scene, node_to_delete)
        
        # 2. 处理新增或更新的节点
        nodes_added = 0
        nodes_updated = 0
        
        for node_data in updated_nodes:
            node_name = node_data.get("name", "")
            if not node_name:
                continue
            
            if node_name in current_nodes_dict:
                # 节点存在，检查是否需要更新
                existing_node = current_nodes_dict[node_name]
                if self._should_update_node(existing_node, node_data):
                    updated_node = self._update_node(scene, existing_node, node_data)
                    if updated_node:
                        # 如果节点被转换，更新字典中的引用
                        if updated_node is not existing_node:
                            current_nodes_dict[node_name] = updated_node
                        nodes_updated += 1
                        self._log(f"🔄 更新节点: {node_name}")
            else:
                # 节点不存在，考虑是否添加
                # 添加前进行成本评估：只有确实重要的节点才添加
                if self._should_add_node(node_data):
                    new_node = self._create_node_from_ai_response(node_data)
                    scene.root_nodes.append(new_node)
                    nodes_added += 1
                    self._log(f"➕ 添加节点: {node_name}")
                else:
                    self._log(f"⏭️ 跳过添加（成本控制）: {node_name}")
        
        self._log(f"📊 优化结果: 删除 {len(nodes_to_delete)} 个，更新 {nodes_updated} 个，新增 {nodes_added} 个")
    
    def _remove_node_from_scene(self, scene: Scene, node_to_delete: SceneNode):
        """从场景中删除节点"""
        
        def remove_from_parent(parent: ContainerNode, target: SceneNode) -> bool:
            """从父节点中删除子节点"""
            for i, child in enumerate(parent.children):
                if child is target:
                    parent.children.pop(i)
                    return True
                if isinstance(child, ContainerNode):
                    if remove_from_parent(child, target):
                        return True
            return False
        
        # 检查是否是根节点
        for i, root in enumerate(scene.root_nodes):
            if root is node_to_delete:
                scene.root_nodes.pop(i)
                return
        
        # 否则在子节点中查找
        for root in scene.root_nodes:
            if isinstance(root, ContainerNode):
                if remove_from_parent(root, node_to_delete):
                    return
    
    def _should_update_node(self, existing_node: SceneNode, new_data: Dict[str, Any]) -> bool:
        """
        判断是否需要更新节点
        
        只更新真正有意义的变更：
        1. 节点类型变化（item <-> container）
        2. 容器类型变化（physical <-> character <-> abstract）
        3. 描述有明显改进
        """
        new_type = NodeType(new_data.get("node_type", "item"))
        
        # 节点类型变化 - 需要更新
        if existing_node.node_type != new_type:
            return True
        
        # 对于容器节点，检查容器类型变化
        if isinstance(existing_node, ContainerNode):
            new_container_type = ContainerType(new_data.get("container_type", "physical"))
            if existing_node.container_type != new_container_type:
                return True
        
        # 检查描述是否有显著改进（更长、更详细）
        new_desc = new_data.get("description", "")
        if len(new_desc) > len(existing_node.description) * 1.5:  # 描述长度增加50%以上
            return True
        
        # 默认不更新，节省成本
        return False
    
    def _update_node(self, scene: Scene, node: SceneNode, new_data: Dict[str, Any]):
        """更新节点属性"""
        # 更新基础属性
        node.description = new_data.get("description") or node.description
        node.position = new_data.get("position") or node.position
        
        # 更新节点类型（如果需要）
        new_type_str = new_data.get("node_type") or "item"
        if new_type_str:
            new_type = NodeType(new_type_str)
            if node.node_type != new_type:
                # 类型转换需要特殊处理
                converted_node = self._convert_node_type(scene, node, new_type, new_data)
                # 替换场景中的节点
                self._replace_node_in_scene(scene, node, converted_node)
                return converted_node
        
        # 更新容器特有属性
        if isinstance(node, ContainerNode):
            new_container_type_str = new_data.get("container_type") or "physical"
            if new_container_type_str:
                try:
                    new_container_type = ContainerType(new_container_type_str)
                    node.container_type = new_container_type
                except ValueError:
                    # 如果类型无效，保持原类型
                    pass
        
        # 更新物品特有属性
        if isinstance(node, ItemNode):
            attrs = new_data.get("attributes") or {}
            node.material = attrs.get("material") or node.material
            node.color = attrs.get("color") or node.color
            node.size = attrs.get("size") or node.size
            node.condition = attrs.get("condition") or node.condition
        
        return node
    
    def _replace_node_in_scene(self, scene: Scene, old_node: SceneNode, new_node: SceneNode):
        """
        在场景中替换节点
        
        Args:
            scene: 场景对象
            old_node: 要替换的旧节点
            new_node: 新节点
        """
        # 查找父节点
        parent = self._find_parent_of_node(scene, old_node)
        
        if parent:
            # 在父节点的子节点列表中替换
            for i, child in enumerate(parent.children):
                if child is old_node:
                    parent.children[i] = new_node
                    self._log(f"   🔄 在父节点 '{parent.name}' 中替换节点")
                    return
        else:
            # 根节点替换
            for i, root in enumerate(scene.root_nodes):
                if root is old_node:
                    scene.root_nodes[i] = new_node
                    self._log(f"   🔄 替换根节点")
                    return
        
        self._log(f"   ⚠️ 未找到要替换的节点: {old_node.name}")
    
    def _convert_node_type(self, scene: Scene, node: SceneNode, new_type: NodeType, data: Dict[str, Any]) -> SceneNode:
        """
        转换节点类型（item <-> container）
        
        Args:
            scene: 场景对象
            node: 要转换的节点
            new_type: 新的节点类型
            data: 新节点的数据（包含描述、属性等）
        
        Returns:
            转换后的新节点
        """
        self._log(f"[转换] 转换节点类型: {node.name} ({node.node_type.value} -> {new_type.value})")
        
        # 如果类型相同，不需要转换
        if node.node_type == new_type:
            self._log(f"   [跳过] 节点类型相同，无需转换")
            return node
        
        # 获取父节点（如果存在）
        parent = self._find_parent_of_node(scene, node)
        
        if new_type == NodeType.ITEM:
            # 容器 -> 物品
            return self._convert_container_to_item(node, data, parent)
        else:
            # 物品 -> 容器
            return self._convert_item_to_container(node, data, parent)
    
    def _find_parent_of_node(self, scene: Scene, node: SceneNode) -> Optional[ContainerNode]:
        """
        查找节点的父节点
        
        Args:
            scene: 场景对象
            node: 要查找父节点的节点
        
        Returns:
            父节点，如果是根节点则返回None
        """
        # 遍历场景查找节点的父节点
        def search_parent(current_node: SceneNode, target: SceneNode) -> Optional[ContainerNode]:
            if isinstance(current_node, ContainerNode):
                for child in current_node.children:
                    if child is target:
                        return current_node
                    # 递归搜索子节点
                    result = search_parent(child, target)
                    if result:
                        return result
            return None
        
        # 在根节点中查找
        for root in scene.root_nodes:
            if root is node:
                # 根节点没有父节点
                return None
            if isinstance(root, ContainerNode):
                result = search_parent(root, node)
                if result:
                    return result
        
        return None
    
    def _convert_container_to_item(self, container: ContainerNode, data: Dict[str, Any], parent: Optional[ContainerNode]) -> ItemNode:
        """
        将容器节点转换为物品节点
        
        Args:
            container: 要转换的容器节点
            data: 新物品节点的数据
            parent: 父节点（如果存在）
        
        Returns:
            转换后的物品节点
        """
        self._log(f"   [转换] 容器 -> 物品: {container.name}")
        
        # 创建新的物品节点
        item_node = ItemNode(
            name=data.get("name", container.name),
            node_type=NodeType.ITEM,
            description=data.get("description", container.description),
            level=container.level,
            parent_path=container.parent_path,
            theme=container.theme,
            position=data.get("position", container.position),
            attributes=data.get("attributes", container.attributes),
            node_id=container.node_id,
            created_at=container.created_at,
            material=data.get("attributes", {}).get("material", ""),
            color=data.get("attributes", {}).get("color", ""),
            size=data.get("attributes", {}).get("size", ""),
            condition=data.get("attributes", {}).get("condition", "")
        )
        
        # 记录转换信息
        if container.children:
            self._log(f"   [警告] 容器有 {len(container.children)} 个子节点，转换后将丢失这些子节点")
        
        return item_node
    
    def _convert_item_to_container(self, item: ItemNode, data: Dict[str, Any], parent: Optional[ContainerNode]) -> ContainerNode:
        """
        将物品节点转换为容器节点
        
        Args:
            item: 要转换的物品节点
            data: 新容器节点的数据
            parent: 父节点（如果存在）
        
        Returns:
            转换后的容器节点
        """
        self._log(f"   📦 物品 -> 容器: {item.name}")
        
        # 确定容器类型
        container_type_str = data.get("container_type", "physical")
        try:
            container_type = ContainerType(container_type_str)
        except ValueError:
            container_type = ContainerType.PHYSICAL
            self._log(f"   ⚠️ 无效的容器类型 '{container_type_str}'，使用默认类型 'physical'")
        
        # 创建新的容器节点
        container_node = ContainerNode(
            name=data.get("name", item.name),
            node_type=NodeType.CONTAINER,
            description=data.get("description", item.description),
            level=item.level,
            parent_path=item.parent_path,
            theme=item.theme,
            position=data.get("position", item.position),
            attributes=data.get("attributes", item.attributes),
            node_id=item.node_id,
            created_at=item.created_at,
            container_type=container_type,
            is_expanded=False,
            max_depth=self.config.max_depth
        )
        
        # 如果原物品有属性，可以尝试转换为初始子节点
        self._log(f"   📝 物品转换为容器，可以后续展开")
        
        return container_node
    
    def _should_add_node(self, node_data: Dict[str, Any]) -> bool:
        """
        成本控制：判断是否应该添加新节点
        
        添加条件：
        1. 节点有详细描述（不是空的）
        2. 节点有明确的场景作用
        3. 不是过于琐碎的物品
        """
        if not self.config.cost_control:
            return True
        
        name = node_data.get("name", "")
        description = node_data.get("description", "")
        node_type = node_data.get("node_type", "item")
        
        # 1. 长度检查
        if len(description) < self.config.min_description_length:
            self._log(f"   ⚠️ 描述太短 ({len(description)} < {self.config.min_description_length})")
            return False
        
        # 2. 总节点数检查
        if self.stats.total_nodes_generated >= self.config.max_total_nodes:
            self._log(f"   ⚠️ 已达到最大节点数限制 ({self.config.max_total_nodes})")
            return False
        
        # 3. 物品节点的额外检查
        if node_type == "item":
            # 忽略过于通用的物品
            generic_items = ["桌子", "椅子", "门", "窗户", "墙", "地板", "天花板", "空气", "光线"]
            if name in generic_items and len(description) < 20:
                self._log(f"   ⚠️ 通用物品且描述简单: {name}")
                return False
            
            # 检查是否可能是冗余物品
            if "墙上" in description or "地面" in description or "角落" in description:
                # 建筑结构相关的物品，如果描述简单就跳过
                if len(description) < 15:
                    return False
        
        return True
    
    def _identify_redundant_nodes(self, scene: Scene) -> List[SceneNode]:
        """
        识别冗余节点（用于激进剪枝）
        """
        redundant = []
        
        def check_node(node):
            # 判断节点是否冗余的条件
            if isinstance(node, ItemNode):
                # 物品节点冗余条件
                if not node.description or len(node.description) < 5:
                    redundant.append(node)
                elif node.name in ["未知物品", "杂物", "其他", "东西"]:
                    redundant.append(node)
            
            elif isinstance(node, ContainerNode):
                # 容器节点冗余条件
                if not node.children and not node.description:
                    # 空容器且无描述
                    redundant.append(node)
                elif node.container_type == ContainerType.ABSTRACT and not node.children:
                    # 空的抽象容器
                    redundant.append(node)
                
                # 递归检查子节点
                for child in node.children:
                    check_node(child)
        
        for root in scene.root_nodes:
            check_node(root)
        
        return redundant
    
    def _aggressive_pruning(self, scene: Scene):
        """
        激进剪枝：删除所有可删除的节点
        """
        if not self.config.aggressive_pruning:
            return
        
        self._log("🔪 执行激进剪枝...")
        
        redundant_nodes = self._identify_redundant_nodes(scene)
        
        if redundant_nodes:
            self._log(f"发现 {len(redundant_nodes)} 个冗余节点")
            for node in redundant_nodes[:10]:  # 只显示前10个
                self._log(f"  删除: {node.name}")
            if len(redundant_nodes) > 10:
                self._log(f"   ... 等 {len(redundant_nodes)} 个节点")
            
            for node in redundant_nodes:
                self._remove_node_from_scene(scene, node)
    
    def _print_round_summary(self):
        """打印轮次总结"""
        self._log("\n" + "="*60)
        self._log("📊 生成轮次总结")
        self._log("="*60)
        
        for round_info in self.round_history:
            if round_info.round_number == 0:
                self._log(f"\n第 0 轮（初始生成）:")
                self._log(f"  新增节点: {round_info.new_nodes_count}")
            else:
                self._log(f"\n第 {round_info.round_number} 轮:")
                self._log(f"  新增节点: {round_info.new_nodes_count}")
                self._log(f"  展开容器: {', '.join(round_info.expanded_containers) if round_info.expanded_containers else '无'}")
                self._log(f"  完整性评分: {round_info.completeness_score}%")
                if round_info.issues:
                    self._log(f"  发现问题: {len(round_info.issues)}个")


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