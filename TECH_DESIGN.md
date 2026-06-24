# 错题Pro — 技术方案文档（TECH DESIGN）

> 版本：v1.4 | 对应PRD：v1.4 | 已部署：https://mistake-pro.zeabur.app

---

## 一、商业模式与合规分析

### 1.1 双版本策略

产品分两个版本，同一后端，同一数据引擎，差异仅在表现层：

| | **基础版（标准版）** | **趣味版（升级版）** |
|---|---|---|
| **定位** | 纯粹高效的错题管理学习工具 | 在基础版功能上叠加游戏化动机层 |
| **目标用户** | 高年级学生（初中/高中）、自律性较强的学生、偏好简洁工具的家长 | 低年级学生（小学/初中）、需要外部动机驱动的学生 |
| **核心功能** | 错题录入(文字+OCR) → AI诊断 → 变式题练习 → 间隔复习 → 知识版图 → 家长报告 → 导出打印 | 基础版全部功能 + 回合制战斗游戏层 + 千人千面IP角色 + 知识征服地图 + 成就系统 |
| **界面风格** | 简洁、高效、偏工具型 | 游戏化、角色扮演、视觉冲击 |
| **AI引擎** | 完全相同 | 完全相同 |
| **数据库** | 共享数据模型，游戏相关字段仅在趣味版启用 ||

**版本隔离方式**：用户在 `profile.json`（CLI）或 `users` 表（服务端）中有一条 `version` 字段（`"basic"` | `"fun"`）。后端同一套代码，前端根据 version 渲染不同的 UI。API 层有一个 `GET /api/v1/user/version` 接口，前端据此决定加载哪套界面。

**升级路径**：基础版 → 趣味版（补差价升级，数据无缝迁移，游戏层即刻激活）

### 1.2 变现路径

**定价策略**：

| | 基础版 | 趣味版 |
|---|---|---|
| 免费试用 | 7天全功能试用 | 7天全功能试用 |
| 按月 | ¥XX/月 | ¥XX/月（比基础版高） |
| 按学期 | ¥XX/学期（约5个月） | ¥XX/学期 |

**主产品形态**：微信小程序，基础版和趣味版为同一个小程序内的两个模式（可在设置中切换/升级）。

**前置条件路径**：

```
现在（个人身份）          注册微信小程序（个人主体）→ 免费试用版上线
                                 ↓
                        积累种子用户，验证产品
                                 ↓
                        注册个体工商户（几百元，1-2周）
                                 ↓
完成商业化准备            微信认证（300元/年）
                                 ↓
                        开通微信支付
                                 ↓
                        上线基础版 + 趣味版双版本付费
```

### 1.2 引流策略（小红书 → 微信私域 → 小程序）

```
小红书内容引流          微信生态承接              产品交付
─────────────────     ─────────────────     ──────────────────

图文/视频内容    →    私信引导加微信     →    微信社群
错题诊断案例         个人微信/企业微信          打卡、答疑
学习方法分享    →    朋友圈运营          →    微信小程序
提分故事              产品体验邀请              （错题Pro）
AI效果展示                                →    免费 → 付费转化
```

**小红书内容方向**（MVP完成后启动，不在本次开发范围）：
| 类型 | 示例选题 |
|------|---------|
| 错题诊断案例 | "四年级学生这道分数题，AI一眼看出问题在通分" |
| 学习效果对比 | "抄两个月错题本 vs AI助手，期末差距有多大" |
| 家长共鸣 | "孩子一看到错题就烦，我用这招让他主动练习" |
| 知识干货 | "小学数学12个最易错知识点排行" |

### 1.3 合规

| 合规维度 | 分析 | 措施 |
|---------|------|------|
| **IP版权** | 系统内置动漫角色图片=侵权 | 系统绝不上传任何IP图片，默认用emoji/几何图形。IP图片由用户自行上传到自己的存储空间，用户协议声明责任归属 |
| **未成年隐私** | 14岁以下未成年人数据受《个人信息保护法》保护 | 首次设置由家长完成；隐私政策声明数据仅用于出题诊断；服务端仅存脱敏后的知识点统计数据 |
| **教育资质** | "错题Pro"属学习工具，非教学活动 | 宣传避免"AI辅导""AI老师"等表述；明确定位为"学习辅助工具" |
| **小程序合规** | 个人主体可上线但不能支付 | 免费版→个人主体；付费版→个体工商户后升级 |

### 1.4 合规文案（应用内展示）

---

#### 文案一：用户服务协议

```
《错题Pro用户服务协议》

更新日期：2026年6月13日
生效日期：2026年6月13日

欢迎使用错题Pro！本协议是您与错题Pro（以下简称"我们"）之间关于使用
错题Pro服务（以下简称"本服务"）的法律协议。

一、服务说明
错题Pro是一款AI驱动的学习辅助工具，帮助学生分析错题原因、
生成变式练习题、追踪知识点掌握情况。本服务不提供课程教学，不替代
学校教育和教师指导。基础版提供核心错题管理功能，趣味版额外提供
游戏化学习体验。

二、用户注册与使用
1. 您应提供真实、准确的个人信息（昵称、所在地区、年级、教材版本）。
2. 如果您是14周岁以下的未成年人，须由您的监护人阅读并同意本协议后，
   方可在监护人的指导下使用本服务。
3. 您应妥善保管账号信息，因账号泄露导致的后果由您自行承担。
4. 您不得利用本服务从事任何违法违规活动。

三、学习数据
1. 您上传的错题内容、作答记录等学习数据，仅用于为您提供AI诊断、
   生成变式题、生成学习报告等核心服务功能。
2. 我们不会将您的学习数据用于其他用户的训练或推荐。
3. 您可在设置中随时导出或申请删除您的全部数据。

四、AI生成内容说明
1. 本服务中的AI诊断结果、变式练习题等内容由人工智能模型生成，
   仅供学习参考，可能存在不准确之处。我们不对AI生成内容的绝对
   准确性做任何保证。
2. 如您发现AI生成的内容有误，可通过反馈渠道告知我们。

五、知识产权
1. 错题Pro的软件代码、界面设计、算法逻辑等知识产权归我们所有。
2. 您上传的错题内容的知识产权仍归您所有。
3. 未经授权，您不得对错题Pro进行反向工程、破解或修改。

六、IP图片声明（适用于趣味版）
1. 趣味版允许用户自行上传图片作为游戏角色。
2. 我们不在系统中内置任何受版权保护的动漫、影视、游戏角色图片。
3. 用户上传的IP图片仅供个人学习使用，不得用于商业传播。
4. 如权利人认为用户上传的图片侵犯了其合法权益，可联系我们，
   我们将在核实后依照相关法律法规予以处理。

七、免责声明
1. 本服务按"现状"提供，我们不保证服务完全无中断或无错误。
2. 因网络故障、第三方服务异常等不可抗力导致的服务中断，
   我们不承担责任，但将尽力恢复服务。
3. 您使用本服务产生的学习效果因人而异，我们不承诺特定的成绩提升。

八、协议修改
我们可能根据法律法规变化或产品迭代需要修改本协议。修改后的协议将在
应用内公告，继续使用本服务即视为同意修改后的协议。

九、联系方式
如有任何问题或建议，请联系：[联系邮箱待填写]
```

