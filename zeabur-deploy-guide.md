# Zeabur 部署手册（专属版）

> 基于 tiger-tennis 项目实战总结。适用机器：macOS，Node.js v24，GitHub 账号 dasoncdx，Zeabur 账号已充值。

---

## 一、核心原则（先读）

1. **Monorepo 不要整体部署到 Zeabur**：Zeabur 无法正确识别 `apps/backend` 子目录，会误判语言类型（我们踩坑：被识别为 Python 跑了 Uvicorn）。**解决方案：把后端单独建一个 GitHub 仓库部署。**

2. **前端静态文件**单独作为一个 Static 服务，需要 `index.html` 和 `Caddyfile` 手动维护。

3. **Prisma 7 的配置方式与旧版完全不同**，踩过多次坑，有专门章节说明。

4. **Hono 路由顺序**：具体路由必须在参数路由之前注册，这是一个反复出现的 bug 根源。

---

## 二、GitHub 推送配置

### 认证方式
GitHub 不支持密码推送，必须用 PAT（Personal Access Token）。

**生成步骤：**
1. 打开 https://github.com/settings/tokens/new
2. Note 随意填，Expiration 选 90 天，勾选 `repo`（整组）
3. 生成后复制 `ghp_` 开头的 token（只显示一次）

**使用方式：**
```bash
# 设置 remote 时把 token 嵌入 URL
git remote set-url origin https://dasoncdx:<TOKEN>@github.com/dasoncdx/<REPO>.git
git push -u origin main

# 推送成功后立即清除 token（安全）
git remote set-url origin https://github.com/dasoncdx/<REPO>.git
```

---

## 三、后端部署（Node.js + Hono）

### 3.1 必须单独建仓库

**不要**把 monorepo 整体推给 Zeabur 部署后端。

```bash
# 在临时目录准备独立后端仓库
mkdir /tmp/my-backend
cp -r apps/backend/. /tmp/my-backend/
cd /tmp/my-backend
git init && git branch -M main
git add -A && git commit -m "Initial backend"
git remote add origin https://dasoncdx:<TOKEN>@github.com/dasoncdx/my-backend-repo.git
git push -u origin main
```

确保独立仓库的根目录有：
```
├── src/
├── prisma/
│   ├── schema.prisma
│   └── prisma.config.ts   ← Prisma 7 必须有
├── package.json
├── tsconfig.json
└── zbpack.json            ← Zeabur 构建配置
```

### 3.2 zbpack.json（告诉 Zeabur 如何构建）

```json
{
  "build_command": "npm install && npx prisma generate && npx tsc",
  "start_command": "node dist/index.js",
  "node_version": "20"
}
```

### 3.3 tsconfig.json（关键配置）

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "CommonJS",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "strict": false,
    "outDir": "./dist",
    "rootDir": "./src",
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**坑：** `moduleResolution` 必须用 `"bundler"` 而不是 `"node"`，否则 TypeScript 5 会报 `TS5107` 错误导致构建失败。

### 3.4 package.json 关键字段

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "postinstall": "prisma generate"
  },
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
```

**坑：** `postinstall` 里加 `prisma generate`，确保 Zeabur 安装依赖后自动生成 Prisma Client。

### 3.5 Zeabur 环境变量（必须配置）

在 Zeabur 服务的「环境变量」里添加：

```
DATABASE_URL=postgresql://root:<密码>@<host>:<port>/zeabur
JWT_SECRET=your-secret-key
PORT=8080
```

### 3.6 Zeabur 部署步骤

1. Zeabur 控制台 → 进入项目 → 新建服务 → GitHub → 选择后端仓库
2. 出现「构建计划预览」时，确认显示：
   - **Provider**: `nodejs` ✅（如果显示 `docker` 或 `python` 就是识别错了）
   - **Framework**: `hono` ✅
3. 点「配置」→ 添加环境变量（见上）→ 下一步 → 部署
4. 部署成功后到「网络」标签 → 生成域名

**坑：** 如果 Provider 显示为 `python`（Uvicorn 在跑），说明 Zeabur 误识别了，原因通常是：
- 整个 monorepo 被推上来了（根目录有 `requirements.txt` 等 Python 文件）
- 解决：把后端抽成独立仓库

---

## 四、Prisma 7 配置（重要，与旧版完全不同）

### 4.1 prisma.config.ts（必须有这个文件）

```typescript
import 'dotenv/config'
import { defineConfig } from 'prisma/config'

