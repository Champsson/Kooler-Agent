import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import re # Import re for escaping

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Mock config before importing the service
with patch.dict(os.environ, {
    'PINECONE_API_KEY': 'fake-pinecone-key',
    'PINECONE_ENVIRONMENT': 'fake-pinecone-env',
    'PINECONE_INDEX_NAME': 'fake-index',
    'OPENAI_API_KEY': 'fake-openai-key'
}):
    from app.services import vector_service
    from app.config import config # Ensure config is loaded with mocks

# Fixture to reset mocks for each test
@pytest.fixture(autouse=True)
def reset_mocks():
    # Reset the global variables in the service module
    vector_service.pinecone_client = None
    vector_service.pinecone_index = None
    # Mock the clients used within the service
    vector_service.openai_client = MagicMock()
    # Clear cache if necessary
    if hasattr(vector_service, 'query_vector_db') and hasattr(vector_service.query_vector_db, 'cache_clear'):
        vector_service.query_vector_db.cache_clear()

# Patch the Pinecone class where it is instantiated
@patch('app.services.vector_service.pinecone.Pinecone')
def test_initialize_pinecone_index_exists(MockPinecone):
    """Test Pinecone initialization when the index already exists."""
    mock_pinecone_instance = MockPinecone.return_value
    mock_index_instance = MagicMock(name="MockIndexInstance") # Create a mock for the index
    mock_index_instance.describe_index_stats.return_value = {'total_vector_count': 100} # Mock stats

    # Mock the Index method *on the instance* to return our mock index
    mock_pinecone_instance.Index.return_value = mock_index_instance

    # Mock list_indexes to return the index name
    mock_index_info = MagicMock()
    mock_index_info.name = config.PINECONE_INDEX_NAME
    mock_pinecone_instance.list_indexes.return_value = [mock_index_info]

    # Call the function to test
    vector_service.initialize_pinecone()

    # Assertions
    MockPinecone.assert_called_once_with(api_key=config.PINECONE_API_KEY, environment=config.PINECONE_ENVIRONMENT)
    mock_pinecone_instance.list_indexes.assert_called_once()
    mock_pinecone_instance.create_index.assert_not_called() # Ensure create_index is NOT called
    mock_pinecone_instance.Index.assert_called_once_with(config.PINECONE_INDEX_NAME) # Check Index() was called
    assert vector_service.pinecone_index == mock_index_instance # Check the global variable is set
    mock_index_instance.describe_index_stats.assert_called_once() # Check stats were described

@patch('app.services.vector_service.pinecone.Pinecone')
def test_initialize_pinecone_index_does_not_exist(MockPinecone):
    """Test Pinecone initialization raises ValueError when the index does not exist."""
    mock_pinecone_instance = MockPinecone.return_value

    # Mock list_indexes to return an empty list or list without the target index
    mock_pinecone_instance.list_indexes.return_value = []

    # Expect ValueError because the code raises it if index not found
    # Match the exact literal string including the tabs
    expected_error_msg_literal = f"Pinecone index \t'{config.PINECONE_INDEX_NAME}'\t not found."
    with pytest.raises(ValueError, match=expected_error_msg_literal):
        vector_service.initialize_pinecone()

    # Assertions
    MockPinecone.assert_called_once_with(api_key=config.PINECONE_API_KEY, environment=config.PINECONE_ENVIRONMENT)
    mock_pinecone_instance.list_indexes.assert_called_once()
    mock_pinecone_instance.create_index.assert_not_called() # Ensure create_index is NOT called by default
    assert vector_service.pinecone_index is None # Index should not be set

def test_get_embedding():
    """Test generating embeddings using mocked OpenAI client."""
    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.1] * 1536 # Example embedding vector
    vector_service.openai_client.embeddings.create.return_value = MagicMock(data=[mock_embedding])

    text = "This is a test text.\nWith newline."
    expected_input_text = "This is a test text. With newline."
    embedding = vector_service.get_embedding(text)

    vector_service.openai_client.embeddings.create.assert_called_once_with(
        input=[expected_input_text], model="text-embedding-3-small"
    )
    assert len(embedding) == 1536
    assert embedding[0] == 0.1

@patch('app.services.vector_service.initialize_pinecone') # Prevent actual init
def test_upsert_vectors(mock_init_pinecone):
    """Test upserting vectors into the mocked Pinecone index."""
    # Ensure pinecone_index is mocked directly on the module
    mock_index = MagicMock()
    vector_service.pinecone_index = mock_index

    vectors_to_upsert = [
        ('id1', [0.1]*1536, {'text': 'chunk 1'}),
        ('id2', [0.2]*1536, {'text': 'chunk 2'})
    ]

    vector_service.upsert_vectors(vectors_to_upsert)

    mock_init_pinecone.assert_not_called() # Should not initialize if index is already set
    mock_index.upsert.assert_called_once_with(vectors=vectors_to_upsert)

@patch('app.services.vector_service.initialize_pinecone') # Prevent actual init
@patch('app.services.vector_service.get_embedding')
def test_query_vector_db(mock_get_embedding, mock_init_pinecone):
    """Test querying the vector database using mocked index and embedding."""
    # Ensure pinecone_index is mocked directly on the module
    mock_index = MagicMock()
    vector_service.pinecone_index = mock_index

    # Mock get_embedding return value
    mock_query_embedding = [0.5] * 1536
    mock_get_embedding.return_value = mock_query_embedding

    # Mock the index query response object and its .get() method
    mock_match_data = {
        'id': 'match1',
        'score': 0.9,
        'metadata': {'text': 'matched text chunk'}
    }
    mock_match_object = MagicMock(**mock_match_data)
    mock_query_response = MagicMock()
    # Configure the .get() method on the query response mock
    mock_query_response.get.return_value = [mock_match_object]
    mock_index.query.return_value = mock_query_response

    query_text = "User query"
    top_k = 3
    results = vector_service.query_vector_db(query_text, top_k=top_k)

    # Assertions
    mock_init_pinecone.assert_not_called() # Should not initialize if index is already set
    mock_get_embedding.assert_called_once_with(query_text)
    mock_index.query.assert_called_once_with(
        vector=mock_query_embedding,
        top_k=top_k,
        include_metadata=True # Corrected the truncated value
    )
    # Check that the .get() was called on the response object with the correct key
    mock_query_response.get.assert_called_once_with('matches', []) # Removed tab
    assert len(results) == 1
    # Access results like a list of objects
    assert results[0].id == 'match1'
    assert results[0].score == 0.9
    assert results[0].metadata['text'] == 'matched text chunk'

# Add more tests as needed, e.g., for error handling, edge cases