---

#### 文案二：隐私政策

```
《错题Pro隐私政策》

更新日期：2026年6月13日
生效日期：2026年6月13日

错题Pro（以下简称"我们"）深知个人信息对您和您的孩子的重要性。
本隐私政策将清晰说明我们如何收集、使用和保护您的个人信息。

一、我们收集哪些信息

1. 您主动提供的信息：
   - 学生昵称（非真实姓名，可使用化名）
   - 年级和教材版本（可在首页年级选择器中修改，用于确定出题难度和范围）
   - 学科选择（用于管理不同学科的错题，默认数学）

2. 使用过程中产生的信息：
   - 错题内容（题目文字、错误答案、错题照片）
   - 作答记录（对变式题的答案和正确性）
   - 知识点掌握度数据（由系统根据作答情况自动计算）

3. 设备信息：
   - 微信小程序运行时，微信平台会收集必要的设备标识信息
     （如OpenID），我们仅用于识别用户身份，不获取您的微信好友、
     朋友圈等社交信息。

二、我们如何使用这些信息

1. 错题内容和作答记录：用于AI诊断、生成变式练习题、批改反馈。
2. 年级和教材版本：用于确保AI出题难度适当、内容在课纲范围内。
3. 掌握度数据：用于生成家长报告、安排科学的复习计划。
5. 我们不会将您的数据用于：
   - 个性化广告投放
   - 出售或转让给第三方
   - 训练其他用户的AI模型

三、数据存储与安全

1. 您的学习数据存储在加密的云服务器上。
2. 我们采取行业标准的安全措施保护您的数据。
3. 您可随时导出全部数据，或在设置中申请永久删除。
4. 删除数据后，系统在30天内完成彻底清除，期间数据不会被使用。

四、未成年人保护

1. 如果您的孩子未满14周岁，请由监护人完成初始设置并阅读本隐私政策。
2. 我们仅收集提供核心学习功能所必需的最少信息。
3. 我们不会利用未成年人的学习数据进行用户画像或行为分析。

五、家长权利

作为监护人，您有权：
1. 查看孩子的学习报告和知识掌握情况
2. 导出孩子的错题数据和练习记录
3. 要求更正不准确的个人信息
4. 要求删除孩子的账户和全部数据

六、AI服务说明

本服务调用第三方AI服务商（Anthropic）的API完成错题诊断和题目生成。
我们仅将脱敏后的题目文本发送给AI服务商处理，不附带学生姓名、
学校等个人身份信息。AI服务商不会将发送的内容用于其模型训练。

七、政策更新

如本隐私政策发生重大变更，我们将在应用内以弹窗方式通知您。
继续使用本服务即视为同意更新后的隐私政策。

八、联系方式
如果您对本隐私政策有任何疑问，请联系：[联系邮箱待填写]
```

---

#### 文案三：首次启动综合告知

```
┌──────────────────────────────────────┐
│                                      │
│        欢迎使用错题Pro                │
│                                      │
│  在开始之前，请阅读并同意以下内容：    │
│                                      │
│  □ 我已阅读并同意《用户服务协议》     │
│    [点击查看全文]                     │
│                                      │
│  □ 我已阅读并同意《隐私政策》         │
│    [点击查看全文]                     │
│                                      │
│  □ 我是监护人 / 我已满14周岁          │
│    （如使用者未满14周岁，须由         │
│     监护人勾选此项并指导使用）         │
│                                      │
│  ┌────────────────────────────────┐  │
│  │         [ 同意并开始 ]         │  │
│  └────────────────────────────────┘  │
│                                      │
│  三个勾选框全部勾选后，按钮才可点击    │
└──────────────────────────────────────┘
```

### 1.5 产品命名说明

| | |
|------|------|
| 产品名称 | **错题Pro** |
| 基础版（标准版） | 错题Pro 基础版 — 纯粹高效的AI错题管理工具 |
| 趣味版（升级版） | 错题Pro 趣味版 — 叠加游戏化学习体验 |
| 品牌含义 | Pro = Professional，错题的Pro级管理。简洁有力，两个版本通用 |

---

## 二、系统架构

### 2.1 总览

```
┌─────────────────────────────────────────┐
│          微信小程序 (uni-app)             │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ 学生端       │  │ 家长端            │  │
│  │ 拍照/做题    │  │ 知识版图/报告     │  │
│  │ 战斗游戏     │  │ 错题浏览/导出     │  │
│  └──────┬──────┘  └────────┬─────────┘  │
└─────────┼──────────────────┼────────────┘
          │      HTTPS       │
┌─────────▼──────────────────▼────────────┐
│          FastAPI 服务端                  │
│  ┌──────────────────────────────────┐   │
│  │ 路由层 /api/v1/*                  │   │
│  │  ├─ auth/    (微信登录)          │   │
│  │  ├─ mistakes/(错题CRUD)          │   │
│  │  ├─ variants/(变式题生成/作答)    │   │
│  │  ├─ game/    (战斗会话)          │   │
│  │  ├─ report/  (家长报告)          │   │
│  │  └─ user/    (配置/科目/地区)    │   │
│  ├──────────────────────────────────┤   │
│  │ AI引擎层                          │   │
│  │  ├─ diagnosis.py  (诊断)         │   │
│  │  ├─ variants.py   (变式生成)     │   │
│  │  ├─ checker.py    (批改)         │   │
│  │  ├─ scheduler.py  (调度)         │   │
│  │  └─ prompts.py    (prompt模板)   │   │
│  ├──────────────────────────────────┤   │
│  │ Celery Worker (异步AI调用)        │   │
│  └──────────────────────────────────┘   │
│                                          │
│  PostgreSQL      Redis                   │
│  (Zeabur内置)    (Zeabur内置)            │
└──────────────────────────────────────────┘
          │                    │
┌─────────▼──────┐  ┌─────────▼──────────┐
│  Anthropic API │  │  腾讯云COS          │
│  Claude Vision │  │  (照片/IP图片)      │
│  (AI + OCR)    │  │  (Zeabur静态文件)   │
└────────────────┘  └────────────────────┘
```

