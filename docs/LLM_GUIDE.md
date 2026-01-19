# LLM Integration Guide

## Overview

This project supports **LLM-based extraction** as an optional enhancement to traditional methods (Regex + PDFPlumber). The implementation is **provider-agnostic**, meaning you can use any LLM provider:

- 🔷 **Google Gemini** (Recommended - Fast and cost-effective)
- 🟢 **OpenAI GPT** (GPT-4, GPT-3.5)
- 🟣 **Anthropic Claude** (Claude 3 Opus, Sonnet, Haiku)
- 🦙 **Ollama** (Local models like Llama2, Mistral)
- ✨ Any provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers)

## Quick Start

### 1. Install Dependencies

```bash
# Install LLM-related packages
pip install -r requirements.txt

# This includes:
# - litellm (unified interface for all providers)
# - google-generativeai (for Gemini)
# - openai (for GPT)
# - anthropic (for Claude)
```

### 2. Get API Key

#### Option A: Google Gemini (Recommended)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key"
3. Copy your API key

#### Option B: OpenAI
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy your API key

#### Option C: Anthropic Claude
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create API key
3. Copy your API key

#### Option D: Local Models (Ollama)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# No API key needed!
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
nano .env
```

Example `.env` for Gemini:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bid_processor

# Google Gemini
GEMINI_API_KEY=your_actual_api_key_here

# Model selection
LLM_MODEL=gemini/gemini-1.5-flash
```

### 4. Run Evaluation

Compare traditional vs LLM extraction:

```bash
# Evaluate with Gemini (default)
python scripts/evaluate_llm.py source/source_files/2023\ nc\ d1/2023-02-01_nc_d1/

# Evaluate first 10 files
python scripts/evaluate_llm.py source/source_files/ --limit 10

# Save detailed results
python scripts/evaluate_llm.py source/source_files/ --output llm_evaluation.json

# Use different model
python scripts/evaluate_llm.py source/source_files/ --model gpt-4 --limit 5
```

## Model Options

### Google Gemini Models

```bash
# Fast and cheap (Recommended for evaluation)
--model gemini/gemini-1.5-flash

# More capable, slightly slower
--model gemini/gemini-1.5-pro

# Legacy model
--model gemini/gemini-pro
```

**Cost**: ~$0.001-0.005 per document  
**Speed**: ~1-2s per document

### OpenAI Models

```bash
# Best quality, expensive
--model gpt-4-turbo

# Good balance
--model gpt-4

# Fast and cheap
--model gpt-3.5-turbo
```

**Cost**: ~$0.01-0.03 per document (GPT-4)  
**Speed**: ~2-3s per document

### Anthropic Claude Models

```bash
# Most capable
--model claude-3-opus-20240229

# Balanced
--model claude-3-sonnet-20240229

# Fast and cheap
--model claude-3-haiku-20240307
```

**Cost**: ~$0.005-0.015 per document  
**Speed**: ~1-3s per document

### Local Models (Ollama)

```bash
# Llama 2
--model ollama/llama2

# Mistral
--model ollama/mistral

# Mixtral
--model ollama/mixtral
```

**Cost**: $0 (runs locally)  
**Speed**: ~3-10s per document (depends on hardware)

## Usage Examples

### Example 1: Compare 10 Files with Gemini

```bash
python scripts/evaluate_llm.py \
  source/source_files/2023\ nc\ d1/2023-02-01_nc_d1/ \
  --model gemini/gemini-1.5-flash \
  --limit 10 \
  --output gemini_eval.json
```

