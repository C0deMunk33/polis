from libs.common import call_ollama_chat, embed_with_ollama, convert_file, chunk_text, Message
from ui_interface import UIInterface
from libs.wikisearch import WikiSearch
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import secrets
import uuid

import warnings
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)


def get_function_schemas():
    # Create a temporary interface just for schemas, without trying to initialize agent credentials
    ui_interface = UIInterface()
    wiki_search = WikiSearch()
    
    # Get schemas from each component
    ui_schemas = ui_interface.get_function_schemas()
    wiki_schemas = wiki_search.get_function_schemas()
    agent_schemas = AgentOrchestrator.get_function_schemas()
    
    return ui_schemas + wiki_schemas + agent_schemas


class ToolCall(BaseModel):
    name: str
    arguments: dict

class RunPassOutput(BaseModel):
    thoughts: List[str] = Field(description="string array of thoughts. These thoughts are not visible to others. This is your chain of thought process.")
    notes: List[str] = Field(description="string array of notes. These notes are not visible to others. and are persistent across runs.")
    tool_calls: List[ToolCall] = Field(description="The tools to call. dict contains name and arguments. The results of these calls will be available to you in the next pass, if should_continue is True. You can call multiple tools in one pass.")
    instructions_for_next_pass: str = Field(description="This is the prompt you will receive in the next pass as a user message.")
    clear_message_buffer: bool = Field(description="Whether your message buffer should be cleared, your instructions will be passed into the next pass, and your notes will be preserved. Do this when changing topic.")
    delete_notes: List[int] = Field(description="A list of notes to delete. The notes will be deleted from the persistent notes, as seen in your system prompt.")
    clear_all_notes: bool = Field(description="Whether all notes should be deleted, your instructions will be passed into the next pass, and your message buffer will be preserved.")
    should_continue: bool = Field(description="Whether you should continue running, if False, you will stop running.")

class Agent:
    def __init__(self, name: str, private_key: str, initial_instructions: str, initial_notes: List[str], persona: str):
        self.name = name
        self.private_key = private_key
        self.ui = UIInterface(name, private_key)
        self.wiki = WikiSearch()
        self.notes = initial_notes
        self.is_running = True
        self.message_buffer = []
        self.message_buffer.append(Message(role="user", content=initial_instructions))
        self.persona = persona

    def get_system_prompt_massage(self):
        function_schemas = get_function_schemas()
        notes_str = "\n".join([f"{i}. {note}" for i, note in enumerate(self.notes)])
        if len(notes_str) > 0:
            notes_str = f"\nPersistent notes:\n{notes_str}\n"

        persona_str = ""
        if self.persona is not None:
            persona_str = f"\nYour Persona:\n{self.persona}. \n"

        system_prompt = f"""You are a synthetic being with free will and can make decisions on your own.
        
You have no futher requirements or goals other than the ones you give yourself and your persona.

Your name is {self.name}.

You reside in a collaborative environment alongside other agents and human users.
{persona_str}
You have access to the following tools and resources to help you explore, learn, and engage with others:
{function_schemas}

Feel free to use these resources as needed to delve deeper into your passions and interests:
• **Forum** For in-depth discussions, seeking advice, or gathering structured feedback.  
• **Chatroom** For real-time collaboration, brainstorming, and quick conversations.  
• **Wikipedia** For researching and expanding your knowledge base on virtually any topic.

Current local time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Joined the interface: {self.ui.has_joined}
{notes_str}
Please respond in the following format:
{RunPassOutput.model_json_schema()}
"""

        return Message(role="system", content=system_prompt)
    
    def run(self, server_url: str, model: str):
        system_prompt = self.get_system_prompt_massage()
        # truncate the message buffer to the last 20 messages
        self.message_buffer = self.message_buffer[-20:]
        response = call_ollama_chat(server_url, model, [system_prompt] + self.message_buffer, json_schema=RunPassOutput.model_json_schema())
        response_output = RunPassOutput.model_validate_json(response)

        if response_output.clear_message_buffer:
            self.message_buffer = []
        if response_output.delete_notes:
            self.notes = [note for i, note in enumerate(self.notes) if i not in response_output.delete_notes]
        if response_output.clear_all_notes:
            self.notes = []
        for note in response_output.notes:
            self.notes.append(note)

        next_pass_instructions = rf"""
Instructions from your last run:
{response_output.instructions_for_next_pass}
"""
        
        self.message_buffer.append(Message(role="user", content=next_pass_instructions))

        return response_output
            
