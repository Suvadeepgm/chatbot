import streamlit as st
from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex, SimpleDirectoryReader, ChatPromptTemplate
from llama_index.llms.huggingface import HuggingFaceInferenceAPI
from dotenv import load_dotenv
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
import os
import base64


load_dotenv()


Settings.llm = HuggingFaceInferenceAPI(
    model_name="google/gemma-1.1-7b-it",
    tokenizer_name="google/gemma-1.1-7b-it",
    context_window=3000,
    #token=os.getenv("HF_TOKEN"),
    token="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",
    max_new_tokens=512,
    generate_kwargs={"temperature": 0.1},
)
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)


PERSIST_DIR = "./db"
DATA_DIR = "data"


os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PERSIST_DIR, exist_ok=True)

def displayPDF(file):
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def data_ingestion():
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    storage_context = StorageContext.from_defaults()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=PERSIST_DIR)

def handle_query(query):
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context)
    chat_text_qa_msgs = [
    (
        "user",
        """You are a Q&A assistant named PdfMadeEasy, created by Suvadeep. Your main goal is to give you answers as accurately as possible, based on the instructions and context you have been given. If a question does not match the provided context or is outside the scope of the document, kindly advise the user to ask questions within the context of the document. Provide the name of the document wherever possible. 
        Context:
        {context_str}
        Question:
        {query_str}
        """
    )
    ]
    text_qa_template = ChatPromptTemplate.from_messages(chat_text_qa_msgs)
    
    query_engine = index.as_query_engine(text_qa_template=text_qa_template)
    answer = query_engine.query(query)
    
    if hasattr(answer, 'response'):
        return answer.response
    elif isinstance(answer, dict) and 'response' in answer:
        return answer['response']
    else:
        return "Sorry, I couldn't find an answer."


# Streamlit app initialization
st.title("PDF ChatBot")
#st.markdown("Retrieval-Augmented Generation") 
#st.markdown("Start chat ...")

if 'messages' not in st.session_state:
    st.session_state.messages = [{'role': 'assistant', "content": 'Hello! Upload PDF files and ask me anything about the contents.'}]

with st.sidebar:
    st.title("Documents:")
    uploaded_files = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", type="pdf", accept_multiple_files=True)
    if st.button("Submit & Process"):
        if uploaded_files:
            with st.spinner("Processing..."):
                # Save uploaded files to data directory
                for uploaded_file in uploaded_files:
                    filepath = os.path.join(DATA_DIR, uploaded_file.name)
                    with open(filepath, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                # Process PDF files every time new files are uploaded
                data_ingestion()
                st.success("Done")

user_prompt = st.chat_input("Ask me anything about the content of the PDF:")
if user_prompt:
    st.session_state.messages.append({'role': 'user', "content": user_prompt})
    response = handle_query(user_prompt)
    st.session_state.messages.append({'role': 'assistant', "content": response})

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['content'])
