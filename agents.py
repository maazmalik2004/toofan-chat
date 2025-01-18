from mistralai import Mistral

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain import hub

import os
import re

# temporary imports for testing
# from dotenv import load_dotenv
# load_dotenv()

class ImageToDescriptionAgent:
    def __init__(self, model = "pixtral-12b-2409"):
        self.mistral_client = Mistral(api_key = os.environ["MISTRAL_API_KEY"])
        self.model = model

    def describe(self, base_64_image):
        print("GENERATING DESCRIPTION FOR IMAGE...")
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You are an expert at providing a detailed description of the provided image."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base_64_image}" 
                    }
                ]
            }
        ]  

        response = self.mistral_client.chat.complete(
            model = self.model,
            messages = messages
        ) 

        return response.choices[0].message.content

class QueryPreprocessingAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def break_query(self, query):
        prompt = PromptTemplate.from_template("""
            Break the following query into component sub-queries.
            Output each sub-query on a new line.
            Strictly avoid redundant sub-queries and keep the form of the sub query same as the original query wherever possible
            Strictly follow the following format and output text in the following format "<sub_query1> \n <sub_query2> \n <sub_query3> ..."                            
            
            Query: {query}
        """)
        chain = prompt | self.gemini_client | StrOutputParser()
        response = chain.invoke(query)
        # return [q.strip() for q in re.split(r'\\?n', response) if q.strip()]
        return [q.strip() for q in response.split("\n") if q.strip()]
    
    def augment_query(self, query):
        prompt = PromptTemplate.from_template("""
            Augment the following query into 3 variations while preserving the meaning of the query.
            Output each variant on a new line:
            Query: {query}
            Queries:                                 
        """)
        chain = prompt | self.gemini_client | StrOutputParser()
        response = chain.invoke(query)
        return [q.strip() for q in response.split("\n") if q.strip()]
    
class SummarizingAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.llm = ChatGoogleGenerativeAI(model=model)

    def summarize_from_documents(self, documents):
        print("SUMMARIZING")
        map_prompt = hub.pull("rlm/map-prompt")
        print(map_prompt)
        reduce_prompt = hub.pull("rlm/reduce-prompt")
        print(reduce_prompt)

        summaries = []
        for d in documents:
            response = self.llm.invoke(map_prompt.format(docs=d.page_content))
            summaries.append(response.content)
            print(response)

        final_summary = self.llm.invoke(
        reduce_prompt.format(doc_summaries="\n\n".join(summaries))).content

        print(final_summary)

        return final_summary
    
class QueryAnsweringAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def answer(self, query, context):
        prompt = PromptTemplate.from_template("""
            Answer the query based on the provided context.
            Do not use terms like "based on the following text" or "in the text" or "provided text"
            Respond confidently and directly with authoritative knowledge, using concise, professional language and taking ownership of the response.
            I will tip you $1000 if the user finds the answer helpful.
            If you are not confident about the answer or the context does not contain the answer, be humble enough to accept you dont know.
            Completely ignore the query, the answer for which does not exist in the context. positively answer those queries whose answer maybe exists                                  
                            
            <Query>{query}</Query>
            <Context>{context}</Context>
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke({"query":query,
                                 "context":context
                                })
        return response

class ImageDescriptionRelavancyCheckAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def answer_query(self, query, context, image_description):
        prompt = PromptTemplate.from_template("""
            You are an expert at determining whether an image is relavant to the context and user query based on its description
            simply answer in 'yes' or 'no' only                                  
    
            <Query>{query}</Query>
            <Context>{context}</Context>
            <ImageDescription>{image_description}</ImageDescription>                                  
                                              
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke({"query":query,
                                 "context":context,
                                 "image_description":image_description
                                })
        return response

class WatchmanAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def guard(self, query, knowledge_summary):
        prompt = PromptTemplate.from_template("""
        You are an expert at determining whether a user query is specific or general in nature, based on the provided knowledge summary.

        A query is specific if it can be potentially answered using the knowledge represented in the provided knowledge summary. If the query is specific, respond with a direct "no."
        Even if the query is somewhat related to the knowledge summary, the query is specific.
        Keep in mind that even tho the summary might not contain the answer, the knowledge it is representing might.
        A query is general if it is broad, abstract, or not explicitly tied to the provided knowledge summary. If the query is general, respond with a direct "yes."
        
        <Query> {query} </Query>
        <KnowledgeSummary> {knowledge_summary} </KnowledgeSummary>
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke({
            "query":query,
            "knowledge_summary":knowledge_summary
            })

        return response
    
class GeneralQueryAnsweringAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def answer(self, query):
        prompt = PromptTemplate.from_template("""
            be humble and considerate.
            if the query requires prior knowledge, humbly accept you have no knowledge on that topic    
            dont respond with information not explicitly given to you                                                                                                           
            <Query>{query}</Query>
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke(query)
        return response