### 2.2 技术栈

| 层 | 选型 | 理由 |
|---|------|------|
| **小程序前端** | uni-app 3 + Vue 3 + uView Plus | 一套代码编译到微信小程序+H5，生态成熟 |
| **后端框架** | Python 3 + FastAPI | 和AI引擎同语言，async高性能，自动OpenAPI文档 |
| **异步任务** | Celery + Redis | AI调用耗时较长（3-15秒），异步处理不阻塞请求 |
| **数据库** | PostgreSQL 15 (Zeabur内置) | 生产级，JSON字段支持好，容易迁移 |
| **缓存** | Redis (Zeabur内置) | AI结果缓存、Session、Celery Broker |
| **文件存储** | Zeabur静态文件(MVP) → 腾讯云COS(后期) | 接口统一(URL)，切换无痛 |
| **AI** | Anthropic SDK (claude-sonnet-4-20250514) | 结构化JSON输出稳定 |
| **OCR** | Claude Vision API | 同一SDK，图片直传，OCR+诊断一次调用 |
| **部署** | Zeabur (新加坡，Tencent Cloud 2C 4GB) | 已有账号，git push自动部署 |

### 2.3 开发阶段与运行环境

```
Phase 1-2 (引擎闭环)
  本地CLI
  环境：macOS + Python 3
  数据库：本地SQLite
  AI：Anthropic API 直调
  存储：本地文件系统

Phase 3 (游戏层)
  本地CLI + Rich游戏界面
  环境同上
  SQLite 不变

Phase 4 (服务端上线)
  FastAPI 部署到 Zeabur
  PostgreSQL + Redis (Zeabur内置)
  IP图片迁移到 Zeabur静态文件
  uni-app 开发小程序前端
```

### 2.4 认证系统设计

**CLI阶段（Phase 1-3）**：本地密码认证

```
首次启动 → 设置昵称 + 密码 → pbkdf2哈希存储到 profile.json
后续启动 → 输入密码 → 比对哈希 → 进入主菜单
测试账号 → audit.py 初始化时写入
```

**`profile.json` 中的认证字段**：
```json
{
  "student_name": "小明",
  "password_hash": "pbkdf2:sha256:...",
  ...
}
```

**认证函数（auth.py）**：
- `create_account(name, password)` → 生成哈希，写入profile
- `login(password)` → 比对哈希，返回成功/失败
- `change_password(old, new)` → 验证旧密码，更新哈希
- `reset_account()` → 删除profile，重新设置

**服务端阶段（Phase 4+）**：JWT Token
- 微信小程序：微信登录openid免密
- Web管理后台：邮箱+密码 → JWT

**测试账号（audit.py 初始化时写入）**：
| 昵称 | 密码 | 用途 |
|------|------|------|
| `测试学生` | `test123` | 基础功能测试 |
| `demo` | `demo` | 演示账号 |

### 2.5 审计模块设计（audit.py）

**用途**：开发完成后自检，生成审计报告。

**审计项目**：
1. **文件完整性**：所有 `.py` 文件存在且可导入
2. **数据库**：4张表正确创建，CRUD正常
3. **Prompt**：三个prompt函数输出合法格式化字符串
4. **AI连接**：API Key配置有效，调用返回合法JSON（可选，需联网）
5. **认证**：创建账号、登录、密码变更正常
6. **集成**：`review_workflow()` 端到端（需AI Key）
7. **样例数据**：写入10道覆盖各年级/错误类型的测试错题

**运行方式**：
```bash
python audit.py              # 全部检查
python audit.py --quick      # 仅本地检查（不含AI调用）
python audit.py --seed       # 仅写入测试数据
```

**输出**：终端彩色报告 + `audit_report.json`

### 2.6 架构关键设计

**AI引擎无状态**：引擎层函数是纯函数（输入→输出），不持有数据库连接、不影响前端形态。CLI和小程序调用同一套函数。

**游戏层与引擎分离**：引擎返回结构化数据`{is_correct, feedback, hint, action_type}`，游戏层负责渲染。两者通过明确接口通信。基础版不接入游戏层，直接展示题目和反馈；趣味版调用游戏层做战斗渲染。MVP先落地基础版，游戏层作为后续迭代叠加。

**版本隔离轻量**：通过 `users.version` 字段（`"basic"` | `"fun"`）区分。后端同一套代码，接口不区分版本，前端根据版本字段决定渲染哪套UI。基础版和趣味版数据互通，升级只需改一个字段。

**数据库迁移路径清晰**：从SQLite→PostgreSQL只需改连接字符串和少量DDL语法差异。从Zeabur→自建服务器只需`pg_dump`导出和`COS`文件同步。

---

## 三、数据模型

### 3.1 PostgreSQL DDL

