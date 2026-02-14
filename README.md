# AI驱动的层次化场景生成系统

一个基于DeepSeek大语言模型的智能场景生成系统，能够根据剧本和场景需求自动生成层次化的场景结构。

## 核心特性

### 1. 智能场景分解
- 根据剧本和场景需求，AI自动识别并分解场景元素
- 智能区分"末端物品"和"可展开容器"
- 支持物理容器、人物容器、抽象容器三种类型

### 2. 递归式细节生成
- 从宏观场景开始，逐层深入到微观细节
- 每个容器节点可进一步展开其内部内容
- 直到没有需要展开的容器为止

### 3. 灵活的类型系统
- **物品节点 (ItemNode)**: 不可再分的基础元素（苹果、杯子、书本等）
- **容器节点 (ContainerNode)**: 可包含其他节点
  - 物理容器：桌子、抽屉、房间、柜子
  - 人物容器：人物可以携带物品、穿着衣物
  - 抽象容器：想法、系统、概念

### 4. 上下文感知
- 每个容器有自己的"主题"和"层级"
- 生成时考虑时代背景、场景氛围、逻辑合理性

### 5. 并行处理效率
- 多个容器可同时展开，提高生成速度
- 每个AI工作器获得足够的上下文信息，保证生成一致性

## 系统架构

```
scene_generator/
├── models.py          # 数据模型（节点类、场景类）
├── ai_client.py       # DeepSeek AI调用模块
├── generator.py       # 核心生成引擎
├── main.py            # 主入口和命令行工具
├── examples.py        # 使用示例
├── requirements.txt   # 依赖
└── README.md          # 文档
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基础使用

```python
from main import generate_scene, SceneVisualizer

# 生成场景
scene = generate_scene(
    script="一位古代书生在书房中苦读，准备科举考试。",
    scene_requirement="生成一个古代书房场景",
    era="明朝",
    atmosphere="宁静、专注"
)

# 查看场景结构
SceneVisualizer.print_tree(scene)

# 保存为JSON
scene_json = scene.to_json()
```

### 命令行使用

```bash
# 运行内置示例
python main.py --example ancient_study

# 自定义场景生成
python main.py --script "剧本内容" --requirement "场景需求" --era "古代"

# 保存输出
python main.py --example modern_office --output scene.json
```

## 核心概念

### 节点类型

#### 物品节点 (ItemNode)
末端节点，不可再分的基础元素：
- 小型物品：杯子、笔、手机、钥匙
- 食物：苹果、面包、咖啡
- 文具：书本、纸张、信封

#### 容器节点 (ContainerNode)
可包含其他节点的元素：

**物理容器 (Physical)**
- 家具：桌子、柜子、书架、抽屉
- 空间：房间、建筑、车辆
- 容器：箱子、袋子、盒子

**人物容器 (Character)**
- 人物可以携带物品
- 人物可以穿着衣物
- 人物可以持有道具

**抽象容器 (Abstract)**
- 想法、计划
- 系统、概念
- 虚拟空间

### 层级结构

```
场景 (Level 0)
├── 容器：书桌 (Level 1)
│   ├── 物品：书本 (Level 2)
│   ├── 物品：笔筒 (Level 2)
│   │   ├── 物品：钢笔 (Level 3)
│   │   └── 物品：铅笔 (Level 3)
│   └── 容器：抽屉 (Level 2)
│       ├── 物品：钥匙 (Level 3)
│       └── 物品：印章 (Level 3)
└── 容器：人物-书生 (Level 1)
    ├── 物品：长袍 (Level 2)
    └── 物品：折扇 (Level 2)
```

## API参考

### generate_scene()

```python
def generate_scene(
    script: str,              # 剧本内容
    scene_requirement: str,   # 场景需求描述
    era: str = "现代",        # 时代背景
    location: str = "",       # 地点
    atmosphere: str = "",     # 氛围
    style: str = "",          # 风格
    max_depth: int = 5,       # 最大递归深度
    parallel: bool = True,    # 是否并行处理
    verbose: bool = True      # 是否输出日志
) -> Scene
```

### SceneGenerator类

```python
from generator import SceneGenerator, GeneratorConfig

