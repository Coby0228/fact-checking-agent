from autogen_core.models import UserMessage, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient
import os, asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():

    client = OpenAIChatCompletionClient(
        model="qwen3:30b",
        base_url=os.getenv("OLLAMA_BASE_URL"),  # e.g. http://host:11434/v1
        api_key=os.getenv("OLLAMA_API_KEY"),  # e.g. OLLAMA_API_KEY
        options={
            "temperature": 0.0,  # 設定溫度為 0.0 以確保可預測的回應
            "max_tokens": 100,  # 設定最大 token 數量
        },
        model_info=ModelInfo(
            family="unknown",
            vision=False,
            function_calling=False,
            json_output=False,
            structured_output=False
        )
    )
    res = await client.create(
        [UserMessage(content="說個笑話/no_think", source="user")]
    )
    print(res)
    await client.close()

asyncio.run(main())
