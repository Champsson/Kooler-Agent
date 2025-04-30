import pinecone
from openai import OpenAI
from ..config import config
from ..utils import get_logger
import time
from .cache_service import cache_response # Import the cache decorator

logger = get_logger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# Initialize Pinecone
pinecone_client = None
pinecone_index = None

def initialize_pinecone():
    """Initializes the Pinecone client and index connection."""
    global pinecone_client, pinecone_index
    if pinecone_client and pinecone_index:
        logger.info("Pinecone already initialized.")
        return

    if not config.PINECONE_API_KEY or not config.PINECONE_ENVIRONMENT:
        logger.error("Pinecone API Key or Environment not configured. Cannot initialize Pinecone.")
        raise ValueError("Pinecone API Key or Environment not set.")

    try:
        logger.info(f"Initializing Pinecone with environment: {config.PINECONE_ENVIRONMENT}")
        pinecone_client = pinecone.Pinecone(
            api_key=config.PINECONE_API_KEY,
            environment=config.PINECONE_ENVIRONMENT
        )

        index_name = config.PINECONE_INDEX_NAME
        logger.info(f"Connecting to Pinecone index: {index_name}")

        # Check if index exists
        index_exists = False
        for index_info in pinecone_client.list_indexes():
            if index_info.name == index_name:
                index_exists = True
                break
        
        if not index_exists:
            # Keep the tabs in the error message as they are in the original code causing the test failure
            logger.error(f"Pinecone index \t'{index_name}'\t does not exist. Please create it first.")
            raise ValueError(f"Pinecone index \t'{index_name}'\t not found.")

        pinecone_index = pinecone_client.Index(index_name)
        logger.info(f"Successfully connected to Pinecone index \t'{index_name}'\t. Stats: {pinecone_index.describe_index_stats()}")

    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}", exc_info=True)
        pinecone_client = None
        pinecone_index = None
        raise

def get_embedding(text, model="text-embedding-3-small"):
    """Generates an embedding for the given text using OpenAI."""
    try:
        text = text.replace("\n", " ")
        response = openai_client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to get embedding for text: \t{text[:100]}...\t Error: {e}", exc_info=True)
        raise

def upsert_vectors(vectors):
    """Upserts vectors into the Pinecone index.
    Args:
        vectors (list): A list of tuples, where each tuple is (id, vector, metadata).
                      Example: [('\tvec1\t', [0.1, 0.2], {'\ttext\t': '\tchunk1\t'}), ...]
    """
    if not pinecone_index:
        logger.error("Pinecone index not initialized. Cannot upsert vectors.")
        initialize_pinecone() # Attempt to initialize
        if not pinecone_index:
             raise ConnectionError("Pinecone index is not available.")

    try:
        logger.info(f"Upserting {len(vectors)} vectors to Pinecone index \t'{config.PINECONE_INDEX_NAME}'\t...")
        # Pinecone client expects vectors in the format: [(id, values, metadata), ...]
        upsert_response = pinecone_index.upsert(vectors=vectors)
        logger.info(f"Upsert response: {upsert_response}")
        return upsert_response
    except Exception as e:
        logger.error(f"Failed to upsert vectors: {e}", exc_info=True)
        raise

@cache_response(ttl=3600) # Cache results for 1 hour
def query_vector_db(query_text, top_k=5):
    """Queries the Pinecone index for relevant documents based on query text."""
    if not pinecone_index:
        logger.error("Pinecone index not initialized. Cannot query.")
        initialize_pinecone() # Attempt to initialize
        if not pinecone_index:
             raise ConnectionError("Pinecone index is not available.")

    try:
        logger.info(f"Generating embedding for query: \t{query_text[:100]}...\t")
        query_embedding = get_embedding(query_text)

        logger.info(f"Querying Pinecone index \t'{config.PINECONE_INDEX_NAME}'\t with top_k={top_k}...")
        query_response = pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        # Call .get() only once
        matches = query_response.get('matches', [])
        logger.info(f"Query response received. Found {len(matches)} matches.")
        return matches
    except Exception as e:
        logger.error(f"Failed to query vector database: {e}", exc_info=True)
        raise

# Initialize Pinecone on module load (optional, can be deferred)
# initialize_pinecone()

