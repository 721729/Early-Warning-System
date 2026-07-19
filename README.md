# 绿电哨兵 — 焚烧炉设备健康度监测平台

AI 设备故障预警系统 / 高能环境产业命题赛道 / 2026 AI 先锋人才大赛

---

## 项目简介

面向垃圾焚烧厂一线运维人员的设备健康度监测平台。基于 **腐蚀动力学 + AI 混合建模**（阿伦尼乌斯方程 × PatchTST），实现过热器高温腐蚀爆管的提前预警、趋势预测与运维建议生成。

核心命题：焚烧炉的命脉不在"发多少电"，而在"炉子不能停"。生态环境部令第 10 号规定炉温须 ≥850°C、污染物自动监测超标即违法。一次过热器爆管停炉 10 天左右，综合损失数百万元。

**技术路线**：GitHub 原版 PatchTST（47 万参数）学习 15 参数正常工况模式。阿伦尼乌斯方程作为物理约束嵌入损失函数——AI 负责判断"是不是出事了"，化学方程负责解释"出了什么事、壁厚还剩多少"。两者双轨交叉验证。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🏠 实时总览 | 6 设备健康度 + 15 参数传感器面板 + 壁厚趋势图，每 3 秒自动推进 |
| ⚠️ 预警管理 | 三级预警（黄/橙/红），编辑/删除/状态变更，一键清空 |
| 📋 工单管理 | 自动生成预填工单，编辑/指派/状态切换，一键清空 |
| 📦 备件库存 | 6 种备件，admin 可编辑，库存不足红色预警 |
| 🧠 AI 分析 | 消融实验、RevIN 对比、多参数检测、数据驱动阈值 |
| 🔧 运维建议 | 三维交叉分析（腐蚀×HCl×壁厚×MSE），分级排程+库存检查 |
| 🔐 登录鉴权 | JWT + RBAC 四级权限，XSS 防护，输入校验 |
| 👥 用户管理 | Admin 专属：新建/改密/角色/禁用，admin 角色不可越权赋予 |
| 📢 通知模块 | 管理员发布/编辑/删除，AI 预警自动推送 |
| 🤖 AI 引擎 | 持久仿真实例 → 15 参数 → PatchTST 推理 → 前端实时渲染 |

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 模型 | GitHub 原版 PatchTST (ICLR 2023, IBM Research, MIT), 47 万参数, no-RevIN |
| 物理约束 | 阿伦尼乌斯腐蚀方程 → 自定义 PhysicsLoss, λ=0.1 |
| 仿真引擎 | 持久仿真实例，A=55 单一来源（`ml/config.py`），异常×30 / 危险×45 工况乘子，15 参数多模态 |
| 后端 API | FastAPI + SQLAlchemy, JWT + RBAC, 8 模块 25+ 端点 |
| 数据库 | MySQL 8.0 (Docker), 6 表 |
| 前端 | Vue 3 + Vite + ECharts, 7 页面工业暗色 UI |

## 模型来源 & 关键实验

| 问题 | 选择和依据 |
|------|-----------|
| 用什么模型？ | GitHub 原版 PatchTST (`yuqinie98/PatchTST`), ICLR 2023, MIT 开源 |
| RevIN 开/关？ | **关。** ON→loss 0.012 但 F1=0.04；OFF→loss 0.020 但 F1=0.86 |
| 阈值从哪来？ | **正常段 MSE 的 95/99/99.9 统计分位**（`ml/calc_thresholds.py` 自动重算 → `thresholds.json`），不手工调 |
| 为什么加物理约束？ | 故障样本稀少时防"壁厚不减反增"反物理预测 |

## 消融实验结果

| 指标 | 纯 AI | 物理+AI | 效果 |
|------|-------|---------|------|
| F1 | 0.863 | 0.855 | 持平 |
| **误报率** | 6.0% | **2.8%** | ↓53% |
| 漏报率 | 6.2% | 17.2% | ↑11pp |
| 物理一致性 | 100% | 100% | 均无反物理输出 |

**实时仿真检测**：正常 MSE ~0.00015，异常 MSE ~0.00098（6.4x 分离比），三级分位阈值自动分离。

### 三级预警阈值（数据驱动，BIZ-002）

