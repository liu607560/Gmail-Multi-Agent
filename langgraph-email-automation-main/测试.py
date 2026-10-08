import chromadb

client = chromadb.PersistentClient(path="db")
print(client.list_collections())

collection = client.get_collection("langchain")
data = collection.get(include=["documents", "metadatas"])

for index, (chunk_id, document) in enumerate(
    zip(data["ids"], data["documents"]),
    start=1
):
    print(f"\n{'=' * 80}")
    print(f"Chunk {index}")
    print(f"ID: {chunk_id}")
    print("-" * 80)
    print(document)