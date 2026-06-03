# SCSP v0 设计文档（开发蓝图）

> 项目名称：`SCSP`（Spaceborne Computing Simulation Platform，天基计算仿真平台）  
> 文档定位：v0 版本总体技术方案与实施蓝图  
> 适用范围：指导研究型 Python 仿真内核与网页端可交互平台的一体化演进

---

## 1. 项目简介

### 1.1 SCSP 的定位

`SCSP` 是面向天基算力平台场景的仿真框架，重点研究“遥感星—计算大星”协同推理中，星间互联速率、模型负载特征与部署策略对任务时延及有效算力的影响规律。

### 1.2 v1 现状能力

当前 v1 版本已具备可运行的脚本化仿真能力，主要包括：

- 支持单点仿真与多带宽参数扫描（`link_bandwidth_gbps` 可为单值或列表）
- 支持 `1 遥感星 + 2 计算大星` 的双星流水线协同推理近似建模
- 支持通信时延建模（传播延迟 + 传输时间）
- 输出任务时延、有效算力与瓶颈阶段
- 输出 JSON/CSV 结果，并生成延时-带宽点线图

### 1.3 v2 建设目标

v2 的建设目标不是简单增加脚本数量，而是构建**网页端可交互仿真平台**，实现：

- 参数可视化配置
- 场景结构化管理与实验可复现
- 单点/扫参/批量实验的统一管理
- 多维度结果分析与导出
- 仿真引擎 API 化，前后端职责解耦

---

## 2. 当前 v1 逻辑梳理

### 2.1 研究场景与边界条件

当前 v1 重点场景如下：

- `1 遥感星 + 2 计算大星`
- 在轨推理，数据不上行回传地面
- 暂不考虑小星
- 暂不考虑星内互联带宽
- 暂不考虑排队延迟
- 暂不考虑复杂机会链路建链/重捕获过程

几何与构型背景约束：

- 计算星轨道高度：500 km
- 遥感星轨道高度：535 km（v1 尚未显式引入机会窗口建模）
- 编队模式：紧密（10 km）/分散（100 km）

### 2.2 v1 代码执行主流程

当前执行链路可归纳为：

1. `run_scsp.py` 读取 JSON 配置并构造 `V1SimulationConfig`
2. 根据配置执行单点仿真或 sweep 扫描
3. `simulator.py` 计算：
   - 样本数量（整景切块）
   - 通信时延（遥感星 -> 星1、星1 -> 星2）
   - 双星计算时延（按切分比例与利用率）
   - 3 阶段流水线 makespan
4. `analysis.py` 汇总 sweep 结果并识别性能拐点
5. 输出 `single.json`、`sweep.json`、`sweep.csv` 及延时-带宽图

### 2.3 通信建模口径

v1 当前链路时延模型为：

- 通信时延 = 传播延迟 + 传输时间
- 传播延迟由 `inter_sat_distance_km` 决定
- 传输时间由数据量与 `link_bandwidth_gbps` 决定
- 未纳入排队延迟

### 2.4 任务与数据口径

- 任务类型：遥感图像理解
- 整景近似：15 km × 15 km，0.5 m 分辨率
- 对应像素规模：约 `300000 × 300000`
- 默认切块粒度：`512 × 512`
- 每个 patch 作为基本推理单元

### 2.5 模型画像口径（资源画像）

v1 采用“模型资源画像”建模，而非真实模型执行器。

- `Qwen2.5-VL-7B`
  - 参数量：7B
  - 512×512 prefill：约 4 TFLOPs
  - prefill 中间激活：约 5 MiB（当前配置中也存在 2.2 MiB 实验值）
  - 单 token decode：约 14.3 GFLOPs
  - decode 中间激活：约 7 KiB
- `Qwen2.5-VL-72B`
  - 参数量：72B
  - 512×512 prefill：约 50 TFLOPs
  - prefill 中间激活：约 5 MiB
  - 单 token decode：约 143.5 GFLOPs
  - decode 中间激活：约 16 KiB