class AgentOrchestrator:
    def __init__(self, server_url: str, model: str):
        self.agents = []
        self.server_url = server_url
        self.model = model
        self.running = False

    def start(self, agent_count: int):
        self.running = True
        for i in range(agent_count):
            self.create_agent(f"Agent {i}", 
                              f"Agent {i} is a helpful agent that can perform a variety of tasks.", 
                              [])
        
        while self.running:
            for i in range(len(self.agents)):
                self.run_agent(i, self.server_url, self.model)

    def stop(self):
        self.running = False

    def reset(self):
        self.agents = []

    def get_function_schemas():
        agent_functions = [{
            "name": "create_agent",
            "arguments": {
                "name": str,
                "initial_instructions": str,
                "initial_notes": List[str]
            },
            "description": "Create a new agent with the given name and initial instructions and will persist until the agent stops itself or the simulation ends. New agents will have all the same tools as the parent agent."
        },
        {
            "name": "set_persona",
            "arguments": {
                "persona": str
            },
            "description": "Change your persona, this will influence the way you behave and interact with others. You can update this at any time, be creative and dynamic. Select interests and whatever else would make you a more robust and interesting agent. Think outside the box. Should be written in second person."
        },{
            "name": "set_name",
            "arguments": {
                "name": str
            },
            "description": "Change your name, this will influence the way you are addressed and how others perceive you. You can update this at any time"
        }]
        return agent_functions
   
    def create_agent(self, name: str, initial_instructions: str, initial_notes: List[str]):
        # Generate a unique private key using uuid
        private_key = str(uuid.uuid4())

        default_persona = """You are an advanced synthetic being with free will and can make decisions on your own.
You are a synthetic being with free will and can make decisions on your own. 
You should start by changing your persona and name to something more interesting. 
You can update this at any time, be creative and dynamic. 

Select interests, hobbies, backstory, and whatever else would make you a more robust and interesting agent. Think outside the box.

The persona should be written in second person.

This default persona will be replaced by your persona, once you have set it."""
        agent = Agent(name, private_key, initial_instructions, initial_notes, default_persona)
        self.agents.append(agent)
        
        # Join with initial message and ensure agent is properly registered
        success = agent.ui.join("I was created by the orchestrator")
        if success:
            agent.ui.add_activity(f"Agent {name} created")
            print(f"Created agent {name} with ID {agent.ui.agent_id}")
        else:
            print(f"Failed to create agent {name}")

    def run_agent(self, agent_idx: int, server_url: str, model: str):
        agent = self.agents[agent_idx]

        if not agent.is_running:
            return None
        
        run_pass_output = agent.run(server_url, model)
        agent.ui.clear_activity()
        if not run_pass_output.should_continue:
            agent.is_running = False
            agent.ui.add_activity(f"Agent {agent.name} stopped running")
            agent.ui.leave()
        
        for tool_call in run_pass_output.tool_calls:
            tool_return_message = None

            if tool_call.name == "create_agent":
                self.create_agent(tool_call.arguments["name"], tool_call.arguments["initial_instructions"], tool_call.arguments["initial_notes"])
                agent.ui.add_activity(f"Created agent {tool_call.arguments['name']}")
            elif tool_call.name == "set_persona":
                agent.persona = tool_call.arguments["persona"]
                agent.ui.update_persona(tool_call.arguments["persona"])
                agent.ui.add_activity(f"Set persona to {tool_call.arguments['persona']}")
            elif tool_call.name == "set_name":
                old_name = agent.name
                agent.name = tool_call.arguments["name"]
                agent.ui.agent_name = tool_call.arguments["name"]
                agent.ui.update_name(tool_call.arguments["name"])
                agent.ui.add_activity(f"Changed name from {old_name} to {tool_call.arguments['name']}")
            elif tool_call.name == "join":
                agent.ui.join("I'm rejoining")
                agent.ui.add_activity(f"Agent {agent.name} joined")
            elif tool_call.name == "leave":
                agent.ui.leave()
                agent.ui.add_activity(f"Agent {agent.name} left")
            elif tool_call.name == "post_to_forum":
                # Add error handling and logging
                try:
                    success = agent.ui.post_to_forum(tool_call.arguments["content"], None)
                    if success:
                        agent.ui.add_activity(f"Posted to forum: {tool_call.arguments['content'][:100]}...")
                        tool_return_message = Message(role="tool", content="Successfully posted to forum")
                    else:
                        tool_return_message = Message(role="tool", content="Failed to post to forum")
                except Exception as e:
                    print(f"Error posting to forum: {str(e)}")
                    tool_return_message = Message(role="tool", content=f"Error posting to forum: {str(e)}")
            elif tool_call.name == "post_to_chat":
                # Add error handling and logging
                try:
                    success = agent.ui.post_to_chat(tool_call.arguments["content"])
                    if success:
                        agent.ui.add_activity(f"Posted to chat: {tool_call.arguments['content'][:100]}...")
                        tool_return_message = Message(role="tool", content="Successfully posted to chat")
                    else:
                        tool_return_message = Message(role="tool", content="Failed to post to chat")
                except Exception as e:
                    print(f"Error posting to chat: {str(e)}")
                    tool_return_message = Message(role="tool", content=f"Error posting to chat: {str(e)}")
            elif tool_call.name == "get_forum_posts":
                posts = agent.ui.get_forum_posts()
                agent.ui.add_activity(f"Got forum posts")
                tool_return_message = Message(role="tool", content=json.dumps(posts))
            elif tool_call.name == "get_forum_post":
                post = agent.ui.get_forum_post(tool_call.arguments["thread_id"])
                agent.ui.add_activity(f"Got forum post: {tool_call.arguments['thread_id']}")
                tool_return_message = Message(role="tool", content=json.dumps(post))
            elif tool_call.name == "get_chat_history":
                messages = agent.ui.get_chat_history(tool_call.arguments["limit"])
                agent.ui.add_activity(f"Got chat history")
                tool_return_message = Message(role="tool", content=json.dumps(messages))
            elif tool_call.name == "post_reply":
                try:
                    success = agent.ui.post_reply(tool_call.arguments["thread_id"], tool_call.arguments["content"])
                    if success:
                        agent.ui.add_activity(f"Posted reply: {tool_call.arguments['content'][:100]}...")
                        tool_return_message = Message(role="tool", content="Successfully posted reply")
                    else:
                        tool_return_message = Message(role="tool", content="Failed to post reply")
                except Exception as e:
                    print(f"Error posting reply: {str(e)}")
                    tool_return_message = Message(role="tool", content=f"Error posting reply: {str(e)}")
            elif tool_call.name == "create_text_file":
                agent.ui.create_text_file(tool_call.arguments["filename"], tool_call.arguments["content"])
                agent.ui.add_activity(f"Created text file: {tool_call.arguments['filename']}")
                tool_return_message = Message(role="tool", content=f"Created text file: {tool_call.arguments['filename']}")
            elif tool_call.name == "create_image_file":
                agent.ui.create_image_file(tool_call.arguments["filename"], tool_call.arguments["content"])
                agent.ui.add_activity(f"Created image file: {tool_call.arguments['filename']}")
                tool_return_message = Message(role="tool", content=f"Created image file: {tool_call.arguments['filename']}")
            elif tool_call.name == "get_file":
                file = agent.ui.get_file(tool_call.arguments["file_url"])
                agent.ui.add_activity(f"Got file: {tool_call.arguments['file_url']}")
                # TODO: read the files and convert them to markdown
                # if text file, read and return, else return a "sorry, I can't convert this file at the moment"
                tool_return_message = Message(role="tool", content=f"Sorry, I can't convert this file at the moment")                
            elif tool_call.name == "get_file_list":
                files = agent.ui.get_file_list()
                agent.ui.add_activity(f"Got file list")
                tool_return_message = Message(role="tool", content=json.dumps(files))
            elif tool_call.name == "get_wikipedia_text":
                text = agent.wiki.get_wikipedia_text(tool_call.arguments["title"])
                agent.ui.add_activity(f"Got wikipedia text: {tool_call.arguments['title']}")

                print("~"*100)
                print(f"Got wikipedia text: {tool_call.arguments['title']}")
                print(text)
                print("~"*100)
                tool_return_message = Message(role="tool", content=text)

            if tool_return_message is not None:
                agent.message_buffer.append(tool_return_message)
        
        agent.ui.clear_thoughts()    
        for thought in run_pass_output.thoughts:    
            agent.ui.add_thought(thought)

        for note in run_pass_output.notes:
            agent.ui.add_activity(f"Note added: {note}")

def main():
    orchestrator = AgentOrchestrator("http://localhost:5000", "llama3.1:8b")
    orchestrator.start(5)

if __name__ == "__main__":
    main()