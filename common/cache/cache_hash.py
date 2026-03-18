import re
import json
import hashlib
from typing import Any, Dict
import xml.etree.ElementTree as ET

def _extract_semantic_fingerprint(ui_json: Dict[str, Any]) -> list:
    """
    终极锚点指纹法：只提取 2~6 个汉字的标准 UI 按钮/标签作为页面骨架。
    彻底无视任何动态数字、英文代币、长短横幅、以及节点数量的变化。
    """
    fingerprint_features = set()  # 使用 set 自动去重，完美免疫列表项数量波动
    elements = ui_json.get("ui_elements", [])

    for el in elements:
        raw_text = el.get("text", "") or el.get("desc", "")

        # 1. 纯净提取：抹除所有数字、字母、符号，只保留纯汉字
        cn_text = re.sub(r"[^\u4e00-\u9fa5]", "", raw_text)

        # <2个字：通常是无意义的单字、价格碎块
        # >6个字：通常是滚动的公告、超长横幅
        if 2 <= len(cn_text) <= 6:
            # 动态黑名单：屏蔽特定高频滚动的短汉字分类和短横幅
            if cn_text in [
                "加密货币", "比特币", "模因币", "美股代币", "贵金属代币", "热门资产",  # 资产分类
                "已上线", "已上架", "上架", "下架", "公告", "活动"  # 短横幅词汇
            ]:
                continue

            # 加入特征库 (例: "TextView|机器人")
            fingerprint_features.add(f"{el.get('class')}|{cn_text}")

    # 强制排序并转为列表，保证哈希的绝对一致性
    sorted_features = sorted(list(fingerprint_features))
    return sorted_features

def _extract_qa_text_stream(raw_xml: str) -> str:
    """
    【问答专属】提取页面纯文本流。
    忽略坐标、ID、类名，只保留真实可见的文字和数字，保证 AI 读取数据的绝对准确性。
    """
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return ""

    text_stream = []
    for node in root.iter():
        attrib = node.attrib
        res_id = attrib.get("resource-id", "")

        # 1. 拦截底层系统通知噪音，防止其污染业务数据的 Hash
        if "com.android.systemui" in res_id:
            continue

        text = attrib.get("text", "").strip()
        desc = attrib.get("content-desc", "").strip()

        # 2. 合并文本，确保不遗漏任何数据
        content = f"{text} {desc}".strip()
        if not content:
            continue

        # 3. 拦截派网等 App 特有的通知栏噪音
        if content in [
            "OpenVPN Connect通知：",
            "VPN",
            "VoLTE",
            "Bluetooth disconnected.",
        ]:
            continue

        text_stream.append(content)

    # 按从上到下的渲染顺序，将所有文字拼接成一段长文本
    return " | ".join(text_stream)

def compute_chat_cache_key(instruction: str, raw_xml: str) -> str:
    """
    计算交流问答的 Cache Key
    公式 = Hash( 标准化的问题 + 页面的纯文本流 )
    """
    # 1. 标准化用户指令（防抖：转小写、去多余空格）
    normalized_inst = re.sub(r"\s+", " ", instruction).strip().lower()

    # 2. 提取当前页面的真实文本血肉
    page_text_stream = _extract_qa_text_stream(raw_xml)

    # 3. 组合计算（加前缀以彻底隔离 L1 的动作缓存）
    combined_str = f"CHAT_V1::{normalized_inst}::{page_text_stream}"

    hash_obj = hashlib.sha256()
    hash_obj.update(combined_str.encode("utf-8"))
    return "CHAT_" + hash_obj.hexdigest()


def compute_ui_hash(ui_json: Dict[str, Any]) -> str:
    fingerprint = _extract_semantic_fingerprint(ui_json)
    fingerprint_str = json.dumps(fingerprint)
    hash_obj = hashlib.sha256()
    hash_obj.update(fingerprint_str.encode("utf-8"))
    return hash_obj.hexdigest()

def compute_instruction_hash(instruction: str) -> str:
    normalized_inst = re.sub(r"\s+", " ", instruction).strip().lower()
    hash_obj = hashlib.sha256()
    hash_obj.update(normalized_inst.encode("utf-8"))
    return hash_obj.hexdigest()

def compute_cache_key(instruction: str, ui_json: Dict[str, Any]) -> str:
    instruction_hash = compute_instruction_hash(instruction)
    ui_hash = compute_ui_hash(ui_json)
    return f"{instruction_hash}_{ui_hash}"
