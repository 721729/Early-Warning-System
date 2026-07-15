# 绿电哨兵 — 焚烧炉设备健康度监测平台

AI 设备故障预警系统 / 高能环境产业命题赛道 / 2026 AI 先锋人才大赛

---

## 项目简介

面向垃圾焚烧厂一线运维人员的设备健康度监测平台。基于 **腐蚀动力学 + AI 混合建模**（阿伦尼乌斯方程 × PatchTST），实现过热器高温腐蚀爆管的提前预警、趋势预测与运维建议生成。

核心命题：焚烧炉的命脉不在"发多少电"，而在"炉子不能停"。生态环境部令第 10 号规定炉温须 ≥850°C、污染物自动监测超标即违法。一次过热器爆管停炉 7~15 天，综合损失 200~400 万元。

**技术路线**：GitHub 原版 PatchTST（47 万参数）学习 15 参数正常工况模式。阿伦尼乌斯方程作为物理约束嵌入损失函数——AI 负责判断"是不是出事了"，化学方程负责解释"出了什么事、壁厚还剩多少"。两者双轨交叉验证。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🏠 实时总览 | 6 设备健康度 + 15 参数传感器面板 + 壁厚趋势图，每 3 秒自动推进 |
| ⚠️ 预警管理 | 三级预警（黄/橙/红），编辑/删除/状态变更，一键清空 |
| 📋 工单管理 | 自动生成预填工单，编辑/指派/状态切换，一键清空 |
| 🧠 AI 分析 | 消融实验结果、RevIN 开关对比、多参数检测说明 |
| 🔐 登录鉴权 | JWT + RBAC 四级权限，XSS 防护，输入校验 |
| 👥 用户管理 | Admin 专属：新建/改密/角色/禁用，admin 角色不可越权获取 |
| 📢 通知模块 | 管理员发布/编辑/删除，AI 预警自动推送 |
| 📋 审计日志 | 全操作留痕，INSERT-only 不可删改 |
| 🤖 AI 引擎 | 持久仿真实例 → 15 参数数据流 → PatchTST 实时推理 → 前端渲染 |

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 模型 | GitHub 原版 PatchTST (ICLR 2023, IBM Research, MIT), 47 万参数, no-RevIN |
| 物理约束 | 阿伦尼乌斯腐蚀方程 → 自定义 PhysicsLoss, λ=0.1 |
| 仿真引擎 | 耐久仿真实例，A=200(正常)→A=1500(异常加速7.5倍)，15 参数多模态输出 |
| 后端 API | FastAPI + SQLAlchemy, JWT + RBAC, 7 模块 20+ 端点 |
| 数据库 | MySQL 8.0 (Docker), 6 表 |
| 前端 | Vue 3 + Vite + ECharts, 6 页面工业暗色 UI |

## 模型来源 & 关键实验

| 问题 | 选择和依据 |
|------|-----------|
| 用什么模型？ | GitHub 原版 PatchTST (`yuqinie98/PatchTST`), ICLR 2023, MIT 开源 |
| RevIN 开/关？ | **关。** ON→loss 0.012 但 F1=0.04；OFF→loss 0.020 但 F1=0.86 |
| 阈值从哪来？ | **训练数据 99 分位自动计算**（`thresholds.json`），不手工调 |
| 为什么加物理约束？ | 故障样本稀少时防"壁厚不减反增"反物理预测 |

## 消融实验结果

| 指标 | 纯 AI | 物理+AI | 效果 |
|------|-------|---------|------|
| F1 | 0.863 | 0.855 | 持平 |
| **误报率** | 6.0% | **2.8%** | ↓53% |
| 漏报率 | 6.2% | 17.2% | ↑11pp |
| 物理一致性 | 100% | 100% | 均无反物理输出 |

**实时仿真检测**：正常 MSE ~0.00015，异常 MSE ~0.00057（3.8x），99 分位阈值自动分离。

⚠️ 免责声明：仿真数据用阿伦尼乌斯方程生成，AI 用同一方程约束——当前验证的是**架构可行性**，不是模型准确性。真实场景需 Pilot 阶段用检修壁厚数据重新校准 A/Ea/m 参数。

## 快速开始

### 环境要求
- Linux / macOS, Python 3.12+, Docker, Node.js 18+

### 一键启动（推荐）

```bash
git clone https://github.com/721729/Early-Warning-System.git && cd green-power-sentinel
bash start.sh               # Docker + 后端 + 前端
# 浏览器 → http://localhost:3000  admin / admin123
```

### 手动启动

```bash
# 1. 生成仿真数据 + 训练模型
cd ml && pip install -r requirements.txt
python simulate.py && python train.py

# 2. 数据库 + 后端
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
│   ├── config.py                # 腐蚀参数 + 超参数
│   ├── thresholds.json          # 数据驱动阈值(99分位自动计算)
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
| 打开首页 | 仿真自动推进，每 3 秒 1 小时 |
| 点 ⏩ 快进到异常 | 跳至第 120 天异常段，AI 检出黄/橙预警 |
| 点 🔄 重置 | 仿真从头开始 |
| 点 ▶ 自动推进 | 切换自动/暂停模式 |

## 安全设计

- **CORS 白名单**：环境变量配置，公网部署改域名即可
- **JWT (HS256)**：2h 访问令牌 + 8h 刷新令牌
- **RBAC 四级权限**：中间件统一校验，admin 角色不可越权赋予
- **XSS 防护**：输入 html.escape + Pydantic 校验
- **SQL 注入防护**：SQLAlchemy ORM 参数化查询
- **安全响应头**：X-Content-Type-Options / X-Frame-Options / XSS-Protection

## 赛后 Pilot 计划

1. 仿真权重迁移至真实 DCS 数据微调
2. 检修壁厚数据校准阿伦尼乌斯参数 (A/Ea/m)
3. λ 参数扫描 (0.01~1.0) 最优平衡点
4. 边缘工控机离线推理验证
5. 验收：预警提前量 ≥7 天, 零漏报, 误报率 <10%

## License

MIT — 本项目代码可自由使用、修改、分发。依赖的 PatchTST 同为 MIT 协议。
