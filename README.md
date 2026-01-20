# Bid PDF Document Processor

**Production-ready ETL pipeline for extracting structured data from construction bid PDFs**  
*Edgevanta Data Engineering Challenge - January 2026*

---

## 🏆 Results Summary

- ✅ **96% Success Rate** - 96/100 PDFs processed successfully
- ⚡ **14.3 docs/second** - High-throughput processing
- 📊 **71.9% Completeness** - Average data extraction completeness
- 🔍 **79.2% Validation** - Business rule compliance rate
- ⏱️ **0.073s** - Average processing time per document

## 🎯 Project Overview

This project implements a complete ETL pipeline to process PDF documents from North Carolina DOT construction bid lettings, extracting structured data for analytics and reporting.

**Key Features**:
- Multi-strategy extraction (Regex + PDFPlumber)
- Automated document classification
- Data quality validation with business rules
- PostgreSQL storage with proper schema design
- Comprehensive observability and logging
- Production-ready code with error handling

## 📊 Supported Document Types

1. **Invitation to Bid** - Contract solicitation documents
2. **Bid Tabs** - Tabular bid submissions with pricing
3. **Award Letter** - Contract award notifications
4. **Item C Report** - Bid comparison summaries
5. **Bids As Read** - Raw bid readings (summary lines)
6. **Bid Summary** - Bid summary rollups

## 🏗️ Architecture

```
PDF Files → Classifier → Extractor (Regex/PDFPlumber) → Validator → PostgreSQL
                                                                       → CSV Export
```

### Key Components

- **Classifier**: Identifies document type by filename and content
- **Extractors**: Specialized parsers for each document type
- **Validators**: Ensure data quality and completeness
- **Loaders**: Save to PostgreSQL or export to CSV

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL)

### Installation

```bash
# Clone repository
cd bid-pdf-document-processor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (uv)
pip install uv
uv pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Setup database
docker-compose up -d
```

### Run Pipeline

```bash
# Process all PDFs in source directory
python scripts/run_pipeline.py source/source_files/

# Process specific folder
python scripts/run_pipeline.py source/source_files/2023\ nc\ d1/2023-02-01_nc_d1/

# Save results to JSON
python scripts/run_pipeline.py source/source_files/ --output results.json

# Summary only
python scripts/run_pipeline.py source/source_files/ --summary-only
 
# Load results into PostgreSQL
python scripts/run_pipeline.py source/source_files/ --load-postgres

# Load with custom DB URL
python scripts/run_pipeline.py source/source_files/ --load-postgres --database-url "postgresql://user:pass@host:5432/db"

# Restrict files by glob pattern
python scripts/run_pipeline.py source/source_files/ --pattern "**/*Bid Tabs*.pdf"

# Incremental processing (skip unchanged)
python scripts/run_pipeline.py source/source_files/ --incremental --state-file .pipeline_state.json

# Run via Docker (build + run with Postgres)
# Uses DATABASE_URL and SOURCE_DIR from .env
bash scripts/run_docker_pipeline.sh
```

### Pipeline Parameters

