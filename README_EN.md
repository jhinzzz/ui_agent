# ScreenForge

[中文](./README.md) | **English**

> Agentic UI Automation Framework
>
> Cross-platform agentic UI automation engine for UI exploration, self-healing, and test generation.

ScreenForge is a cross-platform UI automation engine powered by large language models (LLMs) and multimodal vision models (VLMs), focused on UI exploration, interactive recording, self-healing execution, and test script generation.

The project has evolved from pure "Human-in-the-loop" recording into an **"Agent-in-the-loop" exploration engine**. Whether a human records flows through natural-language interaction or an external super agent such as Claude Code, Cursor, or AutoGen sends high-level goals, ScreenForge can observe, reason, act, and generate Pytest + Allure test scripts that follow enterprise-grade practices.

## ✨ Key Features

🗣️ **Two operating modes**:

- **Interactive recording mode**: control the device like a chat session, generate standard test code step by step, and use built-in L1/L2 semantic action cache to reduce cost and improve speed.
- **Agentic exploration mode**: provide a high-level goal such as "log in and verify the failure message," and the engine performs multi-step exploration, closed-loop validation, and full-script generation autonomously.

👁️ **Multimodal visual perception (`--vision`)**: beyond the XML cleanup and dimensionality reduction pipeline, ScreenForge can inject live screenshots into the model context. When facing game UIs, charts, canvas-heavy pages, or custom-rendered interfaces, vision helps the model actually see what is happening.

🛡️ **Self-healing and anti-stagnation**: the engine includes UI stagnation detection and circuit breaking. When it hits invalid taps or blocked elements, it feeds the failure back into the model to change strategy. Only repeated failures or a frozen page will trip the circuit breaker, which prevents wasting tokens in infinite loops.

📦 **Unified cross-platform architecture**: the engine uses a clean adapter pattern so the same workflow can target:

- `Android` (`uiautomator2`)
- `iOS` (`facebook-wda`)
- `Web` (`Playwright`)

🎬 **End-to-end traceability and replay**: generated scripts include standardized `@allure.step` annotations, automatic screenshots on assertion failure, and support for automatic execution video recording and Allure artifact attachment through Scrcpy or native platform mechanisms.

⚡ **Aggressive token optimization**: the Android XML cleanup and dimensionality reduction pipeline strips system noise, isolated symbols, and oversized redundant nodes. In practice, token consumption can drop by more than 80%, improving both latency and cost.

🧾 **Structured run artifacts (`--json`)**: `agent_cli.py` can stream JSON Lines events to stdout and persist `summary.json`, `steps.jsonl`, `artifacts.json`, and screenshot indexes under `report/runs/<run_id>/`, making it easy for higher-level agents and orchestration systems to consume the run.

## 🛠️ Requirements and Installation

### 1. Prerequisites

- Python 3.10 or above, Python 3.11+ recommended
- An Android device or emulator with Developer Mode and USB debugging enabled, connected to your computer

### 2. Create a virtual environment

Using a virtual environment is strongly recommended:

```bash
# Create the virtual environment
python -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 3. Install Python dependencies

After activating the virtual environment, run this in the project root:

```bash
pip install -r requirement.txt
```

If you only want the core dependencies, you can install them manually:

```bash
pip install uiautomator2 openai pytest allure-pytest loguru filelock numpy sentence-transformers
```

*(Note: for iOS or Web support, install the additional `facebook-wda` or `playwright` dependencies yourself.)*

### 4. Initialize the Android device

Run the following command to push the `uiautomator2` daemon (ATX app) to the device:

```bash
python -m uiautomator2 init
```

*(Note: the first run may trigger installation prompts on the device. Approve all of them.)*

### 5. Install supporting tools (Allure and Scrcpy)

- **Allure CLI** for visual report generation
  - macOS: `brew install allure`
  - Windows: use Scoop (`scoop install allure`) or download it from GitHub Releases and configure your environment variables
- **Scrcpy** for video recording during playback
  - macOS: `brew install scrcpy`
  - Windows: download it from the official Scrcpy repository

## ⚙️ Configuration

Using environment variables is strongly recommended so you do not leak secrets in code. You can also inspect `config/config.py` directly:

```bash
# API key
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"

