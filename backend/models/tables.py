"""SQLAlchemy ORM模型 —— 对应 deploy/init.sql 中的5张表"""
from sqlalchemy import (Column, Integer, String, DateTime, Text,
                        Enum as SAEnum, DECIMAL, Boolean, JSON, Index, ForeignKey)
from sqlalchemy.sql import func
from backend.models.database import Base
import enum


class UserRole(str, enum.Enum):
    值长 = "值长"
    检修班长 = "检修班长"
    厂长 = "厂长"
    管理员 = "管理员"


class AlertLevel(str, enum.Enum):
    yellow = "yellow"
    orange = "orange"
    red = "red"


class AlertStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    resolved = "resolved"


class WorkOrderStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"
    in_progress = "in_progress"
    completed = "completed"


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False)   # 值长/检修班长/厂长/管理员
    plant_id = Column(Integer, default=None)
    real_name = Column(String(32), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False)
    device_name = Column(String(64), nullable=False)
    device_type = Column(String(32), nullable=False)
    material = Column(String(32), default="")
    original_wall_thickness = Column(DECIMAL(5, 2))
    min_allowable_thickness = Column(DECIMAL(5, 2))
    install_date = Column(DateTime, default=None)
    dcs_tag = Column(String(32), default="")


class AlertLog(Base):
    __tablename__ = "alert_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, nullable=False)
    alert_level = Column(SAEnum(AlertLevel), nullable=False)
    alert_time = Column(DateTime, server_default=func.now())
    reason = Column(Text)
    predicted_loss = Column(DECIMAL(10, 2), default=0)
    status = Column(SAEnum(AlertStatus), default=AlertStatus.pending)
    confirm_by = Column(String(32), default="")
    confirm_time = Column(DateTime, default=None)
    resolution = Column(Text)
    close_time = Column(DateTime, default=None)
    __table_args__ = (Index("idx_device_time", "device_id", "alert_time"),
                      Index("idx_status", "status"))


class WorkOrder(Base):
    __tablename__ = "work_order"
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alert_log.id"), default=None)
    device_id = Column(Integer, nullable=False)
    fault_desc = Column(Text)
    root_cause = Column(Text)
    action_plan = Column(Text)
    spare_parts = Column(Text)
    similar_cases = Column(Text)
    assignee = Column(String(32), default="")
    status = Column(SAEnum(WorkOrderStatus), default=WorkOrderStatus.draft)
    create_time = Column(DateTime, server_default=func.now())
    complete_time = Column(DateTime, default=None)


class KgRelation(Base):
    __tablename__ = "kg_relation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_type = Column(String(32), nullable=False)
    fault_mode = Column(String(128), nullable=False)
    phenomenon = Column(Text)
    root_cause = Column(Text)
    action_plan = Column(Text)
    spare_parts = Column(Text)
    source = Column(SAEnum("manual", "NLP_auto"), default="manual")
    occurrence_count = Column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    username = Column(String(32), default="")
    action = Column(String(64), nullable=False)
    resource = Column(String(128), default="")
    source_ip = Column(String(45), default="")
    result = Column(SAEnum("success", "failure"), nullable=False)
    detail = Column(JSON, default=None)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_user_time", "user_id", "created_at"),)