| Parameter | Description |
| --- | --- |
| source_dir | Directory containing PDF files (positional) |
| --pattern | Glob pattern for PDF files (default: **/*.pdf) |
| --output | Output JSON file for results |
| --summary-only | Only print summary statistics |
| --incremental | Skip unchanged files using cached fingerprints |
| --state-file | Optional path for incremental state cache |
| --load-postgres | Load extraction results into PostgreSQL |
| --database-url | PostgreSQL connection string (overrides DATABASE_URL env var) |

### Database Migrations

Migrations run automatically when using `--load-postgres` or the Docker entrypoint.
If you need to run them manually:

```bash
bash scripts/run_migrations.sh
```

## 📁 Project Structure

```
bid-pdf-document-processor/
├── src/
│   ├── extractors/          # PDF extraction logic
│   │   ├── base_extractor.py
│   │   ├── bids_as_read_extractor.py
│   │   ├── bid_summary_extractor.py
│   │   ├── invitation_extractor.py
│   │   ├── bid_tabs_extractor.py
│   │   ├── award_letter_extractor.py
│   │   └── item_c_extractor.py
│   ├── transformers/        # Data transformation
│   ├── loaders/             # Database/CSV loaders
│   ├── validators/          # Data quality checks
│   ├── pipeline/            # Orchestration
│   │   ├── classifier.py
│   │   └── orchestrator.py
│   └── models/              # Data models
│       ├── database_models.py
│       └── schemas.py
├── tests/                   # Unit tests
├── scripts/                 # Executable scripts
├── notebooks/               # Jupyter notebooks for analysis
├── sql/                     # Database schema
├── docs/                    # Documentation
└── source/                  # Input PDF files
```

## 🔍 Extraction Strategies

### 1. Regex Pattern Matching
- **Use case**: Structured text with predictable patterns
- **Pros**: Fast, no external dependencies
- **Cons**: Brittle with format variations

### 2. PDFPlumber Table Extraction
- **Use case**: Tabular data (Bid Tabs)
- **Pros**: Accurate for well-formatted tables
- **Cons**: Requires structured layout

### 3. LLM-based Extraction (Future)
- Planned as an optional fallback for complex/edge cases
- See [docs/LLM_GUIDE.md](docs/LLM_GUIDE.md) for the roadmap

## 📊 Database Schema

```sql
contracts      -- Main contract information
  ├── bidders      -- Companies that submitted bids
  └── bid_items    -- Line items from bid tabs
  
extraction_logs  -- Pipeline execution tracking
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run CI-like test script
bash scripts/run_tests_ci.sh

# Run pipeline via Docker + PostgreSQL
bash scripts/run_docker_pipeline.sh
```

## 🧩 Scripts

- [scripts/run_pipeline.py](scripts/run_pipeline.py) - Executa o pipeline de extração, com opções de saída e carga no Postgres.
- [scripts/run_demo.py](scripts/run_demo.py) - Demonstração com métricas resumidas.
- [scripts/run_tests_ci.sh](scripts/run_tests_ci.sh) - Testes em modo CI com cobertura.
- [scripts/run_docker_pipeline.sh](scripts/run_docker_pipeline.sh) - Build + run via Docker com PostgreSQL.
- [scripts/run_migrations.sh](scripts/run_migrations.sh) - Executa migrations do Alembic.

## 🤖 LLM Evaluation (Future)

LLM evaluation tooling is planned for a future release. See
[docs/LLM_GUIDE.md](docs/LLM_GUIDE.md) for the roadmap.

## 📈 Data Quality & Validation

- Schema validation using Pydantic
- Business rule checks (totals match, dates valid)
- Confidence scoring per extraction
- Extraction logs for auditing

## 🎯 Actual Results (Tested on 100 Real PDFs)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Success Rate | >90% | 96% | ✅ Exceeded |
| Processing Speed | <5s | 0.073s | ✅ 68x faster |
| Data Completeness | >90% | 71.9% | ⚠️ Good (improving) |
| Throughput | N/A | 14.3 docs/s | ✅ Excellent |

**Document Type Breakdown**:
- Invitation to Bid: 27/27 (100%)
- Bid Tabs: 27/27 (100%)
- Award Letter: 28/28 (100%)
- Item C Report: 14/14 (100%)

## 🛠️ Development

```bash
# Install dev dependencies (uv)
pip install uv
uv pip install -r requirements.txt

# Run linting
flake8 src/

# Format code
black src/

# Type checking
mypy src/
```

## 📝 Completed vs Future Enhancements

### ✅ Completed
- [x] Complete ETL pipeline
- [x] 6 specialized extractors
- [x] PostgreSQL loader implementation
- [x] Data validation layer (business rules)
- [x] Jupyter notebook for analysis
- [x] Comprehensive documentation
- [x] Demo script with metrics
- [x] Structured logging

### 🔜 Future Enhancements
- [ ] Complete bid items table extraction
- [ ] REST API for on-demand extraction
- [ ] Real-time monitoring dashboard
- [ ] Parallel processing (multiprocessing)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Automated tests (pytest)
- [ ] Docker production image
- [ ] LLM fallback for low-confidence cases (future)

## 🤝 Technical Decisions

### Why Python?
- Rich ecosystem for PDF processing (pypdf, pdfplumber)
- Strong data engineering libraries (pandas, SQLAlchemy)
- Easy integration with AI/ML tools

### Why PostgreSQL?
- Robust ACID compliance
- Excellent support for structured data
- Good query performance
- Free and open source

### Why Multiple Extraction Methods?
- Different document types require different approaches
- Fallback strategy ensures resilience
- Allows benchmarking and optimization

## � Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and technical decisions
- [SUMMARY.md](docs/SUMMARY.md) - Executive summary and results
- [PRESENTATION_GUIDE.md](docs/PRESENTATION_GUIDE.md) - Technical interview preparation

## 🎥 Quick Demo

```bash
# Run complete demonstration
python scripts/run_demo.py "source/source_files/2023 nc d1/" --output demo_results.json

# Expected output:
# ✓ 96/100 documents successfully processed
# ✓ 96.0% extraction success rate
# ✓ 71.9% average data completeness
# ✓ 0.073s average processing time
# ✓ Validated 96 extractions
```

## 🏗️ Built With

- **Python 3.12** - Core language
- **pypdf + pdfplumber** - PDF extraction
- **PostgreSQL** - Data storage
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **structlog** - Structured logging
- **Jupyter** - Analysis & visualization

## 📧 Contact

**Andre Pereira**  
Data Engineer Challenge - Edgevanta  
January 2026

---

**Note**: This is a technical exercise demonstrating production-ready data engineering practices for PDF document processing. The solution prioritizes reliability, maintainability, and scalability.
