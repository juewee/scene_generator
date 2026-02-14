"""
场景生成系统 - 主入口

提供简单易用的API接口和命令行工具
"""

import asyncio
import json
import argparse
from typing import Optional
from datetime import datetime

from models import Scene, SceneContext
from ai_client import AIConfig
from generator import SceneGenerator, GeneratorConfig, SceneVisualizer


def generate_scene(
    script: str,
    scene_requirement: str,
    era: str = "现代",
    location: str = "",
    atmosphere: str = "",
    style: str = "",
    max_depth: int = 5,
    parallel: bool = True,
    verbose: bool = True
) -> Scene:
    """
    生成场景的便捷函数
    
    Args:
        script: 剧本内容
        scene_requirement: 场景需求描述
        era: 时代背景
        location: 地点
        atmosphere: 氛围
        style: 风格
        max_depth: 最大递归深度
        parallel: 是否启用并行处理
        verbose: 是否输出详细日志
    
    Returns:
        生成的Scene对象
    """
    generator = SceneGenerator(
        generator_config=GeneratorConfig(
            max_depth=max_depth,
            parallel_expansion=parallel,
            verbose=verbose
        )
    )
    
    return generator.generate_scene(
        script=script,
        scene_requirement=scene_requirement,
        era=era,
        location=location,
        atmosphere=atmosphere,
        style=style
    )


async def generate_scene_async(
    script: str,
    scene_requirement: str,
    era: str = "现代",
    location: str = "",
    atmosphere: str = "",
    style: str = "",
    max_depth: int = 5,
    parallel: bool = True,
    verbose: bool = True
) -> Scene:
    """
    异步生成场景的便捷函数
    """
    generator = SceneGenerator(
        generator_config=GeneratorConfig(
            max_depth=max_depth,
            parallel_expansion=parallel,
            verbose=verbose
        )
    )
    
    return await generator.generate_scene_async(
        script=script,
        scene_requirement=scene_requirement,
        era=era,
        location=location,
        atmosphere=atmosphere,
        style=style
    )


async def generate_scene_with_rounds_async(
    script: str,
    scene_requirement: str,
    era: str = "现代",
    location: str = "",
    atmosphere: str = "",
    style: str = "",
    max_rounds: int = 5,
    completeness_threshold: int = 90,
    min_new_nodes_per_round: int = 3,
    max_concurrent: int = 30,
    cost_control: bool = True,
    max_total_nodes: int = 200,
    verbose: bool = True
) -> Scene:
    """
    带轮次总结的异步场景生成（优化版）
    
    Args:
        script: 剧本内容
        scene_requirement: 场景需求
        era: 时代背景
        location: 地点
        atmosphere: 氛围
        style: 风格
        max_rounds: 最大轮次数
        completeness_threshold: 完整性阈值
        min_new_nodes_per_round: 每轮最少新增节点数
        max_concurrent: 最大并发数
        cost_control: 是否启用成本控制
        max_total_nodes: 最大总节点数
        verbose: 是否输出详细日志
    
    Returns:
        生成的场景
    """
    generator = SceneGenerator(
        generator_config=GeneratorConfig(
            max_depth=5,
            parallel_expansion=True,
            verbose=verbose,
            cost_control=cost_control,
            max_total_nodes=max_total_nodes,
            min_description_length=10,
            aggressive_pruning=True
        )
    )
    
    generator.max_concurrent = max_concurrent
    
    return await generator.generate_scene_async_with_rounds(
        script=script,
        scene_requirement=scene_requirement,
        era=era,
        location=location,
        atmosphere=atmosphere,
        style=style,
        max_rounds=max_rounds,
        completeness_threshold=completeness_threshold,
        min_new_nodes_per_round=min_new_nodes_per_round
    )


def generate_scene_with_rounds(
    script: str,
    scene_requirement: str,
    era: str = "现代",
    location: str = "",
    atmosphere: str = "",
    style: str = "",
    max_rounds: int = 5,
    completeness_threshold: int = 90,
    min_new_nodes_per_round: int = 3,
    max_concurrent: int = 30,
    cost_control: bool = True,
    max_total_nodes: int = 200,
    verbose: bool = True
) -> Scene:
    """
    同步版本的带轮次总结场景生成
    """
    return asyncio.run(
        generate_scene_with_rounds_async(
            script=script,
            scene_requirement=scene_requirement,
            era=era,
            location=location,
            atmosphere=atmosphere,
            style=style,
            max_rounds=max_rounds,
            completeness_threshold=completeness_threshold,
            min_new_nodes_per_round=min_new_nodes_per_round,
            max_concurrent=max_concurrent,
            cost_control=cost_control,
            max_total_nodes=max_total_nodes,
            verbose=verbose
        )
    )


def save_scene(scene: Scene, output_path: str, format: str = "json") -> None:
    """
    保存场景到文件
    
    Args:
        scene: 场景对象
        output_path: 输出路径
        format: 输出格式 (json/markdown)
    """
    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(scene.to_json(indent=2))
    elif format == "markdown":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(SceneVisualizer.to_markdown(scene))
    else:
        raise ValueError(f"不支持的格式: {format}")


# ============== 示例场景 ==============

