import { cn } from '@extension/ui';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import Link from '@tiptap/extension-link';
import Typography from '@tiptap/extension-typography';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { createLowlight } from 'lowlight';
import { useEffect } from 'react';
import './MarkdownViewer.scss';

// 创建 lowlight 实例
const lowlight = createLowlight();

interface MarkdownViewerProps {
  content: string;
  isLight?: boolean;
  className?: string;
}

const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ content, isLight = true, className }) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3, 4, 5, 6],
        },
      }),
      Typography,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: cn(
            'cursor-pointer underline',
            isLight ? 'text-blue-600 hover:text-blue-800' : 'text-blue-400 hover:text-blue-300',
          ),
        },
      }),
      CodeBlockLowlight.configure({
        lowlight,
        HTMLAttributes: {
          class: cn(
            'rounded-lg p-4 overflow-x-auto',
            isLight ? 'bg-gray-100 text-gray-900' : 'bg-gray-800 text-gray-100',
          ),
        },
      }),
    ],
    content: '',
    editable: false,
    editorProps: {
      attributes: {
        class: cn('prose prose-sm max-w-none focus:outline-none', isLight ? 'prose-gray' : 'prose-invert', className),
      },
    },
  });

  useEffect(() => {
    if (editor && content) {
      // 将 markdown 内容解析并设置到编辑器
      const htmlContent = parseMarkdownToHTML(content);
      editor.commands.setContent(htmlContent);
    }
  }, [content, editor]);

  return <EditorContent editor={editor} />;
};

// 简单的 Markdown 到 HTML 转换函数
const parseMarkdownToHTML = (markdown: string): string => {
  let html = markdown;

  // 代码块
  html = html.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (match, lang, code) => `<pre><code class="language-${lang || 'plaintext'}">${escapeHtml(code.trim())}</code></pre>`,
  );

  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 标题
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 粗体
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // 斜体
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  // 无序列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // 有序列表
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // 段落
  html = html
    .split('\n\n')
    .map(para => {
      if (para.trim() && !para.startsWith('<')) {
        return `<p>${para}</p>`;
      }
      return para;
    })
    .join('\n');

  return html;
};

const escapeHtml = (text: string): string => {
  const map: { [key: string]: string } = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, m => map[m]);
};

export { MarkdownViewer };
