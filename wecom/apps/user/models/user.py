import random
import string
import traceback

from flask_login import UserMixin, login_user
from sqlalchemy.orm import load_only
from sqlalchemy import Column, Enum, String, Boolean, Integer

from wecom.core.database import BaseModel, db
from wecom.utils.log import logger


import datetime as dt

from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property

from wecom.core.database import Column, PkModel, db, reference_col, relationship
from wecom.core.extensions import bcrypt


class Role(PkModel):
    """A role for a user."""
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}

    name = Column(db.String(80), unique=True, nullable=False)
    user_id = reference_col("users", nullable=True)
    user = relationship("User", backref="roles")

    def __init__(self, name, **kwargs):
        """Create instance."""
        super().__init__(name=name, **kwargs)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Role({self.name})>"


class User(UserMixin, BaseModel):
    """A user of the app."""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    username = Column(db.String(80), unique=True, nullable=False)
    email = Column(db.String(80), unique=True, nullable=False)
    _password = Column("password", db.LargeBinary(128), nullable=True)
    created_at = Column(
        db.DateTime, nullable=False, default=dt.datetime.now(dt.timezone.utc)
    )
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    active = Column(db.Boolean(), default=False)
    is_admin = Column(db.Boolean(), default=False)

    @hybrid_property
    def password(self):
        """Hashed password."""
        return self._password

    @password.setter
    def password(self, value):
        """Set password."""
        self._password = bcrypt.generate_password_hash(value)

    def check_password(self, value):
        """Check password."""
        return bcrypt.check_password_hash(self._password, value)

    @property
    def full_name(self):
        """Full user name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<User({self.username!r})>"


class WecomUser(BaseModel, UserMixin):
    __tablename__ = 'wecom_user'

    username = Column(String(100), nullable=False, server_default="")
    user_id = Column(Integer, nullable=False, server_default='0')
    email = Column(String(100), nullable=False, server_default="")
    mobile = Column(String(100), nullable=False, server_default="")
    source = Column(Enum("wx", "qywx", "dingtalk", "feishu"), nullable=False)
    is_enabled = Column(Boolean, nullable=False, server_default="0")
    is_push = Column(Boolean, nullable=False, server_default="0")

    @classmethod
    def get_unique_user_id(cls, k=6):
        query = cls.query.options(load_only(cls.user_id)).all()
        user_ids_set = {obj.user_id for obj in query}

        retry_time = 0
        while retry_time < len(user_ids_set) + 1:
            retry_time += 1
            uniq_seq = "1" + "".join(random.choices(string.digits, k=k - 1))
            user_id = int(uniq_seq)

            if user_id not in user_ids_set:
                return user_id

        raise ValueError("[WXUser] 计算用户唯一id失败")

    @classmethod
    def create(cls, **kwargs):
        logger.info("User.create => user_kwargs: %s", kwargs)

        fields = cls.fields()
        values = {key: val for key, val in kwargs.items() if key in fields}

        username = values.get("username")
        instance = cls.query.filter_by(username=username).first()

        if instance is None:
            instance = cls(**values)
        else:
            for key, val in values.items():
                setattr(instance, key, val)

        if not instance.user_id:
            instance.user_id = cls.get_unique_user_id()

        db.session.add(instance)
        db.session.commit()

        return instance

    @classmethod
    def get_available_username_list(cls, agent_id: str):
        """ 所有激活的、可推送的用户 """
        users = cls.query.options(load_only(cls.userid)).filter_by(is_enabled=True, agent_id=agent_id).all()
        return [user.userid for user in users]