EXAMPLE_SCENES = {
    "ancient_study": {
        "script": "一位古代书生在书房中苦读，准备科举考试。窗外月光如水，书桌上堆满了书籍和文房四宝。",
        "scene_requirement": "生成一个古代书房场景，需要体现书生的学习环境和生活状态",
        "era": "明朝",
        "location": "江南某小镇的书房",
        "atmosphere": "宁静、专注、略带忧郁",
        "style": "古典文人风格"
    },
    "modern_office": {
        "script": "一位程序员在深夜加班，办公室里只有他一个人。桌上摆着咖啡、笔记本电脑和各种文件。",
        "scene_requirement": "生成一个现代办公室场景，体现程序员的加班状态",
        "era": "现代",
        "location": "城市写字楼",
        "atmosphere": "疲惫、专注、孤独",
        "style": "现代都市风格"
    },
    "fantasy_tavern": {
        "script": "冒险者们在一家奇幻酒馆中休息，酒馆里充满了各种奇异的生物和神秘的氛围。",
        "scene_requirement": "生成一个奇幻酒馆场景，包含各种奇幻元素",
        "era": "奇幻中世纪",
        "location": "边境小镇的冒险者酒馆",
        "atmosphere": "热闹、神秘、充满冒险气息",
        "style": "奇幻风格"
    },
    "crime_scene": {
        "script": "侦探正在调查一个密室案件，房间里有各种可疑的线索和物品。",
        "scene_requirement": "生成一个案发现场场景，包含各种可能的线索",
        "era": "现代",
        "location": "城市公寓",
        "atmosphere": "紧张、悬疑、压抑",
        "style": "侦探推理风格"
    }
}


def run_example(example_name: str = "ancient_study", use_rounds: bool = True) -> Scene:
    """
    运行示例场景生成
    
    Args:
        example_name: 示例名称
        use_rounds: 是否使用轮次总结模式
    
    Returns:
        生成的场景
    """
    if example_name not in EXAMPLE_SCENES:
        print(f"可用的示例: {list(EXAMPLE_SCENES.keys())}")
        return None
    
    example = EXAMPLE_SCENES[example_name]
    
    print(f"\n{'='*60}")
    print(f"运行示例: {example_name} ({'轮次模式' if use_rounds else '普通模式'})")
    print(f"{'='*60}\n")
    
    if use_rounds:
        scene = generate_scene_with_rounds(
            script=example["script"],
            scene_requirement=example["scene_requirement"],
            era=example.get("era", "现代"),
            location=example.get("location", ""),
            atmosphere=example.get("atmosphere", ""),
            style=example.get("style", ""),
            max_rounds=5,
            completeness_threshold=90,
            max_concurrent=30,
            cost_control=True
        )
    else:
        scene = generate_scene(
            script=example["script"],
            scene_requirement=example["scene_requirement"],
            era=example.get("era", "现代"),
            location=example.get("location", ""),
            atmosphere=example.get("atmosphere", ""),
            style=example.get("style", "")
        )
    
    return scene


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="AI驱动的层次化场景生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行内置示例（轮次模式）
  python main.py --example ancient_study --rounds
  
  # 运行内置示例（普通模式）
  python main.py --example modern_office
  
  # 自定义场景生成（轮次模式）
  python main.py --script "剧本内容" --requirement "场景需求" --era "古代" --rounds
  
  # 保存输出
  python main.py --example fantasy_tavern --output scene.json --rounds
        """
    )
    
    # 场景参数
    parser.add_argument("--script", type=str, help="剧本内容")
    parser.add_argument("--requirement", type=str, help="场景需求描述")
    parser.add_argument("--era", type=str, default="现代", help="时代背景")
    parser.add_argument("--location", type=str, default="", help="地点")
    parser.add_argument("--atmosphere", type=str, default="", help="氛围")
    parser.add_argument("--style", type=str, default="", help="风格")
    
    # 生成参数
    parser.add_argument("--max-depth", type=int, default=5, help="最大递归深度")
    parser.add_argument("--no-parallel", action="store_true", help="禁用并行处理")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    # 新增：轮次模式参数
    parser.add_argument("--rounds", action="store_true", help="使用轮次总结模式")
    parser.add_argument("--max-rounds", type=int, default=5, help="最大轮次数")
    parser.add_argument("--threshold", type=int, default=90, help="完整性阈值")
    parser.add_argument("--min-nodes", type=int, default=3, help="每轮最少新增节点数")
    parser.add_argument("--concurrent", type=int, default=30, help="最大并发数")
    parser.add_argument("--no-cost-control", action="store_true", help="禁用成本控制")
    parser.add_argument("--max-nodes", type=int, default=200, help="最大总节点数")
    
    # 示例和输出
    parser.add_argument("--example", type=str, choices=list(EXAMPLE_SCENES.keys()),
                        help="运行内置示例")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--format", type=str, choices=["json", "markdown"], 
                        default="json", help="输出格式")
    
    args = parser.parse_args()
    
    # 生成场景
    if args.example:
        scene = run_example(args.example, use_rounds=args.rounds)
    elif args.script and args.requirement:
        if args.rounds:
            scene = generate_scene_with_rounds(
                script=args.script,
                scene_requirement=args.requirement,
                era=args.era,
                location=args.location,
                atmosphere=args.atmosphere,
                style=args.style,
                max_rounds=args.max_rounds,
                completeness_threshold=args.threshold,
                min_new_nodes_per_round=args.min_nodes,
                max_concurrent=args.concurrent,
                cost_control=not args.no_cost_control,
                max_total_nodes=args.max_nodes,
                verbose=not args.quiet
            )
        else:
            scene = generate_scene(
                script=args.script,
                scene_requirement=args.requirement,
                era=args.era,
                location=args.location,
                atmosphere=args.atmosphere,
                style=args.style,
                max_depth=args.max_depth,
                parallel=not args.no_parallel,
                verbose=not args.quiet
            )
    else:
        parser.print_help()
        return
    
    if scene:
        # 显示结果
        SceneVisualizer.print_tree(scene)
        
        # 保存输出
        if args.output:
            save_scene(scene, args.output, args.format)
            print(f"\n场景已保存到: {args.output}")


if __name__ == "__main__":
    main()