```sql
-- ============================================
-- 1. 用户表
-- ============================================
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    wx_openid       VARCHAR(64) UNIQUE,           -- 微信openid（CLI阶段可为NULL）
    student_name    VARCHAR(64) NOT NULL,
    province        VARCHAR(32) NOT NULL,          -- 省
    city            VARCHAR(32) NOT NULL,          -- 市
    district        VARCHAR(32) NOT NULL,          -- 区
    grade_level     VARCHAR(16) NOT NULL,          -- grade_1 ~ grade_12
    curriculum_ver  VARCHAR(32) NOT NULL DEFAULT '人教版',
    version         VARCHAR(16) NOT NULL DEFAULT 'basic',  -- 'basic' | 'fun' 版本类型
    avatar_url      VARCHAR(512),                  -- 头像URL（COS）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- 2. 用户科目（多选）
-- ============================================
CREATE TABLE user_subjects (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    subject         VARCHAR(16) NOT NULL,          -- 'math' | 'english' | 'chinese'
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(user_id, subject)
);

-- ============================================
-- 3. 错题表
-- ============================================
CREATE TABLE mistakes (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    subject         VARCHAR(16) NOT NULL,          -- 学科
    original_problem TEXT NOT NULL,                 -- 错题题目文本
    wrong_answer    TEXT NOT NULL,                  -- 学生的错误答案
    correct_answer  TEXT,                           -- AI确定的正确答案
    knowledge_point VARCHAR(128) NOT NULL,          -- 知识点（如"分数的通分"）
    error_type      VARCHAR(16) NOT NULL,           -- knowledge_gap | thinking_error | careless
    error_analysis  TEXT NOT NULL,                  -- AI诊断分析（给系统/家长）
    pool_status     VARCHAR(16) NOT NULL DEFAULT 'active',  -- active | observing | dormant
    photo_url       VARCHAR(512),                   -- 拍照原图URL（可为NULL，文字输入则无）
    grade_level     VARCHAR(16) NOT NULL,           -- 当时年级（快照，防止留级变化）
    curriculum_ver  VARCHAR(32) NOT NULL,           -- 当时教材版本（快照）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ                    -- 最后复习时间
);

CREATE INDEX idx_mistakes_user ON mistakes(user_id);
CREATE INDEX idx_mistakes_pool ON mistakes(pool_status);
CREATE INDEX idx_mistakes_kp ON mistakes(knowledge_point);

-- ============================================
-- 4. 变式练习题表
-- ============================================
CREATE TABLE variants (
    id              BIGSERIAL PRIMARY KEY,
    mistake_id      BIGINT NOT NULL REFERENCES mistakes(id),
    problem_text    TEXT NOT NULL,                  -- 变式题题目
    correct_answer  TEXT NOT NULL,                  -- 正确答案
    difficulty      VARCHAR(16) NOT NULL DEFAULT 'same',  -- easy | same | slightly_harder
    session_id      VARCHAR(36),                    -- 出题会话UUID（一次复习内的多题共享）
    is_original     BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE=原题重现（仅期中/期末）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_variants_mistake ON variants(mistake_id);

-- ============================================
-- 5. 作答记录表
-- ============================================
CREATE TABLE attempts (
    id              BIGSERIAL PRIMARY KEY,
    variant_id      BIGINT NOT NULL REFERENCES variants(id),
    user_id         BIGINT NOT NULL REFERENCES users(id),
    student_answer  TEXT NOT NULL,
    is_correct      BOOLEAN NOT NULL,
    same_error      BOOLEAN,                        -- 是否重复了原错题的错误模式
    feedback        TEXT NOT NULL,                  -- AI反馈文案
    hint            TEXT,                           -- 提示（如果重复错误）
    attempted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attempts_variant ON attempts(variant_id);
CREATE INDEX idx_attempts_user ON attempts(user_id);

-- ============================================
-- 6. 知识点掌握度表
-- ============================================
CREATE TABLE knowledge_mastery (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    subject         VARCHAR(16) NOT NULL,
    knowledge_point VARCHAR(128) NOT NULL,
    total_attempts  INT NOT NULL DEFAULT 0,
    correct_attempts INT NOT NULL DEFAULT 0,
    mastery_score   REAL NOT NULL DEFAULT 0.0,      -- 0.0 ~ 1.0 加权掌握度
    streak          INT NOT NULL DEFAULT 0,          -- 连续正确次数
    pool_status     VARCHAR(16) NOT NULL DEFAULT 'active',
    last_practiced_at TIMESTAMPTZ,
    next_review_at  TIMESTAMPTZ,                    -- 下次复习时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, subject, knowledge_point)
);

CREATE INDEX idx_mastery_user ON knowledge_mastery(user_id);
CREATE INDEX idx_mastery_review ON knowledge_mastery(next_review_at);

-- ============================================
-- 7. 家长报告快照表（避免每次实时计算）
-- ============================================
CREATE TABLE report_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id),
    report_type     VARCHAR(16) NOT NULL,           -- weekly | unit | midterm | final
    report_data     JSONB NOT NULL,                 -- 完整报告JSON（版图+判定+趋势+TODO）
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON report_snapshots(user_id);
```

### 3.2 数据模型设计要点

- **用户年级/教材快照**：`mistakes` 表中的 `grade_level` 和 `curriculum_ver` 是录入时的快照，而非指向 `users` 表的外键。学生升年级后，旧错题仍关联当时的年级，不会错乱。
- **session_id**：一次复习会话生成的所有变式题共享同一个UUID，方便统计"本次会话做对了几道、做错了几道"。
- **is_original**：标记变式题是否为原题重现（期中/期末复习时才可能为TRUE）。
- **report_snapshots**：家长报告的计算涉及多表JOIN和趋势对比，不需要每次打开实时算。定时生成快照，打开即看。

### 3.3 Phase 1-2 本地SQLite差异

CLI原型阶段用SQLite，差异仅在于：
- `BIGSERIAL` → `INTEGER PRIMARY KEY AUTOINCREMENT`
- `TIMESTAMPTZ` → `TEXT`（ISO 8601字符串）
- `JSONB` → `TEXT`（存JSON字符串）
- 无外键约束（SQLite需手动 `PRAGMA foreign_keys = ON`）

---

## 四、API 设计

### 4.1 接口总览

```
# 认证（CLI阶段本地，Phase 4服务端）
POST   /api/v1/auth/register      注册账号
POST   /api/v1/auth/login         登录（CLI:密码 / 服务端:微信code）
POST   /api/v1/auth/logout        登出
PUT    /api/v1/auth/password      修改密码

GET    /api/v1/user/profile       获取用户配置
PUT    /api/v1/user/profile       修改用户配置

POST   /api/v1/mistakes           上传错题（文字 or OCR确认后的文本）
GET    /api/v1/mistakes           获取错题列表（按学科/池状态/知识点筛选）
GET    /api/v1/mistakes/:id       获取单道错题详情

POST   /api/v1/review/start       开始一轮复习（返回变式题列表）
POST   /api/v1/review/:id/answer  提交某道变式题的答案（返回批改反馈）
GET    /api/v1/review/today       查看今日待复习知识点

GET    /api/v1/progress/heatmap   知识版图热力图（知识点×掌握度）
GET    /api/v1/progress/trend     掌握度趋势（较上一周期变化）
GET    /api/v1/report/weekly       周报快照
GET    /api/v1/report/unit         单元报告快照
GET    /api/v1/report/final        期末报告快照

GET    /api/v1/export/mistakes    导出错题集
GET    /api/v1/export/variants    导出变式题集

GET    /api/v1/game/status        获取游戏状态（地图/角色/敌人）
POST   /api/v1/game/battle/start  开始一场战斗
POST   /api/v1/game/battle/attack 答题攻击

POST   /api/v1/upload/photo       上传错题照片（OCR）
POST   /api/v1/upload/ip          上传IP图片
```

### 4.2 核心接口定义

#### POST /api/v1/mistakes

```json
// Request
{
  "subject": "math",
  "original_problem": "小明买了3/4千克苹果，吃了1/4千克，还剩多少千克？",
  "wrong_answer": "1/2",
  "photo_url": "https://xxx.cos.xxx/photo.jpg"   // 可选，拍照则有
}

// Response (异步，由Celery处理后返回)
{
  "mistake_id": 42,
  "knowledge_point": "分数的减法（同分母）",
  "error_type": "thinking_error",
  "error_analysis": "学生将分子分母分别相减...",
  "correct_answer": "1/2千克 = 2/4千克，3/4 - 1/4 = 2/4 = 1/2千克，但学生可能...",
  "pool_status": "active"
}
```