# Base URL, useful when using a proxy or third-party gateway
export OPENAI_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"

# Model name, ideally a strong reasoning model with multimodal support
export MODEL_NAME="doubao-seed-2.0-lite-260215"
```

**Multi-environment configuration**: the project supports `dev`, `prod`, `us_dev`, and `us_prod` app package or URL switching. See `APP_ENV_CONFIG` in `config/config.py`.

## 🚀 Core Workflow 1: Integrate with a Super Agent (Agentic Mode)

This is the **ultimate form** of ScreenForge. You can expose ScreenForge as a Tool or Skill for external super agents such as Claude Code or Cursor. The model can read `docs/agent_guide.md` directly to learn how to drive the engine.

**Typical usage**:
From Cursor Terminal, or as an instruction to Claude Code:

> *"Please read `docs/agent_guide.md`. We added a logout feature. Generate a test case for it, save it as `test_logout.py`, and then run pytest."*

The external agent will call the underlying CLI exploration engine:

```bash
python agent_cli.py --goal "Open Settings, log out, and finally verify that the login button is visible" \
                    --output "test_cases/test_logout.py" \
                    --platform android \
                    --vision \
                    --json \
                    --max_retries 3
```

### Core CLI parameters

- `-goal`: required, a high-level test goal that must include both the flow and the final assertion
- `-output`: optional, output path for the generated script. The engine automatically creates platform-specific directories such as `test_cases/android/`
- `-platform`: optional, target platform, one of `android`, `ios`, or `web`
- `-vision`: optional flag, enables multimodal visual assistance and is recommended for graphically complex UIs
- `-json`: optional flag, streams JSON Lines events to stdout for upstream agents or orchestration systems
- `-context`: optional, path to a temporary `txt` or `md` file containing PRD details, credentials, or other complex constraints
- `-max_retries`: optional, circuit-breaker threshold for consecutive retries on a single step, default is `3`

When exploration finishes, the engine exits with `0` on success and `1` on failure or circuit breaker activation. Upstream agents can use that exit code to decide whether to reflect and retry.

### Run artifacts

- `report/runs/<run_id>/summary.json`: run summary, exit code, output script path
- `report/runs/<run_id>/steps.jsonl`: persisted structured event stream
- `report/runs/<run_id>/artifacts.json`: generated script, screenshots, and other artifact indexes
- `report/runs/<run_id>/screenshots/`: screenshots captured in `--vision` mode

### Recommended docs for integrators

- `docs/agent_guide.md`: integration rules for upstream agents
- `docs/skills/execute_ui_automation.md`: execution skill contract and parameter rules

## 💻 Core Workflow 2: Interactive Recording Mode

If you want to guide the recording process manually, step by step, launch the interactive engine:

```bash
python main.py
```

The terminal will then prompt you for natural-language commands:

```text
👉 Enter a natural-language command (type 'q' to quit): Click the "Profile" tab
[System] Fetching and compressing the XML tree...
[Action] Waiting for and clicking: text='Profile'

👉 Enter a natural-language command (type 'q' to quit): Verify that "Log Out" appears on the page
[Assert] Checking element existence: text='Log Out'
[Assert] ✅ Assertion passed

