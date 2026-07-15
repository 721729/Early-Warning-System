# 绿电哨兵 — 焚烧炉设备健康度监测平台

AI 设备故障预警系统 / 高能环境产业命题赛道 / 2026 AI 先锋人才大赛

---

## 项目简介

面向垃圾焚烧厂一线运维人员的设备健康度监测平台。基于 **腐蚀动力学 + 物理信息 AI 混合建模**，实现过热器高温腐蚀爆管的提前预警、趋势预测与运维建议生成。

核心命题：焚烧炉的命脉不在"发多少电"，而在"炉子不能停"。生态环境部令第 10 号规定炉温须 ≥850°C、污染物自动监测超标即违法。一次过热器爆管停炉 7~15 天，综合损失 200~400 万元。本方案以腐蚀动力学为技术底座，将阿伦尼乌斯方程嵌入深度学习损失函数，让 AI 在故障样本稀少的焚烧炉场景下实现低误报的异常检测。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| AI 模型 | **GitHub 原版 PatchTST** (ICLR 2023, IBM Research, MIT) | 47.4 万参数, 3层 Transformer, no-RevIN |
| 物理约束 | 阿伦尼乌斯腐蚀方程 → 自定义 PhysicsLoss | 嵌入训练循环, λ=0.1 |
| 仿真数据 | NumPy + Pandas, AR(1) 过程 + 噪声注入 | 6 个月分钟级, 16 字段 |
| 后端 API | FastAPI + SQLAlchemy + Pydantic | JWT 认证 + RBAC + 审计日志 |
| 数据库 | InfluxDB 2.7 / MySQL 8.0 / Redis 7 | Docker Compose 一键部署 |
| Vue 前端 | Vue 3 + Vite + ECharts + Axios | 登录 → JWT → 设备树 → 健康度剖面图 → 预警面板 |

## 功能特性

| 功能 | 说明 |
|------|------|
| 🔐 登录鉴权 | JWT + RBAC 四级权限（管理员/厂长/检修班长/值长），输入校验 + XSS 防护 |
| 🏠 实时总览 | 6 设备健康度进度条 + AI 异常得分 + 传感器数据 + 壁厚趋势图 |
| ⚠️ 预警管理 | 三级预警（黄/橙/红），AI 置信度标注，预估损失金额 |
| 🧠 AI 分析 | 消融实验结果表、RevIN 开关对比、15 参数传感器说明、阿伦尼乌斯参数校准方案 |
| 📋 审计日志 | 全操作留痕（登录/确认预警/创建工单），INSERT-only 不可删改 |
| 👥 用户管理 | 管理员专属：新建用户、修改密码、角色变更、启用/禁用（含越权防护） |
| 📢 通知模块 | 管理员发布通知，所有用户可见，XSS 输入过滤 |
| 🤖 AI 推理 | GitHub 原版 PatchTST（47 万参数）加载权重，实时推理腐蚀速率/异常得分/预警等级/RUL |

**全部组件开源、兼容 Linux。前后端已全面对接——前端每 5 秒从后端拉取 AI 推理结果，6 个设备健康度数据全部来自 PatchTST 模型。**

## 模型来源 & 关键实验

| 问题 | 我们的选择和依据 |
|------|-----------------|
| 用什么模型？ | GitHub 原版 PatchTST (`yuqinie98/PatchTST`), ICLR 2023 顶会论文, MIT 开源 |
| RevIN 开还是关？ | **关了。** 实测对比：RevIN=ON → loss 0.012 但异常检测 F1=0.04（几乎全漏）；RevIN=OFF → loss 0.020 但 F1=0.86。RevIN 是为预测设计的, 会抹除正常/异常的分布差异 |
| 为什么加物理约束？ | 焚烧炉故障样本稀少（一年爆管 1~2 次）, 纯 AI 在数据稀疏区域会输出"壁厚不减反增"这类反物理预测。阿伦尼乌斯方程（化学工程百年验证）作为物理约束正则项, 确保所有预测遵守腐蚀动力学 |

## 消融实验结果（GitHub 原版 PatchTST, 47.4 万参数, RevIN=OFF）

训练：前 100 天正常工况, 471 个 48h 窗口, 35 epochs。测试：后 80 天, 312 个窗口（含 120-134 天异常段）。

| 指标 | 纯 AI (λ=0) | 物理 + AI (λ=0.1) | 效果 |
|------|------------|-------------------|------|
| F1 分数 | 0.863 | 0.855 | 基本持平 |
| **误报率 FPR** | 6.0% | **2.8%** | **↓53% (砍半)** |
| 漏报率 FNR | 6.2% | 17.2% | ↑11pp（代价） |
| 准确率 | 93.9% | 94.2% | +0.3pp |
| 物理一致性 | 100% | 100% | 均无反物理输出 |

**结论：物理约束将误报率从 6.0% 压至 2.8%——砍掉一半以上。** 焚烧厂运维最大的痛点是"报警太多导致不信任 AI"——每月从 ~45 条假预警降到 ~21 条。代价是漏报率上升, 属精确率-召回率的标准权衡, λ 参数扫描可进一步优化。腐蚀误差 24% 和 RUL 偏差来源于阿伦尼乌斯 A 参数未在真实检修数据上校准——属 Pilot 任务。

## 快速开始

### 环境要求
- Linux (Ubuntu 22.04+) / macOS, Python 3.12+, Docker & Docker Compose

### 1. 克隆 & 环境

