---
name: mlops-inference
description: Expert guidance for LLM inference — constrained generation (Guidance), GGUF quantization, vLLM serving, and model optimization. Consolidated inference expertise.
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [guidance, transformers, llama-cpp-python]
metadata:
  hermes:
    tags: [Inference, LLM Serving, Constrained Generation, GGUF, Quantization, vLLM, Structured Output, JSON Validation, Grammar, Format Enforcement]
---

# MLOPs Inference — LLM Inference & Optimization

Expert-level guidance for LLM inference pipelines. Consolidated from multiple specialized skills covering constrained generation, model quantization, and serving optimization.

## Skills Consolidated Here

- **Guidance** — Constrained LLM generation with regex/grammars for guaranteed valid JSON/XML/code
- **GGUF Quantization** — llama.cpp GGUF format for efficient CPU/GPU inference
- **vLLM Serving** — High-throughput LLM serving with OpenAI-compatible API

---

## When to Use Each Component

### Guidance (Constrained Generation)
Use when you need to:
- Control LLM output syntax with regex or grammars
- Guarantee valid JSON/XML/code generation
- Enforce structured formats (dates, emails, IDs, etc.)
- Build multi-step workflows with Pythonic control flow
- Reduce latency vs traditional prompting approaches

### GGUF Quantization
Use when you need to:
- Run large models on limited GPU/CPU resources
- Reduce memory footprint through quantization
- Serve models locally with llama.cpp

### vLLM
Use when you need:
- High-throughput batch inference
- OpenAI-compatible REST API
- PagedAttention for memory efficiency

---

## Guidance — Constrained LLM Generation

### Quick Start

```python
from guidance import models, gen

# Load model (supports OpenAI, Transformers, llama.cpp)
lm = models.OpenAI("gpt-4")

# Generate with constraints
result = lm + "The capital of France is " + gen("capital", max_tokens=5)
print(result["capital"])  # "Paris"
```

### Regex Constraints

```python
# Constrain to valid email format
lm += "Email: " + gen("email", regex=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Constrain to date format (YYYY-MM-DD)
lm += "Date: " + gen("date", regex=r"\d{4}-\d{2}-\d{2}")

# Constrain to phone number
lm += "Phone: " + gen("phone", regex=r"\d{3}-\d{3}-\d{4}")
```

### Selection Constraints

```python
from guidance import models, gen, select

lm = models.Anthropic("claude-sonnet-4-5-20250929")

# Constrain to specific choices
lm += "Sentiment: " + select(["positive", "negative", "neutral"], name="sentiment")
```

### Token Healing

Guidance automatically "heals" token boundaries between prompt and generation — no awkward spacing issues.

### JSON Generation Pattern

```python
from guidance import models, gen, system, user, assistant

lm = models.Anthropic("claude-sonnet-4-5-20250929")

with system():
    lm += "You generate valid JSON."

with user():
    lm += "Generate a user profile with name, age, and email."

with assistant():
    lm += """{
    "name": """ + gen("name", regex=r'"[A-Za-z ]+"', max_tokens=30) + """,
    "age": """ + gen("age", regex=r"[0-9]+", max_tokens=3) + """,
    "email": """ + gen("email", regex=r'"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"', max_tokens=50) + """
}"""

print(lm)  # Valid JSON guaranteed
```

### ReAct Agent Pattern

```python
from guidance import models, gen, select, guidance

@guidance(stateless=False)
def react_agent(lm, question):
    """ReAct agent with tool use."""
    tools = {
        "calculator": lambda expr: eval(expr),
        "search": lambda query: f"Search results for: {query}",
    }

    lm += f"Question: {question}\n\n"

    for round in range(5):
        lm += f"Thought: " + gen("thought", stop="\n") + "\n"
        lm += "Action: " + select(["calculator", "search", "answer"], name="action")

        if lm["action"] == "answer":
            lm += "\nFinal Answer: " + gen("answer", max_tokens=100)
            break

        lm += "\nAction Input: " + gen("action_input", stop="\n") + "\n"

        if lm["action"] in tools:
            result = tools[lm["action"]](lm["action_input"])
            lm += f"Observation: {result}\n\n"

    return lm
```

---

## GGUF Quantization

GGUF (General Gradient-Uniform Format) is llama.cpp's format for quantized models — dramatically reduces memory requirements.

### Quantization Levels

| Type | Memory | Quality | Speed |
|------|--------|---------|-------|
| Q2_K | ~3.5GB (7B) | Low | Fast |
| Q3_K_M | ~4.3GB (7B) | Medium-Low | Fast |
| Q4_K_M | ~4.9GB (7B) | Medium | Medium |
| Q5_K_M | ~5.7GB (7B) | Medium-High | Medium |
| Q6_K | ~6.7GB (7B) | High | Medium |
| Q8_0 | ~8.1GB (7B) | Very High | Slow |

**Recommendation**: Q4_K_M for most use cases — best quality/perf trade-off.

### Conversion Pipeline

```bash
# 1. Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
mkdir build && cd build
cmake .. && cmake --build . --config Release

# 2. Convert HuggingFace model to GGUF
python ../convert_hf_to_gguf.py /path/to/hf-model --outfile model.gguf

# 3. Quantize
./quantize model.gguf model-Q4_K_M.gguf Q4_K_M
```

### Loading in Python

```python
from llama_cpp import Llama

llm = Llama(
    model_path="./model-Q4_K_M.gguf",
    n_ctx=4096,
    n_gpu_layers=35  # Layers offloaded to GPU
)

response = llm(
    "Explain quantum computing in simple terms:",
    max_tokens=256,
    temperature=0.7
)
print(response["choices"][0]["text"])
```

---

## vLLM Serving

### Installation

```bash
pip install vllm
```

### Server Launch

```bash
vllm serve meta-llama/Llama-2-7b-chat-hf \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.9 \
    --port 8000
```

### OpenAI-Compatible API

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="none")

response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum entanglement."}
    ],
    temperature=0.7,
    max_tokens=256
)

print(response.choices[0].message.content)
```

---

## Resources

- Guidance GitHub: https://github.com/guidance-ai/guidance (18k+ stars)
- llama.cpp: https://github.com/ggerganov/llama.cpp
- vLLM: https://github.com/vllm-project/vllm
- TRL: https://huggingface.co/docs/trl
