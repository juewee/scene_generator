"""
场景生成系统 - 数据模型

定义了场景节点的核心数据结构，包括：
- NodeType: 节点类型枚举（物品/容器）
- SceneNode: 场景节点基类
- ItemNode: 物品节点（末端节点）
- ContainerNode: 容器节点（可展开节点）
- SceneContext: 场景上下文信息
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json


class NodeType(Enum):
    """节点类型枚举"""
    ITEM = "item"           # 物品节点 - 末端节点，不可再分
    CONTAINER = "container"  # 容器节点 - 可包含其他节点


class ContainerType(Enum):
    """容器类型枚举"""
    PHYSICAL = "physical"    # 物理容器（桌子、抽屉、房间、柜子）
    CHARACTER = "character"  # 人物容器（人物可以携带物品、穿着衣物）
    ABSTRACT = "abstract"    # 抽象容器（想法、系统、概念）


@dataclass
class SceneContext:
    """
    场景上下文信息
    
    包含场景生成的背景信息，用于指导AI生成符合场景氛围的内容
    """
    # 基础信息
    script: str                    # 剧本内容
    scene_requirement: str         # 场景需求描述
    
    # 时代背景
    era: str = "现代"              # 时代背景（古代、现代、未来等）
    location: str = ""             # 地点描述
    
    # 氛围与风格
    atmosphere: str = ""           # 场景氛围（紧张、温馨、神秘等）
    style: str = ""                # 风格描述
    
    # 扩展属性
    extra_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt_context(self) -> str:
        """生成用于AI提示的上下文描述"""
        parts = [
            f"【剧本背景】{self.script}",
            f"【场景需求】{self.scene_requirement}",
        ]
        
        if self.era:
            parts.append(f"【时代背景】{self.era}")
        if self.location:
            parts.append(f"【地点】{self.location}")
        if self.atmosphere:
            parts.append(f"【氛围】{self.atmosphere}")
        if self.style:
            parts.append(f"【风格】{self.style}")
            
        return "\n".join(parts)


@dataclass
class SceneNode:
    """
    场景节点基类
    
    所有场景元素的基础类，包含节点的基本属性
    """
    # 基础属性
    name: str                              # 节点名称
    node_type: NodeType                    # 节点类型
    description: str = ""                  # 详细描述
    
    # 层级结构
    level: int = 0                         # 层级深度（0为根级别）
    parent_path: str = ""                  # 父节点路径（用于追踪层级）
    theme: str = ""                        # 当前容器的主题
    
    # 位置与属性
    position: Optional[str] = None         # 位置描述
    attributes: Dict[str, Any] = field(default_factory=dict)  # 扩展属性
    
    # 元数据
    node_id: str = ""                      # 唯一标识符
    created_at: str = ""                   # 创建时间
    
    def get_full_path(self) -> str:
        """获取节点的完整路径"""
        if self.parent_path:
            return f"{self.parent_path}/{self.name}"
        return self.name
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "node_type": self.node_type.value,
            "description": self.description,
            "level": self.level,
            "parent_path": self.parent_path,
            "theme": self.theme,
            "position": self.position,
            "attributes": self.attributes,
            "node_id": self.node_id,
            "full_path": self.get_full_path()
        }


@dataclass
class ItemNode(SceneNode):
    """
    物品节点
    
    末端节点，不可再分的基础元素
    例如：苹果、杯子、书本、钥匙等
    """
    # 物品特有属性
    material: str = ""         # 材质
    color: str = ""            # 颜色
    size: str = ""             # 大小
    condition: str = ""        # 状态（新的、旧的、破损的等）
    
    def __post_init__(self):
        self.node_type = NodeType.ITEM
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base = super().to_dict()
        base.update({
            "material": self.material,
            "color": self.color,
            "size": self.size,
            "condition": self.condition
        })
        return base


@dataclass
class ContainerNode(SceneNode):
    """
    容器节点
    
    可包含其他节点的元素，支持递归展开
    包括：物理容器、人物容器、抽象容器
    """
    # 容器特有属性
    container_type: ContainerType = ContainerType.PHYSICAL
    children: List[SceneNode] = field(default_factory=list)  # 子节点列表
    is_expanded: bool = False   # 是否已展开
    max_depth: int = 5          # 最大展开深度
    
    def __post_init__(self):
        self.node_type = NodeType.CONTAINER
    
    def add_child(self, child: SceneNode) -> None:
        """添加子节点"""
        child.level = self.level + 1
        child.parent_path = self.get_full_path()
        child.theme = self.theme  # 继承主题
        self.children.append(child)
    
    def get_unexpanded_containers(self) -> List['ContainerNode']:
        """获取所有未展开的容器节点（包括子节点中的）"""
        containers = []
        if not self.is_expanded:
            containers.append(self)
        for child in self.children:
            if isinstance(child, ContainerNode):
                containers.extend(child.get_unexpanded_containers())
        return containers
    
    def count_items(self) -> int:
        """统计物品节点数量"""
        count = 0
        for child in self.children:
            if isinstance(child, ItemNode):
                count += 1
            elif isinstance(child, ContainerNode):
                count += child.count_items()
        return count
    
    def count_containers(self) -> int:
        """统计容器节点数量"""
        count = 1  # 自己
        for child in self.children:
            if isinstance(child, ContainerNode):
                count += child.count_containers()
        return count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（递归）"""
        base = super().to_dict()
        base.update({
            "container_type": self.container_type.value,
            "is_expanded": self.is_expanded,
            "children": [child.to_dict() for child in self.children],
            "item_count": self.count_items(),
            "container_count": self.count_containers()
        })
        return base