### 2.6 计算节点画像口径

- 单大星峰值算力目标：`>= 2 PFLOPS`
- v1 以利用率因子估算有效算力：
  - prefill 建议值：0.5
  - decode 建议值：0.2
- 当前代码以统一参数 `single_star_compute_utilization` 表示利用率，该口径属于等效工程建模，不代表硬件 benchmark。

### 2.7 部署方式口径

- 双星流水线并行
- 按模型深度 1:1 切分
- 暂不考虑张量并行
- 暂不考虑星内互联带宽

### 2.8 输出指标定义

当前 v1 指标如下：

- 任务时延：`total_latency_s`
- 有效算力：`effective_compute_flops` / `effective_compute_pflops`

定义口径：

- 有效算力 = 总任务计算量 / 总任务完成时间
- 任务时延由通信与计算共同构成（流水线 makespan）

### 2.9 当前结论示例

- 在部分 prefill 场景中，性能拐点约出现在 100 Gbps 附近（受模型画像、利用率、中间激活规模共同影响）
- 当瓶颈位于计算阶段时，提升带宽对总时延改善的边际收益显著降低

---

## 3. v1 的局限性

当前 v1 主要局限包括：

- 参数、逻辑与结果在脚本层耦合度较高
- 输入输出虽采用 JSON，但缺少统一 schema 与版本治理
- 实验管理能力不足（缺少实验注册、批量追踪、复现元数据）
- 缺少独立的结果管理层（目前主要为文件输出）
- 缺少网页交互层
- 链路建模偏静态（尚未支持机会链路/窗口链路）
- 尚未支持星内互联、星地链路、阴影区等扩展问题
- MoE active parameter 折减与 decode 全流程时延尚未系统纳入

---

## 4. v2 总体目标

v2 目标是建设“可配置、可复现、可扩展、可交互”的仿真平台，其核心目标包括：

- 前端可配置、后端可复现、结果可追踪
- 仿真引擎模块化并具备 API 化能力
- 支持单点、扫参、批量实验统一编排
- 支持多模型画像、多部署策略与多链路模式扩展
- 形成“研究可用 + 工程可持续”的平台化能力

---

## 5. v2 分层架构设计（A/B/C/D）

### A. 参数配置层

该层负责输入参数标准化、场景模板管理、参数校验与默认值管理。

配置域包括：

- 星座构型配置
  - 遥感星高度
  - 计算星高度
  - 计算星数量
  - 遥感星与计算星间距离
  - 计算星间距离
- 模型部署配置
  - 模型名称
  - 模型参数量
  - 预填充计算量
  - 解码计算量
  - 中间激活值大小
- 算力节点配置
  - 单节点峰值算力
  - prefill 利用率
  - decode 利用率
- 天基任务配置
  - 整景尺寸
  - 切块大小
  - 解码输出 token 数量
- 通信链路配置
  - 星间互联带宽
  - 遥感星—计算星链路模式（stable / intermittent）
  - 建链时间
  - 重捕获时间
  - 窗口长度（扩展预留）

### B. 仿真引擎层

该层是 v1 Python 脚本的核心演进对象。

- v1 目前可视为该层原型实现
- v2 需要完成模块化、函数化、接口化、结构化输入输出
- Web 前端与实验管理层应统一调用该层 API，而非直接调用脚本

### C. 实验与结果管理层

该层负责仿真任务编排与实验资产管理：

- 单点仿真
- 参数扫描
- 批量实验
- 实验保存与复现
- 场景模板管理
- 结果索引、对比与归档

### D. 可视化与交互层

该层负责平台可用性与分析表达能力：

- 网页参数配置界面
- 单次仿真结果展示
- 敏感性分析曲线
- 热力图
- 结果导出（CSV/JSON/图表）

---

## 6. 数据模型设计（建议）

建议在 v2 统一以下核心对象（可采用 `Pydantic` 或 `dataclass`）：

- `ScenarioConfig`
  - `scenario_id`, `scenario_name`, `description`
  - `constellation_config`, `task_config`, `deployment_config`, `link_config`
  - `created_at`, `version`
