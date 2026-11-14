"""LLM Client implementations for Zalo AI DataMate.

Supports local Ollama serving, OpenAI-compatible endpoints (vLLM, LocalAI),
and Mock client for testing.
"""

from abc import ABC, abstractmethod
import json
import time
from typing import Any, Dict, Optional
import urllib.error
import urllib.request


class BaseLLMClient(ABC):
  """Abstract LLM Client interface."""

  @abstractmethod
  def generate(self, prompt: str) -> str:
    """Generate text completion from prompt."""
    pass


class MockLLMClient(BaseLLMClient):
  """Mock LLM Client for testing without model weights."""

  def __init__(self, canned_responses: Optional[Dict[str, str]] = None):
    self.canned_responses = canned_responses or {}

  def generate(self, prompt: str) -> str:
    for key, resp in self.canned_responses.items():
      if key.lower() in prompt.lower():
        return resp
    return """```python
def solve(con):
    return {"type": "abstain"}
```"""


class OllamaClient(BaseLLMClient):
  """Ollama REST API client using standard library urllib with retry mechanism."""

  def __init__(
      self,
      model_name: str = 'qwen2.5-coder:7b',
      host: str = 'http://127.0.0.1:11434',
      temperature: float = 0.0,
      timeout: float = 300.0,
      num_ctx: int = 16384,
      num_predict: int = 3072,
  ):
    self.model_name = model_name
    self.host = host.rstrip('/')
    self.temperature = temperature
    self.timeout = timeout
    self.num_ctx = num_ctx
    self.num_predict = num_predict

  def generate(self, prompt: str) -> str:
    url = f'{self.host}/api/generate'
    payload = {
        'model': self.model_name,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': self.temperature,
            'num_predict': self.num_predict,
            'num_ctx': self.num_ctx,
        },
    }
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )

    max_attempts = 2
    for attempt in range(max_attempts):
      try:
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
          res_data = json.loads(response.read().decode('utf-8'))
          resp_text = res_data.get('response', '')
          thinking = res_data.get('thinking', '')
          if thinking and '<reasoning>' not in resp_text:
            return f'<reasoning>\n{thinking.strip()}\n</reasoning>\n{resp_text.strip()}'
          return resp_text
      except urllib.error.URLError as e:
        if attempt < max_attempts - 1:
          time.sleep(2)
          continue
        raise ConnectionError(
            f'Could not connect to Ollama at {self.host}. Make sure "ollama serve"'
            f' is running: {e}'
        )
      except TimeoutError as e:
        if attempt < max_attempts - 1:
          time.sleep(3)
          continue
        raise TimeoutError(f'Ollama request timed out after {self.timeout}s: {e}')
      except Exception as e:
        if attempt < max_attempts - 1:
          time.sleep(2)
          continue
        raise RuntimeError(f'Ollama generation error: {e}')


class OpenAICompatibleClient(BaseLLMClient):
  """OpenAI-compatible client (for vLLM, LocalAI, llama-server)."""

  def __init__(
      self,
      model_name: str = 'qwen2.5-coder:7b',
      base_url: str = 'http://127.0.0.1:8000/v1',
      api_key: str = 'token-dummy',
      temperature: float = 0.0,
      timeout: float = 60.0,
  ):
    self.model_name = model_name
    self.base_url = base_url.rstrip('/')
    self.api_key = api_key
    self.temperature = temperature
    self.timeout = timeout

  def generate(self, prompt: str) -> str:
    url = f'{self.base_url}/chat/completions'
    payload = {
        'model': self.model_name,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': self.temperature,
        'max_tokens': 512,
        'stop': ['```\n\n', '```\r\n\r\n'],
    }
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        },
    )

    try:
      with urllib.request.urlopen(req, timeout=self.timeout) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        return res_data['choices'][0]['message']['content']
    except Exception as e:
      raise RuntimeError(f'OpenAI-compatible API generation error: {e}')

