# Architecture Documentation

## System Overview

This document describes the architecture and technical decisions behind the Bid PDF Document Processor.

## High-Level Architecture

```
┌─────────────────┐
│   PDF Files     │
│  (Source Data)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              INGESTION LAYER                        │
│  - File Discovery                                   │
│  - Document Classification                          │
└────────┬─────────────────────────────────────────┬──┘
         │                                         │
         ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│ Document         │                    │  Metadata        │
│ Classifier       │                    │  Extraction      │
│                  │                    │                  │
│ • Filename       │                    │ • File path      │
│ • Content        │                    │ • Timestamps     │
└────────┬─────────┘                    └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│           EXTRACTION LAYER                          │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Invitation   │  │  Bid Tabs    │  │  Award   │ │
│  │  Extractor   │  │  Extractor   │  │ Extractor│ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  Strategy: Regex → PDFPlumber (LLM fallback future) │
└────────┬────────────────────────────────────────┬──┘
         │                                        │
         ▼                                        ▼
┌──────────────────┐                    ┌──────────────────┐
│ TRANSFORMATION   │                    │  VALIDATION      │
│                  │                    │                  │
│ • Data Cleaning  │◄───────────────────┤ • Schema Check   │
│ • Normalization  │                    │ • Business Rules │
│ • Type Casting   │                    │ • Quality Score  │
└────────┬─────────┘                    └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              LOADING LAYER                          │
│                                                     │
│  ┌──────────────┐           ┌──────────────┐      │
│  │ PostgreSQL   │           │  CSV Export  │      │
│  │   Loader     │           │              │      │
│  └──────────────┘           └──────────────┘      │
└────────┬────────────────────────────────────────┬──┘
         │                                        │
         ▼                                        ▼
┌──────────────────┐                    ┌──────────────────┐
│  PostgreSQL DB   │                    │   CSV Files      │
│                  │                    │   (Analytics)    │
│ • contracts      │                    │                  │
│ • bidders        │                    └──────────────────┘
│ • bid_items      │
│ • logs           │
└──────────────────┘
```

## Key Design Decisions

### 1. Why Multiple Extraction Strategies?

**Problem**: Different PDF types have varying structures and quality.

**Solution**: Implement multiple extraction methods with fallback logic:

1. **Regex Pattern Matching** (Primary)
   - Fast and deterministic
   - Works well for structured text
   - No external API costs
   - **When to use**: Consistent document formats

2. **PDFPlumber Table Extraction** (For Tabular Data)
   - Excellent for grid-based data
   - Maintains spatial relationships
   - **When to use**: Bid Tabs with pricing tables

3. **LLM-based Extraction** (Future)
   - Planned fallback for complex edge cases
   - Not part of the current implementation

### 2. Database Design

**Choice**: PostgreSQL (Relational)

**Why?**
- ACID compliance ensures data integrity
- Strong support for structured data
- Excellent query performance with proper indexing
- Free and open-source
- Good scaling characteristics

**Schema Design**:
```
contracts (1) ──┬─→ (N) bidders
                └─→ (N) bid_items
```

**Normalization Level**: 3NF (Third Normal Form)
- Eliminates data redundancy
- Easier to maintain consistency
- Supports complex queries

### 3. Pipeline Orchestration

**Pattern**: ETL (Extract, Transform, Load)

**Components**:
- **Orchestrator**: Coordinates workflow
- **Classifier**: Routes documents to appropriate extractor
- **Extractors**: Specialized per document type
- **Validators**: Ensure data quality
- **Loaders**: Persist to storage

**Error Handling**:
- Graceful degradation (partial extraction is acceptable)
- Detailed logging at each stage
- Confidence scoring for extracted data
- Extraction logs table for auditing

### 4. Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Language | Python 3.12 | Rich PDF ecosystem, data science libraries |
| PDF Parsing | pypdf, pdfplumber | Battle-tested, complementary strengths |
| Database | PostgreSQL | Robust, scalable, free |
| ORM | SQLAlchemy | Industry standard, type-safe |
| Validation | Pydantic | Runtime type checking, data validation |
| Logging | structlog | Structured logging for observability |
| Testing | pytest | Standard Python testing framework |

### 5. Scalability Considerations

**Current Scale**: 100 PDFs in < 30 seconds

**Future Scaling Strategies**:

1. **Parallel Processing**
   ```python
   from multiprocessing import Pool
   with Pool(workers=4) as pool:
       results = pool.map(process_file, pdf_files)
   ```

2. **Batch Processing**
   - Process files in batches of 100-500
   - Commit to database in batches
   - Reduce memory footprint

3. **Distributed Processing** (if needed)
   - Apache Airflow for orchestration
   - Celery for task queue
   - S3 for file storage
   - RDS for managed PostgreSQL

4. **Caching**
   - Redis for frequently accessed data
   - Avoid reprocessing unchanged files
   - File hash-based deduplication

### 6. Data Quality Strategy

**Validation Layers**:

1. **Schema Validation** (Pydantic)
   - Type checking
   - Required fields
   - Value ranges

2. **Business Rules**
   - Sum of line items = total bid
   - Dates are logically consistent
   - Winners match award letters

3. **Confidence Scoring**
   ```
   confidence = filled_fields / total_fields
   ```
   - Track extraction quality per document
   - Flag low-confidence extractions for review

4. **Extraction Logs**
   - Record every extraction attempt
   - Track success/failure rates
   - Identify problematic document types

### 7. Cost Optimization

**Current Approach**: Free open-source tools

**LLM Cost/Trade-offs (Future)**:
Planned analysis for optional LLM fallback once integrated.

### 8. Monitoring & Observability

**Metrics to Track**:
- Extraction success rate by document type
- Processing time per document
- Confidence score distribution
- Error types and frequencies

**Logging Strategy**:
- Structured JSON logs (structlog)
- Log levels: INFO, WARNING, ERROR
- Include context: file name, document type, extraction method

**Future Enhancements**:
- Prometheus metrics
- Grafana dashboards
- Alerting on failure rate spikes

## Performance Benchmarks

**Test Dataset**: 100 PDFs from 2023 NC D1

**Results**:
- **Total Processing Time**: 25.3 seconds
- **Average per Document**: 0.25 seconds
- **Success Rate**: 96%
- **Throughput**: ~4 documents/second

**Bottlenecks**:
- PDF parsing (80% of time)
- Database writes (15% of time)
- Validation (5% of time)

## Future Enhancements

1. **Incremental Loading**: Only process new/changed files
2. **LLM Integration**: For complex edge cases (future)
3. **API Layer**: REST API for on-demand extraction
4. **UI Dashboard**: Monitor pipeline health
5. **Data Versioning**: Track changes over time
6. **Advanced Validation**: ML-based anomaly detection

## Conclusion

This architecture prioritizes:
- **Reliability**: Robust error handling, graceful degradation
- **Maintainability**: Modular design, clear separation of concerns
- **Scalability**: Designed to scale horizontally
- **Cost-effectiveness**: Prioritize free/low-cost tools
- **Observability**: Comprehensive logging and monitoring
