from ..services import vector_service
from ..utils import get_logger

logger = get_logger(__name__)

def query_knowledge_base(query: str) -> str:
    """Queries the Kooler knowledge base (Pinecone) to find relevant information based on the user query.

    Args:
        query (str): The user's question or query to search for in the knowledge base.

    Returns:
        str: A formatted string containing the most relevant information found, or a message indicating no relevant information was found.
    """
    logger.info(f"Received knowledge base query: 	{query}	")
    try:
        # Ensure Pinecone is initialized before querying
        vector_service.initialize_pinecone()
        
        matches = vector_service.query_vector_db(query, top_k=3) # Get top 3 relevant chunks
        
        if not matches:
            logger.info("No relevant information found in the knowledge base.")
            return "I couldn't find specific information about that in the Kooler knowledge base."

        # Format the results
        context = "\n\n---\n\n".join([match[	'metadata	'][	'text	'] for match in matches])
        result_string = f"Based on the Kooler knowledge base, here's some relevant information:\n\n{context}"
        
        logger.info(f"Found {len(matches)} relevant chunks. Returning formatted result.")
        return result_string

    except ConnectionError as ce:
        logger.error(f"Knowledge base query failed due to connection error: {ce}")
        return "Sorry, I'm having trouble connecting to the knowledge base right now. Please try again later."
    except Exception as e:
        logger.error(f"An error occurred during knowledge base query: {e}", exc_info=True)
        return "Sorry, an unexpected error occurred while searching the knowledge base."

# Example usage (for testing)
if __name__ == '__main__':
    test_query = "How to reset a garage door opener?"
    print(f"Testing knowledge base query: {test_query}")
    result = query_knowledge_base(test_query)
    print("\nResult:")
    print(result)

    test_query_2 = "What are the business hours?"
    print(f"\nTesting knowledge base query: {test_query_2}")
    result_2 = query_knowledge_base(test_query_2)
    print("\nResult:")
    print(result_2)

