# 快速开始指南

## 🚀 立即启动

```bash
# 进入 web 目录
cd web

# 安装依赖 (首次运行)
npm install

# 启动开发服务器
npm run dev
```

访问 **http://localhost:3000** 开始学习！

## 📖 学习路径

### 推荐学习顺序

1. **从首页开始** - 了解整体架构
2. **点击 "开始学习"** - 进入时间线
3. **按顺序学习 s01 → s12** - 渐进式掌握
4. **每章四步走**:
   - 📖 **Learn**: 阅读文档教程
   - ▶️ **Simulate**: 运行模拟器观察执行
   - 💻 **Code**: 查看源代码实现
   - 🔍 **Deep Dive**: 深入理解架构设计

### 12 个章节概览

| 阶段 | 章节 | 主题 | 核心概念 |
|------|------|------|----------|
| **Tools** | s01 | Agent 循环 | while 循环 + 工具调用 |
| | s02 | 工具使用 | dispatch map + 路径沙箱 |
| **Planning** | s03 | TodoWrite | 任务计划 + 提醒系统 |
| | s04 | 子智能体 | 上下文隔离 |
| | s05 | 技能加载 | 按需知识注入 |
| | s07 | 任务系统 | 依赖图 + 持久化 |
| **Memory** | s06 | 上下文压缩 | 三层压缩策略 |
| **Concurrency** | s08 | 后台任务 | 非阻塞执行 |
| **Collaboration** | s09 | 团队 | 邮箱 + 生命周期 |
| | s10 | 协议 | 请求 - 响应模式 |
| | s11 | 自主智能体 | 任务板轮询 |
| | s12 | 隔离 | worktree 任务隔离 |

## 🎯 使用技巧

### 进度追踪
- 完成章节后点击进度追踪器中的章节标记为已完成
- 进度自动保存到本地浏览器
- 随时查看学习进度统计

### 成就系统
解锁 8 个成就徽章：
- ⭐ First Step - 完成第 1 章
- 🔧 Tools Master - 完成 Tools 层
- 🎯 Master Planner - 完成 Planning 层
- 🧠 Memory Keeper - 完成 Memory 层
- 🏅 Team Player - 完成 Collaboration 层
- ⚡ Halfway There - 完成 6 章
- 📖 Scholar - 完成全部 12 章
- 🏆 Agent Legend - 掌握 Harness 工程

### 语言切换
点击右上角语言按钮切换：
- EN (English)
- 中文
- 日本語

### 暗色模式
点击太阳/月亮图标切换明暗主题

### 版本对比
在"Compare"页面选择两个版本，查看：
- 代码量变化
- 新增工具
- 新增类/函数
- 架构层变化

## 💡 学习建议

### 每章学习流程

1. **阅读文档** (Learn 标签)
   - 理解问题和解决方案
   - 查看流程图和架构图
   - 阅读代码示例

2. **运行模拟器** (Simulate 标签)
   - 点击 Play 观看自动执行
   - 使用 Step 单步调试
   - 观察消息数组增长

3. **查看源码** (Code 标签)
   - 阅读完整的 Python 实现
   - 注意新增的类和函数
   - 理解工具 handlers

4. **深入探索** (Deep Dive 标签)
   - 查看执行流程图
   - 理解架构设计
   - 阅读设计决策

### 实践练习

每章都有"Try It"部分，在本地运行：

```bash
cd learn-claude-code
python agents/s01_agent_loop.py
```

尝试文档中推荐的 prompts，观察 agent 的行为。

## 🎨 网站特性

### 可视化组件

- **知识图谱**: 首页的环形图展示 12 章关系
- **进度条**: 实时显示学习进度百分比
- **时间线**: 垂直布局展示学习路径
- **架构图**: 每章的组件关系图
- **执行流程图**: while 循环的可视化

### 动画效果

- 页面加载渐入动画
- 卡片悬停上浮效果
- 进度条平滑过渡
- 成就解锁动画
- 按钮点击反馈

## 🔧 开发相关

### 内容提取

```bash
# 手动运行内容提取
npm run extract
```

这会扫描 `agents/` 和 `docs/` 目录，生成：
- `versions.json` - 版本元数据
- `docs.json` - 文档内容

### 构建生产版本

```bash
npm run build
npm start
```

### 项目结构

```
web/
├── src/
│   ├── app/              # Next.js 路由
│   ├── components/       # React 组件
│   ├── data/            # 数据文件
│   ├── hooks/           # React Hooks
│   ├── i18n/            # 国际化
│   ├── lib/             # 工具函数
│   └── types/           # TypeScript 类型
└── scripts/             # 构建脚本
```

## ❓ 常见问题

**Q: 进度丢失了怎么办？**
A: 进度保存在浏览器 localStorage，清除缓存会重置进度。

**Q: 如何重置所有进度？**
A: 点击进度追踪器的"Reset"按钮。

**Q: 模拟器不工作？**
A: 确保已加载场景数据，刷新页面重试。

**Q: 代码高亮不显示？**
A: 某些代码块可能需要几秒加载，等待一下即可。

## 📚 更多资源

- 主项目 README: `../README.md`
- 增强功能文档: `README-ENHANCEMENTS.md`
- 项目总结: `PROJECT-SUMMARY.md`

## 🎉 开始学习吧！

现在访问 http://localhost:3000 开始你的 Harness Engineering 学习之旅！

记住核心理念：**"The model IS the agent. You're just building the vehicle."**
