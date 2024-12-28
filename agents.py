# agents : summarizer, image to description, image description relavancy check, query answering, query preprocessing agent

from langchain_google_genai import ChatGoogleGenerativeAI  # for interfacing with Gemini LLM
from langchain_core.prompts import PromptTemplate  # for creating a prompt template
from langchain_core.output_parsers import StrOutputParser  # for parsing the model's output
from mistralai import Mistral
from dotenv import load_dotenv
import os

load_dotenv()

class ImageToDescriptionAgent:
    def __init__(self, model = "pixtral-12b-2409"):
        self.mistral_client = Mistral(api_key = os.environ["MISTRAL_API_KEY"])
        self.model = model

    def generate_description(self, base_64_image):
        print("GENERATING DESCRIPTION...")
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
            Break the following query into component sub-queries while preserving the meaning of the queries.
            Output each sub-query on a new line:
            Query: {query}
            Sub-queries:
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke(query)

        return [q.strip() for q in response.split("\n") if q.strip()]

    def augment_query(self, query):
        prompt = PromptTemplate.from_template("""
            Augment the following query into 3 variations while preserving the meaning of the query.
            Output each variant on a new line:
            Query: {query}
            Variant queries:
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
            summarize the following query wihout loosing information.
            Query: {query}
            Summary:
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke(query)

        return response
    
class QueryAnsweringAgent():
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
            <Context>{context}</Context>-
        """)

        chain = prompt | self.gemini_client | StrOutputParser()

        response = chain.invoke({"query":query,
                                 "context":context
                                })
        return response
    
query_summarizer = SummarizingAgent()
output = query_summarizer.summarize_query("""4. Check for Cloudflare Issues
Since the error mentions cloudflare, it’s possible that Cloudflare (a web performance and security company) is blocking or misrouting your request.
Try making the request with a different IP address or network.
Use a VPN or proxy to bypass potential geographical restrictions.
Ensure your request includes the necessary headers.
5. Inspect Your Local Environment
If you are behind a corporate firewall or proxy, this might interfere with the request. Ensure your environment allows outgoing connections to the API endpoint.
6. Test Outside Your Script
Use a tool like Postman or cURL to test the API call manually. If it works, the issue is likely with your script.
7. Contact the API Provider
If none of the above work, contact the API provider to confirm if their service is operational or if they are experiencing issues.
If you share your script's relevant portion or clarify what service/API you're working with, I can provide more specific guidance.""")

print(output)
    
# # query_preprocessor = QueryPreprocessingAgent()
# # output = query_preprocessor.break_query("How does artificial intelligence impact global economies, and in what ways can it influence employment trends across different industries while addressing ethical concerns, such as data privacy and algorithmic bias, and how do governments and international organizations regulate its usage to ensure fairness and sustainability while fostering innovation?")
# # output = query_preprocessor.augment_query("list down the core principles of indian democracy")
# query_answering_agent = QueryAnsweringAgent()
# output = query_answering_agent.answer_query("what is a nike",
#                                  """Nike Shoe Details

# 1. Nike Air Max 270

# Description: The Nike Air Max 270 features Nike's largest Air unit in the heel, offering supreme comfort and style. It's inspired by the Air Max icons of the early 1990s.

# Key Features:

# Breathable mesh upper for lightweight comfort.

# Foam midsole with large Max Air unit for cushioning.

# Rubber outsole for durability and traction.

# Retail Price: $160

# Available Stores:

# Nike Official Website

# Foot Locker

# Finish Line

# Dick’s Sporting Goods

# 2. Nike Dunk Low Retro

# Description: A classic that never goes out of style, the Nike Dunk Low Retro offers a timeless silhouette with bold color blocking and premium materials.

# Key Features:

# Low-top design for everyday versatility.

# Premium leather upper for durability and style.

# Foam midsole for lightweight cushioning.

# Rubber outsole with pivot circle for excellent traction.

# Retail Price: $110

# Available Stores:

# Nike Official Website

# StockX

# GOAT

# Champs Sports

# 3. Nike ZoomX Vaporfly Next% 2

# Description: Designed for speed, the Nike ZoomX Vaporfly Next% 2 is engineered for long-distance runners aiming to achieve new personal records. This shoe is a favorite among elite marathon runners.

# Key Features:

# Lightweight and breathable mesh upper.

# Full-length ZoomX foam midsole for energy return.

# Carbon-fiber plate for propulsion with every step.

# Grippy rubber outsole for superior traction.

# Retail Price: $250

# Available Stores:

# Nike Official Website

# Road Runner Sports

# Running Warehouse

# Fleet Feet

# Each of these shoes offers unique features to cater to different needs, whether you're looking for everyday wear, classic streetwear, or elite running performance.""")

# print(output)