- `TaskConfig`
  - `image_type`, `image_resolution`, `tile_size`
  - `num_images`
- `ModelProfile`
  - `model_name`, `params_billion`
  - `prefill_flops_per_patch`, `decode_flops_per_token`
  - `prefill_activation_mib`, `decode_activation_kib`
  - `moe_enabled`, `active_parameter_ratio`
- `ComputeNodeConfig`
  - `node_type`, `peak_pflops`
  - `prefill_utilization`, `decode_utilization`
  - `power_limit_kw`
- `LinkConfig`
  - `bandwidth_gbps`
  - `distance_km`
  - `mode`（`stable` / `intermittent`）
  - `setup_time_ms`, `reacquire_time_ms`, `window_ms`
  - `latency_target_ms`
- `DeploymentConfig`
  - `parallelism_type`（pipeline/tensor/hybrid）
  - `pipeline_split_ratio`
  - `tensor_parallel_degree`（扩展预留）
- `SimulationResult`
  - `total_latency_s`, `effective_compute_pflops`
  - `data_tx_latency_s`, `inter_stage_latency_s`
  - `stage1_compute_latency_s`, `stage2_compute_latency_s`
  - `bottleneck_stage`
  - `target_met`, `target_margin_ms`（建议新增）
- `ExperimentRecord`
  - `experiment_id`, `scenario_id`
  - `run_mode`（single/sweep/batch）
  - `input_snapshot`, `result_files`, `status`
  - `started_at`, `finished_at`, `engine_version`

---

## 7. 仿真引擎模块化拆分建议

建议将引擎拆分为以下模块：

- `geometry` / `image`
  - 轨道几何、距离推导、整景切片、样本数量计算
- `model_runtime`
  - 模型画像、prefill/decode 负载、MoE active parameter 折减
- `communication`
  - 传播/传输时延模型、稳定链路与机会链路模型
- `deployment`
  - 流水线并行、切分策略、后续张量并行扩展
- `metrics`
  - 时延、有效算力、利用率、达标判定
- `experiment_runner`
  - 单点、扫参、批量任务执行与结果汇总

---

## 8. v2 网页端功能设计

建议页面与功能模块如下：

- 概览页
  - 平台简介、近期实验、关键指标概览
- 星座构型配置页
  - 星体数量、轨道高度、星间距离、编队模式
- 模型部署配置页
  - 模型画像选择（7B/72B/MoE）与部署策略配置（流水线切分）
- 算力节点配置页
  - 峰值算力、prefill/decode 利用率、功耗限制
- 通信链路配置页
  - 带宽、链路模式、建链/重捕获参数、窗口参数
- 实验运行页
  - 单点仿真、扫参、批量实验启动与状态跟踪
- 结果分析页
  - 延时-带宽曲线、有效算力曲线、热力图、瓶颈占比图
- 结果导出页
  - JSON/CSV/图表导出与实验复现信息

---

## 9. 当前代码改造建议（实施顺序）

> 本节仅给出实施路径，不在当前轮次执行大规模代码开发。

### 阶段 1：引擎 API 化与结构化输入输出

1. 固化 `run_simulation(config)` 与 `run_sweep(config)` 标准接口  
2. 引入统一配置 schema（含版本号与默认值治理）  
3. 将 CLI 层与引擎层解耦（CLI 专注 I/O 编排）

阶段 1 当前落地状态（已完成）：

- 新增引擎接口模块 `scsp/engine.py`，提供 `run_simulation`、`run_sweep`、`validate_bandwidth_input`
- 在 `scsp/config.py` 中新增配置归一化与校验入口（`normalize_raw_config`、`validate_raw_config`、`build_simulation_config`）
- `run_scsp.py` 改为调用引擎 API，CLI 仅负责参数读取、文件输出与绘图编排
- 增加 `schema_version` 规范字段（默认 `1.0`）以支持后续配置演进

### 阶段 2：模块重构

