from ollama import Client
import random
from pydantic import BaseModel
from markitdown import MarkItDown
import semchunk


def call_ollama_chat(server_url, model, messages, json_schema=None, temperature=None, tools=None):
    try:
        client = Client(
            host=server_url
        )
        
        response = client.chat(
            #model='huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q8_0', 
            #model='MFDoom/deepseek-r1-tool-calling:14b',
            model='huggingface.co/bartowski/Qwen2.5-14B-Instruct-1M-GGUF',
            stream=False,
            messages=messages,
            format=json_schema,
            tools=tools,
            options={
                'num_ctx':100000,
                'seed': random.randint(0, 1000000)
            })

        return response.message.content

    except Exception as error:
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Error")
        print(error)
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        return "error"
    
def embed_with_ollama(server_url, text, model="nomic-embed-text"):
    client = Client(
        host=server_url
    )

    results = client.embed(
        model=model,
        input=text
    )

    return results["embeddings"][0]

def convert_file(file_path):
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content

def chunk_text(text, chunk_size, overlap=0):
    chunker = semchunk.chunkerify(lambda text: len(text.split()), chunk_size)
    res = chunker(text, overlap)
    return res


class Message(BaseModel):
    role: str
    content: str
    
    def chat_ml(self):
        return {
            "role": self.role,
            "content": self.content
        }