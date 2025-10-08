# OpenRouter Models Quick Reference

**Platform**: iceberg-wsl (synced with yunni)  
**Total Models**: 18  
**Last Updated**: 2025-10-08

---

## Available Models

### Tier 1: Flagship Models (Intelligence 14-18)

| Model | Alias | Context | Features | Score |
|-------|-------|---------|----------|-------|
| `google/gemini-2.5-pro` | `pro`, `gemini` | 1M | Vision, Thinking, Code Gen | 18 |
| `openai/gpt-5-pro` | `gpt5pro` | 400K | Vision, Thinking, Code Gen | 18 |
| `openai/gpt-5-codex` | `codex`, `gpt5codex` | 400K | Code-specialized | 17 |
| `openai/gpt-5` | `gpt5` | 400K | Vision, Thinking | 16 |
| `x-ai/grok-4` | `grok`, `grok4` | 256K | Vision, Thinking | 15 |
| `deepseek/deepseek-r1-0528` | `deepseek-r1`, `r1` | 65K | Thinking, Reasoning | 15 |
| `openai/o3-pro` | `o3pro` | 200K | Vision | 15 |
| `anthropic/claude-opus-4.1` | `opus` | 200K | Vision | 14 |
| `openai/o3` | `o3` | 200K | Vision | 14 |

### Tier 2: Balanced Models (Intelligence 10-13)

| Model | Alias | Context | Features | Score |
|-------|-------|---------|----------|-------|
| **NEW** `qwen/qwen-max` | `qwen`, `qwenmax` | 32K | Vision, Multilingual | 13 |
| **NEW** `zhipuai/glm-4-plus` | `glm-plus` | 128K | Vision, Chinese-English | 13 |
| **NEW** `deepseek/deepseek-chat` | `deepseek-chat` | 65K | Fast, Function calling | 13 |
| `openai/o3-mini-high` | `o3-mini-high` | 200K | Vision | 13 |
| `anthropic/claude-sonnet-4.5` | `sonnet` | 200K | Vision | 12 |
| **NEW** `zhipuai/glm-4.5` | `glm`, `glm4.5` | 128K | Chinese-English | 12 |
| **NEW** `qwen/qwen-2.5-72b-instruct` | `qwen-2.5` | 131K | Powerful 72B | 12 |
| `openai/o3-mini` | `o3-mini` | 200K | Vision | 12 |
| `mistralai/mistral-large-2411` | `mistral` | 128K | JSON, Functions | 11 |
| `openai/o4-mini` | `o4-mini` | 200K | Vision | 11 |
| `google/gemini-2.5-flash` | `flash` | 1M | Vision, Fast | 10 |
| `anthropic/claude-sonnet-4.1` | `sonnet4.1` | 200K | Vision | 10 |
| `openai/gpt-5-mini` | `gpt5mini` | 400K | Efficient | 10 |

### Tier 3: Specialized Models (Intelligence 8-9)

| Model | Alias | Context | Features | Score |
|-------|-------|---------|----------|-------|
| `meta-llama/llama-3-70b` | `llama`, `llama3` | 8K | Text-only | 9 |
| `perplexity/llama-3-sonar-large-32k-online` | `perplexity` | 32K | Web search | 9 |
| `anthropic/claude-3.5-haiku` | `haiku` | 200K | Vision, Fast | 8 |
| `openai/gpt-5-nano` | `gpt5nano` | 400K | Fastest GPT-5 | 8 |

---

## New Models from Yunni (Added 2025-10-08)

### GLM Models (Zhipu AI) 🇨🇳

**GLM-4.5** - Latest bilingual model
```bash
zen:chat --model glm --prompt "解释这个代码 / Explain this code"
```
- **Alias**: `glm`, `glm4.5`, `glm-4.5`
- **Context**: 128K tokens
- **Features**: JSON mode, Function calling
- **Best for**: Chinese-English bilingual tasks

**GLM-4 Plus** - Advanced with vision
```bash
zen:chat --model glm-plus --prompt "Analyze this diagram"
```
- **Alias**: `glm-plus`, `glm4-plus`, `glm-4-plus`
- **Context**: 128K tokens
- **Features**: Vision, JSON mode, Function calling
- **Best for**: Visual analysis in Chinese-English

### QWen Models (Alibaba) 🌏

**QWen-Max** - Large multilingual
```bash
zen:chat --model qwen --prompt "Multilingual code review"
```
- **Alias**: `qwen`, `qwenmax`, `qwen-max`
- **Context**: 32K tokens
- **Features**: Vision, JSON mode, Function calling
- **Best for**: Multilingual tasks with vision

**QWen 2.5 72B** - Powerful instruction model
```bash
zen:chat --model qwen-2.5 --prompt "Complex instruction task"
```
- **Alias**: `qwen-2.5`, `qwen72b`
- **Context**: 131K tokens (largest QWen)
- **Features**: JSON mode, Function calling
- **Best for**: Complex instruction-following tasks

### DeepSeek Chat (Enhanced) 🚀