1. 将 `simulator` 拆分为 `task/model/communication/deployment/metrics` 子模块  
2. 将绘图、扫参与核心引擎彻底剥离  
3. 增加单元测试（通信时延、流水线 makespan、指标口径）

阶段 2 当前落地状态（已完成）：

- 新增模块：
  - `scsp/task.py`：任务载荷建模（样本数、单 patch 输入数据量）
  - `scsp/model.py`：双星切分计算时间建模
  - `scsp/deployment.py`：部署编排与流水线 schedule 封装
  - `scsp/metrics.py`：指标口径计算与结果对象组装
  - `scsp/visualization.py`：可视化逻辑（延时-带宽曲线）从 CLI 剥离
- `scsp/simulator.py` 改为编排层，按职责调用 `task/model/deployment/metrics`
- `run_scsp.py` 不再内联绘图实现，改为调用 `scsp.visualization`
- 新增基础测试：
  - `tests/test_communication.py`
  - `tests/test_deployment.py`
  - `tests/test_metrics.py`

### 阶段 3：实验管理层建设

1. 引入 `ExperimentRecord` 持久化（可先从 SQLite/JSONL 起步）  
2. 支持实验模板、批量运行与复现实验  
3. 增加结果比对与基线回归能力

阶段 3 当前落地状态（已完成）：

- 新增实验管理模块 `scsp/experiment.py`，包含：
  - `ExperimentRecord` 数据结构
  - `JsonlExperimentStore`（JSONL 轻量持久化）
  - `run_experiment`（单实验运行与记录）
  - `run_batch_experiments`（批量实验）
  - `reproduce_experiment`（复现实验）
  - `compare_result_summary`（基础结果比对）
- 新增模板机制：
  - `single_point`
  - `bandwidth_sensitivity`
- 新增实验 CLI：`run_experiment.py`
  - 支持单实验、批量实验、按实验 ID 复现
- 新增测试：`tests/test_experiment.py`，覆盖记录持久化与复现流程

### 阶段 4：Web 平台接入

1. 提供后端 API（建议采用 FastAPI）  
2. 实现前端参数配置、运行控制与结果可视化  
3. 完成结果导出、分享及必要权限管理

阶段 4 当前落地状态（已完成最小闭环）：

- 新增 FastAPI 后端：`scsp/web_api.py`
- 新增 Web 启动脚本：`run_web.py`
- 新增前端原型页面：`web/index.html`（纯 HTML+JS）
- 已开放 API：
  - `POST /api/simulations/single`：运行单点仿真
  - `POST /api/simulations/sweep`：运行参数扫描
  - `POST /api/experiments/run`：运行并保存实验记录
  - `GET /api/experiments`：获取实验列表
  - `GET /api/experiments/{experiment_id}`：获取实验详情
  - `POST /api/experiments/reproduce/{experiment_id}`：复现实验
  - `GET /api/experiments/{experiment_id}/export`：导出实验详情（JSON）
- 前端支持：
  - 参数配置（JSON 文本输入）
  - 运行控制（单点/扫描/保存实验）
  - 结果查看（结构化 JSON 展示）
  - 实验查询与复现
- 新增基础 API 测试：`tests/test_web_api.py`

本地启动方式（最小示例）：

```bash
python3 run_web.py
```

访问：

- `http://localhost:8000/`（前端原型页）
- `http://localhost:8000/docs`（FastAPI OpenAPI 文档）


## 10. 当前仓库参考结构（v1 现状）

```text
SCSP/
├── README.md
├── configs/
├── outputs/
├── run_scsp.py
└── scsp/
    ├── analysis.py
    ├── communication.py
    ├── config.py
    ├── io_utils.py
    ├── models.py
    ├── pipeline.py
    └── simulator.py
```

---

## 11. 结语

`SCSP` 早期脚本形态已具备研究型仿真所需的基础能力；当前 v0 目标是在此之上建设**平台化、可复现、可交互**的网页端能力。  
本文档明确了分层架构、数据模型与改造路径，可作为后续代码重构、接口建设与前端开发的统一技术依据。
