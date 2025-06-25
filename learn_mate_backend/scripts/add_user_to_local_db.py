#!/usr/bin/env python3
"""添加用户到本地数据库的脚本.

使用方法:
1. 批量添加预设用户: python scripts/add_user_to_local_db.py
2. 交互式添加单个用户: python scripts/add_user_to_local_db.py --interactive
3. 命令行添加用户: python scripts/add_user_to_local_db.py --email test@example.com --username testuser --password Test123456!
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import Optional
from getpass import getpass

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, select  # noqa: E402
from app.services.database import DatabaseService  # noqa: E402
from app.core.config import settings  # noqa: E402

# 导入所有模型以确保 SQLModel 关系正确初始化
from app.models.user import User  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.login_history import LoginHistory  # noqa: E402
from app.models.chat_message import ChatMessage  # noqa: E402
from app.models.message_branch import MessageBranch  # noqa: E402
from app.models.thread import Thread  # noqa: E402


async def create_user(
    email: str, username: str, password: str, is_verified: bool = True, is_active: bool = True
) -> Optional[User]:
    """创建用户."""
    db_service = DatabaseService()

    with Session(db_service.engine) as session:
        # 检查用户是否已存在
        existing_user = session.exec(select(User).where((User.email == email) | (User.username == username))).first()

        if existing_user:
            if existing_user.email == email:
                print(f"❌ 用户 {email} 已存在")
            else:
                print(f"❌ 用户名 {username} 已存在")
            return existing_user

        # 创建新用户
        hashed_password = User.hash_password(password)
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=is_active,
            is_verified=is_verified,
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        print("✅ 成功创建用户:")
        print(f"   邮箱: {new_user.email}")
        print(f"   用户名: {new_user.username}")
        print(f"   密码: {password}")
        print(f"   已验证: {new_user.is_verified}")
        print(f"   已激活: {new_user.is_active}")
        print(f"   用户ID: {new_user.id}")

        return new_user


async def interactive_mode():
    """交互式添加用户."""
    print("🚀 交互式添加用户")
    print("-" * 50)

    email = input("请输入邮箱: ").strip()
    username = input("请输入用户名: ").strip()
    password = getpass("请输入密码: ").strip()

    is_verified = input("是否已验证邮箱？(Y/n): ").strip().lower() != "n"
    is_active = input("是否激活账户？(Y/n): ").strip().lower() != "n"

    await create_user(email, username, password, is_verified, is_active)


async def batch_mode():
    """批量添加预设的测试用户."""
    print("🚀 批量添加本地测试用户...")
    print("-" * 50)

    # 测试用户列表
    test_users = [
        {
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123456!",
            "is_verified": True,
            "is_active": True,
        },
        {
            "email": "admin@example.com",
            "username": "admin",
            "password": "Admin123456!",
            "is_verified": True,
            "is_active": True,
        },
        {
            "email": "demo@example.com",
            "username": "demo",
            "password": "Demo123456!",
            "is_verified": True,
            "is_active": True,
        },
        {
            "email": "unverified@example.com",
            "username": "unverified",
            "password": "Test123456!",
            "is_verified": False,  # 未验证用户
            "is_active": True,
        },
        {
            "email": "inactive@example.com",
            "username": "inactive",
            "password": "Test123456!",
            "is_verified": True,
            "is_active": False,  # 未激活用户
        },
    ]

    # 创建用户
    for user_data in test_users:
        await create_user(**user_data)
        print("-" * 50)

    print("\n✨ 测试用户创建完成！")
    print("\n可以使用以下账号登录:")
    print("1. 普通用户: test@example.com / Test123456!")
    print("2. 管理员: admin@example.com / Admin123456!")
    print("3. 演示用户: demo@example.com / Demo123456!")


async def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="添加用户到本地数据库")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式添加用户")
    parser.add_argument("--email", "-e", help="用户邮箱")
    parser.add_argument("--username", "-u", help="用户名")
    parser.add_argument("--password", "-p", help="密码")
    parser.add_argument("--verified", action="store_true", default=True, help="邮箱已验证")
    parser.add_argument("--unverified", action="store_true", help="邮箱未验证")
    parser.add_argument("--active", action="store_true", default=True, help="账户已激活")
    parser.add_argument("--inactive", action="store_true", help="账户未激活")

    args = parser.parse_args()

    if args.interactive:
        await interactive_mode()
    elif args.email and args.username and args.password:
        # 命令行模式
        is_verified = not args.unverified
        is_active = not args.inactive
        await create_user(args.email, args.username, args.password, is_verified, is_active)
    else:
        # 批量模式
        await batch_mode()


if __name__ == "__main__":
    asyncio.run(main())