```bash
git clone https://github.com/721729/Early-Warning-System.git && cd green-power-sentinel
cp .env.example .env
uv venv && source .venv/bin/activate                # 或 python3 -m venv .venv
```

### 2. 生成仿真数据

```bash
cd ml
uv pip install -r requirements.txt                  # 或 pip install -r requirements.txt
python simulate.py          # → simulation_data.csv (82MB, 259K 行)
```

### 3. 训练模型（消融实验）

```bash
python train.py             # → model_b_pure.pth, model_c_fusion.pth (各 1.8MB)
python ablation.py          # → ablation_metrics.json（完整消融指标）
```

### 4. 一键启动（推荐）

```bash
bash start.sh               # Docker + 后端 + 前端全部启动
# 浏览器打开 http://localhost:3000  → admin / admin123
```

### 5. 或手动启动

```bash
docker compose up -d                              # 1. 数据库
cd backend && uv pip install -r requirements.txt  # 2. 后端依赖
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &  # 3. 启动后端
cd ../frontend && npm install && npm run dev &     # 4. 启动前端
```

## 目录结构

```
green-power-sentinel/
├── ml/                       # AI 模型层
│   ├── simulate.py           # 阿伦尼乌斯仿真正向生成 (AR1 + 噪声 + 异常注入)
│   ├── train.py              # GitHub原版PatchTST训练 (含物理约束loss)
│   ├── ablation.py           # 消融实验完整指标 (F1/FPR/FNR/RUL/物理一致性)
│   ├── inference.py          # 推理服务 (腐蚀速率 + 异常得分 + 预警等级 + RUL)
│   └── config.py             # 阿伦尼乌斯参数 + PatchTST超参数
├── backend/                  # API 层
│   ├── main.py               # FastAPI 入口 + CORS白名单 + 安全响应头
│   ├── models/               # SQLAlchemy ORM (6表)
│   ├── routers/              # auth/health/alert/predict/maintenance/users(含通知&用户管理)
│   ├── middleware/auth.py    # JWT解码 + Redis黑名单 + RBAC (4级权限+越权防护)
│   └── services/inference_service.py  # 加载PatchTST权重, 真实AI推理(阈值0.002)
├── frontend/                  # Vue 3 前端 (工业暗色UI)
│   ├── src/views/Login.vue    # 登录页 (XSS防护 + 自动填充禁用)
│   ├── src/views/Dashboard.vue # 总览 (6设备健康度+AI异常得分+趋势+预警, 每5秒拉取AI)
│   ├── src/views/AIAnalysis.vue # AI分析 (消融实验/RevIN对比/参数说明/校准方案)
│   ├── src/views/AlertHistory.vue # 预警记录
│   ├── src/views/AuditLog.vue # 审计日志 (只读)
│   ├── src/views/UserManagement.vue # 用户管理 (admin专属, 新建/改密/角色/禁用)
│   ├── src/router/index.js    # 路由守卫 (未登录→跳登录)
│   └── src/api/request.js     # Axios (自动带JWT, 401跳登录, users/notify API)
├── docker-compose.yml         # InfluxDB + MySQL + Redis 一键部署
├── deploy/init.sql            # 建表 + 默认管理员 (admin/admin123)
├── start.sh                   # 一键启动 (首次建表后续跳过)
└── stop.sh                    # 一键停止
```

## 一个月竞赛成果

- [x] 仿真数据生成 (6个月分钟级, 16字段, 含注入异常)
- [x] PatchTST 消融实验 (纯 AI/融合, F1=0.86, 物理约束降误报率 53%)
- [x] AI 阈值校准 (训练集 MSE 分布 → 95 分位阈值 0.002)
- [x] FastAPI 后端 (7 模块 20+ 端点, JWT + RBAC + XSS 防护 + 越权防护)
- [x] Vue 3 前端 (5 页面工业暗色 UI, 每 5 秒拉取 AI 推理, 6 设备健康度实时更新)
- [x] 前后端全面对接 (PatchTST 模型加载 → 推理 → API → 前端渲染)
- [x] 用户管理 + 通知模块 + 审计日志
- [x] Docker Compose 一键部署 + start.sh/stop.sh 脚本

## 安全设计

- **单向隔离网闸**：AI 平台不持有 DCS 反写通路——即使被完全攻陷也无法控制焚烧炉
- **OPC UA**：证书认证 + AES-256 加密, 拒绝自签名证书
- **JWT (HS256)**：访问令牌 2h, 刷新令牌 8h, 登出加入 Redis 黑名单
- **RBAC 四级权限**：值长 / 检修班长 / 厂长 / 管理员, 中间件统一校验
- **审计日志 INSERT-only**：应用层不可删改, 全操作留痕
- **SQL 注入防护**：SQLAlchemy ORM 参数化查询, 禁止字符串拼接
- **输入校验**：Pydantic 严格类型 + 范围校验, 非法输入 422 拒绝

## 赛后 Pilot 计划

1. 仿真权重迁移至真实 DCS 数据微调（冻结底层, 微调顶层）
2. 真实检修壁厚数据校准阿伦尼乌斯参数 (A / Ea / m)
3. λ 参数扫描 (0.01~1.0) 寻找误报率/漏报率最优平衡点
4. 边缘工控机离线推理验证 + 试运行闭环
5. 验收：预警提前量 ≥7 天, 零漏报, 误报率 <10%

## License

MIT — 本项目代码可自由使用、修改、分发，需保留原始版权声明。依赖的 PatchTST 模型同为 MIT 协议。
