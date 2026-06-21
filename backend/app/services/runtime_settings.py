from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RuntimeSetting

_runtime_settings: dict[str, object] = {}


def get_runtime_setting(key: str, default: object = None) -> object:
    return _runtime_settings.get(key, default)


def get_runtime_str(key: str, default: str | None = None) -> str | None:
    value = get_runtime_setting(key, default)
    if value is None:
        return None
    return str(value)


def get_runtime_bool(key: str, default: bool = False) -> bool:
    value = get_runtime_setting(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def get_runtime_int(key: str, default: int) -> int:
    value = get_runtime_setting(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def load_runtime_settings(session: AsyncSession) -> None:
    result = await session.execute(select(RuntimeSetting))
    _runtime_settings.clear()
    for setting in result.scalars().all():
        _runtime_settings[setting.key] = setting.value_json.get("value")


async def save_runtime_settings(
    session: AsyncSession,
    values: Mapping[str, object],
    *,
    secret_keys: set[str] | None = None,
) -> None:
    secret_keys = secret_keys or set()
    for key, value in values.items():
        setting = await session.get(RuntimeSetting, key)
        if setting:
            setting.value_json = {"value": value}
            setting.is_secret = key in secret_keys
        else:
            session.add(RuntimeSetting(key=key, value_json={"value": value}, is_secret=key in secret_keys))
        _runtime_settings[key] = value