#### POST /api/v1/review/start

```json
// Request
{
  "subject": "math"
}

// Response（系统根据调度器决定本轮覆盖哪些知识点，每个知识点出几道）
{
  "session_id": "uuid-xxx",
  "total_questions": 4,
  "questions": [
    {
      "variant_id": 101,
      "problem": "小红有5/6米长的彩带，用去了1/6米，还剩多少米？",
      "difficulty": "easy",
      "knowledge_point": "分数的减法（同分母）"
    },
    // ... 共3-5道，覆盖到期待复习的知识点
  ]
}
```

#### POST /api/v1/review/:id/answer

```json
// Request
{
  "variant_id": 101,
  "student_answer": "2/3"
}

// Response
{
  "is_correct": true,
  "action_type": "correct",           // perfect | correct | wrong | same_error
  "feedback": "你对同分母分数的减法理解得很透彻，4/6化简成2/3也很到位！",
  "hint": null,
  "hp_change": { "hero": 0, "enemy": -3 }
}
```

### 4.3 异步处理策略

AI调用（诊断、生成变式、批改）耗时3-15秒，走Celery异步：

```
客户端请求 → FastAPI → 任务入Redis → 返回task_id
                                        ↓
                              Celery Worker → 调用Anthropic API
                                        ↓
                              结果写入数据库 + Redis缓存
                                        ↓
客户端轮询 GET /api/v1/tasks/:id → 返回结果
```

对于CLI阶段，因为是本地单用户，异步处理仍建议实现（避免终端阻塞），但不强制。

---

## 五、AI Prompt 模板

所有prompt在代码中为Python函数，接收参数返回格式化字符串。系统角色通过`system`参数传入。

### 5.1 诊断Prompt

```python
DIAGNOSIS_SYSTEM = """你是一位有20年经验的数学教师，擅长错误分析和知识点定位。
你只输出合法的JSON对象，不输出其他任何文字。"""

def diagnosis_prompt(problem: str, wrong_answer: str, grade_level: str, curriculum: str) -> str:
    return f"""请分析以下学生的错误。

=== 学生信息 ===
年级：{grade_level}
教材版本：{curriculum}

=== 错题 ===
题目：{problem}
学生的错误答案：{wrong_answer}

=== 你的任务 ===
1. 确定这道题考察的精确知识点（如"分数的通分""两位数乘一位数的进位乘法"）。请具体到单元级别。
2. 判断错误类型，必须从以下三个中选择一个：
   - knowledge_gap：学生从根本上没理解这个概念
   - thinking_error：学生理解概念但思路或方法选错了
   - careless：思路正确但计算/读题过程中粗心出错
3. 写一段分析（给系统和家长看的，不会展示给学生）：学生具体的思维偏差是什么？
4. 给出正确答案。

=== 输出格式 ===
只返回JSON，不要markdown代码块：
{{"knowledge_point": "...", "error_type": "knowledge_gap|thinking_error|careless", "error_analysis": "...", "correct_answer": "..."}}"""
```

### 5.2 变式生成Prompt

```python
VARIANT_SYSTEM = """你是一位创意数学题设计师，善于针对特定知识盲区设计变式练习题。
你只输出合法的JSON数组，不输出其他任何文字。"""

def variant_gen_prompt(
    knowledge_point: str,
    error_type: str,
    error_analysis: str,
    grade_level: str,
    curriculum: str,
    difficulty: str,          # easy | same | slightly_harder
    count: int,
    is_midterm_review: bool = False   # 期中期末可穿插原题
) -> str:
    return f"""请为一位{grade_level}学生（{curriculum}）设计{count}道变式练习题。

=== 背景 ===
目标知识点：{knowledge_point}
学生的错误类型：{error_type}
错误分析：{error_analysis}

=== 设计要求 ===
{"- 如果需要，可以穿插1道与目标知识点直接相关的真题/经典题，帮助学生练熟真题。" if is_midterm_review else ""}
- 难度：{difficulty}
- 改变题目场景、人物、具体数字、表述方式
- 保持同一个知识点的考察核心不变
- 题目彼此之间要有明显差异（不能只改数字）
- 适合{grade_level}学生的阅读和理解水平
- 题目内容积极健康，符合社会主义核心价值观

=== 输出格式 ===
只返回JSON数组，不要markdown代码块：
[{{"problem": "题目文本", "correct_answer": "正确答案", "difficulty": "{difficulty}"}}]"""
```

### 5.3 批改Prompt

```python
CHECKER_SYSTEM = """你是一位温暖、鼓励的数学导师。
你给出具体、可操作的反馈（2-4句话），始终输出合法的JSON对象。"""

def answer_check_prompt(
    problem: str,
    correct_answer: str,
    student_answer: str,
    knowledge_point: str,
    error_analysis: str
) -> str:
    return f"""请评价学生的作答。

=== 题目 ===
{problem}
正确答案：{correct_answer}

=== 学生作答 ===
学生的答案：{student_answer}

=== 背景 ===
知识点：{knowledge_point}
该学生此前在这个知识点上犯过的错误模式：{error_analysis}

=== 你的任务 ===
1. 判断答案是否正确。要接受等价的表达形式（如0.5 = 1/2 = 50%）。
2. 如果答案是错误的：
   - 判断是否重复了之前描述的错误模式（same_error_pattern）
   - 写2-4句鼓励性的反馈，指出思考方向但不直接给出答案，以一个问题收尾引导学生
   - 提供一个具体的提示（hint），帮助学生找到正确路径
3. 如果答案是正确的：
   - same_error_pattern 设为 null
   - 写2-4句具体的表扬，指出学生对哪个概念或步骤理解得好
   - hint 设为 null
4. 反馈中不要出现任何暗示"你上次也错了""这是你之前错过的题"的表述
5. 根据作答质量给出 action_type：
   - "perfect"：完全正确且过程清晰
   - "correct"：答案正确
   - "wrong"：答案错误，和新错误有关
   - "same_error"：答案错误，且重复了之前的错误模式

=== 输出格式 ===
只返回JSON：
{{"is_correct": true/false, "same_error_pattern": true/false/null, "feedback": "...", "hint": "...或null", "action_type": "perfect|correct|wrong|same_error"}}"""
```

### 5.4 OCR + 诊断合一的Prompt

