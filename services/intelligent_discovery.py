# -*- coding: utf-8 -*-
"""
智能发现核心模块（AI关键技术与产品识别）
----------------------------------------
功能：
1️⃣ 自动识别传入文本或文件内容
2️⃣ 调用 Qwen 大模型抽取技术词 / 产品词
3️⃣ 匹配本地标准词库（rank_table_*.json）
4️⃣ 返回结构化结果

作者：Seren
版本：v2（改进版：强健解析 + 日志打印 + 容错机制）
"""

import os
import re
import json
import pdfplumber
from docx import Document
from dashscope import Generation
from dotenv import load_dotenv

# 保证无论在哪运行都能找到 /app/data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")

# ==================== 环境配置 ====================
load_dotenv()  # 自动读取 .env 文件
API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-xxxx")  # 建议放在环境变量

# ==================== 模型调用函数 ====================
def call_with_messages_qwen_plus(system_prompt, prompt_text):
    """调用 Qwen 模型"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_text.strip()},
    ]
    try:
        response = Generation.call(
            api_key=API_KEY,
            model="qwen3-235b-a22b-instruct-2507",
            messages=messages,
            result_format="message",
            temperature=0.7,
            top_p=0.8,
        )
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code}, {response.message}")
        return response.output.choices[0].message.content.strip()
    except Exception as e:
        print("❌ 调用模型失败:", e)
        return "{}"

# ==================== 文件读取函数 ====================
def extract_text_from_file(file_path):
    ext = file_path.lower().split(".")[-1]
    if ext == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == "pdf":
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    elif ext == "docx":
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        raise ValueError(f"Unsupported file type: {ext}")

# ==================== 词库加载函数 ====================
def load_rank_tables(json_folder):
    """加载 rank_table_*.json 文件"""
    rank_data = []
    for file_name in os.listdir(json_folder):
        if file_name.startswith("rank_table_") and file_name.endswith(".json"):
            file_path = os.path.join(json_folder, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    rank_data.extend(json.load(f))
            except Exception as e:
                print(f"⚠️ 词库文件读取失败 {file_name}: {e}")
    print(f"📚 载入标准词库 {len(rank_data)} 条")
    return rank_data

# ==================== 模糊匹配标准化函数 ====================
def normalize_terms(extracted_words, key_words):
    """模糊匹配模型抽取结果与标准词库"""
    from rapidfuzz import fuzz

    normalized = []
    for word in extracted_words:
        word_low = word.lower()
        best = None
        best_score = 0
        for key in key_words:
            score = fuzz.partial_ratio(word_low, key.lower())
            if score > best_score:
                best_score = score
                best = key
        if best and best_score >= 70:
            normalized.append(best)
        else:
            normalized.append(word)
    return list(dict.fromkeys(normalized))

# ==================== 核心函数 ====================
def intelligent_discovery(input_text_or_file, json_folder):
    """主逻辑：文件或文本输入 → 模型抽取 → 匹配词库 → 返回结果"""

    # ---------- 1️⃣ 读取文本 ----------
    if os.path.exists(input_text_or_file):
        content = extract_text_from_file(input_text_or_file)
    else:
        content = input_text_or_file
    print("📥 输入内容长度:", len(content))

    # ---------- 2️⃣ 调用模型 ----------
    system_prompt = """
        你是一个智能技术发现助手。
        请从以下文本中抽取技术词（如方法、算法、材料、技术名称）和产品词（如设备、工具、产品型号）。
        请只输出 JSON 格式，不要多余解释。格式如下：
        {
          "all_tech_words": ["技术1", "技术2"],
          "all_product_words": ["产品1", "产品2"]
        }
            """

    raw_output = call_with_messages_qwen_plus(system_prompt, content)
    print("🧠 模型原始输出 >>>", raw_output)

    # ---------- 3️⃣ 解析模型返回 ----------
    extraction_json = {"all_tech_words": [], "all_product_words": []}
    try:
        match = re.search(r"\{[\s\S]*\}", raw_output)
        if match:
            extraction_json = json.loads(match.group(0))
        else:
            print("⚠️ 未检测到JSON结构，使用空结构")
    except Exception as e:
        print("❌ JSON解析失败:", e)
        print("⚠️ 原始输出:", raw_output)

    all_tech_words = extraction_json.get("all_tech_words", [])
    all_product_words = extraction_json.get("all_product_words", [])
    print("🎯 抽取结果：", all_tech_words, all_product_words)

    # ---------- 4️⃣ 加载词库 ----------
    rank_entries = load_rank_tables(json_folder)
    key_tech_words = [item['name'] for item in rank_entries if item.get("type") == "技术"]
    key_product_words = [item['name'] for item in rank_entries if item.get("type") == "产品"]

    # ---------- 5️⃣ 模糊匹配 ----------
    normalized_tech = normalize_terms(all_tech_words, key_tech_words)
    normalized_product = normalize_terms(all_product_words, key_product_words)

    key_tech_found = [w for w in normalized_tech if w in key_tech_words]
    key_products_found = [w for w in normalized_product if w in key_product_words]

    # ---------- 6️⃣ 输出 ----------
    print("✅ 匹配到的关键技术:", key_tech_found)
    print("✅ 匹配到的关键产品:", key_products_found)

    return {
        "all_tech_words": normalized_tech,
        "all_product_words": normalized_product,
        "key_tech_found": key_tech_found,
        "key_products_found": key_products_found,
    }

# ==================== 独立测试入口 ====================
if __name__ == "__main__":
    test_text = (
        "本文提出了一种基于图神经网络(GNN)的推荐算法，并开发了OCR识别系统。"
        "此外还使用多模态Transformer进行图像-文本联合分析。"
    )
    res = intelligent_discovery(test_text, "data")
    print(json.dumps(res, ensure_ascii=False, indent=2))
