# Learn Mate Backend Tests

This directory contains comprehensive tests for the Learn Mate backend API.

## Test Structure

```
tests/
├── api/
│   └── v1/
│       ├── test_auth.py          # Authentication endpoint tests
│       ├── test_conversations.py  # Conversation management tests
│       └── test_messages.py       # Message handling tests
├── test_repositories.py          # Repository layer tests
├── test_services.py              # Service layer tests
├── test_integration.py           # End-to-end integration tests
└── conftest.py                   # Pytest fixtures and configuration
```

## Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.sh

# Or using pytest directly
pytest
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest tests/test_repositories.py tests/test_services.py -v

# Run only API tests
pytest tests/api/v1/ -v

# Run only integration tests
pytest -m integration

# Run tests for a specific module
pytest tests/api/v1/test_conversations.py -v
```

### Running with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Running Tests in Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests in watch mode
ptw
```

## Test Configuration

Tests are configured in `pytest.ini` with the following settings:
- Automatic async test support
- Coverage requirements (80% minimum)
- Test discovery patterns
- Warning filters

## Writing Tests

### Test Fixtures

Common fixtures are available in `conftest.py`:

- `client`: FastAPI test client
- `session`: Database session for testing
- `test_user`: Pre-created test user
- `auth_headers`: Authentication headers with valid token
- `test_conversation`: Pre-created conversation
- `test_messages`: Sample messages in a conversation
- `mock_langgraph_agent`: Mocked AI agent for testing

### Example Test

```python
def test_create_conversation(
    client: TestClient,
    auth_headers: dict,
    test_user: User
):
    response = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Test Conversation"}
    )
    
    assert response.status_code == 200
    assert response.json()["title"] == "Test Conversation"
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_service(
    session: Session,
    test_user: User
):
    service = ConversationService(session)
    result = await service.create_conversation(
        user_id=test_user.id,
        title="Async Test"
    )
    assert result.title == "Async Test"
```

### Testing Streaming Responses

```python
with client.stream("POST", url, headers=headers, json=data) as response:
    assert response.status_code == 200
    
    for line in response.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            # Process event
```

## Mocking

The test suite uses various mocking strategies:

1. **Database**: Uses in-memory SQLite for fast, isolated tests
2. **AI Agent**: Mocked to return predictable responses
3. **External Services**: Mocked using `unittest.mock`

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pip install pytest pytest-cov pytest-asyncio
    pytest --cov=app --cov-fail-under=80
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running tests from the backend root directory
2. **Database Errors**: Tests use SQLite in-memory, no PostgreSQL required
3. **Async Warnings**: Use `pytest.mark.asyncio` for async tests

### Debug Mode

Run tests with detailed output:
```bash
pytest -vv --tb=long --log-cli-level=DEBUG
```

## Test Data

Tests use realistic mock data:
- User emails: `test@example.com`, `user1@test.com`, etc.
- Conversation titles: Descriptive and varied
- Messages: Realistic user and AI interactions

## Performance

- Tests run in parallel when possible
- Database is in-memory for speed
- Fixtures are scoped appropriately
- Mock external calls to avoid network delays

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain >80% code coverage
4. Add integration tests for complex flows
5. Document any new fixtures or patterns