# Round 0 Summary

## 1. 本轮实现内容

- 修改 `run_web.py`，使用 `argparse` 增加 `--port` 参数。
- `--port` 类型为 `int`，默认值为 `8000`。
- 将解析出的端口传入 `uvicorn.run("scsp.web_api:app", host="0.0.0.0", port=args.port, reload=False)`。
- 保持 app、host、reload 参数不变。
- 将 `uvicorn` 导入延后到参数解析之后，使 `python3 run_web.py --help` 在当前缺少 `uvicorn` 的基础 Python 环境中也能正常显示帮助。

已执行验证：

- `python3 run_web.py --help`：通过，输出包含 `--port PORT`。
- `python3 -m py_compile run_web.py`：通过。

## 2. AC推进情况

- AC-1: NOT MET。本轮未安装或验证 fastapi/TestClient。
- AC-2: NOT MET。本轮未安装或验证 matplotlib/sweep 图表生成。
- AC-3: PARTIAL。已实现 `run_web.py --port` 参数，且 `--help` 可显示该参数；尚未在端口占用场景下启动服务并验证 `/api/health`。
- AC-4: PARTIAL。已验证 `run_web.py` 语法编译通过；尚未执行全部指定测试。
- AC-5: PARTIAL。本轮未安装依赖、未修改全局 Python 环境；尚未完成依赖声明或完整 git 状态审查。

## 3. 遗留问题

- 当前基础 `python3` 环境缺少 `uvicorn`，直接启动服务仍需要在包含项目依赖的环境中运行。
- 还需要安装/验证 fastapi 与 matplotlib，完成对应测试。
- 还需要验证端口 8000 被占用时使用其他端口启动，并检查新端口 `/api/health` 响应。
- 还需要补充端口排查说明：如何检查已有服务进程、停止已有进程、指定其他端口启动。

## 4. Goal Tracker 更新请求

- 请将 Round 0 记录为：已完成 `run_web.py` 自定义端口参数的最小实现与基础帮助/语法验证。
- 请将 AC-3 更新为 PARTIAL：命令行参数已实现，运行态端口占用验证和操作说明待补。
- 其他 AC 暂不标记完成。

## 5. Lesson Delta（Action / Lesson ID / Notes）

| Action | Lesson ID | Notes |
| --- | --- | --- |
| Add | SCSP-RUN-WEB-HELP-DEFER-IMPORT | 对入口脚本添加 CLI 参数时，若顶层运行依赖可能缺失，可将重依赖导入放在参数解析之后，保证 `--help` 可用并降低环境诊断成本。 |