# 创建生成器
generator = SceneGenerator(
    generator_config=GeneratorConfig(
        max_depth=5,
        max_nodes_per_container=20,
        parallel_expansion=True,
        parallel_batch_size=5,
        verbose=True
    )
)

# 生成场景
scene = generator.generate_scene(
    script="...",
    scene_requirement="..."
)

# 查看统计信息
print(f"AI调用次数: {generator.stats.total_ai_calls}")
print(f"生成节点数: {generator.stats.total_nodes_generated}")
```

### 异步API

```python
import asyncio
from main import generate_scene_async

async def main():
    scene = await generate_scene_async(
        script="...",
        scene_requirement="..."
    )
    return scene

scene = asyncio.run(main())
```

## 内置示例

系统提供多个内置示例场景：

| 示例名 | 描述 |
|--------|------|
| `ancient_study` | 古代书房场景 |
| `modern_office` | 现代办公室场景 |
| `fantasy_tavern` | 奇幻酒馆场景 |
| `crime_scene` | 案发现场场景 |

```bash
python main.py --example ancient_study
```

## 输出格式

### JSON格式

```json
{
  "scene_id": "abc123",
  "scene_name": "场景_20240101_120000",
  "context": "剧本背景...",
  "root_nodes": [
    {
      "name": "书桌",
      "node_type": "container",
      "container_type": "physical",
      "description": "一张古色古香的红木书桌",
      "level": 0,
      "children": [...]
    }
  ],
  "statistics": {
    "total_items": 15,
    "total_containers": 5,
    "max_depth_reached": 3
  }
}
```

### Markdown格式

```markdown
# 场景: 场景_20240101_120000

## 场景上下文
- **剧本**: ...
- **需求**: ...

## 场景结构
- **书桌** [容器-physical]
  - **书本** [物品]
  - **笔筒** [物品]
```

## 高级用法

### 自定义AI配置

```python
from ai_client import AIConfig
from generator import SceneGenerator

ai_config = AIConfig(
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=4096
)

generator = SceneGenerator(ai_config=ai_config)
```

### 遍历场景节点

```python
def traverse_node(node, callback, depth=0):
    callback(node, depth)
    if isinstance(node, ContainerNode):
        for child in node.children:
            traverse_node(child, callback, depth + 1)

# 收集所有物品
for root in scene.root_nodes:
    traverse_node(root, lambda n, d: print(f"{'  '*d}{n.name}"))
```

### 过滤节点

```python
# 查找所有人物容器
characters = []
for root in scene.root_nodes:
    find_nodes_by_condition(
        root,
        lambda n: isinstance(n, ContainerNode) and 
                  n.container_type == ContainerType.CHARACTER,
        characters
    )
```

## 工作原理

### 生成流程

```
1. 初始生成
   └── AI根据剧本和需求生成第一批节点
       └── 区分物品节点和容器节点

2. 递归展开
   └── 检查是否有未展开的容器
       └── 对每个容器调用AI生成子节点
           └── 重复直到没有容器或达到深度限制

3. 并行优化
   └── 多个容器同时展开
       └── 批量处理提高效率
```

### AI提示词策略

系统使用精心设计的提示词模板：
- 系统提示词定义节点类型和判断规则
- 初始生成提示词包含完整上下文
- 容器展开提示词包含层级和主题信息

## 注意事项

1. **API调用限制**: DeepSeek API有调用频率限制，大量生成时建议控制并发数
2. **深度控制**: 建议max_depth不超过5，避免生成过于复杂的结构
3. **上下文长度**: 场景描述不宜过长，保持在合理范围内
4. **错误处理**: 系统会自动处理API调用失败，标记容器为已展开避免重复尝试

## 许可证

MIT License
