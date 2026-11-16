"""通过地区参数和 API Key 环境变量配置生产请求。"""

import os
from dataclasses import dataclass, field
from types import MappingProxyType

PRODUCTION_URLS = MappingProxyType(
    {
        "cn": "https://app-api.pixverseai.cn",
        "global": "https://app-api.pixverse.ai",
    }
)


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    region: str
    api_key: str = field(repr=False)

    def __post_init__(self):
        if self.region not in PRODUCTION_URLS:
            raise ConfigurationError("请使用 --region 指定地区，允许值：global、cn。")
        if not self.api_key or any(ord(c) < 33 or ord(c) > 126 for c in self.api_key):
            raise ConfigurationError("请设置有效的 PIXVERSE_API_KEY（不含空格或控制字符）。")

    @property
    def base_url(self) -> str:
        return PRODUCTION_URLS[self.region]

    @classmethod
    def from_env(cls, region="global"):
        """地区来自命令参数，环境变量只提供 API Key。"""
        return cls(region, os.environ.get("PIXVERSE_API_KEY", ""))
