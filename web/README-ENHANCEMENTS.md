# Learn Claude Code - 增强学习网站

## 🎉 新增功能

### 1. 现代化首页设计
- **Hero Section**: 渐变动画背景，动态特性卡片展示
- **进度追踪器**: 实时学习进度可视化，支持本地存储
- **知识图谱**: 交互式 12 节点环形图，展示完整学习路径
- **成就系统**: 8 个成就徽章，激励用户完成学习

### 2. 交互式组件
- **InteractiveCodeViewer**: 可展开/收起的代码查看器，支持语法高亮和行号
- **VersionComparisonCards**: 美观的版本对比统计卡片
- **SessionVisualization**: 每个章节的专属动画流程图

### 3. 动画效果
- Framer Motion 驱动的平滑过渡动画
- 悬停效果和微交互
- 渐入渐出动画
- 自定义 CSS 动画 (float, pulse-glow, shimmer)

### 4. 学习进度系统
- 本地存储学习进度
- 可视化进度条和统计
- 完成徽章解锁
- 自动追踪访问过的章节

### 5. 响应式设计
- 完美适配移动端、平板和桌面
- 自定义滚动条
- 触摸友好的交互

## 🎨 架构层次

项目按 5 个架构层次组织：

1. **Tools & Execution** (s01-s02): 工具与执行基础
2. **Planning & Coordination** (s03-s05, s07): 规划与协调
3. **Memory Management** (s06): 上下文压缩与记忆
4. **Concurrency** (s08): 并发与后台任务
5. **Collaboration** (s09-s12): 多智能体协作

## 🚀 快速开始

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:3000

## 📚 学习路径

### 阶段 1: 基础 (Tools Layer)
- **s01**: Agent 循环 - 理解核心 while 循环模式
- **s02**: 工具使用 - 添加工具处理器

### 阶段 2: 规划 (Planning Layer)
- **s03**: TodoWrite - 任务计划与提醒
- **s04**: 子智能体 - 上下文隔离
- **s05**: 技能加载 - 按需知识注入
- **s07**: 任务系统 - 依赖图与持久化

### 阶段 3: 记忆 (Memory Layer)
- **s06**: 上下文压缩 - 三层压缩策略

### 阶段 4: 并发 (Concurrency Layer)
- **s08**: 后台任务 - 非阻塞执行

### 阶段 5: 协作 (Collaboration Layer)
- **s09**: 智能体团队 - 邮箱与生命周期
- **s10**: 团队协议 - 请求 - 响应模式
- **s11**: 自主智能体 - 任务板轮询与自动认领
- **s12**: Worktree 隔离 - 目录级任务隔离

## 🏆 成就系统

完成特定目标解锁成就：

1. **First Step** ⭐: 完成第一个章节
2. **Tools Master** 🔧: 完成 Tools 层 (s01-s02)
3. **Master Planner** 🎯: 完成 Planning 层
4. **Memory Keeper** 🧠: 完成 Memory 层
5. **Team Player** 🏅: 完成 Collaboration 层
6. **Halfway There** ⚡: 完成 6 个章节
7. **Scholar** 📖: 完成全部 12 个章节
8. **Agent Legend** 🏆: 掌握完整 Harness 工程

## 💻 技术栈

- **Framework**: Next.js 16.1.6 (App Router)
- **UI**: React 19.2.3
- **Styling**: Tailwind CSS v4
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Markdown**: Unified + Remark + Rehype
- **Diff**: diff 库

## 📁 项目结构

```
web/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── [locale]/          # 国际化路由
│   │   │   ├── (learn)/       # 学习页面组
│   │   │   │   ├── [version]/ # 章节详情页
│   │   │   │   ├── compare/   # 版本对比
│   │   │   │   ├── layers/    # 架构层展示
│   │   │   │   └── timeline/  # 学习路径时间线
│   │   │   └── page.tsx       # 首页
│   │   └── globals.css        # 全局样式
│   ├── components/            # React 组件
│   │   ├── architecture/      # 架构图表
│   │   ├── code/              # 代码查看器
│   │   ├── diff/              # 差异对比
│   │   ├── docs/              # 文档渲染
│   │   ├── home/              # 首页组件
│   │   ├── layout/            # 布局组件
│   │   ├── simulator/         # 模拟器
│   │   ├── timeline/          # 时间线
│   │   ├── ui/                # UI 基础组件
│   │   └── visualizations/    # 可视化组件
│   ├── data/                  # 数据文件
│   │   ├── generated/         # 自动生成的数据
│   │   └── scenarios/         # 模拟器场景
│   ├── hooks/                 # React Hooks
│   ├── i18n/                  # 国际化
│   ├── lib/                   # 工具库
│   └── types/                 # TypeScript 类型
└── scripts/                   # 构建脚本
```

## 🌍 国际化

支持三种语言：
- **English** (en)
- **中文** (zh)
- **日本語** (ja)

语言切换通过顶部导航栏实现。

## 🔧 开发特性

### 内容提取
运行 `npm run extract` 会自动：
- 扫描 `agents/` 目录的 Python 文件
- 提取类、函数、工具定义
- 解析 `docs/` 目录的 Markdown 文档
- 生成 `versions.json` 和 `docs.json`

### 热重载
Turbopack 提供毫秒级热重载，开发体验流畅。

### 代码模拟
每个章节都有交互式模拟器，展示 Agent 循环的执行流程。

## 📊 统计数据

- **12** 个渐进式章节
- **5** 个架构层次
- **694** 行代码 (s12 最终版本)
- **16** 个工具 (最终版本)
- **3** 种语言支持
- **8** 个成就徽章

## 🎯 设计理念

1. **模型即智能体**: 代码只是提供环境的 Harness
2. **渐进式复杂性**: 每次只添加一个机制
3. **可视化优先**: 抽象概念通过图表和动画展示
4. **交互式学习**: 模拟器让理论变得可操作
5. **游戏化激励**: 成就系统保持学习动力

## 📝 学习建议

1. 按顺序学习 s01 → s12
2. 每章先阅读文档，再运行模拟器
3. 查看源码理解实现细节
4. 完成章节后标记为已完成
5. 解锁所有成就成为 Agent Legend!

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进学习体验！

## 📄 许可证

与主项目保持一致的许可证。
