from mistralai import Mistral
from dotenv import load_dotenv
import os

load_dotenv()

class ImageDescriptionGenerator:
    def __init__(self):
        self.mistral_client = Mistral(api_key = os.environ["MISTRAL_API_KEY"])
        self.model = "pixtral-12b-2409"

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