👉 Enter a natural-language command (type 'q' to quit): q
🎉 Recording finished!
```

In this mode, the framework enables the local **L1/L2 semantic cache (`CacheManager`)** by default. Similar UI trees and instructions can be resolved quickly without repeating LLM API calls. It also supports `u` (`Undo`) to revert the previous step.

### Interactive mode shortcuts

- `q`, `quit`, `exit`: quit recording and save the generated test script
- `u`, `undo`: revert the previous step
- `v-on`: enable vision mode
- `v-off`: disable vision mode

## 📁 Project Structure

```text
screenforge/
├── agent_cli.py             # 🤖 Agentic entry point for super-agent-driven exploration
├── main.py                  # 🙋‍♂️ Interactive recording entry point
├── conftest.py              # Pytest fixtures, cross-platform dispatch, video/screenshot attachments
├── pytest.ini               # Pytest configuration
├── config/
│   └── config.py            # Global configuration (API keys, timeouts, multi-env settings)
├── common/
│   ├── ai.py                # Base AI interaction layer (single-step parsing and cache)
│   ├── ai_autonomous.py     # 🤖 Autonomous reasoning brain (self-healing, multimodal, memory flow)
│   ├── executor.py          # Action executor and Python code generation
│   │                         # ├── ActionHandler (abstract base class)
│   │                         # ├── ClickHandler
│   │                         # ├── LongClickHandler / HoverHandler
│   │                         # ├── InputHandler
│   │                         # ├── SwipeHandler / PressHandler
│   │                         # ├── AssertExistHandler
│   │                         # └── AssertTextEqualsHandler
│   ├── history_manager.py   # History manager and code rollback control
│   ├── logs.py              # Logging system based on loguru
│   ├── run_reporter.py      # Structured run output (summary / steps / artifacts)
│   ├── cache/               # Local hybrid semantic cache (exact match + vector retrieval)
│   │   ├── cache_manager.py      # Cache manager (L1/L2 hybrid retrieval)
│   │   ├── embedding_loader.py   # Sentence embedding loader (lazy loading and cleanup)
│   │   ├── cache_hash.py         # UI fingerprint and instruction hash utilities
│   │   ├── cache_storage.py      # Cache persistence and TTL management
│   │   └── cache_stats.py        # Cache hit-rate statistics
│   └── adapters/            # 📱 Cross-platform adapters (Android / iOS / Web)
│       ├── base_adapter.py      # Adapter base class
│       ├── android_adapter.py   # Android uiautomator2 adapter
│       ├── ios_adapter.py       # iOS facebook-wda adapter
│       └── web_adapter.py       # Web Playwright adapter
├── docs/
│   ├── agent_guide.md       # Super-agent integration guide
│   └── skills/
│       └── execute_ui_automation.md
├── utils/
│   └── utils_xml.py         # Android XML cleanup and dimensionality reduction
└── test_cases/              # Generated automation test scripts
    ├── android/             # Android platform scripts
    ├── ios/                 # iOS platform scripts
    └── web/                 # Web platform scripts
```

## 📊 Module Call Chain

```text
┌─────────────────────────────────────────────────────────────────┐
│                         main.py / agent_cli.py                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   ┌─────────┐           ┌───────────┐           ┌─────────────────┐
   │ AIBrain │           │ UIExecutor│           │StepHistoryManager│
   └────┬────┘           └─────┬─────┘           └────────┬────────┘
        │                      │                          │
        ▼                      ▼                          │
   ┌──────────┐          ┌──────────┐                    │
   │CacheManager│         │ActionHandler│                   │
   └────┬─────┘          └──────────┘                    │
        │                      │                          │
        ▼                      │                          │
   ┌──────────────┐            │                          │
   │EmbeddingModel│            │                          │
   │    Loader    │            │                          │
   └──────────────┘            │                          │
                                │                          │
