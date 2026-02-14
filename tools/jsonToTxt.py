import json

def json_to_text(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = []
    
    def process_node(node, level=0):
        indent = "  " * level
        lines = []
        
        # 添加节点名称
        if 'name' in node:
            lines.append(f"{indent}【{node['name']}】")
        
        # 添加描述
        if 'description' in node and node['description']:
            lines.append(f"{indent}描述：{node['description']}")
        
        # 添加位置
        if 'position' in node and node['position']:
            lines.append(f"{indent}位置：{node['position']}")
        
        # 添加属性
        if 'attributes' in node and node['attributes']:
            attrs = []
            for k, v in node['attributes'].items():
                if v:  # 只添加非空属性
                    attrs.append(f"{k}：{v}")
            if attrs:
                lines.append(f"{indent}属性：{', '.join(attrs)}")
        
        # 处理子节点
        if 'children' in node and node['children']:
            lines.append(f"{indent}包含：")
            for child in node['children']:
                child_lines = process_node(child, level + 1)
                lines.extend(child_lines)
        
        return lines
    
    # 处理根节点
    for node in data.get('root_nodes', []):
        result.extend(process_node(node))
        result.append("")  # 空行分隔
    
    return "\n".join(result)

def main():
    # 生成文本
    text = json_to_text('scene.json')
    
    # 打印结果
    print(text)
    
    # 保存到文件
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("\n✅ 文本已保存到 output.txt")

if __name__ == "__main__":
    main()