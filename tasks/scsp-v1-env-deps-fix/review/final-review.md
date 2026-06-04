# Final Review: scsp-v1-env-deps-fix

## 审查结论：APPROVE ✅

## 变更范围

- `run_web.py`：添加 `--port` 参数（argparse，默认 8000）
- `requirements.txt`：新增，记录 fastapi/uvicorn/matplotlib/httpx/pytest/pydantic/starlette
- `.venv/`：新增 fastapi 0.136.3、matplotlib 3.10.9、uvicorn 0.49.0、httpx 0.28.1、pytest 9.0.3（均通过 uv pip 安装到项目本地环境）

## 审查发现

| 发现 | 严重程度 | 状态 |
|------|---------|------|
| `StarletteDeprecationWarning`：starlette.testclient 提示使用 httpx2 替代 httpx | 低 | 不影响功能，可后续升级 starlette 消除 |
| run_web.py 将 `import uvicorn` 延后到参数解析之后 | 低 | 合理设计，保证 `--help` 在缺依赖环境下可用 |

## AC 验证结果

| AC | 状态 | 验证方式 |
|----|------|----------|
| AC-1 fastapi + test_web_api.py | ✅ Verified | pytest PASSED |
| AC-2 matplotlib + sweep plot | ✅ Verified | PNG 文件已生成 |
| AC-3 --port 参数 | ✅ Verified | port 8001 启动并响应 health |
| AC-4 无回归 | ✅ Verified | py_compile + pytest 全通过 |
| AC-5 环境隔离可追溯 | ✅ Verified | .venv 本地安装 + requirements.txt |

## 回归测试

```bash
# py_compile 语法检查
python3 -m py_compile scsp/*.py   # 通过

# 现有测试
pytest tests/test_web_api.py -v      # PASSED
```

## 是否推荐合并/保留

✅ **推荐保留**。改动最小化，无破坏性操作，无回归风险。
