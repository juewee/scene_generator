"""
场景生成系统 - 使用示例

展示各种使用场景和高级功能
"""

import asyncio
import json
from datetime import datetime

from models import Scene, SceneContext, ContainerNode, ContainerType
from ai_client import AIConfig
from generator import (
    SceneGenerator, GeneratorConfig, 
    SceneVisualizer, GenerationStats
)
from main import generate_scene, generate_scene_async, save_scene, EXAMPLE_SCENES


def example_basic_usage():
    """
    示例1: 基础使用
    
    最简单的使用方式，只需要提供剧本和场景需求
    """
    print("\n" + "="*60)
    print("示例1: 基础使用")
    print("="*60 + "\n")
    
    scene = generate_scene(
        script="一个年轻人在咖啡馆里等待约会对象，桌上放着一杯拿铁和一本小说。",
        scene_requirement="生成一个现代咖啡馆场景，体现等待的氛围"
    )
    
    # 打印场景树
    SceneVisualizer.print_tree(scene)
    
    return scene


def example_with_full_context():
    """
    示例2: 完整上下文
    
    提供完整的场景上下文信息，获得更精准的生成结果
    """
    print("\n" + "="*60)
    print("示例2: 完整上下文")
    print("="*60 + "\n")
    
    scene = generate_scene(
        script="""
        清朝末年，一位留洋归来的年轻人在上海的一家西餐厅用餐。
        他穿着西装，桌上摆着刀叉和红酒，窗外是繁华的租界街道。
        """,
        scene_requirement="生成一个清末上海西餐厅场景，体现中西文化交融",
        era="清朝末年",
        location="上海租界西餐厅",
        atmosphere="新旧交替、繁华、略带不协调感",
        style="历史写实风格"
    )
    
    SceneVisualizer.print_tree(scene)
    
    return scene


def example_custom_config():
    """
    示例3: 自定义配置
    
    使用自定义配置控制生成过程
    """
    print("\n" + "="*60)
    print("示例3: 自定义配置")
    print("="*60 + "\n")
    
    # 创建自定义配置
    generator_config = GeneratorConfig(
        max_depth=3,              # 限制最大深度为3层
        max_nodes_per_container=10,  # 每个容器最多10个节点
        parallel_expansion=True,  # 启用并行处理
        parallel_batch_size=3,    # 每批处理3个容器
        verbose=True
    )
    
    # 创建生成器
    generator = SceneGenerator(generator_config=generator_config)
    
    # 生成场景
    scene = generator.generate_scene(
        script="一个侦探在案发现场勘查，房间里有各种可疑的痕迹。",
        scene_requirement="生成一个案发现场场景，包含可能的线索物品",
        era="现代",
        atmosphere="紧张、悬疑"
    )
    
    SceneVisualizer.print_tree(scene)
    
    # 打印统计信息
    print(f"\n生成统计:")
    print(f"  AI调用次数: {generator.stats.total_ai_calls}")
    print(f"  生成节点数: {generator.stats.total_nodes_generated}")
    print(f"  展开容器数: {generator.stats.total_containers_expanded}")
    print(f"  生成耗时: {generator.stats.generation_time:.2f}秒")
    
    return scene


async def example_async_generation():
    """
    示例4: 异步生成
    
    使用异步API进行场景生成，适合批量生成场景
    """
    print("\n" + "="*60)
    print("示例4: 异步生成")
    print("="*60 + "\n")
    
    # 异步生成场景
    scene = await generate_scene_async(
        script="一位魔法师在塔楼顶层的研究室里研究古老的魔法书。",
        scene_requirement="生成一个魔法师研究室场景，充满奇幻元素",
        era="奇幻中世纪",
        location="魔法塔楼顶层",
        atmosphere="神秘、古老、充满魔力",
        style="奇幻风格"
    )
    
    SceneVisualizer.print_tree(scene)
    
    return scene


async def example_batch_generation():
    """
    示例5: 批量生成
    
    并行生成多个场景
    """
    print("\n" + "="*60)
    print("示例5: 批量生成")
    print("="*60 + "\n")
    
    # 定义多个场景需求
    scene_requests = [
        {
            "script": "一位古代将军在帐篷中研究作战地图。",
            "scene_requirement": "古代军营帐篷场景",
            "era": "三国时期",
            "atmosphere": "紧张、严肃"
        },
        {
            "script": "一位现代科学家在实验室里进行实验。",
            "scene_requirement": "现代科学实验室场景",
            "era": "现代",
            "atmosphere": "专注、严谨"
        },
        {
            "script": "一位未来宇航员在太空舱中工作。",
            "scene_requirement": "未来太空舱场景",
            "era": "未来",
            "atmosphere": "科技感、孤独"
        }
    ]
    
    # 并行生成
    tasks = [
        generate_scene_async(
            script=req["script"],
            scene_requirement=req["scene_requirement"],
            era=req.get("era", "现代"),
            atmosphere=req.get("atmosphere", "")
        )
        for req in scene_requests
    ]
    
    scenes = await asyncio.gather(*tasks)
    
    # 显示结果
    for i, scene in enumerate(scenes):
        print(f"\n--- 场景 {i+1} ---")
        print(f"物品数: {scene.total_items}, 容器数: {scene.total_containers}")
    
    return scenes