```python
OCR_DIAGNOSIS_SYSTEM = """你是一位教育经验丰富的数学教师。
你先识别图片中的题目文字和学生答案，再对错误进行诊断分析。
你只输出合法的JSON对象。"""

def ocr_diagnosis_prompt(grade_level: str, curriculum: str) -> str:
    return f"""请仔细观察这张图片，它是一道学生做错的数学题。

=== 第一步：OCR识别 ===
从图片中提取：
1. 题目的完整文字内容
2. 学生写在图片中的答案（可能是手写的，请尽可能准确识别）

=== 第二步：错因诊断 ===
基于识别出的题目和错误答案，进行诊断：
1. 确定这道题考察的精确知识点
2. 判断错误类型（knowledge_gap | thinking_error | careless）
3. 分析具体的思维偏差
4. 给出正确答案

=== 学生信息 ===
年级：{grade_level}
教材版本：{curriculum}

=== 输出格式 ===
只返回JSON：
{{
  "ocr_problem": "识别到的题目文字",
  "ocr_student_answer": "识别到的学生答案",
  "knowledge_point": "...",
  "error_type": "knowledge_gap|thinking_error|careless",
  "error_analysis": "...",
  "correct_answer": "..."
}}"""
```

### 5.5 家长报告生成Prompt（Phase 4）

```python
REPORT_SYSTEM = """你是一位资深教育顾问，善于用家长能理解的语言解读学习数据。
你的建议具体、可操作，不说空话。你只输出合法的JSON对象。"""

def parent_report_prompt(
    student_name: str,
    grade_level: str,
    subject: str,
    knowledge_data: str,    # JSON化的知识点掌握数据
    period_label: str       # "第8周（期中）"
) -> str:
    return f"""请根据以下学习数据，为家长生成一份学习诊断报告。

=== 基本信息 ===
学生：{student_name}
年级：{grade_level}
学科：{subject}
报告周期：{period_label}

=== 知识点掌握数据 ===
{knowledge_data}

=== 你的任务 ===
1. 识别出需要重点关注的知识点（掌握度<70%），每个给出一句趋势解读
2. 对每个薄弱知识点，生成：
   - 一个具体的生活化学习活动建议（A类TODO）
   - 一句家长可以跟孩子聊的话（B类TODO）
3. 识别进步最大的知识点（提升>10%），给出表扬建议
4. 生成整体掌握度判定和节奏建议（C类TODO）

=== 输出格式 ===
只返回JSON：
{{
  "overall_mastery": 76,
  "overall_trend": "+4%",
  "weak_points": [
    {{
      "knowledge_point": "分数加减法",
      "mastery": 45,
      "trend": "+10%",
      "qualitative": "仍未掌握",
      "trend_interpretation": "趋势向上说明练习在起作用",
      "activity_todo": "用切披萨帮孩子理解通分，15分钟",
      "talk_todo": "最近分数加减法有没有觉得比之前顺手一点了？",
      "rhythm_todo": "本周安排2-3次5分钟练习"
    }}
  ],
  "most_improved": [
    {{"knowledge_point": "乘除法", "trend": "+12%", "praise_tip": "可以适当表扬孩子的坚持"}}
  ]
}}"""
```

---

## 六、核心算法

### 6.1 分层退出 + 间隔重复

```python
# scheduler.py 核心逻辑

POOL_TRANSITION = {
    # (当前池, is_correct, consecutive_correct): (新池, 条件说明)
    ("active", True, 3):  "observing",   # 连续3次正确 + 间隔≥3天
    ("active", False, _): "active",       # 保持（重置streak）
    ("observing", True, 2):  "dormant",   # 连续2次抽查正确 + 间隔≥7天
    ("observing", False, _): "active",    # 下滑，重新激活
    ("dormant", True, _):  "dormant",     # 抽查通过，保持休眠
    ("dormant", False, _): "active",      # 假掌握，重新激活
}

INTERVALS = {0: 1, 1: 3, 2: 7, 3: 14, 4: 21, 5: 30}
# streak 5+ → 30天

def calculate_next_review(
    streak: int,
    mastery_score: float
) -> int:
    """返回距离下次复习的天数"""
    interval = INTERVALS.get(streak, 30)
    if mastery_score < 0.3:
        interval = max(1, interval // 2)
    elif mastery_score > 0.8:
        interval = int(interval * 1.5)
    return interval


def compute_mastery_score(
    total_attempts: int,
    correct_attempts: int,
    recent_5: list[bool]      # 最近5次的正确/错误
) -> float:
    """加权掌握度：近期权重0.7，历史权重0.3"""
    if total_attempts == 0:
        return 0.0

    recent_ratio = sum(recent_5) / len(recent_5) if recent_5 else 0
    historical_ratio = correct_attempts / total_attempts

    return round(0.7 * recent_ratio + 0.3 * historical_ratio, 2)


def get_due_knowledge_points(user_id: int) -> list[dict]:
    """查到期需复习的知识点"""
    return db.query("""
        SELECT * FROM knowledge_mastery
        WHERE user_id = %s
          AND pool_status IN ('active', 'observing')
          AND next_review_at <= NOW()
        ORDER BY mastery_score ASC
    """, (user_id,))


def plan_review_session(due_kps: list[dict]) -> list[dict]:
    """
    输入：到期待复习的知识点列表
    输出：本轮出题计划 [{'knowledge_point': ..., 'count': ...}, ...]
    规则：
    - 3-5道题/次
    - active池知识点优先，每个1-3道
    - observing池每个1道
    """
    plan = []
    remaining = 5  # 上限

    # active池优先
    active_kps = [kp for kp in due_kps if kp['pool_status'] == 'active']
    observing_kps = [kp for kp in due_kps if kp['pool_status'] == 'observing']

    for kp in active_kps:
        if remaining <= 0:
            break
        count = min(3, remaining)
        plan.append({'knowledge_point': kp['knowledge_point'], 'count': count})
        remaining -= count

    for kp in observing_kps:
        if remaining <= 0:
            break
        plan.append({'knowledge_point': kp['knowledge_point'], 'count': 1})
        remaining -= 1

    return plan
```

### 6.2 家长知识版图的上卷逻辑

```python
# progress.py 核心逻辑

def build_knowledge_heatmap(user_id: int, subject: str) -> dict:
    """
    三级上卷：
    知识点掌握度 → 知识模块掌握度 → 学科概览
    """
    # 1. 查所有知识点的掌握度
    rows = db.query("""
        SELECT knowledge_point, mastery_score, pool_status,
               total_attempts, correct_attempts, streak
        FROM knowledge_mastery
        WHERE user_id = %s AND subject = %s
    """, (user_id, subject))

    # 2. 按知识点 → 模块映射表归并
    # curriculum.json 中维护了 知识点→模块 的映射
    modules = aggregate_to_modules(rows)

    # 3. 计算模块级掌握度 = 该模块下所有知识点的平均 mastery_score
    for mod in modules:
        mod['mastery'] = avg(kp['mastery_score'] for kp in mod['points'])
        mod['qualitative'] = classify(mod['mastery'])  # 四档判定
        mod['trend'] = compute_trend(mod)              # 较上一周期变化

    return modules


def compute_trend(knowledge_point_data: dict) -> dict:
    """
    对比当前周期 vs 上一周期的掌握度变化
    周期根据 scheduler 的复习间隔定义
    """
    current = knowledge_point_data['current_mastery']
    previous = knowledge_point_data['previous_period_mastery']
    delta = current - previous
    return {
        'value': f"{'+' if delta>0 else ''}{delta * 100:.0f}%",
        'direction': 'up' if delta > 0.03 else ('down' if delta < -0.03 else 'flat')
    }
```

