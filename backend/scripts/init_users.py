"""预置账号初始化脚本

幂等执行：已存在的账号自动跳过。使用方式（在 .venv 环境中）：
    python -m scripts.init_users
"""

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import user  # noqa: F401  注册模型
from app.models.user import User
from sqlalchemy import select

# 各角色预置账号，密码统一 Init@123456，首次登录后建议修改
PRESET_USERS = [
    ("admin", "系统管理员", "admin"),
    ("customer01", "演示客户", "customer"),
    ("underwriter01", "演示核保员", "underwriter"),
    ("examcenter01", "演示体检机构", "exam_center"),
    ("supervisor01", "演示核保主管", "supervisor"),
]
DEFAULT_PASSWORD = "Init@123456"


def main() -> None:
    """创建表并写入不存在的预置账号。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 演示体检机构并关联机构账号（体检录入演示用）
        from app.models.exam import ExamCenter
        center = db.execute(select(ExamCenter).where(ExamCenter.name == "演示体检中心")).scalar_one_or_none()
        if center is None:
            center = ExamCenter(name="演示体检中心", contact_phone="010-88888888",
                                address="北京市演示路 1 号")
            db.add(center)
            db.flush()
            print(f"已创建体检机构：演示体检中心（ID {center.id}）")

        for username, real_name, role in PRESET_USERS:
            exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if exists:
                # 机构账号已存在但无关联时补关联（幂等修复历史数据）
                if role == "exam_center" and exists.exam_center_id is None:
                    exists.exam_center_id = center.id
                    print(f"已补关联机构：{username} -> {center.name}")
                else:
                    print(f"跳过已存在账号：{username}")
                continue
            user = User(username=username, real_name=real_name, role=role,
                        password_hash=hash_password(DEFAULT_PASSWORD))
            if role == "exam_center":
                user.exam_center_id = center.id
            db.add(user)
            print(f"已创建账号：{username}（角色 {role}，密码 {DEFAULT_PASSWORD}）")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
