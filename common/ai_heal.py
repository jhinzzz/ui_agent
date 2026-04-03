import re
import time
from openai import OpenAI
from common.logs import log
import config.config as config


class HealerBrain:
    """AI 测试自愈引擎大脑 (Self-Healing Brain)"""

    def __init__(self):
        # 自愈涉及代码逻辑修改，极其复杂，强制使用拥有最高智慧的视觉旗舰模型
        self.client = OpenAI(
            api_key=config.VISION_API_KEY, base_url=config.VISION_BASE_URL
        )
        self.model_name = config.VISION_MODEL_NAME

    def heal_script(
        self,
        script_content: str,
        error_msg: str,
        error_line_num: int,
        ui_json: str,
        screenshot_base64: str,
        platform: str,
    ) -> str:
        log.info(
            f"🧠 [HealerBrain] 正在深度分析 {platform} 端报错现场并生成修复方案..."
        )
        start_time = time.time()

        system_prompt = """你是一个顶级的自动化测试架构师和 AI 自愈 (Self-Healing) 引擎。
        你的核心任务是：当自动化测试用例在执行中发生元素找不到、超时或定位歧义等报错时，自动修复该测试脚本。

        【输入信息】
        1. 报错的准确行号和 Python 异常堆栈信息。
        2. 案发瞬间的最新屏幕 UI 元素树 (JSON) 和屏幕截图。
        3. 包含报错行的原始测试脚本代码。

        【你的思考步骤】
        1. 研读报错信息：是找不到元素？还是 Strict Mode 找到了多个元素引发冲突？或者是弹窗遮挡？
        2. 观察案发现场：通过分析最新的 UI 树（以及截图），寻找原测试步骤意图操作的元素当前变成了什么样（文案变了？ID 变了？）。
        3. 生成修复策略：在保证原有测试断言和业务流完整性的前提下，修改失败的那几行定位器代码，或者插入处理前置弹窗的代码。

        【输出格式约束】
        - 你必须输出一份**完整且修复后**的 Python 脚本代码，不要遗漏未报错的部分。
        - 修复后的代码必须包裹在 ```python 和 ``` 之间。
        - 请在修复的那行代码上方，加一句简短的注释，例如：`# [AI Healed]: 修复了因为弹窗导致的定位失败`。
        """

        user_prompt = f"""
【报错平台】: {platform}
【报错行号】: 第 {error_line_num} 行
【异常信息】: {error_msg}

【报错瞬间的最新的 UI 树】:
{ui_json}

【原始测试脚本代码】:
{script_content}

请结合上述信息，直接输出修复后的完整 Python 脚本。
"""

        messages = [{"role": "system", "content": system_prompt}]

        user_content = [{"type": "text", "text": user_prompt}]
        if screenshot_base64:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                }
            )

        messages.append({"role": "user", "content": user_content})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # 低温度，保证代码生成的确定性
            )

            result_text = response.choices[0].message.content.strip()

            # 使用正则精准提取 Python 代码块
            match = re.search(r"```python\n(.*?)\n```", result_text, re.DOTALL)
            if match:
                fixed_code = match.group(1).strip()
            else:
                # 兼容模型忘记加 python 标识的情况
                fixed_code = result_text.replace("```", "").strip()

            latency = time.time() - start_time
            log.info(f"⏱️ [HealerBrain] 修复方案生成完毕，耗时: {latency:.2f} 秒")
            return fixed_code

        except Exception as e:
            log.error(f"❌ [HealerBrain] AI 自愈引擎请求失败: {e}")
            return ""