export default defineConfig({
  schema: 'prisma/schema.prisma',
  datasource: {
    url: process.env.DATABASE_URL!,
  },
})
```

**坑：** Prisma 7 不再在 `schema.prisma` 里写 `url = env("DATABASE_URL")`，而是用 `prisma.config.ts`。如果还写在 schema 里会报 `P1012` 错误。

### 4.2 schema.prisma 里的 datasource

```prisma
datasource db {
  provider = "postgresql"
  // 不要写 url！url 在 prisma.config.ts 里
}
```

### 4.3 Prisma Client 初始化（src/lib/prisma.ts）

```typescript
import { PrismaClient } from '@prisma/client'
import { PrismaPg } from '@prisma/adapter-pg'

const adapter = new PrismaPg({
  connectionString: process.env.DATABASE_URL,
})

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

export const prisma =
  globalForPrisma.prisma ?? new PrismaClient({ adapter })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
```

依赖：
```bash
npm install @prisma/adapter-pg pg
```

### 4.4 新建表后的操作顺序

```bash
# 1. 本地修改 schema.prisma
# 2. 推送到数据库（需要 .env 里有 DATABASE_URL）
cd apps/backend
npx prisma db push

# 3. 重新生成 Prisma Client
npx prisma generate

# 4. 推送代码到 GitHub（Zeabur 会自动重新部署）
git push
```

**坑：** 如果生产环境的 Prisma Client 没有新 model（因为 generate 没跑），访问新表会报 500。
**兜底方案：** 新增表的 CRUD 用 `prisma.$executeRaw` 和 `prisma.$queryRaw` 直接写 SQL，完全绕过 Prisma Client 缓存问题：

```typescript
// 插入（ON CONFLICT 防重复）
await prisma.$executeRaw`
  INSERT INTO "MyTable" (id, "colA", "colB", "createdAt")
  VALUES (gen_random_uuid()::text, ${valA}, ${valB}, NOW())
  ON CONFLICT ("colA", "colB") DO NOTHING
`

// 查询
const rows = await prisma.$queryRaw<any[]>`
  SELECT t.id, t.name FROM "MyTable" t WHERE t."userId" = ${userId}
`
```

---

## 五、Hono 路由顺序（高频踩坑）

**规则：具体路径必须在参数路径之前注册。**

```typescript
// ✅ 正确顺序
app.get('/users/my-entries', handler)      // 具体路径先注册
app.get('/users/student-coach', handler)   // 具体路径先注册
app.get('/users/:id', handler)             // 参数路径后注册

// ❌ 错误顺序（/:id 会把 /my-entries 当成 id 的值）
app.get('/users/:id', handler)
app.get('/users/my-entries', handler)      // 永远不会被触发！
```

**症状：** 接口返回 404，但路由明明写了。检查是否被 `/:id` 截获。

---

## 六、前端部署（Taro H5 静态网站）

### 6.1 构建命令

```bash
# 必须在 apps/frontend 目录下执行
cd apps/frontend

# 使用根目录的 taro 二进制（不是全局安装的）
NODE_ENV=production /path/to/project/node_modules/.bin/taro build --type h5

# 构建完后手动复制 Caddyfile（taro copy 对无扩展名文件有 bug）
cp static/Caddyfile dist/Caddyfile
```

**坑：** 直接在根目录运行 `npx taro build` 会找不到配置文件，必须 `cd apps/frontend` 再跑。

### 6.2 static/ 目录（永远不要删这两个文件）

```
apps/frontend/static/
├── index.html    ← H5 入口页面
└── Caddyfile     ← Caddy 静态服务配置
```

**index.html 内容：**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
  <title>应用名称</title>
  <link rel="stylesheet" href="/css/app.css">
</head>
<body>
  <div id="app"></div>
  <script src="/js/352.js"></script>
  <script src="/js/app.js"></script>
</body>
</html>
```

> **注意：** `js/352.js` 的文件名每次构建可能不同，检查 `dist/js/` 目录确认实际文件名。

**Caddyfile 内容：**
```
:8080 {
    root * /usr/share/caddy
    try_files {path} /index.html
    file_server
}
```

**坑：** 端口必须是 `:8080`，Zeabur 静态服务映射的容器端口是 8080。

### 6.3 config/index.js 关键配置