def example_save_and_load():
    """
    示例6: 保存和加载
    
    保存场景到文件，以及从文件加载
    """
    print("\n" + "="*60)
    print("示例6: 保存和加载")
    print("="*60 + "\n")
    
    # 生成场景
    scene = generate_scene(
        script="一位作家在书房里写作，窗外下着雨。",
        scene_requirement="生成一个作家书房场景",
        era="现代",
        atmosphere="安静、文艺"
    )
    
    # 保存为JSON
    json_path = "/home/z/my-project/download/scene_output.json"
    save_scene(scene, json_path, format="json")
    print(f"场景已保存到: {json_path}")
    
    # 保存为Markdown
    md_path = "/home/z/my-project/download/scene_output.md"
    save_scene(scene, md_path, format="markdown")
    print(f"场景已保存到: {md_path}")
    
    # 从JSON加载
    from models import create_node_from_dict
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"\n从文件加载的场景信息:")
    print(f"  场景ID: {data['scene_id']}")
    print(f"  物品数: {data['statistics']['total_items']}")
    print(f"  容器数: {data['statistics']['total_containers']}")
    
    return scene


def example_traverse_scene():
    """
    示例7: 遍历场景
    
    展示如何遍历场景中的所有节点
    """
    print("\n" + "="*60)
    print("示例7: 遍历场景")
    print("="*60 + "\n")
    
    scene = generate_scene(
        script="一位旅行者在火车站候车室等待列车。",
        scene_requirement="生成一个火车站候车室场景",
        era="现代"
    )
    
    def traverse_node(node, callback, depth=0):
        """递归遍历节点"""
        callback(node, depth)
        if isinstance(node, ContainerNode):
            for child in node.children:
                traverse_node(child, callback, depth + 1)
    
    # 收集所有物品
    items = []
    containers = []
    
    def collect(node, depth):
        if node.node_type.value == "item":
            items.append((node.name, depth))
        else:
            containers.append((node.name, depth, node.container_type.value))
    
    for root in scene.root_nodes:
        traverse_node(root, collect)
    
    print("所有物品:")
    for name, depth in items:
        print(f"  {'  ' * depth}📦 {name}")
    
    print("\n所有容器:")
    for name, depth, ctype in containers:
        print(f"  {'  ' * depth}🗄️ {name} ({ctype})")
    
    return scene


def example_filter_nodes():
    """
    示例8: 过滤节点
    
    展示如何根据条件过滤节点
    """
    print("\n" + "="*60)
    print("示例8: 过滤节点")
    print("="*60 + "\n")
    
    scene = generate_scene(
        script="一位收藏家在他的收藏室里展示各种珍稀物品。",
        scene_requirement="生成一个收藏室场景，包含各种收藏品",
        era="现代"
    )
    
    def find_nodes_by_condition(node, condition, results=None):
        """根据条件查找节点"""
        if results is None:
            results = []
        
        if condition(node):
            results.append(node)
        
        if isinstance(node, ContainerNode):
            for child in node.children:
                find_nodes_by_condition(child, condition, results)
        
        return results
    
    # 查找所有人物容器
    characters = []
    for root in scene.root_nodes:
        characters.extend(find_nodes_by_condition(
            root,
            lambda n: isinstance(n, ContainerNode) and n.container_type == ContainerType.CHARACTER
        ))
    
    print(f"找到 {len(characters)} 个人物容器:")
    for char in characters:
        print(f"  👤 {char.name}: {char.description[:50]}...")
    
    # 查找深度>=2的节点
    deep_nodes = []
    for root in scene.root_nodes:
        deep_nodes.extend(find_nodes_by_condition(
            root,
            lambda n: n.level >= 2
        ))
    
    print(f"\n找到 {len(deep_nodes)} 个深度>=2的节点")
    
    return scene


def run_all_examples():
    """运行所有示例"""
    print("\n" + "#"*60)
    print("# AI驱动的层次化场景生成系统 - 使用示例")
    print("#"*60)
    
    # 同步示例
    example_basic_usage()
    example_with_full_context()
    example_custom_config()
    example_save_and_load()
    example_traverse_scene()
    example_filter_nodes()
    
    # 异步示例
    print("\n运行异步示例...")
    asyncio.run(example_async_generation())
    asyncio.run(example_batch_generation())
    
    print("\n" + "#"*60)
    print("# 所有示例运行完成!")
    print("#"*60)


if __name__ == "__main__":
    # 运行单个示例
    # example_basic_usage()
    
    # 运行所有示例
    run_all_examples()
