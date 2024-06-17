import importlib
from functools import lru_cache
from typing import Any, Dict, Union
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES

from . import config as settings


def find_loader(pkg_path: str) -> Any:
    module_path, name = pkg_path.rsplit(":", 1)

    module = importlib.import_module(module_path)
    return getattr(module, name)


@lru_cache(maxsize=1)
def get_user_model():
    """  Return the User model that is active in this project. """
    model_cls = find_loader(settings.USER_MODEL)

    def to_dict(self: model_cls):
        fields = model_cls._meta.fields
        return {name: getattr(self, name) for name in fields}

    def check_password(self: model_cls, password: Union[str, None]):
        # 目前明码验证，极不安全
        if not password or self.password != password:
            return False

        return True

    setattr(model_cls, "to_dict", to_dict)
    setattr(model_cls, "check_password", check_password)
    return model_cls


UserModel = get_user_model()


def get_user(
        userid: Union[str, None] = None,
        username: Union[str, None] = None,
        is_dict: bool = False
) -> Union[UserModel, Dict[str, Any]]:
    """ Peewee ORM """
    user_model_cls = get_user_model()

    if userid:
        expressions = [user_model_cls.user_id == userid]
    elif username:
        expressions = [user_model_cls.user_name == username]
    else:
        raise ValueError('userid and username cannot both be empty.')

    user_obj = user_model_cls.select().where(*expressions).first()

    if user_obj is None:
        raise ValueError(f"Not find user by user_id[{userid}")

    return user_obj.to_dict() if is_dict else user_obj