@dataclass 
class Scene:
    """
    完整场景
    
    包含场景的所有节点和上下文信息
    """
    # 场景信息
    scene_id: str = ""
    scene_name: str = ""
    context: SceneContext = None
    
    # 根节点列表
    root_nodes: List[SceneNode] = field(default_factory=list)
    
    # 元数据
    total_items: int = 0
    total_containers: int = 0
    max_depth_reached: int = 0
    
    def get_all_unexpanded_containers(self) -> List[ContainerNode]:
        """获取所有未展开的容器节点"""
        containers = []
        for node in self.root_nodes:
            if isinstance(node, ContainerNode):
                containers.extend(node.get_unexpanded_containers())
        return containers
    
    def calculate_statistics(self) -> None:
        """计算场景统计信息"""
        self.total_items = 0
        self.total_containers = 0
        self.max_depth_reached = 0
        
        for node in self.root_nodes:
            if isinstance(node, ItemNode):
                self.total_items += 1
            elif isinstance(node, ContainerNode):
                self.total_containers += node.count_containers()
                self.total_items += node.count_items()
                # 计算最大深度
                self._update_max_depth(node)
    
    def _update_max_depth(self, node: SceneNode) -> None:
        """更新最大深度"""
        if node.level > self.max_depth_reached:
            self.max_depth_reached = node.level
        if isinstance(node, ContainerNode):
            for child in node.children:
                self._update_max_depth(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        self.calculate_statistics()
        return {
            "scene_id": self.scene_id,
            "scene_name": self.scene_name,
            "context": self.context.to_prompt_context() if self.context else "",
            "root_nodes": [node.to_dict() for node in self.root_nodes],
            "statistics": {
                "total_items": self.total_items,
                "total_containers": self.total_containers,
                "max_depth_reached": self.max_depth_reached
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


def create_node_from_dict(data: Dict[str, Any]) -> SceneNode:
    """从字典创建节点对象"""
    node_type = NodeType(data.get("node_type", "item"))
    
    if node_type == NodeType.ITEM:
        return ItemNode(
            name=data.get("name", ""),
            description=data.get("description", ""),
            level=data.get("level", 0),
            parent_path=data.get("parent_path", ""),
            theme=data.get("theme", ""),
            position=data.get("position"),
            attributes=data.get("attributes", {}),
            node_id=data.get("node_id", ""),
            material=data.get("material", ""),
            color=data.get("color", ""),
            size=data.get("size", ""),
            condition=data.get("condition", "")
        )
    else:
        container = ContainerNode(
            name=data.get("name", ""),
            description=data.get("description", ""),
            level=data.get("level", 0),
            parent_path=data.get("parent_path", ""),
            theme=data.get("theme", ""),
            position=data.get("position"),
            attributes=data.get("attributes", {}),
            node_id=data.get("node_id", ""),
            container_type=ContainerType(data.get("container_type", "physical")),
            is_expanded=data.get("is_expanded", False)
        )
        
        # 递归创建子节点
        for child_data in data.get("children", []):
            child = create_node_from_dict(child_data)
            container.children.append(child)
        
        return container
