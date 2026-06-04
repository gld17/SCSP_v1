# Round 0 验证总结 — scsp-v1-runnability-check

## 本轮验证内容
对 SCSP_v1 项目的前端网页服务和后端仿真引擎进行端到端可运行性验证。

## AC 推进情况

| AC | 状态 | 说明 |
|----|------|------|
| AC-1 | ✅ Verified | Web 服务已在 0.0.0.0:8000 运行；curl /api/health → {"status":"ok"}；GET / → HTTP 200 |
| AC-2 | ✅ Verified | 命令行单次仿真 exit 0，total_latency_s=9.51s；API 返回一致（误差 0%） |
| AC-3 | ✅ Verified | 命令行扫描 rows=3，latencies=[94.22,18.92,9.51]；API 返回一致 |
| AC-4 | ✅ Verified | 实验创建/列表/详情/重现实验全部通过；records.jsonl 存在且内容合法 |
| AC-5 | ✅ Verified | 前端 JS 事件绑定正确（btnRunSingle→single, btnRunSweep→sweep, btnExpStart→run）；所有 API 调用已在 AC-2/3/4 中验证；响应时间 < 60s |
| AC-6 | ⚠️ Partial | py_compile 全通过；test_astra_integration.py PASSED；test_experiment.py PASSED；test_web_api.py SKIPPED（环境缺少 fastapi testclient，非代码回归）；死测试文件已不存在 |

## 遗留问题

1. **test_web_api.py SKIP**：环境缺少 `fastapi.testclient`。不影响实际可运行性（Web 服务已验证正常），但测试覆盖率不完整。建议后续安装 `fastapi[all]` 或 `httpx` 以支持 TestClient。
2. **matplotlib 缺失**：sweep 命令行输出中包含 `plot_error: No module named 'matplotlib'`，导致无法生成扫描曲线图。不影响核心仿真功能。
3. **前端无头浏览器验证降级**：服务器无 playwright/chromium，AC-5 通过分析 JS 调用逻辑 + requests 模拟验证完成。如需完整前端自动化测试，需安装 playwright + chromium。

## Goal Tracker
- 6 条 AC 中，5 条完全 Verified，1 条 Partial（因环境问题而非代码问题）
- 无需进入下一轮 IMPL LOOP

## Lesson Delta
- Action: 在验证类任务中，环境依赖缺失（fastapi testclient, matplotlib, playwright）应标记为环境限制而非代码缺陷
- Lesson ID: ENV-DEPS-SKIP
- Notes: 生产/测试环境应预装 `fastapi[all]`、`matplotlib`、`pytest-playwright` 等依赖
