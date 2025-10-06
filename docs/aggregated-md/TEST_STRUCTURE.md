# Test Structure Documentation

## 📁 Test Organization

### RAG Agent Tests (`rag_agent/tests/`)

Core functionality tests for the RAG agent:

- **`test_chunk_validation.py`** - Chunk validation tests
  - Tests offset integrity, ID stability, length statistics
  - Integration checks for chunking system
  - Validates enhanced chunker functionality

- **`test_regression.py`** - Regression test suite
  - Resource parsing tests
  - Mixed intent detection tests
  - Search functionality without backend
  - Vector search validation

- **`test_generation_pipeline.py`** - Generation pipeline tests
- **`test_query_planner_mixed.py`** - Query planner mixed intent tests
- **`test_smoke.py`** - Smoke tests for basic functionality

### Backend Tests (`backend/tests/`)

API and backend service tests:

- **`test_feedback_integration.py`** - Feedback service integration tests
- **`test_error_handling.py`** - Error handling tests
- **`test_health_endpoint.py`** - Health endpoint tests
- **`test_rag.py`** - RAG API endpoint tests

## 🧪 Test Categories

### 1. **Unit Tests**

- Individual component testing
- Function-level validation
- Mock-based testing

### 2. **Integration Tests**

- Cross-component interaction testing
- End-to-end workflow validation
- API integration testing

### 3. **Regression Tests**

- Feature stability validation
- Performance regression detection
- Compatibility testing

### 4. **Smoke Tests**

- Basic functionality verification
- Quick health checks
- Critical path validation

## 🚀 Running Tests

### RAG Agent Tests

```bash
cd rag_agent
python -m pytest tests/
```

### Backend Tests

```bash
cd backend
python -m pytest tests/
```

### Specific Test Files

```bash
# Chunk validation tests
python rag_agent/tests/test_chunk_validation.py

# Regression tests
python rag_agent/tests/test_regression.py

# Feedback integration tests
python backend/tests/test_feedback_integration.py
```

## 📋 Test Coverage

- **Chunking System**: Validation, integrity, statistics
- **Query Planning**: Intent detection, mixed queries
- **Retrieval Pipeline**: Search functionality, vector operations
- **API Endpoints**: Health, feedback, RAG operations
- **Integration**: Cross-service communication

## 🔧 Maintenance

### Adding New Tests

1. Place unit tests in appropriate `tests/` directory
2. Follow naming convention: `test_*.py`
3. Include proper imports and path setup
4. Add documentation for complex test scenarios

### Test Organization Principles

- **Separation**: Unit vs Integration vs Regression
- **Location**: Tests near the code they test
- **Naming**: Clear, descriptive test names
- **Documentation**: Purpose and scope clearly defined
