import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

# Global model cache for efficiency
_model = None

def get_embedding_model(model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """Get or initialize the embedding model"""
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer(model_name)
            print(f"Embedding model initialized: {model_name}")
        except Exception as e:
            print(f"Error initializing embedding model: {str(e)}")
            try:
                _model = SentenceTransformer("all-MiniLM-L6-v2")
                print("Using fallback model: all-MiniLM-L6-v2")
            except Exception as e2:
                raise Exception(f"Failed to initialize embedding model: {str(e2)}")
    return _model

def generate_embeddings(text, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """Generate embeddings for text using the specified model"""
    model = get_embedding_model(model_name)
    # Handle single string or list of strings
    if isinstance(text, str):
        return model.encode(text).tolist()
    else:
        return model.encode(text).tolist()

def store_in_pinecone(embeddings_data, index_name="deloitte-reports"):
    """Store embeddings data in Pinecone"""
    try:
        # Initialize Pinecone if not already initialized
        api_key = os.getenv("PINECONE_API_KEY")
        
        if not api_key:
            raise ValueError("Pinecone API key not configured")
            
        pc = Pinecone(api_key=api_key)
        
        # Check if index exists
        if index_name not in [idx["name"] for idx in pc.list_indexes()]:
            # Get dimension from first embedding
            dimension = len(embeddings_data[0]['embedding'])
            
            # Create index with the right dimension
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        
        # Get index
        index = pc.Index(index_name)
        
        # Prepare vectors for Pinecone
        vectors = []
        
        for i, item in enumerate(embeddings_data):
            chunk_id = f"{item['metadata']['document_id']}_chunk_{i}"
            vector = {
                "id": chunk_id,
                "values": item['embedding'],
                "metadata": {
                    "text": item['content'],
                    "industry": item['metadata']['industry'],
                    "year": item['metadata']['year'],
                    "document_id": item['metadata']['document_id']
                }
            }
            vectors.append(vector)
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
        
        print(f"Stored {len(embeddings_data)} chunks in Pinecone index '{index_name}'")
        return True
    except Exception as e:
        print(f"Error storing in Pinecone: {str(e)}")
        return False

def search_pinecone(query, index_name="nvidia-financials", filter_dict=None, top_k=5):
    """Search for similar documents in Pinecone"""
    try:
        # Initialize Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        
        if not api_key:
            raise ValueError("Pinecone API key not configured")
            
        pc = Pinecone(api_key=api_key)
        
        # Generate embedding for query
        query_embedding = generate_embeddings(query)
        print("Query embedding: ", query_embedding)
        # Get Pinecone index
        index = pc.Index(index_name)
        
        # Query the index
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )
        print("Results from Pinecone: ", results)
        # Format results
        formatted_results = []
        
        for match in results.get("matches", []):
            metadata = match.get("metadata", {})
            
            formatted_results.append({
                "text": metadata.get("text", ""),
                "document_id": metadata.get("document_id", "unknown"),
                "quarter": metadata.get("quarter", "unknown"),
                "similarity": float(match.get("score", 0.0))
            })
        
        return formatted_results
    except Exception as e:
        print(f"Error searching Pinecone: {str(e)}")
        return []