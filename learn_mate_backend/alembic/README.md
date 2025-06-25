# Alembic 数据库迁移管理

## 概述

本项目使用 Alembic 管理数据库迁移。Alembic 是 SQLAlchemy 的数据库迁移工具，支持自动生成和手动编写迁移脚本。

## 环境配置

迁移脚本从环境变量 `POSTGRES_URL` 读取数据库连接信息：

```bash
export POSTGRES_URL="postgresql://username:password@localhost:5432/database_name"
```

## 常用命令

### 查看当前迁移状态
```bash
alembic current
```

### 查看迁移历史
```bash
alembic history
```

### 创建新的迁移文件

自动生成迁移（通过比较模型和数据库）：
```bash
alembic revision --autogenerate -m "描述本次迁移"
```

手动创建迁移：
```bash
alembic revision -m "描述本次迁移"
```

### 执行迁移

升级到最新版本：
```bash
alembic upgrade head
```

升级到特定版本：
```bash
alembic upgrade <revision>
```

### 回滚迁移

回滚到上一个版本：
```bash
alembic downgrade -1
```

回滚到特定版本：
```bash
alembic downgrade <revision>
```

## 项目结构

```
alembic/
├── versions/          # 迁移文件目录
├── alembic.ini       # Alembic 配置文件
├── env.py            # 环境配置脚本
├── script.py.mako    # 迁移文件模板
└── README.md         # 本文档
```

## 注意事项

1. **循环依赖**: 如果模型之间存在循环依赖（如 `chat_messages` 和 `message_branches`），需要手动调整迁移文件中的表创建顺序。

2. **外键约束**: 确保在创建外键约束之前，被引用的表已经存在。

3. **枚举类型**: PostgreSQL 的枚举类型在删除表后仍然存在，需要单独删除。

4. **生产环境**: 在生产环境执行迁移前，务必先备份数据库。

## 开发流程

1. 修改模型文件（在 `app/models/` 目录下）
2. 运行 `alembic revision --autogenerate -m "描述"`
3. 检查生成的迁移文件，必要时手动调整
4. 运行 `alembic upgrade head` 应用迁移
5. 测试确保迁移正确执行

## 故障排除

### 清空数据库重新开始

如果需要完全重置数据库：

```bash
# 运行清空脚本
python scripts/drop_all_tables.py

# 重新执行所有迁移
alembic upgrade head
```

### 迁移冲突

如果出现迁移冲突，可以：
1. 检查 `alembic_version` 表中的当前版本
2. 使用 `alembic stamp <revision>` 手动设置版本
3. 或者清空数据库重新开始