| 等级 | 触发条件 | 统计含义 | 当前值 |
|------|---------|---------|--------|
| 🟡 yellow | MSE > p95 | 正常工况 5% 误报率 | 0.000186 |
| 🟠 orange | MSE > p99 | 正常工况 1% 误报率 | 0.000210 |
| 🔴 red | MSE > p99.9 **或** 壁厚 ≤ 1.3×最小允许壁厚 | 0.1% 误报率 / 物理红线 | 0.000272 / 3.9mm |

- 物理参数单一来源：`ml/config.py` 的 `MATERIAL_PARAMS`（T22: A=55）；异常工况用 `ANOMALY_ACCEL` 乘子（×1/×30/×45）表达，**不存在第二套 A 值**
- 物理腐蚀速率不参与等级门控（推理侧速率基于基准 A，对异常加速不可观测），用于 RUL/运维建议/展示
- **A 或乘子变更后必须重算阈值**：`.venv/bin/python ml/calc_thresholds.py`（seed=42 可复现，统计口径写入 `thresholds.json` 的 `physics` 字段可审计）

⚠️ 免责声明：仿真数据用阿伦尼乌斯方程生成，AI 用同一方程约束——当前验证的是**架构可行性**，不是模型准确性。真实场景需 Pilot 阶段用检修壁厚数据重新校准 A/Ea/m 参数。

## 快速开始

### 环境要求
- 仅兼容 Linux (Ubuntu 22.04+)，需 Docker + Python 3.12 + Node.js 18+

### 一键启动（推荐）

`start.sh` 内置环境检测——缺 Docker/Python/Node 会自动提示安装命令并询问是否安装。

```bash
git clone --recurse-submodules https://github.com/721729/Early-Warning-System.git && cd green-power-sentinel
cp .env.example .env        # 必需: 修改其中 CHANGE_ME 为强口令 (compose 无弱默认值, 缺 .env 拒绝启动)
bash start.sh               # 检测环境 → 一键启动 Docker + 后端 + 前端
# 浏览器 → http://localhost:3000  admin / admin123
```

### 手动启动

```bash
# 1. 生成仿真数据 + 训练模型
cd ml && pip install -r requirements.txt
python simulate.py && python train.py

# 2. 数据库 + 后端
cp .env.example .env        # 修改 CHANGE_ME 强口令
docker compose up -d
cd ../backend && pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# 3. 前端
cd ../frontend && npm install && npm run dev &
```

## 目录结构

```
green-power-sentinel/
├── ml/                          # AI 模型层
│   ├── simulate.py              # CSV仿真正向生成
│   ├── train.py                 # GitHub原版PatchTST训练
│   ├── ablation.py              # 消融实验完整指标
│   ├── inference.py             # 推理服务
│   ├── config.py                # 腐蚀参数(A单一来源) + 工况乘子 + 超参数
│   ├── physics.py               # 阿伦尼乌斯/三级阈值判定 唯一实现
│   ├── calc_thresholds.py       # 阈值重算脚本(物理参数变更后必跑)
│   ├── thresholds.json          # 数据驱动三级阈值(95/99/99.9分位)
│   └── PatchTST/                # 原版模型代码
├── backend/                     # API 层
│   ├── main.py                  # FastAPI入口 + CORS + 安全头
│   ├── models/                  # SQLAlchemy ORM (6表)
│   ├── routers/                 # auth/health/alert/predict/maintenance/users
│   ├── middleware/auth.py       # JWT + RBAC + 越权防护
│   └── services/
│       ├── inference_service.py # PatchTST权重加载 + 推理
│       └── realtime_sim.py      # 持久化仿真引擎
├── frontend/                    # Vue 3 前端 (6页面)
│   ├── src/views/
│   │   ├── Login.vue            # 登录页
│   │   ├── Dashboard.vue        # 总览(自动推进+快进+重置)
│   │   ├── AlertHistory.vue     # 预警记录(编辑/状态/删除/清空)
│   │   ├── WorkOrders.vue       # 工单管理(编辑/指派/状态/清空)
│   │   ├── AIAnalysis.vue       # AI分析(消融实验/多参数说明)
│   │   ├── AuditLog.vue         # 审计日志(只读)
│   │   └── UserManagement.vue   # 用户管理(admin专属)
│   └── src/api/request.js       # Axios + JWT拦截
├── docker-compose.yml
├── deploy/init.sql
├── start.sh / stop.sh
└── README.md
```

## 演示操作

