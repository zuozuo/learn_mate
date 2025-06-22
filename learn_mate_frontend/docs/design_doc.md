# Learn Mate Chrome 扩展系统设计文档

## 1. 项目概述

### 1.1 项目简介
Learn Mate 是一个基于 Chrome Extension Manifest V3 的智能学习助手扩展，旨在帮助用户更好地管理和追踪学习进度。项目采用现代化的前端技术栈，包括 React、TypeScript、Vite 和 Turborepo。

### 1.2 项目目标
- 提供智能化的学习辅助功能
- 优化用户的学习体验和效率
- 支持多种学习场景和个性化需求
- 构建可扩展的模块化架构

### 1.3 技术愿景
- 采用 Manifest V3 规范，确保与 Chrome 浏览器的最佳兼容性
- 使用 TypeScript 保证代码质量和类型安全
- 基于 React 构建现代化的用户界面
- 利用 Turborepo 实现高效的 monorepo 管理

## 2. 技术架构

### 2.1 整体架构
```
Learn Mate Extension
├── Chrome Extension Core (Manifest V3)
├── React UI Components
├── TypeScript Business Logic
├── Extension APIs Integration
└── Shared Package Architecture
```

### 2.2 技术栈详情

#### 前端技术栈
- **React 19.1.0**: 现代化的用户界面框架
- **TypeScript 5.8.3**: 强类型语言，提供类型安全
- **Tailwind CSS 3.4.17**: 实用程序优先的 CSS 框架
- **Vite 6.3.5**: 现代化的构建工具和开发服务器

#### 构建和开发工具
- **Turborepo 2.5.3**: Monorepo 构建系统，支持并行构建和缓存
- **PNPM**: 高效的包管理器
- **ESLint + Prettier**: 代码质量和格式化工具
- **Husky**: Git hooks 管理

#### Chrome 扩展技术
- **Manifest V3**: 最新的 Chrome 扩展规范
- **Service Worker**: 后台脚本处理
- **Content Scripts**: 页面内容注入
- **Web Extensions API**: 浏览器 API 调用

### 2.3 项目结构

#### 根目录结构
```
learn_mate/
├── chrome-extension/          # Chrome 扩展核心文件
├── packages/                  # 共享包和模块
├── pages/                     # 扩展的各个页面组件
├── tests/                     # 端到端测试
├── docs/                      # 项目文档
└── 配置文件
```

#### Chrome Extension 结构
```
chrome-extension/
├── manifest.ts               # 扩展清单文件配置
├── src/
│   └── background/          # 后台服务工作者
├── public/                  # 静态资源（图标、CSS）
└── 构建配置文件
```

#### Pages 结构
```
pages/
├── popup/                   # 扩展弹窗页面
├── options/                 # 选项设置页面
├── new-tab/                # 新标签页替换
├── side-panel/             # 侧边栏面板
├── devtools/               # 开发者工具扩展
├── devtools-panel/         # 开发者工具面板
├── content/                # 内容脚本
├── content-ui/             # 内容脚本UI组件
└── content-runtime/        # 运行时内容脚本
```

#### Packages 结构
```
packages/
├── shared/                 # 跨模块共享代码
├── storage/                # 存储管理模块
├── i18n/                   # 国际化支持
├── ui/                     # UI组件库
├── hmr/                    # 热模块替换
├── env/                    # 环境变量管理
├── dev-utils/              # 开发工具
├── vite-config/            # Vite配置
├── tailwind-config/        # Tailwind配置
├── tsconfig/               # TypeScript配置
├── module-manager/         # 模块管理器
└── zipper/                 # 打包工具
```

## 3. 功能模块设计

### 3.1 核心功能模块

#### 3.1.1 扩展管理模块 (Background Service)
**位置**: `chrome-extension/src/background/index.ts`

**功能**:
- 扩展生命周期管理
- 主题状态初始化和同步
- 全局事件监听和处理

**实现细节**:
```typescript
// 主题存储初始化
exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});
```

#### 3.1.2 用户界面模块

##### Popup 界面 (`pages/popup/`)
**功能**:
- 扩展的主要交互入口
- 主题切换功能
- 内容脚本注入控制
- GitHub 项目链接跳转

**核心特性**:
- 响应式设计，支持明暗主题
- 集成错误边界和加载状态
- 支持国际化

##### 新标签页 (`pages/new-tab/`)
**功能**:
- 替换浏览器默认新标签页
- 提供定制化的学习界面
- 主题切换和个性化设置

##### 选项页面 (`pages/options/`)
**功能**:
- 扩展的详细设置配置
- 用户偏好管理
- 高级功能配置

##### 侧边栏面板 (`pages/side-panel/`)
**功能**:
- Chrome 114+ 支持的侧边栏功能
- 持久化的学习工具面板
- 实时学习状态显示

#### 3.1.3 内容注入模块

