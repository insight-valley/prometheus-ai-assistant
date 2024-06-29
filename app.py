from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig

from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_text_splitters import HTMLHeaderTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS

from constant import prompt_template, prompt_template_v2

import chainlit as cl

headers_to_split_on = [
    ("h2", "Header 2"),
    ("h4", "Header 4"),
]

loader = AsyncChromiumLoader(["https://samber.github.io/awesome-prometheus-alerts/rules"])
model = ChatOpenAI(temperature=0.1, streaming=True)
embeddings = OpenAIEmbeddings()
html_splitter = HTMLHeaderTextSplitter(headers_to_split_on)

docs = loader.load()

splitted_documents = html_splitter.split_text(docs[0].page_content)
print(len(splitted_documents), "loaded...")

vectorstore = FAISS.from_documents(splitted_documents, embeddings)

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Alertas para Kubernetes",
            message="Alertas para acompanhar a saúde do cluster de Kubernetes (Nodes, API Server ou Etcd)",
            icon="/public/kubernetes.svg",
            ),
        cl.Starter(
            label="Alertas para banco de dados PostgresSQL",
            message="Alertas focados em métricas para bancos de dados Postgres",
            icon="/public/postgresql.svg",
            ),
        cl.Starter(
            label="Alertas focados para servidores usando node_exporter",
            message="Alertas para ajudar a acompanhar métricas do node_exporter",
            icon="/public/server.svg",
            ),
        ]

@cl.on_chat_start
async def on_chat_start():
    
    system_prompt = (
        prompt_template_v2
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    question_answer_chain = create_stuff_documents_chain(model, prompt)
    retriever_chain = create_retrieval_chain(retriever, question_answer_chain)

    runnable = {
        "context": retriever_chain,
        "input": RunnablePassthrough(),
    } | prompt | model | StrOutputParser()

    cl.user_session.set("runnable", runnable)


@cl.on_message
async def on_message(message: cl.Message):
    runnable = cl.user_session.get("runnable")

    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"input": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    await msg.send()
