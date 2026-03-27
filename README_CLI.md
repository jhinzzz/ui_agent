# 📱 UI 自动化智能体 (UI Auto Agent) - 使用参考手册

欢迎 Super Agent。本仓库是一个提供底层 Android UI 驱动和代码生成能力的自动化框架。作为外部主控大脑，你可以通过调用本框架提供的 CLI 工具，完成端到端的自动化测试用例编写。

# 🛠️ 你的核心工具 (Skill)

你目前拥有以下本地命令行工具可以调用：

## 1. `agent_cli.py` (全自动 UI 探索与脚本生成器)

这个工具接收一个宏观目标，会自动连接手机，分析 UI，进行点击、输入并自动在 test_cases/test_auto_generated.py 中生成基于 Pytest 和 Allure 的测试代码。

**调用语法:**

```python
python agent_cli.py --goal "<你的测试目标>" --context "<(可选)包含详细约束的文件路径>" --env "<(可选)dev/prod>"
```

**调用示例:**

```python
python agent_cli.py --goal "验证用户使用错误密码登录时，会出现'密码错误'的提示" --context "./docs/login_prd.md"
```


# 🧠 你的工作流 (Workflow)

当人类让你“根据 PRD 编写一个登录模块的自动化测试用例”时，请严格遵循以下步骤：

1. 分析与理解: 阅读用户提供的 PRD 或 Git Diff 文件，拆解出需要测试的核心业务流。

2. 生成任务描述: 将业务流转换为一段清晰的、包含前置条件和预期断言的 goal（目标）。

3. 调用底层引擎: 执行 python agent_cli.py --goal "..."，并将详细要求写入一个临时文件通过 --context 传入。

4. 验证生成结果: 命令执行完毕后，读取 test_cases/test_auto_generated.py 文件，检查生成的代码是否符合 Pytest 规范，是否包含预期的 @allure.step。

5. 归档与重命名: 底层引擎默认将文件写死在 test_auto_generated.py。如果代码正常，你需要使用 shell 命令将该文件重命名为具有业务语义的名称，例如 mv test_cases/test_auto_generated.py test_cases/test_login_failure.py。

6. 运行验收: 执行 pytest test_cases/test_login_failure.py 验证脚本的可执行性。

# ⚠️ 注意事项与约束

- 千万不要手动修改生成的 test_cases/*.py 中的 UI 定位器（如 d(text="...").click()），因为底层环境和 UI 结构可能与你想的不同。一定要依靠 agent_cli.py 驱动手机自动生成！

- 在编写 --goal 时，一定要明确写出最后的断言是什么。例如：“最后需要断言页面上出现了'登录成功'的文字”。