##### 基础内容脚本 (`pages/content/`)
**功能**:
- 页面内容分析和处理
- 学习相关数据收集
- 与背景脚本通信

**匹配规则**:
- 全站匹配: `['http://*/*', 'https://*/*', '<all_urls>']`
- 示例站点: `['https://example.com/*']`

##### UI 内容脚本 (`pages/content-ui/`)
**功能**:
- 在网页中注入 React 组件
- 提供学习辅助 UI 元素
- 主题切换控制

##### 运行时内容脚本 (`pages/content-runtime/`)
**功能**:
- 动态注入的内容脚本
- 按需加载的功能模块
- 特定页面的增强功能

#### 3.1.4 开发者工具扩展

##### DevTools 页面 (`pages/devtools/`)
**功能**:
- 扩展开发者工具功能
- 学习数据调试和分析

##### DevTools 面板 (`pages/devtools-panel/`)
**功能**:
- 自定义开发者工具面板
- 实时数据监控和分析

### 3.2 支撑模块

#### 3.2.1 存储管理 (`packages/storage/`)
**核心功能**:
- Chrome Storage API 封装
- 主题状态管理
- 数据持久化和同步

**主题存储实现**:
```typescript
export const exampleThemeStorage: ThemeStorageType = {
  ...storage,
  toggle: async () => {
    await storage.set(currentState => {
      const newTheme = currentState.theme === 'light' ? 'dark' : 'light';
      return {
        theme: newTheme,
        isLight: newTheme === 'light',
      };
    });
  },
};
```

**特性**:
- 支持本地和同步存储
- 实时更新机制
- 类型安全的存储接口

#### 3.2.2 国际化支持 (`packages/i18n/`)
**功能**:
- 多语言支持框架
- 类型安全的翻译函数
- 动态语言切换

**支持语言**:
- 英语 (en) - 默认语言
- 可扩展支持更多语言

**使用示例**:
```typescript
t('toggleTheme')           // "Toggle theme"
t('hello', 'World')        // "Hello World"
t('greeting', 'John Doe')  // "Hello, My name is John Doe"
```

#### 3.2.3 UI 组件库 (`packages/ui/`)
**功能**:
- 统一的 UI 组件库
- 主题感知组件
- 可复用的界面元素

**核心组件**:
- `ToggleButton`: 主题切换按钮
- `ErrorDisplay`: 错误显示组件
- `LoadingSpinner`: 加载状态组件

#### 3.2.4 共享模块 (`packages/shared/`)
**功能**:
- 跨模块共享代码
- 通用工具函数
- 高阶组件 (HOC)
- React Hooks

**核心工具**:
- `withErrorBoundary`: 错误边界HOC
- `withSuspense`: 加载状态HOC
- `useStorage`: 存储状态Hook
- `colorfulLogger`: 开发日志工具

#### 3.2.5 热模块替换 (`packages/hmr/`)
**功能**:
- 开发时的热重载支持
- 自动化的构建更新
- 开发体验优化

#### 3.2.6 环境配置 (`packages/env/`)
**功能**:
- 环境变量管理
- 构建配置控制
- 开发/生产环境区分

## 4. 数据流设计

### 4.1 状态管理
```
User Action → Component State → Storage API → Chrome Storage → Background Script
     ↑                                                              ↓
     └── UI Update ← Component Re-render ← Storage Event ← Storage Sync
```

### 4.2 消息通信
```
Content Script ↔ Background Service ↔ Popup/Options
      ↑                 ↑                   ↑
      └── Page DOM   Storage API    User Interaction
```

### 4.3 主题状态流
```
Theme Toggle → Storage Update → All Components Re-render → UI Theme Switch
```

## 5. 扩展权限和安全

### 5.1 所需权限
- `storage`: 数据存储和同步
- `scripting`: 内容脚本注入
- `tabs`: 标签页管理
- `notifications`: 通知功能
- `sidePanel`: 侧边栏面板 (Chrome 114+)

### 5.2 主机权限
- `<all_urls>`: 访问所有网站（开发阶段）
- 生产环境应限制为必要的网站域名

### 5.3 安全考虑
- Content Security Policy (CSP) 合规
- 最小权限原则
- 安全的消息传递机制
- 用户数据隐私保护

## 6. 构建和部署

### 6.1 开发环境
```bash
# 安装依赖
pnpm install

# 开发模式 (Chrome)
pnpm dev

# 开发模式 (Firefox)
pnpm dev:firefox
```

### 6.2 生产构建
```bash
# 生产构建 (Chrome)
pnpm build

# 生产构建 (Firefox)
pnpm build:firefox

# 打包发布
pnpm zip
```

### 6.3 构建流程
1. **环境变量设置**: 通过 `set-global-env` 脚本设置构建环境
2. **并行构建**: Turborepo 管理的并行构建任务
3. **类型检查**: TypeScript 编译和类型验证
4. **代码质量**: ESLint 检查和 Prettier 格式化
5. **资源打包**: Vite 构建和资源优化
6. **扩展打包**: 生成可安装的扩展文件

