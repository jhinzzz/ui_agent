from abc import ABC, abstractmethod
from common.logs import log
import config.config as config

class ActionHandler(ABC):
    @abstractmethod
    def execute(self, element, extra_value: str) -> bool:
        pass

    @abstractmethod
    def generate_code(self, u2_key: str, l_value: str, extra_value: str, timeout: float) -> list:
        pass

    @abstractmethod
    def get_log_message(self, l_type: str, l_value: str, extra_value: str) -> str:
        pass


class ClickHandler(ActionHandler):
    def execute(self, element, extra_value: str) -> bool:
        if not element.wait(timeout=config.DEFAULT_TIMEOUT):
            return False
        element.click()
        return True

    def generate_code(self, u2_key: str, l_value: str, extra_value: str, timeout: float) -> list:
        return [
            f"    with allure.step('点击元素: [{l_value}]'):\n",
            f"        log.info('执行操作: 点击元素 [{l_value}]')\n",
            f"        d({u2_key}='{l_value}').wait(timeout={timeout})\n",
            f"        d({u2_key}='{l_value}').click()\n"
        ]

    def get_log_message(self, l_type: str, l_value: str, extra_value: str) -> str:
        return f"✅ [Action] 正在等待并点击: {l_type}='{l_value}'"


class InputHandler(ActionHandler):
    def execute(self, element, extra_value: str) -> bool:
        if not element.wait(timeout=config.DEFAULT_TIMEOUT):
            return False
        element.set_text(extra_value)
        return True

    def generate_code(self, u2_key: str, l_value: str, extra_value: str, timeout: float) -> list:
        return [
            f"    with allure.step('输入文本: [{extra_value}] 到 [{l_value}]'):\n",
            f"        log.info('执行操作: 在 [{l_value}] 输入 [{extra_value}]')\n",
            f"        d({u2_key}='{l_value}').wait(timeout={timeout})\n",
            f"        d({u2_key}='{l_value}').set_text('{extra_value}')\n"
        ]

    def get_log_message(self, l_type: str, l_value: str, extra_value: str) -> str:
        return f"[Action] 正在等待并输入: {l_type}='{l_value}', 内容='{extra_value}'"


class AssertExistHandler(ActionHandler):
    def execute(self, element, extra_value: str) -> bool:
        is_exist = element.wait(timeout=config.DEFAULT_TIMEOUT)
        if not is_exist:
            log.warning("[Warning] 元素未出现 (但仍会生成断言代码)")
        else:
            log.info("[Assert] 校验通过")
        return True

    def generate_code(self, u2_key: str, l_value: str, extra_value: str, timeout: float) -> list:
        return [
            f"    with allure.step('断言: 验证元素 [{l_value}] 存在'):\n",
            f"        log.info('执行断言: 检查元素 [{l_value}] 是否存在')\n",
            f"        is_exist = d({u2_key}='{l_value}').wait(timeout={timeout})\n",
            "        if not is_exist:\n",
            f"            log.error('断言失败: 期望元素 [{l_value}] 未出现')\n",
            f"        assert is_exist, '断言失败: 期望元素 {l_value} 未出现'\n",
            "        log.info('断言成功: 元素已出现')\n"
        ]

    def get_log_message(self, l_type: str, l_value: str, extra_value: str) -> str:
        return f"[Assert] 校验元素存在: {l_type}='{l_value}'"


class AssertTextEqualsHandler(ActionHandler):
    def execute(self, element, extra_value: str) -> bool:
        if not element.wait(timeout=config.DEFAULT_TIMEOUT):
            return False

        actual_text = element.get_text()
        if actual_text != extra_value:
            log.warning(f"[Warning] 期望 '{extra_value}', 实际 '{actual_text}'")
        else:
            log.info("[Assert] 校验通过")
        return True

    def generate_code(self, u2_key: str, l_value: str, extra_value: str, timeout: float) -> list:
        return [
            f"    with allure.step('断言: 验证元素文本等于 [{extra_value}]'):\n",
            f"        log.info('执行断言: 检查元素 [{l_value}] 文本是否为 [{extra_value}]')\n",
            f"        actual_text = d({u2_key}='{l_value}').get_text()\n",
            f"        if actual_text != '{extra_value}':\n",
            f"            log.error(f'断言失败: 期望 [{extra_value}], 实际 [{{actual_text}}]')\n",
            f"        assert actual_text == '{extra_value}', f'断言失败: 期望 {extra_value}, 实际 {{actual_text}}'\n",
            f"        log.info(f'断言成功: 元素文本确为 [{extra_value}]')\n"
        ]

    def get_log_message(self, l_type: str, l_value: str, extra_value: str) -> str:
        return f"[Assert] 校验文本一致: {l_type}='{l_value}', 期望='{extra_value}'"


class UIExecutor:
    def __init__(self, device):
        self.d = device
        self._handlers = {
            "click": ClickHandler(),
            "input": InputHandler(),
            "assert_exist": AssertExistHandler(),
            "assert_text_equals": AssertTextEqualsHandler(),
        }

    def execute_and_record(self, action_data: dict, file_obj=None) -> dict:
        """执行动作，返回生成的代码行、动作描述和操作数据信息（融合 Allure 报告代码）
        如果提供了 file_obj，则保持向后兼容性，同时写入文件
        返回值: {
            "success": bool,
            "code_lines": list,  # 生成的代码行列表
            "action_description": str,  # 动作描述
            "action_info": {  # 操作数据信息用于历史跟踪
                "action_type": str,
                "locator_type": str,
                "locator_value": str,
                "extra_value": str
            }
        }
        """
        action = action_data.get("action")
        l_type = action_data.get("locator_type")
        l_value = action_data.get("locator_value")
        extra_value = action_data.get("extra_value", "")

        result = {
            "success": False,
            "code_lines": [],
            "action_description": "",
            "action_info": {
                "action_type": action,
                "locator_type": l_type,
                "locator_value": l_value,
                "extra_value": extra_value
            }
        }

        if not action or not l_value:
            print("[System] AI 返回的动作数据不完整，跳过执行。")
            return result

        # 映射 u2 的定位参数格式
        u2_locator_map = {
            "resourceId": "resourceId",
            "text": "text",
            "description": "description",
        }
        u2_key = u2_locator_map.get(l_type, l_type)

        handler = self._handlers.get(action)
        if not handler:
            log.error(f"[Error] 不支持的动作类型: {action}")
            return result

        element = self.d(**{u2_key: l_value})
        timeout = config.DEFAULT_TIMEOUT

        try:
            log.info(handler.get_log_message(l_type, l_value, extra_value))

            if not handler.execute(element, extra_value):
                log.error(f"[Error] {timeout}秒内未找到元素，放弃录制！")
                return result

            code_lines = handler.generate_code(u2_key, l_value, extra_value, timeout)

            # 构建返回结果
            result["success"] = True
            result["code_lines"] = code_lines
            result["action_description"] = handler.get_log_message(l_type, l_value, extra_value)

            # 保持向后兼容性：如果提供了 file_obj，则同时写入文件
            if file_obj is not None:
                for line in code_lines:
                    file_obj.write(line)
                file_obj.flush()

            return result

        except Exception as e:
            log.error(f"[Execute Error] 执行时发生异常: {e}")
            return result
