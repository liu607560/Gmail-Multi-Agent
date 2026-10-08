import os

from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

RAG_SEARCH_PROMPT_TEMPLATE = """
Using the following pieces of retrieved context, answer the question comprehensively and concisely.
Ensure your response fully addresses the question based on the given context.

**IMPORTANT:**
Just provide the answer and never mention or refer to having access to the external context or information in your answer.
If you are unable to determine the answer from the provided context, state 'I don't know.'

Question: {question}
Context: {context}
"""

print("Loading & Chunking Docs...")
with open("./data/agency.txt", "r", encoding="utf-8") as file:
    docs = [Document(page_content=file.read())]

doc_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
doc_chunks = doc_splitter.split_documents(docs)

print("Creating vector embeddings...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

connection = os.environ["PGVECTOR_CONNECTION_STRING"]
collection_name = os.getenv("PGVECTOR_COLLECTION", "email_knowledge")

vectorstore = PGVector.from_documents(
    documents=doc_chunks,
    embedding=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)

# Semantic vector search
vectorstore_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Test RAG chain
print("Test RAG chain...")
prompt = ChatPromptTemplate.from_template(RAG_SEARCH_PROMPT_TEMPLATE)
llm = ChatOpenAI(model="gpt-6.1-sol",
                 api_key=os.environ["NEBULA_API_KEY"],
                 base_url=os.environ["NEBULA_BASE_URL"],
                 temperature=0.1)

rag_chain = (
    {"context": vectorstore_retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

query = "你们有什么价格表"
result = rag_chain.invoke(query)
print(f"Question: {query}")
print(f"Answer: {result}")