### 6.4 Turborepo 任务配置
```json
{
  "tasks": {
    "ready": "准备构建环境",
    "dev": "开发模式构建",
    "build": "生产模式构建",
    "type-check": "TypeScript 类型检查",
    "lint": "代码质量检查",
    "format": "代码格式化",
    "e2e": "端到端测试"
  }
}
```

## 7. 测试策略

### 7.1 端到端测试 (`tests/e2e/`)
**测试框架**: WebdriverIO

**测试覆盖**:
- 各个页面组件的功能测试
- 内容脚本注入和交互测试
- 主题切换和持久化测试
- 跨浏览器兼容性测试

**测试文件**:
- `smoke.test.ts`: 基础功能冒烟测试
- `page-*.test.ts`: 各页面专项测试

### 7.2 开发测试
```bash
# 运行端到端测试
pnpm e2e

# Firefox 端到端测试
pnpm e2e:firefox
```

## 8. 开发工具和工作流

### 8.1 开发工具链
- **模块管理器**: `pnpm module-manager` - 启用/禁用功能模块
- **版本管理**: `pnpm update-version` - 统一版本更新
- **环境配置**: 自动化的环境变量管理
- **热重载**: 开发时的实时更新

### 8.2 代码质量保证
- **Husky**: Git hooks 管理
- **lint-staged**: 提交前代码检查
- **TypeScript**: 编译时类型检查
- **ESLint**: 代码规范检查
- **Prettier**: 代码格式化

### 8.3 工作流程
1. **功能开发**: 在对应的 pages 或 packages 目录下开发
2. **实时预览**: 使用 `pnpm dev` 进行开发调试
3. **代码提交**: 自动触发代码检查和格式化
4. **构建测试**: `pnpm build` 生产构建验证
5. **端到端测试**: `pnpm e2e` 功能验证
6. **发布打包**: `pnpm zip` 生成发布包

## 9. 扩展和定制

### 9.1 添加新页面
1. 在 `pages/` 目录创建新页面模块
2. 配置 `manifest.ts` 添加页面声明
3. 更新构建配置和路由

### 9.2 添加新功能包
1. 在 `packages/` 目录创建新包
2. 配置 `package.json` 和依赖关系
3. 在 `pnpm-workspace.yaml` 中注册

### 9.3 自定义主题
1. 修改 `packages/tailwind-config/` 配置
2. 更新主题存储接口
3. 调整 UI 组件的主题支持

### 9.4 国际化扩展
1. 在 `packages/i18n/locales/` 添加新语言包
2. 更新翻译键值对
3. 配置语言检测和切换逻辑

## 10. 性能优化

### 10.1 构建优化
- **代码分割**: Vite 的动态导入和代码分割
- **依赖优化**: pnpm 的依赖去重和缓存
- **并行构建**: Turborepo 的任务并行化
- **增量构建**: 基于文件变更的增量编译

### 10.2 运行时优化
- **懒加载**: React 组件和功能模块的按需加载
- **存储优化**: 高效的 Chrome Storage API 使用
- **内存管理**: 适当的组件卸载和资源清理
- **缓存策略**: 静态资源和数据的缓存机制

## 11. 监控和调试

### 11.1 开发调试
- **控制台日志**: 彩色日志输出和分类
- **Chrome DevTools**: 扩展页面的调试支持
- **热重载**: 代码变更的实时反馈
- **错误边界**: React 错误的捕获和处理

### 11.2 生产监控
- **错误追踪**: 生产环境的错误收集
- **性能监控**: 扩展运行时的性能指标
- **用户反馈**: 通过 Chrome Web Store 的用户反馈

## 12. 未来规划

### 12.1 功能扩展
- **AI 学习助手**: 集成机器学习功能
- **学习数据分析**: 深度的学习行为分析
- **云端同步**: 跨设备的学习数据同步
- **社交功能**: 学习社区和分享功能

### 12.2 技术升级
- **React 19**: 利用最新的 React 特性
- **Web Components**: 更好的组件复用
- **PWA 支持**: 渐进式 Web 应用特性
- **WebAssembly**: 性能关键模块的原生化

### 12.3 平台扩展
- **Firefox 扩展**: 完善的 Firefox 支持
- **Edge 扩展**: Microsoft Edge 平台支持
- **移动端**: 移动浏览器扩展支持

---

## 总结

Learn Mate Chrome 扩展采用了现代化的技术架构，通过 Manifest V3、React、TypeScript 和 Turborepo 的组合，构建了一个可扩展、高质量的学习助手扩展。项目的模块化设计和完善的工具链为后续的功能扩展和维护提供了坚实的基础。

该系统设计文档为开发团队提供了全面的技术指导，涵盖了从架构设计到具体实现的各个方面，确保项目的可持续发展和高质量交付。