import streamlit as st
from langchain_community.document_loaders import PyPDFDirectoryLoader
from pypdf import PdfReader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pinecone import Pinecone as PineconeClient
from langchain.chains.question_answering import load_qa_chain
from datetime import datetime
from langchain_community.vectorstores import Pinecone
import os
import time


def save_pdf_to_directory(uploaded_file, directory):
    if uploaded_file is not None:
        # Define directory to save file
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Save uploaded PDF file to directory
        with open(os.path.join(directory, uploaded_file.name), "wb") as pdf_file:
            pdf_file.write(uploaded_file.getbuffer())
        
        st.success(f"File '{uploaded_file.name}' saved successfully to {directory}!")


def load_docs(dir):
  loader = PyPDFDirectoryLoader(dir)
  documents = loader.load()
  return documents


def get_pdf_text(pdf_doc):
    text = ""
    pdf_reader = PdfReader(pdf_doc)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def create_docs(user_pdf_list, unique_id):
    docs=[]
    for filename in user_pdf_list:
        chunks = get_pdf_text(filename)

        docs.append(Document(
            page_content = chunks,
            metadata = {"name":filename.name, "type=": filename.type, "size": filename.size, "unique_id": unique_id, 'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ))

        
    return docs

# transform documents
def split_docs(documents, chunk_size=400, chunk_overlap=20):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(documents)
    
    return docs

def get_embeddings():
    embedding = OpenAIEmbeddings()
    return embedding


def push_to_pinecone(docs, embedding):

    pc = PineconeClient(api_key="9fe6ffcf-09a0-4f3c-9b30-e76fdf938dd5")
    index_name="chatbotdb"
    index = pc.Index(index_name)

    index.delete(delete_all=True, namespace='rag_bot')    
    
    vector = []
    for i, doc in enumerate(docs):
        entry = { "id": str(i),
                "values": embedding.embed_query(doc.page_content),
                "metadata":doc.metadata}
        vector.append(entry)

    
    index = Pinecone.from_documents(docs, embedding, index_name = index_name, namespace='rag_bot')

    st.sidebar.write("This 30 seconds delay is added Manually... \n(because I'm using some free resources)")
    time.sleep(30)

    return index



#Function to pull index data from Pinecone
def pull_from_pinecone(embeddings):

    pinecone_apikey = "9fe6ffcf-09a0-4f3c-9b30-e76fdf938dd5"
    pinecone_index_name ="chatbotdb"

    PineconeClient(
    api_key=pinecone_apikey
    )

    #PineconeStore is an alias name of Pinecone class, please look at the imports section at the top :)
    index = Pinecone.from_existing_index(pinecone_index_name, embeddings, namespace='rag_bot')

    return index




def get_similar_doc(query, embedding,k=2):

    pc = PineconeClient(api_key="9fe6ffcf-09a0-4f3c-9b30-e76fdf938dd5")
    index_name="chatbotdb"
    index = pc.Index(index_name)

    index = pull_from_pinecone(embeddings=embedding)
    similar_doc = index.similarity_search_with_score(query, int(k))
    
    return [doc for doc, similarity_score in similar_doc]
    


def get_answer(query, embedding, k=2):
    llm=ChatOpenAI(temperature=0.5)
    chain = load_qa_chain(llm, chain_type="stuff")

    relevent_doc = get_similar_doc(query, embedding,k=2)
    response = chain.run(input_documents = relevent_doc, question=query)
    return response
