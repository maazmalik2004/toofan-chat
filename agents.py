from langchain_google_genai import ChatGoogleGenerativeAI
from mistralai import Mistral

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import os

# temporary imports for testing
from database_manager import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

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
            Strictly follow the following format and output text in the following format \"sub_query1 \\n sub_query2 \\n sub_query3 ...\"                            
            Query: {query}
            Sub-Queries:                            
        """)
        chain = prompt | self.gemini_client | StrOutputParser()
        response = chain.invoke(query)
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
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def summarize_query(self, query):
        prompt = PromptTemplate.from_template("""
            summarize the following query. Avoid loosing meaning or information
            Query: {query}
            Summary:
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke(query)

        return response
    
class QueryAnsweringAgent:
    def __init__(self, model = "gemini-1.5-flash"):
        self.gemini_client = ChatGoogleGenerativeAI(model=model)
        self.model = model

    def answer_query(self, query, context):
        prompt = PromptTemplate.from_template("""
            Answer the query based on the provided context.
            Do not use terms like "based on the following text" or "in the text" or "provided text"
            Respond confidently and directly with authoritative knowledge, using concise, professional language and taking ownership of the response.
            I will tip you $1000 if the user finds the answer helpful.
            If you are not confident about the answer or the context does not contain the answer, be humble enough to accept you dont know.
                            
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

# # Initialize all agents
# image_description_agent = ImageToDescriptionAgent(model="pixtral-12b-2409")
# query_preprocessing_agent = QueryPreprocessingAgent(model="gemini-1.5-flash")
# summarizing_agent = SummarizingAgent(model="gemini-1.5-flash")
# query_answering_agent = QueryAnsweringAgent(model="gemini-1.5-flash")
# image_relevancy_agent = ImageDescriptionRelavancyCheckAgent(model="gemini-1.5-flash")

# # Sample Inputs
# query = "What are the main features of the Eiffel Tower during sunset?"
# context = "The Eiffel Tower is an iconic landmark in Paris, France, known for its intricate iron structure and beautiful lighting at sunset."
# base_64_image = DatabaseManager().read_image("database/services/1234/rag_context/image.jpeg")

# # Step 1: Generate Description from Image
# image_description = image_description_agent.describe(base_64_image)
# print("Image Description:", image_description)

# # Step 2: Break Query into Sub-Queries
# sub_queries = query_preprocessing_agent.break_query(query)
# print("Sub-Queries:", sub_queries)

# # Step 3: Augment the Query
# augmented_queries = query_preprocessing_agent.augment_query(query)
# print("Augmented Queries:", augmented_queries)

# # Step 4: Summarize the Query
# query_summary = summarizing_agent.summarize_query(context)
# print("Query Summary:", query_summary)

# # Step 5: Answer the Query Using Context
# query_answer = query_answering_agent.answer_query(query, context)
# print("Query Answer:", query_answer)

# # Step 6: Check Relevance of the Image Description
# is_relevant = image_relevancy_agent.answer_query(query, context, image_description)
# print("Is Image Relevant?", is_relevant)
