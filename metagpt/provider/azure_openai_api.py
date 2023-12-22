# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/5 23:08
@Author  : alexanderwu
@File    : openai.py
@Modified By: mashenquan, 2023/8/20. Remove global configuration `CONFIG`, enable configuration support for business isolation;
            Change cost control from global to company level.
@Modified By: mashenquan, 2023/11/21. Fix bug: ReadTimeout.
@Modified By: mashenquan, 2023/12/1. Fix bug: Unclosed connection caused by openai 0.x.
"""


from openai import AsyncAzureOpenAI, AzureOpenAI
from openai._base_client import AsyncHttpxClientWrapper, SyncHttpxClientWrapper

from metagpt.config import CONFIG, Config, LLMProviderEnum
from metagpt.provider.llm_provider_registry import register_provider
from metagpt.provider.openai_api import OpenAIGPTAPI, RateLimiter


@register_provider(LLMProviderEnum.AZURE_OPENAI)
class AzureOpenAIGPTAPI(OpenAIGPTAPI):
    """
    Check https://platform.openai.com/examples for examples
    """

    def __init__(self):
        self.config: Config = CONFIG
        self.__init_openai()
        self.auto_max_tokens = False
        # https://learn.microsoft.com/zh-cn/azure/ai-services/openai/how-to/migration?tabs=python-new%2Cdalle-fix
        self._client = AsyncAzureOpenAI(
            api_key=CONFIG.openai_api_key,
            api_version=CONFIG.openai_api_version,
            azure_endpoint=CONFIG.openai_api_base,
        )
        RateLimiter.__init__(self, rpm=self.rpm)

    def _make_client(self):
        kwargs, async_kwargs = self._make_client_kwargs()
        self.client = AzureOpenAI(**kwargs)
        self.async_client = AsyncAzureOpenAI(**async_kwargs)

    def _make_client_kwargs(self) -> (dict, dict):
        kwargs = dict(
            api_key=self.config.openai_api_key,
            api_version=self.config.openai_api_version,
            azure_endpoint=self.config.openai_base_url,
        )
        async_kwargs = kwargs.copy()

        # to use proxy, openai v1 needs http_client
        proxy_params = self._get_proxy_params()
        if proxy_params:
            kwargs["http_client"] = SyncHttpxClientWrapper(**proxy_params)
            async_kwargs["http_client"] = AsyncHttpxClientWrapper(**proxy_params)

        return kwargs, async_kwargs

    def _cons_kwargs(self, messages: list[dict], timeout=3, **configs) -> dict:
        kwargs = {
            "messages": messages,
            "max_tokens": self.get_max_tokens(messages),
            "n": 1,
            "stop": None,
            "temperature": 0.3,
            "model": CONFIG.deployment_id,
        }
        if configs:
            kwargs.update(configs)
        try:
            default_timeout = int(CONFIG.TIMEOUT) if CONFIG.TIMEOUT else 0
        except ValueError:
            default_timeout = 0
        kwargs["timeout"] = max(default_timeout, timeout)

        return kwargs