---

## 七、项目文件结构

```
错题Pro/
├── README.md
├── .env.example
├── .gitignore
│
├── backend/                         # FastAPI 服务端
│   ├── requirements.txt
│   ├── alembic/                     # 数据库迁移
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                  # FastAPI入口，路由注册
│   │   ├── config.py                # 配置管理（环境变量）
│   │   ├── database.py              # PostgreSQL连接池
│   │   ├── redis_client.py          # Redis连接
│   │   │
│   │   ├── api/                     # 路由层
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # /api/v1/auth/
│   │   │   ├── mistakes.py          # /api/v1/mistakes/
│   │   │   ├── review.py            # /api/v1/review/
│   │   │   ├── report.py            # /api/v1/report/
│   │   │   ├── export.py            # /api/v1/export/
│   │   │   ├── game.py              # /api/v1/game/
│   │   │   └── upload.py            # /api/v1/upload/
│   │   │
│   │   ├── engine/                  # AI引擎（核心，无状态）
│   │   │   ├── __init__.py
│   │   │   ├── prompts.py           # 所有prompt模板
│   │   │   ├── diagnosis.py         # 诊断 + OCR诊断
│   │   │   ├── variants.py          # 变式题生成
│   │   │   ├── checker.py           # 批改反馈
│   │   │   └── client.py            # Anthropic API调用封装
│   │   │
│   │   ├── services/                # 业务服务层
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py         # 间隔重复 + 分层退出
│   │   │   ├── progress.py          # 知识版图上卷 + 趋势
│   │   │   ├── report.py            # 家长报告生成
│   │   │   └── ocr.py               # OCR流程编排
│   │   │
│   │   ├── models/                  # Pydantic模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── mistake.py
│   │   │   ├── variant.py
│   │   │   ├── attempt.py
│   │   │   └── report.py
│   │   │
│   │   └── tasks/                   # Celery任务
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       └── ai_tasks.py          # AI调用异步任务
│   │
│   └── tests/
│       ├── test_prompts.py
│       ├── test_scheduler.py
│       ├── test_progress.py
│       └── test_api.py
│
├── frontend/                        # uni-app 小程序
│   ├── pages/
│   │   ├── index/                   # 首页/主菜单
│   │   ├── settings/                # 初始设置/修改配置
│   │   ├── mistakes/
│   │   │   ├── input/               # 录入错题（文字/拍照）
│   │   │   ├── confirm/             # OCR确认编辑
│   │   │   └── list/                # 错题列表
│   │   ├── review/
│   │   │   ├── battle/              # 战斗界面（核心）
│   │   │   ├── map/                 # 知识地图
│   │   │   └── result/              # 每日完成总结
│   │   ├── hero/                    # 英雄选择
│   │   └── parent/
│   │       ├── heatmap/             # 知识版图
│   │       ├── report/              # 家长报告
│   │       └── export/              # 导出
│   ├── components/                  # 通用组件
│   └── static/
│
├── cli/                             # Phase 1-2 CLI原型
│   ├── main.py                      # CLI入口
│   ├── cli.py                       # Rich界面
│   ├── game_ui.py                   # 游戏层
│   ├── db.py                        # SQLite（CLI专用）
│   ├── engine/                      # 与backend/engine/同步
│   └── tests/
│
├── data/
│   ├── regions.json                 # 省-市-区三级数据
│   └── curriculum.json              # 课程大纲（Phase 4填充）
│
└── docs/
    ├── PRD.md
    ├── TECH_DESIGN.md               # 本文档
    └── DESIGN.md                    # 设计方案文档
```

### 文件结构设计要点

- **`engine/` 目录完全共享**：CLI和backend的AI引擎用同一套代码（prompts.py, diagnosis.py, variants.py, checker.py, scheduler.py），可通过软链接或git submodule保持同步。
- **CLI是独立可运行的**：Phase 1-2可以脱离服务器跑完整闭环，数据走本地SQLite。
- **backend上线后CLI不退场**：作为本地调试、测试的工具保留。

---

## 八、部署方案

### 8.1 Zeabur 部署配置（v1.2 实际生效版）

```
项目结构（线上实际运行）：
  ├── run.py               # 唯一入口，所有业务逻辑
  ├── db.py / ai.py / prompts.py / scheduler.py  # 引擎模块
  ├── requirements.txt      # openai, fastapi, uvicorn, python-dotenv, python-multipart
  ├── Procfile             # web: python run.py
  └── .gitignore           # 排除 .env, .session, user_data/

Zeabur 服务配置：
  - Provider: python（自动检测）
  - Server：Tencent Cloud Tencent Singapore 2C 4GB
  - 入口：run.py（通过 Procfile: python run.py）
  - 端口：8080（环境变量 PORT=8080）

环境变量（Zeabur 控制台配置）：
  - DEEPSEEK_API_KEY=sk-xxx         # DeepSeek API Key
  - DEEPSEEK_BASE_URL=https://api.deepseek.com
  - PORT=8080

数据存储策略（容器兼容）：
  - 用户认证：内存字典 _users（持久化可选）
  - 错题/变式/答题：SQLite（/tmp/mistake_pro_data/user_data/{name}/mistakes.db）
  - Session：内存字典 _sessions + Cookie（sid）

v1.2 路由变更：
  - 底部导航从4Tab（首页/录入/版图/报告）改为3Tab（错题本/考点通/我的）
  - 新增：GET /home（重写为错题本布局）、GET /exam-points、GET /exam-point/{kp}、GET /profile
  - 新增：POST /generate-variants、POST /update-grade
  - 简化：POST /register（移除地区/年级/科目字段）
  - 保留：GET /map、GET /report、GET /mistakes（仍可通过URL访问）
  - 所有文件写入 try/except 静默跳过，确保在只读文件系统下不崩溃

构建/部署流程：
  1. git push → GitHub → Zeabur 自动检测 → pip install → python run.py
  2. 健康检查：GET / 返回 {"ok":true}
  3. 首次请求触发 _ensure() 初始化测试账号
  4. 已知踩坑：必须用 Procfile 指定 python run.py，不能依赖 Zeabur 自动检测 uvicorn

域名：https://mistake-pro.zeabur.app
```

