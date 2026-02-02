import os
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI

# ================= 配置区域 (在这里修改参数) =================

# 1. 在这里输入你的提示词 (支持换行，写长篇描述)
PROMPT = """
A cute pixel art portrait of a young Asian girl with long black hair, wearing a white dress, hands resting gently on her cheeks, smiling sweetly. She is sitting at a table with a lace tablecloth, blurred dried flowers in the foreground. Soft warm lighting, pastel colors, 16-bit game style, retro aesthetic, chibi style, adorable, detailed pixel art, high quality. --ar 2:3
"""

# 2. 选择你要使用的模型 (Poe 上的 Bot 名字)
# MODEL = "Nano-Banana-Pro"
MODEL = "Qwen-Image"

# 3. 生成图片的保存文件名 (如果文件已存在，会自动添加序号，如 book_1.png)
OUTPUT_FILE = "cute_girl.png"

# 4. 批量生成数量 (设置你想一次生成几张图)
BATCH_SIZE = 5

# =========================================================

# 加载环境变量
load_dotenv()

def get_unique_filename(filename):
    """
    如果文件已存在，则在文件名后添加序号。
    例如: image.png -> image_1.png -> image_2.png
    """
    if not os.path.exists(filename):
        return filename
    
    base_name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{base_name}_{counter}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1

def get_image_url(content):
    """
    从机器人的回复中提取图片链接。
    """
    # 匹配 Markdown 图片格式 ![alt](url)
    markdown_regex = r"!\[.*?\]\((.*?)\)"
    match = re.search(markdown_regex, content)
    if match:
        return match.group(1)
    
    # 匹配原始 URL (http/https)
    url_regex = r"(https?://[^\s)]+)"
    match = re.search(url_regex, content)
    if match:
        return match.group(1)
    
    return None

def download_image(url, output_path):
    """
    下载图片并保存到本地。
    """
    try:
        print(f"正在下载图片到: {output_path} ...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ 图片已成功保存: {output_path}")
    except Exception as e:
        print(f"❌ 下载图片失败: {e}")

def main():
    api_key = os.getenv("POE_API_KEY")
    if not api_key:
        print("错误: 未在环境变量中找到 POE_API_KEY。请检查 .env 文件。")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.poe.com/v1"
    )

    # 去除提示词首尾的空白字符
    clean_prompt = PROMPT.strip()
    
    print("=" * 50)
    print(f"开始批量生成任务")
    print(f"计划生成数量: {BATCH_SIZE}")
    print(f"模型: {MODEL}")
    print(f"提示词: {clean_prompt}")
    print("=" * 50)

    for i in range(BATCH_SIZE):
        print(f"\n[正在执行第 {i+1}/{BATCH_SIZE} 次生成任务]")
        
        try:
            # 确定当前任务的输出文件名
            current_output_file = get_unique_filename(OUTPUT_FILE)
            
            # 发送请求给 Poe
            print("正在发送请求，请稍候...")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": clean_prompt}],
                stream=False
            )
            
            content = response.choices[0].message.content
            # 只打印前100个字符避免刷屏，或者根据需要打印
            print(f"机器人回复: {content[:100]}..." if len(content) > 100 else f"机器人回复: {content}")
            
            image_url = get_image_url(content)
            
            if image_url:
                print(f"找到图片链接: {image_url}")
                download_image(image_url, current_output_file)
            else:
                print("❌ 在回复中未找到图片链接。")

        except Exception as e:
            print(f"❌ 第 {i+1} 次生成发生错误: {e}")

    print("\n" + "=" * 50)
    print("所有任务执行完毕！")

if __name__ == "__main__":
    main()
