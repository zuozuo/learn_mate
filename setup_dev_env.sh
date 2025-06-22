#!/bin/bash

# Learn Mate 开发环境设置脚本
# 此脚本用于快速设置 Learn Mate 项目的开发环境

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印信息函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "开始设置 Learn Mate 开发环境..."

# 检查当前目录
if [ ! -d "learn_mate_backend" ] || [ ! -d "learn_mate_frontend" ]; then
    print_error "请在 learn_mate 项目根目录下运行此脚本"
    exit 1
fi

# 1. 检查并安装必要的系统依赖
print_info "检查系统依赖..."

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    print_error "Homebrew 未安装，请先安装 Homebrew: https://brew.sh"
    exit 1
fi
print_success "Homebrew 已安装"

# 检查并安装 PostgreSQL
if ! command -v psql &> /dev/null; then
    print_info "PostgreSQL 未安装，正在安装..."
    brew install postgresql@15
    print_success "PostgreSQL 15 安装完成"
else
    print_success "PostgreSQL 已安装"
fi

# 检查并安装 uv
if ! command -v uv &> /dev/null; then
    print_info "uv 未安装，正在安装..."
    pip install uv
    print_success "uv 安装完成"
else
    print_success "uv 已安装"
fi

# 检查并安装 Node.js (用于前端)
if ! command -v node &> /dev/null; then
    print_warning "Node.js 未安装，如需运行前端项目请安装 Node.js"
else
    print_success "Node.js 已安装 (版本: $(node --version))"
fi

# 2. 设置后端环境
print_info "设置后端环境..."

cd learn_mate_backend

# 安装 Python 依赖
print_info "安装 Python 依赖..."
uv sync
print_success "Python 依赖安装完成"

# 启动 PostgreSQL 服务
print_info "启动 PostgreSQL 服务..."
brew services start postgresql@15
print_success "PostgreSQL 服务已启动"

# 添加 PostgreSQL 到 PATH
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

# 创建数据库
print_info "创建开发数据库..."
if ! createdb learn_mate_dev 2>/dev/null; then
    print_warning "数据库 learn_mate_dev 可能已存在"
else
    print_success "数据库 learn_mate_dev 创建成功"
fi

# 检查环境配置文件
if [ ! -f ".env.development" ]; then
    print_info "创建开发环境配置文件..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.development
        print_success "已从 .env.example 创建 .env.development"
        print_warning "请编辑 .env.development 文件，设置正确的配置项（特别是 OpenAI API 密钥）"
    else
        print_error ".env.example 文件不存在"
    fi
else
    print_success "开发环境配置文件已存在"
fi

cd ..

# 3. 设置前端环境（如果需要）
if [ -d "learn_mate_frontend" ]; then
    print_info "设置前端环境..."
    cd learn_mate_frontend
    
    if command -v npm &> /dev/null && [ -f "package.json" ]; then
        print_info "安装前端依赖..."
        npm install
        print_success "前端依赖安装完成"
    elif command -v pnpm &> /dev/null && [ -f "package.json" ]; then
        print_info "使用 pnpm 安装前端依赖..."
        pnpm install
        print_success "前端依赖安装完成"
    else
        print_warning "未找到 npm 或 pnpm，跳过前端依赖安装"
    fi
    
    cd ..
fi

# 4. 创建便捷脚本
print_info "创建便捷启动脚本..."

# 后端启动脚本
cat > start_backend.sh << 'EOF'
#!/bin/bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
unset http_proxy https_proxy all_proxy
cd learn_mate_backend
make dev
EOF

chmod +x start_backend.sh
print_success "后端启动脚本 start_backend.sh 创建完成"

# 前端启动脚本（如果有 package.json）
if [ -f "learn_mate_frontend/package.json" ]; then
    cat > start_frontend.sh << 'EOF'
#!/bin/bash
cd learn_mate_frontend
if command -v pnpm &> /dev/null; then
    pnpm dev
elif command -v npm &> /dev/null; then
    npm run dev
else
    echo "请安装 npm 或 pnpm"
    exit 1
fi
EOF
chmod +x start_frontend.sh
print_success "前端启动脚本 start_frontend.sh 创建完成"
fi

# 5. 输出使用说明
print_success "开发环境设置完成！"
echo
print_info "使用说明："
echo "1. 编辑 learn_mate_backend/.env.development 文件，设置正确的配置项"
echo "   - 特别是 LLM_API_KEY (OpenAI API 密钥)"
echo "   - 数据库连接已配置为: postgresql://$(whoami):@localhost:5432/learn_mate_dev"
echo
echo "2. 启动后端服务："
echo "   ./start_backend.sh"
echo "   或者："
echo "   cd learn_mate_backend && make dev"
echo
if [ -f "start_frontend.sh" ]; then
echo "3. 启动前端服务（新终端窗口）："
echo "   ./start_frontend.sh"
echo
fi
echo "4. 访问服务："
echo "   - 后端 API 文档: http://localhost:8000/docs"
echo "   - 后端健康检查: http://localhost:8000/health"
if [ -f "learn_mate_frontend/package.json" ]; then
echo "   - 前端应用: http://localhost:3000 (或按前端项目配置)"
fi
echo
print_info "开发环境设置完成，祝您开发愉快！"