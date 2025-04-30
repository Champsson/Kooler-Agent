import os
import sys
import argparse
import uuid

# Add project root to sys.path to allow importing app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.services import vector_service
from app.utils import get_logger
from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter

logger = get_logger(__name__)

# --- Configuration ---
# Using RecursiveCharacterTextSplitter as a robust default. 
# If Markdown structure is crucial for context, MarkdownTextSplitter can be used.
CHUNK_SIZE = 1000  # Size of text chunks
CHUNK_OVERLAP = 150 # Overlap between chunks
BATCH_SIZE = 100   # Number of vectors to upsert in one batch

def process_and_embed_document(file_path):
    """Reads, chunks, embeds, and upserts a document into Pinecone."""
    logger.info(f"Starting processing for document: {file_path}")

    # 1. Read Document Content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read document: {file_path}")
    except Exception as e:
        logger.error(f"Failed to read document {file_path}: {e}", exc_info=True)
        return

    # 2. Chunk Document
    # text_splitter = MarkdownTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", " ", ""] # Common separators
    )
    chunks = text_splitter.split_text(content)
    logger.info(f"Document split into {len(chunks)} chunks.")

    if not chunks:
        logger.warning("No chunks were generated from the document.")
        return

    # 3. Initialize Pinecone (ensure connection is ready)
    try:
        vector_service.initialize_pinecone()
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone during ingestion: {e}")
        return # Stop processing if Pinecone isn't available

    # 4. Embed and Prepare Vectors in Batches
    vectors_to_upsert = []
    total_processed = 0
    for i, chunk in enumerate(chunks):
        try:
            embedding = vector_service.get_embedding(chunk)
            vector_id = str(uuid.uuid4()) # Generate unique ID for each vector
            metadata = {"text": chunk, "source": os.path.basename(file_path), "chunk_index": i}
            vectors_to_upsert.append((vector_id, embedding, metadata))
            total_processed += 1
            logger.debug(f"Generated embedding for chunk {i+1}/{len(chunks)}")

            # Upsert in batches
            if len(vectors_to_upsert) >= BATCH_SIZE:
                logger.info(f"Upserting batch of {len(vectors_to_upsert)} vectors...")
                vector_service.upsert_vectors(vectors_to_upsert)
                vectors_to_upsert = [] # Clear the batch

        except Exception as e:
            logger.error(f"Failed to process chunk {i}: {e}", exc_info=True)
            # Decide whether to skip the chunk or stop the process
            # continue # Skip this chunk
            # return # Stop processing

    # 5. Upsert any remaining vectors
    if vectors_to_upsert:
        logger.info(f"Upserting final batch of {len(vectors_to_upsert)} vectors...")
        try:
            vector_service.upsert_vectors(vectors_to_upsert)
        except Exception as e:
            logger.error(f"Failed to upsert final batch: {e}", exc_info=True)

    logger.info(f"Finished processing document {file_path}. Total chunks processed: {total_processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process and embed documents into Pinecone.")
    parser.add_argument(
        "--file", 
        type=str, 
        required=True, 
        help="Path to the document file to process (e.g., data/Weggy_Master_Document.md)"
    )
    args = parser.parse_args()

    # Construct absolute path if a relative path is given
    file_path_arg = args.file
    if not os.path.isabs(file_path_arg):
        file_path_arg = os.path.join(project_root, file_path_arg)
    
    if not os.path.exists(file_path_arg):
        logger.error(f"Input file not found: {file_path_arg}")
        sys.exit(1)

    process_and_embed_document(file_path_arg)

