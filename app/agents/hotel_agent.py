import chromadb
import pandas as pd
import streamlit as st
import os
import asyncio 
import chromadb.utils.embedding_functions as embedding_functions
from pathlib import Path
from logging import getLogger

EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
COLLECTION_NAME = "indian_hotels"

SCRIPT_DIR = Path(__file__).parent

FILE_PATH = SCRIPT_DIR.parent / "data" / "hotel_details.csv"

logger = getLogger(__name__)

class HotelRecommenderAgent:
    def __init__(self, database_path=FILE_PATH, db_directory='./chroma_db'):
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.client = chromadb.PersistentClient(path=db_directory)
        
        try:
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_function
            )
            
            if self.collection.count() == 0:
                logger.info("Collection is new or empty. Ingesting data...")
                self._ingest_data(database_path)
            else:
                logger.info(f"Connected to existing ChromaDB collection with {self.collection.count()} items.")

        except Exception as e:
            st.error(f"Error connecting to ChromaDB: {e}")
            logger.error(f"Error connecting to ChromaDB: {e}")

    def _ingest_data(self, database_path):
        """Helper function to load CSV and populate ChromaDB in batches."""
        try:
            db = pd.read_csv(database_path)
            
            required_columns = {
                'Hotel Name': 'name',
                'description': 'description',
                'Place': 'address',
                'Rating': 'rating'
            }
            
            db = db[list(required_columns.keys())]
            db = db.rename(columns=required_columns)
            db = db.dropna(subset=['name', 'description'])
            
            db['rating'] = pd.to_numeric(db['rating'], errors='coerce').fillna(0.0)
            db['address'] = db['address'].astype(str)
            db['description'] = db['description'].astype(str)
            db['name'] = db['name'].astype(str)
            
            db.reset_index(drop=True, inplace=True)

            logger.info(f"Ingesting {len(db)} hotels into ChromaDB...")

            documents = db['description'].tolist()
            metadatas = db.to_dict(orient='records')
            ids = [f"hotel_{i}" for i in range(len(db))]

            batch_size = 1000
            total_items = len(documents)

            for i in range(0, total_items, batch_size):
                end_index = min(i + batch_size, total_items)
                batch_docs = documents[i:end_index]
                batch_metadatas = metadatas[i:end_index]
                batch_ids = ids[i:end_index]
                
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
            logger.info("Ingestion complete.")
            
        except FileNotFoundError:
            st.error(f"Error: Hotel database file not found at {database_path}")
        except KeyError as e:
            st.error(f"Error: Your CSV is missing a required column: {e}")
        except Exception as e:
            st.error(f"An error occurred during data ingestion: {e}")

    async def find_hotels(self, user_preference, destination_city, top_k=3):
        """
        Async finds hotels using ChromaDB's query function,
        running the sync query in a separate thread.
        """
        print(f"Querying ChromaDB for: '{user_preference}' in city: '{destination_city}'")
        
        def _query_chroma():
            """
            Internal synchronous function to run in a thread.
            """
            where_filter = {
                "address": destination_city.title()
            }
            results = self.collection.query(
                query_texts=[user_preference],
                n_results=top_k,
                where=where_filter
            )
            
            recommended_hotels = []
            if not results['metadatas'] or not results['metadatas'][0]:
                logger.info(f"No hotels found in ChromaDB for city: {destination_city.title()}")
                return []
                
            for metadata in results['metadatas'][0]:
                recommended_hotels.append({
                    'name': metadata.get('name'),
                    'description': metadata.get('description'),
                    'address': metadata.get('address'),
                    'rating': metadata.get('rating')
                })
            return recommended_hotels

        try:
            recommended_hotels = await asyncio.to_thread(_query_chroma)
            return recommended_hotels

        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            st.error(f"Error querying hotel database: {e}")
            return [{'name': 'Error', 'description': 'Error querying database.', 'address': '', 'rating': 'N/A'}]