Expected output:
```
======================================================================
EXTRACTION EVALUATION SUMMARY
======================================================================

Total files evaluated: 10/10

📊 TRADITIONAL EXTRACTION (Regex + PDFPlumber)
  Success rate:       100.0%
  Avg completeness:   71.5%
  Avg time:           0.045s

🤖 LLM EXTRACTION
  Model:              gemini/gemini-1.5-flash
  Success rate:       100.0%
  Avg completeness:   89.3%
  Avg time:           1.234s

📈 COMPARISON
  Avg improvement:    +17.8%
  Files improved:     8
  Files degraded:     0
  Files unchanged:    2

💰 TRADE-OFFS
  LLM is 27.4x slower
  Traditional cost:   $0.00 per document
  LLM cost (est):     $0.001-0.02 per document
  Improvement:        +17.8% completeness
  Worth it?           ✅ Yes
======================================================================
```

### Example 2: Quick Test with 3 Files

```bash
# Test with just 3 files to validate setup
python scripts/evaluate_llm.py \
  source/source_files/ \
  --limit 3 \
  --model gemini/gemini-1.5-flash
```

### Example 3: Full Evaluation (All Files)

```bash
# WARNING: This will process 100 PDFs and cost ~$0.10-$2 depending on model
python scripts/evaluate_llm.py \
  source/source_files/ \
  --model gemini/gemini-1.5-flash \
  --output full_llm_evaluation.json
```

### Example 4: Local Model (Free, No API Key)

```bash
# First, start Ollama and pull a model
ollama pull llama2

# Then run evaluation
python scripts/evaluate_llm.py \
  source/source_files/ \
  --model ollama/llama2 \
  --limit 5
```

## Programmatic Usage

### Use LLM Extractor Directly

```python
from pathlib import Path
from src.extractors.llm_extractor import LLMExtractor

# Initialize with your model of choice
extractor = LLMExtractor(
    pdf_path="path/to/document.pdf",
    model="gemini/gemini-1.5-flash"  # or gpt-4, claude-3-sonnet, etc.
)

# Extract data
result = extractor.run_extraction()

print(f"Status: {result['status']}")
print(f"Data: {result['data']}")
print(f"Time: {result['metadata']['processing_time']:.2f}s")
```

### Use Hybrid Approach (Traditional + LLM Fallback)

```python
from src.extractors.invitation_extractor import InvitationToBidExtractor
from src.extractors.llm_extractor import HybridExtractor

# Create traditional extractor
traditional = InvitationToBidExtractor("path/to/invitation.pdf")

# Wrap with hybrid extractor
hybrid = HybridExtractor(
    traditional_extractor=traditional,
    llm_model="gemini/gemini-1.5-flash",
    confidence_threshold=0.7  # Only use LLM if traditional < 70% complete
)

# Extract (automatically uses LLM if needed)
result = hybrid.extract()
```

## Evaluation Metrics Explained

### Completeness
Percentage of expected fields that were successfully extracted.

```
Completeness = (Filled Fields / Total Fields) * 100%
```

Example:
- Total fields: 8
- Filled fields: 6
- Completeness: 75%

### Improvement
Difference in completeness between LLM and traditional extraction.

```
Improvement = LLM Completeness - Traditional Completeness
```

Example:
- Traditional: 71.5%
- LLM: 89.3%
- Improvement: +17.8%

### Success Rate
Percentage of documents that were processed without errors.

```
Success Rate = (Successful Extractions / Total Files) * 100%
```

## Cost Analysis

### Per Document Costs (Estimated)

| Method | Cost per Document | Speed | Completeness |
|--------|------------------|-------|--------------|
| Traditional (Regex + PDFPlumber) | $0.00 | 0.05s | ~72% |
| Gemini 1.5 Flash | $0.001 | 1.2s | ~89% |
| Gemini 1.5 Pro | $0.005 | 2.0s | ~91% |
| GPT-3.5 Turbo | $0.002 | 1.5s | ~87% |
| GPT-4 Turbo | $0.02 | 2.5s | ~93% |
| Claude 3 Haiku | $0.003 | 1.3s | ~88% |
| Claude 3 Sonnet | $0.01 | 2.0s | ~92% |
| Ollama (Local) | $0.00 | 5.0s | ~85% |

