# Latest User Requirements

## 当前任务：集成 Tiptap Editor 渲染 Markdown 响应

### 任务描述
参考 Tiptap 文档，在前端项目中引入 Tiptap editor，使用一个只读的 Tiptap editor 来渲染 markdown 格式的响应。

### 参考文档
- https://tiptap.dev/docs/editor/getting-started/install/react
- https://template.tiptap.dev/preview/templates/simple
- https://github.com/ueberdosis/tiptap
- https://tiptap.dev/docs/editor/getting-started/overview

### 已完成的工作
1. ✅ 创建了 `MarkdownViewer` 组件（`pages/new-tab/src/components/MarkdownViewer.tsx`）
   - 使用 Tiptap React 实现只读编辑器
   - 配置了 StarterKit、Typography、Link 和 CodeBlockLowlight 扩展
   - 实现了简单的 Markdown 到 HTML 转换函数
   - 支持代码高亮（使用 lowlight）

2. ✅ 创建了对应的样式文件（`MarkdownViewer.scss`）
   - 定义了标题、段落、列表、代码块等元素的样式
   - 支持亮色和暗色主题

3. ✅ 集成到聊天界面
   - 在 `NewTab.tsx` 中导入了 MarkdownViewer 组件
   - 替换了原有的 `formatContent` 函数
   - 在消息渲染和 thinking 内容渲染中使用 MarkdownViewer

### 修改的文件
- 创建：`/pages/new-tab/src/components/MarkdownViewer.tsx`
- 创建：`/pages/new-tab/src/components/MarkdownViewer.scss`
- 修改：`/pages/new-tab/src/NewTab.tsx`

### 待完成的工作
1. **安装依赖**（由于网络问题暂时未完成）：
   ```bash
   pnpm add @tiptap/react @tiptap/pm @tiptap/starter-kit @tiptap/extension-typography @tiptap/extension-link @tiptap/extension-code-block-lowlight lowlight
   ```

2. **功能增强**：
   - 支持更多 Markdown 特性（表格、任务列表等）
   - 优化 Markdown 解析逻辑
   - 添加更多代码语言的语法高亮支持

3. **性能优化**：
   - 实现内容缓存机制
   - 优化大文本渲染性能

### 技术要点
- Tiptap 是基于 ProseMirror 的富文本编辑器框架
- 使用 `editable: false` 创建只读编辑器
- 通过扩展系统支持各种 Markdown 特性
- 使用 lowlight（highlight.js 的轻量版）实现代码高亮