┌───────────────────────────────┴───────────────────────────────┐
│                    BasePlatformAdapter                         │
│            (AndroidU2Adapter / IosWdaAdapter / WebAdapter)    │
└────────────────────────────────────────────────────────────────┘
```

## 🗂️ Cache Architecture

The project implements a **hybrid L1/L2 semantic cache** to reduce LLM API calls dramatically.

### L1 cache: page action cache

- **Best for**: highly similar commands on pages with the same structural skeleton, such as taps
- **Match method**: exact match on UI page fingerprint hash plus instruction semantic hash
- **Hit condition**: 90%+ UI tree structural similarity and an identical instruction

### L2 cache: pure Q&A cache

- **Best for**: repeated questions such as assertions or code generation requests, regardless of the current page
- **Match method**: exact match on instruction semantic hash
- **Hit condition**: identical instruction text, page ignored

### Vector semantic retrieval as fallback

When exact matching misses, the system uses a **Sentence-Transformer** model to compute semantic embeddings for instructions and retrieve the closest cached result. If the similarity reaches the threshold, `L1: 90%`, `L2: 88%`, the cache still hits.

## 📝 Changelog

### 2026-03-30

#### 🏗️ Refactoring

- **EmbeddingModelLoader responsibility split**: extracted model-loading logic from `CacheManager` into a dedicated `EmbeddingModelLoader` class to improve maintainability and testability.
  - The old 85-line `_get_model` method is now a 3-line delegation
  - Model loading, cache cleanup, and network configuration are now clearly separated
  - Dependency injection is supported, which simplifies unit testing

#### 🐛 Bug fixes

- **Platform directory check in `agent_cli.py`**: fixed a bug where platform directories might not exist during dynamic path generation. The engine now creates `test_cases/<platform>/` automatically.
- **Exception handling in `main.py`**: replaced an empty `pass` inside the `finally` block with `log.warning`, so exceptions are no longer swallowed silently.

### Historical versions

- **v0.2.0**: added the hybrid L1/L2 semantic cache system
- **v0.1.0**: initial release with Agentic and Interactive modes

## ❓ FAQ

**Q1: I get `DeviceNotFoundError` or the device cannot connect at runtime. What should I do?**  
Make sure USB debugging is enabled and the device is connected. Run `adb devices` to verify that the device is online. If it is, run `python -m uiautomator2 init` again.

**Q2: The model keeps returning garbled content or actions that cannot be parsed.**  
Check `MODEL_NAME` in `config.py`. Understanding UI structures requires strong reasoning. A flagship-scale model is recommended. If you are using a domestic model provider, prefer one with strong code and JSON output ability.

**Q3: The recorder clicks successfully, but replay fails because it cannot find the element.**  
This is often caused by page animations or slow network loading. Increase `DEFAULT_TIMEOUT` in `config.py`, default `5.0` seconds, to improve tolerance.

**Q4: When should I enable `--vision`?**  
For standard Android native screens, the default XML compression pipeline is usually enough and is both faster and cheaper. But for complex Web H5 canvas pages, Unity game UIs, or dynamic garbled `resource-id`s, `--vision` is strongly recommended so the multimodal model can use screenshots to locate targets accurately.

**Q5: Why does `agent_cli.py` stop with an error in the middle of a run?**  
That means the **self-healing circuit breaker** was triggered. If the engine fails repeatedly on the same page, for example because the target is covered, or the UI becomes stagnant and nothing responds after an action, it stops proactively with a non-zero exit code once `--max_retries` is reached. At that point, inspect the logs, refine `--goal`, or provide better context.

**Q6: Video recording does not work.**  
Make sure Scrcpy is installed. Run `scrcpy --version` to verify. If it still fails, check whether the device has granted screen recording permission. Videos for failed cases are attached to the Allure report automatically.

**Q7: The semantic cache does not hit even though I repeated the same action.**  
Check the following:

1. Is the cache enabled? Set `CACHE_ENABLED = True` in `config.py`
2. Has the UI tree changed? L1 cache depends on the page fingerprint, so structural changes can invalidate it
3. Is the instruction identical? L2 cache requires exact text equality

**Q8: The first run is slow and says it is downloading a model.**  
That is expected. On the first run, the Sentence-Transformer model, around 100 MB, must be downloaded. Through a domestic mirror this usually takes 1 to 3 minutes. Later runs use the local cache and are much faster.

**Q9: How do I clear the cache?**

```python
from common.cache import CacheManager
cm = CacheManager()
cm.clear()  # Clear all cache entries
```

## 🐛 Bug Report Guide

If you encounter a problem, please include:

1. **Reproduction steps**: the exact command or sequence of actions
2. **Error logs**: the full error output, including stack traces
3. **Environment info**: operating system, Python version, device model, and OS version
4. **Screenshots or videos**: if the issue involves UI behavior

**Contact**

- Email: jhin.fangz@gmail.com

Thanks for the feedback. I will look into it as soon as possible.