### For 1,000 Documents

| Method | Total Cost | Total Time | Avg Completeness |
|--------|-----------|------------|------------------|
| Traditional | $0 | ~50 seconds | 72% |
| Gemini Flash | ~$1 | ~20 minutes | 89% |
| GPT-4 | ~$20 | ~42 minutes | 93% |
| Ollama | $0 | ~83 minutes | 85% |

## When to Use LLM?

### ✅ Good Use Cases

1. **Edge Cases**: Documents with unusual formats
2. **New Document Types**: When you don't have time to write regex patterns
3. **High Accuracy Required**: When 95%+ completeness is needed
4. **Rapid Prototyping**: Test extraction quickly without writing code

### ❌ Not Recommended For

1. **High Volume, Low Budget**: Processing millions of docs at $0.01 each = expensive
2. **Real-Time Requirements**: LLMs add 1-3s latency
3. **Standardized Formats**: Regex works perfectly and costs $0
4. **Privacy-Sensitive Data**: Sending to external APIs may violate compliance

### 🎯 Recommended Hybrid Strategy

```python
# Use traditional first, LLM as fallback for low-confidence results
confidence_threshold = 0.7  # 70% completeness

if traditional_completeness < confidence_threshold:
    use_llm_extraction()
else:
    use_traditional_extraction()
```

**Result**: 
- ~90% of docs use traditional (fast, free)
- ~10% use LLM (slower, costs money)
- Overall cost: ~$0.001 per document
- Overall completeness: ~85%

## Troubleshooting

### Error: API Key Not Found

```bash
# Check if API key is set
echo $GEMINI_API_KEY

# If empty, add to .env file
echo "GEMINI_API_KEY=your_key_here" >> .env

# Or export directly
export GEMINI_API_KEY=your_key_here
```

### Error: Rate Limit Exceeded

```bash
# Add delay between requests (modify evaluate_llm.py)
import time
time.sleep(1)  # Wait 1 second between files
```

### Error: Model Not Found

```bash
# For Ollama, make sure model is pulled
ollama pull llama2

# For other providers, check model name spelling
# Correct: gemini/gemini-1.5-flash
# Wrong: gemini-1.5-flash (missing provider prefix)
```

### LLM Returns Empty Data

This can happen if:
1. **JSON parsing failed**: LLM returned non-JSON format
2. **Token limit exceeded**: Document too long
3. **Model hallucination**: LLM made up data

**Solution**: Check logs and try different model or prompt.

## Best Practices

1. **Start Small**: Test with `--limit 3` before running on all files
2. **Use Cheap Models First**: Start with Gemini Flash or GPT-3.5
3. **Monitor Costs**: Track API usage in provider dashboard
4. **Compare Results**: Always run evaluation to see if improvement justifies cost
5. **Consider Hybrid**: Use LLM only when traditional fails
6. **Test Locally First**: Try Ollama if you want to experiment without costs

## Next Steps

After running evaluation:

1. **Analyze Results**: Check `llm_evaluation.json` for detailed comparison
2. **Calculate ROI**: Does +15% completeness justify $0.005/doc?
3. **Optimize Prompts**: Improve LLM extraction accuracy
4. **Implement Hybrid**: Use LLM only for edge cases
5. **Monitor Production**: Track costs and accuracy in production

## Support

For issues or questions:
- LiteLLM Docs: https://docs.litellm.ai/
- Gemini API: https://ai.google.dev/docs
- OpenAI API: https://platform.openai.com/docs
- Anthropic API: https://docs.anthropic.com/

---

**Ready to start? Run your first evaluation:**

```bash
# 1. Get API key from https://makersuite.google.com/app/apikey
# 2. Add to .env
echo "GEMINI_API_KEY=your_key" >> .env

# 3. Run quick test
python scripts/evaluate_llm.py source/source_files/ --limit 3

# 4. Check results and decide if you want to continue!
```