### 8.1.3 v1.3 — 双引擎大改（OCR流水线 + 知识库）

```
错题识别引擎（4阶段流水线）：
  - 新增：pure_ocr_prompt() in prompts.py — 纯OCR文字提取（分离OCR与诊断）
  - 新增：pure_ocr_from_bytes() in ai.py — 调用DeepSeek Vision，MIME类型自动检测
  - 重写：_JS_OCR — 4阶段JS流程：ocrUpload → renderSelectionUI → confirmSelection
  - 重写：POST /mistake/ocr — 纯OCR返回题目列表[{question_index, question_text, student_answer, has_correction_mark, correction_text}]
  - 新增：POST /mistake/diagnose — 接收选中题目，逐题诊断+保存+生成变式题
  - 新增：selection UI组件 — .qcard/.qcheck/.qbadge-wrong/.sel-all-btn + 全选错题/全选所有
  - 修复：OCR MIME type从硬编码image/jpeg改为从上传文件自动检测

举一反三引擎（知识库驱动）：
  - 新增：knowledge_base表（db.py Schema）— 按年级/学科/教材存储知识点+例题
  - 新增：knowledge_base.py — generate_knowledge_tree/seed_knowledge_base/seed_all_grades/expand_knowledge_point/match_knowledge_point/get_few_shot_examples/get_kb_stats
  - 新增：variant_gen_prompt_with_examples() in prompts.py — few-shot变式题prompt
  - 增强：generate_variants() 支持 few_shot_examples 参数 — 查知识库取例题作为参考
  - 集成：所有变式题生成点（/mistake/diagnose, /mistake/new, /generate-variants）接入知识库
  - 新增：POST /admin/seed-knowledge-base — 一键种子1-12年级知识库
  - 新增：GET /admin/kb-stats — 知识库统计

其他改动：
  - /mistake/new（POST）支持 subject 参数（不再硬编码"math"）
  - goM() 手动录入同样传递当前选择的学科
```

### 8.1.4 v1.4 — 图片处理模式（摒弃OCR文字提取）

```
新文件：
  - image_utils.py — flatten_page()文档展平(OpenCV) + erase_handwriting()手写擦除(inpaint)
  - requirements.txt +opencv-python-headless +numpy

新函数（ai.py）：
  - analyze_homework() — 单次Vision API调用，返回手写区域+题目区域坐标

新端点：
  - POST /mistake/process-image — 展平→AI分析→擦除→返回处理图+区域坐标
  - POST /mistake/save-regions — 从处理图裁剪选中区域→保存图片+SQLite记录

新增依赖：
  - opencv-python-headless>=4.0.0：Canny边缘检测+透视矫正+inpainting
  - numpy>=1.24.0：数组运算
  - FastAPI StaticFiles mount：/static/ 目录服务

前端JS重写（_JS_OCR → 图片处理JS）：
  - processImage()：上传→调用/mistake/process-image→渲染处理图
  - renderProcessedUI()：处理图+"+"按钮覆盖层（绝对定位）
  - placeButtons()：根据区域坐标放置"+"按钮
  - toggleRegion(idx)：点选/取消区域
  - saveRegions()：发送选中区域到/mistake/save-regions裁剪保存

CSS新增：
  - .proc-img-wrap：relative容器
  - .proc-img：处理图，全宽响应式
  - .pbtn：28px圆形"+"按钮，绝对定位，z-index:5
  - .pbtn-sel：选中态绿色+勾号

数据存储：
  - 裁剪图存 saved/{subject}/crop_{timestamp}_{idx}.jpg
  - original_problem字段格式：IMAGE:saved/{subject}/crop_xxx.jpg
  - 错题本页面识别IMAGE:前缀，展示图片而非文字

技术要点：
  - 总耗时~5-7秒：展平<1s + AI分析3-5s + 擦除<1s
  - 图像压缩：处理后图片限制2048px长边，JPEG quality=80
  - 降级策略：AI分析失败返回空regions（不阻塞流程）
  - Python 3.12运行（Python 3.14无opencv预编译wheel）
```

### 8.2 未来迁移路径

```
Zeabur → 腾讯云：
  PostgreSQL  → pg_dump → 腾讯云 PostgreSQL（标准SQL，零代码改动）
  Redis       → redis-dump → 腾讯云 Redis（零代码改动）
  文件存储    → cos-sync → 腾讯云COS（只改URL前缀，一行配置）
  FastAPI     → 腾讯云轻量服务器/CVM（Docker Compose 一键部署）

代码改动量：仅改环境变量中的连接字符串和文件URL前缀，
          业务代码零改动。
```

---

## 九、关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | uni-app | 一套代码→小程序+H5，比纯微信原生开发复用度高 |
| 后端语言 | Python | Anthropic SDK首选语言，AI引擎不收语言税 |
| 数据库 | PostgreSQL | Zeabur内置，JSONB支持好，迁移标准 |
| 异步方案 | Celery + Redis | AI调用需异步，Celery生态成熟 |
| OCR | Claude Vision | 同SDK，一次调用OCR+诊断，不用额外接OCR服务 |
| CLI先行 | Python + SQLite | 零配置验证核心引擎，降低试错成本 |
| 文件存储 | Zeabur静态→COS | MVP够用，迁移只改URL |
| 认证 | 微信登录 | 小程序原生，无需开发注册登录 |
| 开源 | 不开源 | 不走GitHub路线，产品闭源商业化 |

---

## 十、开发顺序与技术风险

### 风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Claude Vision OCR对手写体识别不准 | 中 | 用户需手动修改，体验下降 | 确认编辑环节兜底，打印体优先 |
| AI返回非法JSON | 低 | 功能中断 | 重试2次 + try/except + 降级提示 |
| Zeabur新加坡到国内延迟高 | 中 | 小程序加载慢 | 静态资源CDN，API响应加loading动画 |
| 个转企微信认证被拒 | 低 | 付费功能延期 | 提前准备材料，预留2-4周缓冲 |
| uni-app兼容问题 | 中 | 某些组件在H5和小程序表现不一致 | MVP只做小程序，不做H5 |

### 建议开发时序

```
Phase 1（2-3天）  CLI + 引擎闭环  ← 最快验证AI出题质量
Phase 2（2-3天）  CLI + 调度      ← 验证时间维度方案
Phase 3（3-5天）  CLI + 游戏层    ← 验证动机方案
                 ↓ 种子用户试用
Phase 4（5-7天）  服务端 + 小程序  ← 正式上线
```
