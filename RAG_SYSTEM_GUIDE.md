# RAG System Technical Guide

This document provides a comprehensive overview of the RAG (Retrieval-Augmented Generation) system implementation.
It includes the latest enhancements and performance optimizations.

## 🏗️ Architecture Overview

### Core Components

1. **Document Ingestion Pipeline**
   - PDF processing with PyMuPDF
   - Intelligent chunking with enhanced chunker
   - Metadata extraction and normalization

2. **Hybrid Search System**
   - BM25 (keyword-based) search via SQLite FTS5
   - Vector search via Weaviate
   - Score-based fusion with z-score normalization

3. **Advanced Ranking System**
   - Cross-Encoder reranking with sentence-transformers
   - Feature boost layer for tie-breaking
   - Protected-Top logic for fair competition

4. **Response Generation**
   - Context packing with token budget management
   - Discord-optimized output formatting
   - Multiple LLM providers support (OpenAI, Azure OpenAI)

## 🔍 Search & Retrieval Pipeline

### Hybrid Search Implementation

The system combines two complementary search methods:

#### BM25 Search (SQLite FTS5)

```python
# BM25 configuration
k_bm25 = 50
bm25_weight = 0.2
```

**Features:**

- Full-text search with FTS5
- Query preprocessing and escaping
- Source-based filtering
- Configurable result limits

#### Vector Search (Weaviate)

```python
# Vector search configuration
k_vec = 50
vec_weight = 0.8
```

**Features:**

- OpenAI text-embedding-3-small embeddings
- Semantic similarity search
- Multi-modal support (text, images)
- Batch processing capabilities

### Score Fusion Methods

#### 1. Z-Score Normalization Fusion

```python
# Primary fusion method
score_fused = (bm25_score_norm * bm25_weight) + (vec_score_norm * vec_weight)
```

#### 2. Rank-Based RRF (Reciprocal Rank Fusion)

```python
# Fallback fusion method
rrf_c = 15  # RRF constant
rrf_score = 1 / (rrf_c + rank)
```

### Cross-Encoder Reranking

```python
# Reranking configuration
use_rerank = True
rerank_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
preselect_topn = 50
```

**Benefits:**

- Improved relevance scoring
- Query-document semantic matching
- Better handling of complex queries

## 🎯 Advanced Ranking Features

### Feature Boost Layer

The system implements a sophisticated feature boost layer for tie-breaking:

```python
# Feature weights
lexical_weight = 0.20    # Query-document lexical overlap
title_weight = 0.10      # Title/section heading matches
position_weight = 0.08   # Document position priority
neighbor_weight = 0.05   # Adjacent chunk bonus
```

### Protected-Top Logic

Ensures fair competition between different ranking methods:

```python
# Protected-Top configuration
ce_top1_included = True    # Always include Cross-Encoder top-1
bm25_seed_included = True  # Include BM25 top seed
vec_seed_included = True   # Include vector top seed
per_doc_cap = 3           # Maximum chunks per document
```

### Per-Document Capping

Limits the number of chunks from a single document:

```python
# Document capping
per_doc_cap = 3
cap_exception_relevant = True  # Allow more for relevant documents
```

## 📊 Performance Metrics

### Current Performance (k=10)

Based on evaluation with 100 test cases:

| Metric | Value | Target |
|--------|-------|---------|
| **nDCG@10** | 0.401 | >0.3 |
| **Hit Rate** | 0.918 | >0.5 |
| **Precision@10** | 0.174 | - |
| **Recall@10** | 0.490 | - |
| **MRR@10** | 0.401 | - |
| **Average Latency** | <1000ms | <1000ms |

### Key Improvements

- **Hit Rate**: 0.490 → 0.918 (87% improvement)
- **nDCG@10**: 0.174 → 0.401 (130% improvement)
- **Median Rank**: 6.0 → 5.0 (17% improvement)

## 🛠️ Configuration Parameters

### Search Parameters

```python
# Basic search configuration
k_bm25 = 50              # BM25 result count
k_vec = 50               # Vector search result count
k_final = 3              # Final result count

# Fusion weights
bm25_weight = 0.2        # BM25 contribution
vec_weight = 0.8         # Vector search contribution

# Reranking parameters
use_rerank = True        # Enable Cross-Encoder reranking
rerank_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
preselect_topn = 50      # Candidates for reranking
per_doc_cap = 3          # Max chunks per document
```

### Feature Boost Weights

```python
# Feature boost configuration
lexical_weight = 0.20    # Lexical overlap bonus
title_weight = 0.10      # Title hit bonus
position_weight = 0.08   # Position priority
neighbor_weight = 0.05   # Neighbor chunk bonus
```

## 🔧 Evaluation Framework

### Evaluation Metrics

The system tracks comprehensive performance metrics:

#### Retrieval Metrics

- **Precision@k**: Accuracy of top-k results
- **Recall@k**: Coverage of relevant documents
- **nDCG@k**: Normalized Discounted Cumulative Gain
- **MRR@k**: Mean Reciprocal Rank
- **Hit Rate**: Percentage of queries with at least one relevant result

