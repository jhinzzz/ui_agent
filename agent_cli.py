import os
import sys
import time
import base64
import argparse
from datetime import datetime

from common.logs import log
from common.executor import UIExecutor
from common.history_manager import StepHistoryManager
from common.ai_autonomous import AutonomousBrain
from common.adapters import AndroidU2Adapter, IosWdaAdapter, WebPlaywrightAdapter
import config.config as config
from utils.utils_xml import compress_android_xml
from main import get_initial_header, save_to_disk


def main():
    parser = argparse.ArgumentParser(description="多端自动化测试自主 Agent 底层执行器")
    parser.add_argument("--goal", type=str, required=True, help="宏观测试目标")
    parser.add_argument(
        "--context", type=str, default="", help="包含 PRD、用例详细说明的文件路径"
    )
    parser.add_argument(
        "--env",
        type=str,
        default="dev",
        choices=["dev", "prod", "us_dev", "us_prod"],
        help="测试环境",
    )
    parser.add_argument("--max_steps", type=int, default=15, help="最大自主探索步数")
    parser.add_argument(
        "--max_retries",
        type=int,
        default=3,
        help="单步操作的最大连续容错重试次数，防 Token 消耗死循环",
    )
    parser.add_argument(
        "--output", type=str, default="", help="指定生成的 pytest 脚本路径"
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="android",
        choices=["android", "ios", "web"],
        help="目标测试平台",
    )
    parser.add_argument(
        "--vision", action="store_true", help="是否开启多模态(视觉)模式"
    )
    args = parser.parse_args()

    # 【动态目录处理】如果没有指定 output，则根据平台和时间戳自动生成
    if not args.output:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        platform_dir = os.path.join(base_dir, "test_cases", args.platform)
        os.makedirs(platform_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_script_path = os.path.join(
            platform_dir, f"test_auto_agent_{timestamp}.py"
        )
    else:
        output_script_path = args.output

    os.makedirs(os.path.dirname(os.path.abspath(output_script_path)), exist_ok=True)

    log.info("=" * 60)
    log.info("🚀 启动全自动 UI 测试 Agent")
    log.info(f"🎯 核心目标: {args.goal}")
    log.info(f"🛡️ 熔断配置: 单步最多连续重试 {args.max_retries} 次")
    log.info(
        f"📱 目标平台: {args.platform} | 👁️ 视觉辅助: {'开启' if args.vision else '关闭'}"
    )
    log.info(f"📁 目标文件: {output_script_path}")
    log.info("=" * 60)

    context_content = ""
    if args.context and os.path.exists(args.context):
        with open(args.context, "r", encoding="utf-8") as f:
            context_content = f.read()
        log.info(f"📄 已成功加载业务上下文文件: {args.context}")

    try:
        if args.platform == "android":
            adapter = AndroidU2Adapter()
        elif args.platform == "ios":
            adapter = IosWdaAdapter()
        elif args.platform == "web":
            adapter = WebPlaywrightAdapter()
        else:
            raise ValueError(f"不支持的平台: {args.platform}")

        adapter.setup()
        device = adapter.driver
        log.info(f"✅ {args.platform} 平台已连接并初始化完成")
    except Exception as e:
        log.error(f"❌ 设备/浏览器连接失败: {e}")
        sys.exit(1)

    if args.platform == "android":
        app_package = config.APP_ENV_CONFIG.get(args.env, {}).get("android")
        if app_package:
            device.app_start(app_package)

    history_manager = StepHistoryManager(initial_content=get_initial_header())
    save_to_disk(output_script_path, get_initial_header())

    brain = AutonomousBrain()
    executor = UIExecutor(device)

    step_count = 0
    last_error = ""
    consecutive_failures = 0
    last_ui_json = ""

    try:
        while step_count < args.max_steps:
            step_count += 1
            log.info(f"\n--- 🔄 第 {step_count} 轮探索 ---")

            try:
                if args.platform == "android":
                    device.wait_activity(device.app_current()["activity"], timeout=3)
            except Exception:
                time.sleep(1)

            ui_json = "{}"
            if args.platform == "android":
                try:
                    ui_json = compress_android_xml(device.dump_hierarchy())
                except Exception as e:
                    log.warning(f"⚠️ 抓取 UI 树失败: {e}")

            current_history = history_manager.get_history()

            screenshot_base64 = None
            if args.vision:
                try:
                    img_bytes = adapter.take_screenshot()
                    screenshot_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    log.info("📸 已截取当前屏幕画面，准备发送给视觉大模型。")
                except Exception as e:
                    log.warning(f"⚠️ 截图失败，将降级为纯文本树模式: {e}")

            if last_ui_json == ui_json and step_count > 1 and not last_error:
                last_error = "【系统环境警告】: 上一步动作已被物理执行，但页面 UI 没有任何改变！可能原因：1.输入项不合法导致按钮无效 2.需要先勾选协议 3.遇到了不可见弹窗。请切勿重复执行相同的动作，请更换策略！"
                log.warning("⚠️ 检测到 UI 僵死(操作无响应)，已向大模型注入防重复警告。")

            last_ui_json = ui_json

            decision_data = brain.get_next_autonomous_action(
                goal=args.goal,
                context=context_content,
                ui_json=ui_json,
                history=current_history,
                last_error=last_error,
                screenshot_base64=screenshot_base64,
            )

            status = decision_data.get("status")
            action_data = decision_data.get("result", {})
            last_error = ""

            if status == "success":
                if action_data and action_data.get("action"):
                    log.info(
                        "🔍 检测到伴随 success 状态的最终动作/断言，正在执行固化..."
                    )
                    result = executor.execute_and_record(action_data)
                    if result.get("success"):
                        history_manager.add_step(
                            result["code_lines"], result["action_description"]
                        )
                        save_to_disk(
                            output_script_path,
                            history_manager.get_current_file_content(),
                        )
                        log.info(f"✅ 最终动作执行成功: {result['action_description']}")
                    else:
                        log.error("❌ 最终动作/断言执行失败，任务验证未通过！")
                        sys.exit(1)

                log.info("🎉 [Agent 结论]: 核心目标与断言已全部达成！")
                sys.exit(0)

            elif status == "failed":
                log.warning("⚠️ [Agent 结论]: 任务无法继续，AI 主动判断为失败。")
                sys.exit(1)

            elif status == "running":
                if not action_data:
                    last_error = "模型返回了 running 状态，但没有提供具体的 action。请提供明确的动作。"
                    consecutive_failures += 1
                else:
                    result = executor.execute_and_record(action_data)
                    if result.get("success"):
                        consecutive_failures = 0
                        history_manager.add_step(
                            result["code_lines"], result["action_description"]
                        )
                        save_to_disk(
                            output_script_path,
                            history_manager.get_current_file_content(),
                        )
                        log.info(f"✅ 动作执行成功: {result['action_description']}")
                    else:
                        consecutive_failures += 1
                        action_repr = f"{action_data.get('action')} - {action_data.get('locator_type')}={action_data.get('locator_value')}"
                        last_error = f"尝试执行动作 [{action_repr}] 失败！未在当前页面找到该元素，或元素不可操作。"
                        log.warning(
                            f"⚠️ 执行受挫，准备让大模型进行第 {consecutive_failures} 次自愈尝试..."
                        )

                if consecutive_failures >= args.max_retries:
                    log.error(
                        f"❌ 连续重试 {args.max_retries} 次均失败，触发熔断机制！"
                    )
                    sys.exit(1)
            else:
                log.error(f"❌ 未知的状态字: {status}")
                sys.exit(1)

        log.warning(
            f"⚠️ 探索超过最大步数限制 ({args.max_steps}步)，可能是逻辑死循环，强制终止。"
        )
        sys.exit(1)

    except KeyboardInterrupt:
        log.warning("\n⚠️ 收到外部强杀信号 (KeyboardInterrupt)！正在安全中止...")
        sys.exit(1)

    finally:
        log.info(f"🏁 任务结束，当前已录制的代码安全存档于: {output_script_path}")
        try:
            adapter.teardown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