**DeepSeek Chat** - Fast general-purpose
```bash
zen:chat --model deepseek-chat --prompt "Quick code analysis"
```
- **Alias**: `deepseek-chat`, `deepseek-v3`
- **Context**: 65K tokens
- **Features**: JSON mode, Function calling
- **Best for**: Fast, capable general tasks

---

## Usage Patterns

### Auto Mode (Recommended)

```bash
# Claude automatically selects from all 18 models
zen:chat --prompt "Your task"

# For Chinese content, might select: GLM-4.5
# For multilingual, might select: QWen-Max
# For reasoning, might select: DeepSeek R1 or GPT-5 Pro
# For vision, might select: Gemini Pro or Claude Sonnet
# For code, might select: GPT-5 Codex
```

### Explicit Model Selection

```bash
# Chinese-English bilingual
zen:chat --model glm --prompt "双语分析 / Bilingual analysis"

# Multilingual with vision
zen:chat --model qwen --prompt "Analyze this image in multiple languages"

# Fast reasoning
zen:chat --model deepseek-chat --prompt "Quick code review"

# Deep reasoning
zen:chat --model deepseek-r1 --prompt "Complex algorithmic problem"
```

### Via Clink (External CLI Tools)

```bash
# Use with Gemini CLI
zen:clink --cli gemini --role analyzer --prompt "Analyze code"

# Use with Claude CLI
zen:clink --cli claude --role architect --prompt "Design system"

# Use with Codex CLI (can use OpenRouter models)
zen:clink --cli codex --role codereviewer --prompt "Review code"
```

---

## Model Capabilities Matrix

| Feature | GLM-4.5 | GLM-4-Plus | QWen-Max | QWen-2.5 | DeepSeek-Chat | DeepSeek-R1 |
|---------|---------|------------|----------|----------|---------------|-------------|
| **Context** | 128K | 128K | 32K | 131K | 65K | 65K |
| **Vision** | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **JSON Mode** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Functions** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Thinking** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Best For** | Bilingual | Visual+CN/EN | Multilingual | Instructions | Fast tasks | Reasoning |

---

## Intelligence Ranking

**Score Guide**: 1-20 (higher = more capable)

```
18  ┃ GPT-5 Pro, Gemini 2.5 Pro
    ┃
17  ┃ GPT-5 Codex
    ┃
16  ┃ GPT-5
    ┃
15  ┃ Grok-4, DeepSeek R1, O3-Pro
    ┃
14  ┃ Claude Opus 4.1, O3
    ┃
13  ┃ GLM-4-Plus, QWen-Max, DeepSeek-Chat, O3-mini-High  ⬅ NEW MODELS
    ┃
12  ┃ Claude Sonnet 4.5, GLM-4.5, QWen-2.5, O3-mini  ⬅ NEW MODELS
    ┃
11  ┃ Mistral Large, O4-mini
    ┃
10  ┃ Gemini Flash, Claude Sonnet 4.1, GPT-5-mini
    ┃
9   ┃ Llama 3 70B, Perplexity
    ┃
8   ┃ Claude Haiku, GPT-5-nano
```

---

## Platform Availability

### Yunni (Mac) ✅
- 18 OpenRouter models
- All aliases configured
- DEFAULT_MODEL=auto

### Iceberg-WSL (Linux) ✅
- 18 OpenRouter models (SYNCED)
- All aliases configured (SYNCED)
- DEFAULT_MODEL=auto (SYNCED)

**Status**: ✅ **100% Platform Parity**

---

## Quick Selection Guide

| Task Type | Recommended Model | Why |
|-----------|------------------|-----|
| **Chinese-English** | `glm` | Native bilingual support |
| **Multilingual + Vision** | `qwen` | Best multilingual with images |
| **Fast code review** | `deepseek-chat` | Fast, capable, cheap |
| **Deep reasoning** | `deepseek-r1` or `gpt5pro` | Extended thinking |
| **Code generation** | `gpt5codex` or `pro` | Code-specialized |
| **Long context** | `qwen-2.5` (131K) or `pro` (1M) | Largest contexts |
| **Vision tasks** | `pro`, `qwen`, `glm-plus` | Vision support |
| **Auto (let Claude pick)** | Just use `auto` | Claude knows best! |

---

## Cost Optimization

**Cheapest Options** (by tier):
- **Tier 1**: DeepSeek R1 (reasoning on budget)
- **Tier 2**: DeepSeek Chat, Gemini Flash (fast + cheap)
- **Tier 3**: GPT-5-nano, Claude Haiku

**Best Value**:
- `qwen-2.5` - 131K context, powerful, affordable
- `deepseek-chat` - Fast and capable
- `flash` - 1M context, ultra-fast

---

**Configuration**: `zen-mcp-server/conf/openrouter_models.json`  
**Verification**: `zen-mcp-server/docs/ICEBERG-WSL-CONFIGURATION-VERIFICATION.md`  
**Status**: ✅ Synced with yunni, ready for use