#### Performance Metrics

- **Latency**: End-to-end response time
- **Throughput**: Queries per second
- **Error Rate**: Failed query percentage

#### Business Metrics

- **User Satisfaction**: Feedback-based rating
- **Query Success Rate**: Successful query percentage
- **Document Coverage**: Percentage of indexed documents retrieved

### Evaluation Dataset

```python
# Gold dataset configuration
total_cases = 100        # Evaluation test cases
supplement_cases = 49    # Additional test cases
intent_distribution = {
    "schedule": 25,      # Schedule-related queries
    "faq": 20,          # FAQ queries
    "training": 15,     # Training-related queries
    "resources": 10,    # Resource queries
    "other": 30         # Other query types
}
```

## 🚀 Deployment & Scaling

### Production Configuration

```python
# Production settings
k_bm25 = 50
k_vec = 50
k_final = 3
use_rerank = True
preselect_topn = 50
per_doc_cap = 3
bm25_weight = 0.2
vec_weight = 0.8
```

### Scaling Considerations

#### Horizontal Scaling

- **API Layer**: Multiple FastAPI instances behind load balancer
- **Vector Database**: Weaviate cluster with replication
- **Document Storage**: Distributed file storage

#### Vertical Scaling

- **Memory**: 4GB+ for vector operations
- **CPU**: Multi-core for parallel processing
- **Storage**: SSD for database performance

### Monitoring & Alerting

#### Key Metrics to Monitor

- **Query Latency**: p95 < 1000ms
- **Hit Rate**: >90%
- **Error Rate**: <5%
- **Memory Usage**: <80% of allocated
- **Disk Usage**: <80% of allocated

#### Alerting Thresholds

- **Critical**: Hit rate < 80%, Error rate > 10%
- **Warning**: Latency > 2000ms, Memory > 90%

## 🔄 Maintenance & Updates

### Regular Maintenance Tasks

1. **Index Updates**
   - Add new documents to index
   - Update embeddings for modified documents
   - Rebalance vector clusters

2. **Performance Monitoring**
   - Review evaluation metrics weekly
   - Analyze failure cases
   - Optimize ranking parameters

3. **Data Quality**
   - Validate document chunking
   - Check embedding quality
   - Monitor query patterns

### Model Updates

```python
# Updating embedding models
embedding_model = "text-embedding-3-small"
rerank_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# A/B testing new models
experimental_rerank_model = "cross-encoder/ms-marco-MiniLM-L-12-v2"
```

## 📚 Best Practices

### Query Optimization

1. **Query Preprocessing**
   - Normalize query text
   - Handle special characters
   - Extract key terms

2. **Result Postprocessing**
   - Apply business rules
   - Filter inappropriate content
   - Rank by business priorities

### Error Handling

1. **Graceful Degradation**
   - Fallback to simpler search if reranking fails
   - Use cached results for common queries
   - Provide meaningful error messages

2. **Monitoring & Logging**
   - Log all search queries and results
   - Track performance metrics
   - Monitor system health

### Security Considerations

1. **Input Validation**
   - Sanitize user queries
   - Prevent injection attacks
   - Rate limit requests

2. **Data Privacy**
   - Anonymize user queries in logs
   - Encrypt sensitive documents
   - Comply with data regulations

## 🔮 Future Enhancements

---

## Enhanced RAG System - Implementation Checklist (Merged)

This section consolidates the implementation checklist previously maintained in `ENHANCED_RAG_CHECKLIST.md`.

## Completed Implementation Items

- Query decomposition and intent detection
- Document preprocessing and metadata enhancement
- Chunking strategy improvements
- Hybrid search enhancements
- Discord-optimized prompt v2.0
- Evaluation dataset expansion (50 items)
- Monitoring and observability enhancements
- API and service integration

## Ready-to-run Commands

```bash
docker-compose up -d
cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
cd bots && python run_bot.py
```

## Enhanced RAG API Testing

```bash
curl -X POST "http://localhost:8001/api/v1/rag/" -H "Content-Type: application/json" -d '{"query": "When is Week 4 Pitch Day?", "top_k": 5}'
curl -X POST "http://localhost:8001/api/v1/enhanced-rag/" -H "Content-Type: application/json" -d '{"query": "What is the exact schedule for Week 4 Pitch Day and can you provide the team matching form link?", "top_k": 5}'
```

## Monitoring & Logs

```bash
curl http://localhost:8001/metrics
docker logs discord-rag-api
docker logs discord-rag-bot
```

### Planned Improvements

1. **Multi-Modal Search**
   - Image and text combined search
   - Video content indexing
   - Audio transcription search

2. **Advanced Reranking**
   - Learned-to-rank models
   - User preference learning
   - Contextual reranking

3. **Real-Time Updates**
   - Streaming document ingestion
   - Incremental index updates
   - Live query processing

### Research Areas

1. **Query Understanding**
   - Intent classification
   - Query expansion
   - Semantic parsing

2. **Document Understanding**
   - Entity extraction
   - Relationship modeling
   - Content summarization

3. **Personalization**
   - User profiling
   - Preference learning
   - Adaptive ranking
