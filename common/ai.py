import json
from openai import OpenAI
from common.logs import log
import config.config as config
from common.cache import CacheManager


class AIBrain:
    def __init__(self):
        # 实例化文本专属客户端
        self.text_client = OpenAI(
            api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL
        )

        # 实例化视觉专属客户端 (彻底与文本解耦)
        self.vision_client = OpenAI(
            api_key=config.VISION_API_KEY, base_url=config.VISION_BASE_URL
        )

        self.cache_manager = CacheManager(
            cache_dir=config.CACHE_DIR,
            enabled=config.CACHE_ENABLED,
            ttl_days=config.CACHE_TTL_DAYS,
            max_size_mb=config.CACHE_MAX_SIZE_MB,
        )

    def _verify_locator_in_ui(self, decision: dict, ui_dict: dict) -> bool:
        """
        [核心防御机制] 校验缓存中推荐的动作，其元素是否真实存在于当前的 UI 树中
        """
        loc_type = decision.get("locator_type")
        loc_val = decision.get("locator_value")

        # 如果动作不需要特定元素 (比如 answer 或某些全局操作)，直接放行
        if (
            not loc_type
            or not loc_val
            or loc_type not in ["text", "description", "resourceId"]
        ):
            return True

        elements = ui_dict.get("ui_elements", [])
        for el in elements:
            if loc_type == "text" and el.get("text") == loc_val:
                return True
            if loc_type == "description" and el.get("desc") == loc_val:
                return True
            if loc_type == "resourceId" and el.get("id") == loc_val:
                return True

        return False

    def get_action(
        self, instruction: str, ui_json: str, screenshot_base64: str = None
    ) -> dict:
        """向大模型发送指令并返回结构化动作 JSON。"""
        try:
            ui_dict = json.loads(ui_json)
        except json.JSONDecodeError:
            ui_dict = {}

        # ==========================================
        # 1. 缓存读取与物理校验阶段
        # ==========================================
        cached_l1 = self.cache_manager.get(instruction, ui_dict)
        if cached_l1 is not None:
            log.info("🎯 [Cache] 命中页面级精准缓存 (L1-Action)")
            return cached_l1

        if hasattr(self.cache_manager, "get_chat_simple"):
            cached_l2 = self.cache_manager.get_chat_simple(instruction)
            if cached_l2 is not None:
                # 在当前页面观察元素是否存在，若不存在则放弃缓存
                if self._verify_locator_in_ui(cached_l2, ui_dict):
                    log.info("🎯 [Cache] 命中全局语义缓存 (L2-Semantic)")
                    return cached_l2
                else:
                    log.warning("⚠️ [Cache] 语义缓存虽命中，但目标元素在当前页面不存在，已放弃该缓存...")

        log.info("❌ [Cache Miss] 缓存未命中，准备请求大模型 API...")

        # ==========================================
        # 2. 提示词与 Payload 组装
        # ==========================================
        vision_prompt = ""
        if screenshot_base64:
            vision_prompt = "\n👁️ 【视觉辅助】: 你同时收到了一张真实屏幕截图。请优先结合视觉画面判断页面结构和元素状态！如果 XML 树找不到或者混乱，以视觉为准。"

        system_prompt = f"""
        你是一个资深的自动化测试专家。
        根据提供的当前屏幕 UI 元素树 (JSON 格式)，理解用户的测试指令，并输出执行策略。
        {vision_prompt}

        允许的 action 类型:
        - "click": 点击元素
        - "input": 在输入框中输入内容
        - "assert_exist": 校验某个元素是否在页面上出现
        - "assert_text_equals": 校验某个元素的文本是否与期望值一致

        允许的 locator_type 类型及优先级说明:
        - 优先级顺序：css > resourceId > text > description

        【🚨 定位器选择重要原则】
        当发现 css 或 resourceId 是动态生成的，请严格降级并优先选择 "text" 或 "description"！

        【强制输出格式】
        必须输出纯 JSON 对象，不要包含任何 markdown 格式，包含顶级 key "result"，内部结构如下:
        {{"result": {{"action": "...", "locator_type": "...", "locator_value": "...", "extra_value": "..."}}}}
        """

        user_prompt = f"用户指令: {instruction}\n当前屏幕 UI 树:\n{ui_json}"
        user_message_content = [{"type": "text", "text": user_prompt}]

        if screenshot_base64:
            user_message_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                }
            )

        # ==========================================
        # 3. 动态智能路由 (绝对分流)
        # ==========================================
        if screenshot_base64:
            active_client = self.vision_client
            active_model = config.VISION_MODEL_NAME
            log.info(f"👁️ 直接调用多模态视觉模型: {active_model}")
        else:
            active_client = self.text_client
            active_model = config.MODEL_NAME

        decision = self._call_llm(
            active_client, active_model, system_prompt, user_message_content
        )

        # ==========================================
        # 4. 缓存全量回写阶段
        # ==========================================
        if decision:
            # (1) 只要成功，必然写入强绑定的页面缓存 (L1)
            self.cache_manager.set(instruction, ui_dict, decision)

            # (2) 【核心修复】全量放开 L2 写入！因为我们在读取时有 _verify_locator_in_ui 的绝对保护！
            if hasattr(self.cache_manager, "set_chat_simple"):
                self.cache_manager.set_chat_simple(instruction, decision)

        return decision

    def _call_llm(
        self,
        client: OpenAI,
        model_name: str,
        system_prompt: str,
        user_message_content: list,
    ) -> dict:
        """封装底层的 LLM 网络调用"""
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message_content},
                ],
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.replace("```", "").strip()

            parsed_json = json.loads(result_text)
            return parsed_json.get("result", {})

        except Exception as e:
            log.error(f"[Error] 模型({model_name})请求或解析失败: {e}")
            return {}
