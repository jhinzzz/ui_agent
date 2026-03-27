import os
from pathlib import Path
from dotenv import load_dotenv

# ==========================================
# 1. 基础路径与 .env 自动加载 (工程化核心)
# ==========================================
# 动态获取项目根目录 (config.py 的上一级目录)
BASE_DIR = Path(__file__).resolve().parent.parent

# 尝试寻找并加载根目录下的 .env 文件到系统环境变量中
# override=False 表示如果宿主系统已经配置了该变量(如在 CI/CD 流水线中)，则以系统优先
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path, override=False)

# ==========================================
# 2. 文本大模型配置 (用于处理纯 XML 树，高频、廉价、快速)
# ==========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
MODEL_NAME = os.getenv("MODEL_NAME", "doubao-seed-2-0-lite-260215")

# ==========================================
# 3. 多模态视觉大模型配置 (用于处理屏幕截图，低频、复杂场景辅助)
# ==========================================
# 默认 fallback 到文本模型的配置，实现优雅降级；若配置了则实现异构解耦
VISION_API_KEY = os.getenv("VISION_API_KEY", OPENAI_API_KEY)
VISION_BASE_URL = os.getenv("VISION_BASE_URL", OPENAI_BASE_URL)
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "doubao-seed-2-0-lite-260215")

# ==========================================
# 4. 自动化测试框架配置
# ==========================================
# 使用绝对路径，彻底杜绝不同命令路径下生成文件夹位置错乱的问题
OUTPUT_SCRIPT_FILE = str(BASE_DIR / "test_cases" / "test_auto_generated.py")

# 全局隐式等待时间，强转为 float 确保安全
DEFAULT_TIMEOUT = float(os.getenv("DEFAULT_TIMEOUT", 5.0))

# ==========================================
# 5. App 环境配置
# ==========================================
APP_ENV_CONFIG = {
    "dev": {
        "android": "com.pionex.client",
        "ios": "org.pionex.debug",
        "web": "https://www.pionexdev.com/cn/",
    },
    "prod": {
        "android": "com.pionex.client",
        "ios": "org.pionex",
        "web": "https://www.pionex.com/",
    },
    "us_dev": {
        "android": "com.pionex.client.us",
        "ios": "org.pionex.debug.us",
        "web": "https://www.pionexusdev.com/",
    },
    "us_prod": {
        "android": "com.pionex.client.us",
        "ios": "org.pionex.us",
        "web": "https://www.pionexus.com/",
    },
}

# ==========================================
# 6. 本地语义缓存配置
# ==========================================
# 强转布尔值，兼容 .env 中的 True/true/1/yes
CACHE_ENABLED = str(os.getenv("CACHE_ENABLED", "True")).lower() in ('true', '1', 't', 'yes')
CACHE_DIR = str(BASE_DIR / '.cache')
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", 7))
CACHE_MAX_SIZE_MB = int(os.getenv("CACHE_MAX_SIZE_MB", 100))
CACHE_COMPRESSION = str(os.getenv("CACHE_COMPRESSION", "False")).lower() in ('true', '1', 't', 'yes')