| 操作 | 效果 |
|------|------|
| 打开首页 | 仿真自动推进，每 3 秒 1 小时，15 参数实时刷新 |
| 点 ⏩ 快进到异常 | 跳至异常段（14天高氯腐蚀），AI 检出黄/橙预警 |
| 点 🔴 危险工况 | Danger模式（60天，×45腐蚀加速乘子），壁厚跌破50%，RUL仅17天 |
| 点 🔄 重置 | 仿真从头开始 |
| 点 📋 运维建议 | 三维交叉分析（腐蚀×HCl×壁厚）+备件库存检查+排程 |

## 安全设计

- **CORS 白名单**：环境变量配置，公网部署改域名即可
- **JWT (HS256)**：2h 访问令牌 + 8h 刷新令牌
- **RBAC 四级权限**：中间件统一校验，admin 角色不可越权赋予
- **XSS 防护**：输入 html.escape + Pydantic 校验
- **SQL 注入防护**：SQLAlchemy ORM 参数化查询
- **安全响应头**：X-Content-Type-Options / X-Frame-Options / XSS-Protection

## 复赛落地规划

初赛已交付仿真驱动的完整Demo。复赛核心变化仅为数据源从仿真切换为真实DCS，
整体架构和AI模型无需重构。同时接入飞书两大能力：

1. 飞书消息机器人——橙/红预警Webhook推送卡片，值长厂长秒级接收
2. 飞书多维表格——预警/工单/健康度同步云端，管理层直接筛选穿透
3. 真实DCS对接 + 检修壁厚数据校准阿伦尼乌斯参数
4. 验收：预警提前量 ≥7 天, 零漏报, 误报率 <10%

### 飞书 AI 接入（PoC 计划）

8.3-8.16 复赛阶段基于飞书 Aily 平台构建"焚烧炉运维助手"，三个接入点：

- **飞书消息机器人**：Webhook 推送橙/红预警交互卡片（标题/正文/确认按钮），端点位 `/api/v1/feishu/push-alert` 已预留，模板见 `workdir/artifacts/feishu_alert_card.json`。
- **飞书多维表格**：API 同步预警/工单/健康度，端点位 `/api/v1/feishu/sync-alert` 已预留，schema 见 `workdir/artifacts/bitable_schema.md`。
- **飞书 AI 助手**：基于 Aily 平台 + 运维知识库（令第 10 号/GB 18485/DL/T 654/SOP），8.3-8.16 实现。

当前初赛阶段已通过架构预留 + 端点位 + 产物文件证明可行性。

## 测试覆盖

pytest 单元测试覆盖 4 个核心模块（运行命令：`pytest`，pytest.ini 已配置）：

| 测试文件 | 覆盖内容 |
|---------|---------|
| `backend/tests/test_auth.py` | JWT 登录/登出、密码哈希验证、token 黑名单 e2e |
| `backend/tests/test_rbac.py` | 四角色 × 接口允许/拒绝矩阵、旧中文角色 token 拒绝回归护栏 |
| `backend/tests/test_realtime_sim_physics.py` | 物理一致性（HCl/壁温/腐蚀速率单调性、A 单一来源 × 乘子） |
| `backend/tests/test_sim_concurrency.py` | 仿真并发安全（多线程推进一致性）+ RUL 滑动窗口过渡 |
| `ml/tests/test_physics.py` | 阿伦尼乌斯纯函数、三级阈值判定、RUL 置信区间、health_score 分段 |
| `ml/tests/test_thresholds_file.py` | thresholds.json 契约（三级分位有序、分离度、可审计性） |

CI: GitHub Actions（配置文件 `.github/workflows/test.yml`），push/PR 自动触发。

## 工程可复现性

- **物理参数 A 单一来源**：`ml/config.py` 的 `MATERIAL_PARAMS.T22.A=55`，训练/推理/实时仿真全仓库唯一来源（BIZ-001）
- **阈值自动重算**：`ml/calc_thresholds.py` 从正常段 MSE 分布算 95/99/99.9 分位，写入 `thresholds.json`（seed=42 可复现）
- **阈值文件可审计**：`thresholds.json` 含 `physics` 字段（A/Ea/工况乘子）+ `_disclaimer` 字段（仿真≠实测声明）
- **一键启动 + 环境检测**：`./start.sh` 自动检测 Docker/Python/Node，缺则提示安装并询问
- **强口令机制**：`.env.example` 强制改 `CHANGE_ME`，未改拒绝启动

## License

MIT — 本项目代码可自由使用、修改、分发。依赖的 PatchTST 同为 MIT 协议。