```javascript
const path = require('path')
const isProduction = process.env.NODE_ENV === 'production'

const config = {
  // ... 其他配置 ...
  copy: {
    patterns: [
      { from: 'static/index.html', to: 'dist/index.html' },
      // Caddyfile 需要手动 cp，taro copy 对无扩展名文件有 bug
    ],
    options: {},
  },
  defineConstants: {
    'process.env.TARO_APP_API_URL': JSON.stringify(
      isProduction ? 'https://your-api.zeabur.app' : 'http://localhost:3001'
    ),
  },
}
```

### 6.4 强制提交 dist 到 Git

```bash
# dist 在 .gitignore 里，必须 -f 强制添加
git add -f apps/frontend/dist

git commit -m "Build frontend"
git push
```

### 6.5 Zeabur 静态服务部署步骤

1. 新建服务 → GitHub → 选择主仓库
2. 点「配置」→ **根目录填 `apps/frontend/dist`**（不是整个 frontend）
3. 直接部署
4. 部署后到「网络」标签 → 生成域名

**坑：**
- 根目录设置为 `apps/frontend/dist` 后，Zeabur 识别为 Caddy 静态服务（正确）
- 如果域名生成后访问 404，用 Zeabur 的「命令」终端进去执行 `caddy reload` 强制重载 Caddyfile
- 首次访问如果 404，刷新几次等 CDN 生效

---

## 七、数据库（PostgreSQL on Zeabur）

### 7.1 创建数据库服务

Zeabur 控制台 → 项目 → 新建服务 → **数据库** → 选 PostgreSQL → 等待启动

### 7.2 获取连接串

服务页面 → 服务状态 → 找「Connection String」那行 → 点右边复制图标

格式：`postgresql://root:<密码>@<IP>:<端口>/zeabur`

### 7.3 初始化数据库

```bash
# 设置好 .env 里的 DATABASE_URL 后
cd apps/backend
npx prisma db push        # 建表
npx tsx prisma/seed.ts    # 写入初始数据
```

---

## 八、watch 模式的坑

Taro 的 `--watch` 模式在 **Node.js v24 + webpack-virtual-modules** 下会崩溃：
```
TypeError: finalInputFileSystem._writeVirtualFile is not a function
```

**规避方案：** 开发时不用 `--watch`，手动重新构建。或者降级 Node 到 v20。

生产构建（无 watch）完全正常，不受此影响。

---

## 九、常见报错速查

| 报错信息 | 原因 | 解决方案 |
|---------|------|---------|
| `P1012: datasource.url is no longer supported` | Prisma 7 不支持在 schema 里写 url | 创建 `prisma.config.ts` |
| `Cannot find module '.prisma/client/default'` | Prisma Client 未生成 | `npx prisma generate` |
| `TS5107: moduleResolution=node10 is deprecated` | tsconfig 用了旧写法 | 改为 `"moduleResolution": "bundler"` |
| Zeabur 显示 Uvicorn 在运行 | 被识别为 Python 项目 | 把后端抽成独立仓库 |
| 接口 404 但路由写了 | Hono 路由被 `/:id` 截获 | 把具体路由移到 `/:id` 之前 |
| 接口 500，报 `studentCoachRelation.findMany` | 新表未在 Prisma Client 中 | 用 `$queryRaw` / `$executeRaw` 代替 |
| 前端 `index.html` 每次构建后消失 | `dist/` 被 taro 清空重建 | 把 `index.html` 放 `static/`，用 copy 配置 |
| GitHub push 鉴权失败 | 密码不再支持 | 用 PAT token 推送 |

---

## 十、部署检查清单

每次部署前过一遍：

**后端：**
- [ ] 是否在独立仓库（不是 monorepo 子目录）
- [ ] `prisma.config.ts` 存在且格式正确
- [ ] `zbpack.json` 存在
- [ ] Zeabur 环境变量已设置（DATABASE_URL / JWT_SECRET / PORT=8080）
- [ ] 新增表已执行 `npx prisma db push`
- [ ] Hono 新路由放在 `/:id` 之前

**前端：**
- [ ] `static/index.html` 和 `static/Caddyfile` 存在
- [ ] 在 `apps/frontend` 目录下执行构建
- [ ] 构建完后执行 `cp static/Caddyfile dist/Caddyfile`
- [ ] `git add -f apps/frontend/dist` 强制提交
- [ ] `dist/js/` 里的实际文件名与 `index.html` 里引用的一致

**Zeabur：**
- [ ] 后端服务 Provider 显示为 `nodejs`（不是 python/docker）
- [ ] 前端服务根目录设置为 `apps/frontend/dist`
- [ ] 两个服务都已生成公开域名
