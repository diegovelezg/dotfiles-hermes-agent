---
name: mlops-training
description: Expert guidance for LLM fine-tuning and reinforcement learning training — PEFT/LoRA, GRPO/RL with TRL, and distributed PyTorch FSDP training. Consolidated training expertise.
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [transformers>=4.47.0, trl>=0.14.0, datasets>=3.2.0, peft>=0.14.0, torch>=2.0]
metadata:
  hermes:
    tags: [Fine-Tuning, PEFT, LoRA, GRPO, RL, TRL, RLHF, DPO, PPO, FSDP, Distributed Training, Post-Training, LLM Training]
---

# MLOPs Training — LLM Fine-Tuning & RL Training

Expert-level guidance for fine-tuning language models and implementing reinforcement learning training pipelines. Consolidated from multiple specialized skills.

## Skills Consolidated Here

- **GRPO/RL Training** — Group Relative Policy Optimization with TRL for reasoning and structured output
- **PEFT Fine-Tuning** — Parameter-efficient fine-tuning with LoRA/QLoRA via PEFT
- **PyTorch FSDP** — Fully Sharded Data Parallel for large-scale distributed training

---

## When to Use Each Component

### GRPO/RL (TRL)
Use when you need to:
- Enforce specific output formats (XML tags, JSON, structured reasoning)
- Teach verifiable tasks with objective correctness metrics (math, coding, fact-checking)
- Improve reasoning capabilities by rewarding chain-of-thought patterns
- Align models to domain-specific behaviors without labeled preference data
- Optimize for multiple objectives simultaneously (format + correctness + style)

**Do NOT use GRPO for:**
- Simple supervised fine-tuning tasks (use SFT instead)
- Tasks without clear reward signals
- When you already have high-quality preference pairs (use DPO/PPO instead)

### PEFT/LoRA
Use for:
- Reducing VRAM requirements (2-4× more efficient)
- Quick domain adaptation without full fine-tuning
- Experimenting with multiple adapter variants
- Low-data fine-tuning scenarios

### FSDP
Use when:
- Training models that don't fit on a single GPU
- Need to scale across multiple nodes
- Want memory efficiency through parameter sharding

---

## GRPO/RL Training with TRL

### Core Concepts

**GRPO Algorithm:**
- Generates **multiple completions** for each prompt (group size: 4-16)
- Compares completions within each group using reward functions
- Updates policy to favor higher-rewarded responses relative to the group

**Critical Difference from PPO:**
- No separate reward model needed
- More sample-efficient (learns from within-group comparisons)
- Simpler to implement and debug

### Reward Function Design

**Golden Rules:**
1. Compose multiple reward functions — each handles one aspect (format, correctness, style)
2. Scale rewards appropriately — higher weight = stronger signal
3. Use incremental rewards — partial credit for partial compliance
4. Test rewards independently — debug each reward function in isolation

| Type | Use Case | Example Weight |
|------|----------|----------------|
| **Correctness** | Verifiable tasks (math, code) | 2.0 (highest) |
| **Format** | Strict structure enforcement | 0.5-1.0 |
| **Length** | Encourage verbosity/conciseness | 0.1-0.5 |
| **Style** | Penalize unwanted patterns | -0.5 to 0.5 |

### Training Configuration

```python
from trl import GRPOConfig

training_args = GRPOConfig(
    output_dir="outputs/grpo-model",
    learning_rate=5e-6,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_generations=8,
    max_prompt_length=256,
    max_completion_length=512,
    num_train_epochs=1,
    bf16=True,
    optim="adamw_8bit",
    max_grad_norm=0.1,
    logging_steps=1,
    save_steps=100,
    report_to="wandb",
)
```

### Loss Behavior — EXPECTED PATTERN
- **Loss starts near 0 and INCREASES during training**
- This is CORRECT — loss measures KL divergence from initial policy
- Model is learning (diverging from original behavior to optimize rewards)
- Monitor reward metrics instead of loss for progress

### Key Training Insights

| Problem | Symptom | Solution |
|---------|---------|----------|
| **Mode collapse** | All completions identical | Increase `num_generations`, add diversity penalty |
| **No learning** | Flat rewards | Check reward function logic, increase LR |
| **OOM errors** | GPU memory exceeded | Reduce `num_generations`, enable gradient checkpointing |
| **Slow training** | < 1 it/s | Enable `use_vllm=True`, use Unsloth, reduce seq length |
| **Format ignored** | Model doesn't follow structure | Increase format reward weight, add incremental rewards |

---

## PEFT Fine-Tuning

### LoRA Configuration

```python
from peft import LoraConfig, get_peft_model

peft_config = LoraConfig(
    r=16,                         # Rank
    lora_alpha=32,               # Scaling factor (typically 2*r)
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    task_type="CAUSAL_LM",
    lora_dropout=0.05,
)
```

### Merging and Saving

```python
# Merge LoRA adapters into base model
if hasattr(trainer.model, 'merge_and_unload'):
    merged_model = trainer.model.merge_and_unload()
    merged_model.save_pretrained("production_model")
    tokenizer.save_pretrained("production_model")
```

---

## PyTorch FSDP

### Basic FSDP Setup

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy, MixedPrecision, BackwardPrefetch
from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy

# Mixed precision for memory savings
mixed_precision_policy = MixedPrecision(
    param_dtype=torch.bfloat16,
    reduce_dtype=torch.float32,
    buffer_dtype=torch.bfloat16,
)

# Auto-wrap policy for transformers
auto_wrap_policy = functools.partial(
    transformer_auto_wrap_policy,
    transformer_layer_cls={TransformerEncoderLayer, TransformerDecoderLayer},
)

model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,
    auto_wrap_policy=auto_wrap_policy,
    mixed_precision=mixed_precision_policy,
    device_id=torch.cuda.current_device(),
)
```

### CPU Offloading

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp.sharded_grad_scaler import ShardedGradScaler

model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,
    cpu_offload=CPUOffload(offload_params=True),
)
```

---

## Best Practices Checklist

**Before Training:**
- [ ] Validate dataset format (prompts as List[Dict])
- [ ] Test reward functions on sample data
- [ ] Calculate expected max_prompt_length from data
- [ ] Choose appropriate num_generations based on GPU memory
- [ ] Set up logging (wandb recommended)

**During Training:**
- [ ] Monitor reward progression (should increase)
- [ ] Check reward_std (should stay > 0.1)
- [ ] Watch for OOM errors (reduce batch size if needed)
- [ ] Sample generations every 50-100 steps
- [ ] Validate format compliance on holdout set

**After Training:**
- [ ] Merge LoRA weights if using PEFT
- [ ] Test on diverse prompts
- [ ] Compare to baseline model
- [ ] Document reward weights and hyperparameters

---

## Resources

- TRL GRPO Trainer: https://huggingface.co/docs/trl/grpo_trainer
- DeepSeek R1 Paper: https://arxiv.org/abs/2501.12948
- PEFT: https://github.com/huggingface/peft
- FSDP: https://pytorch.org/docs/stable/fsdp.html
- Unsloth: https://docs.unsloth.ai/
