import argparse
import os
import sys
import json
import subprocess

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    # store messages to persist across iterations
    messages_array =[{"role": "user", "content": args.p}] 
    
    # start loop, need sentinel value?
    while True:

        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages_array,
            tools=[
            {
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "Read and return the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "required": ["file_path", "content"],
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path of the file to write to"
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to write to the file"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "Execute a shell command",
                    "parameters": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "the command to execute"
                            },
                        }
                    }
                }
            }]
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        # extract message and append to array
        choice = chat.choices[0]
        message = choice.message
        messages_array.append(message.model_dump())

        
        if message.tool_calls:  # check for tool_calls
            for tool_call in message.tool_calls:  # loop through each
                if tool_call.function.name == "Read":
                    func_args = json.loads(tool_call.function.arguments)
                    file_path = func_args["file_path"]
                    with open(file_path, "r") as f:
                        content = f.read()

                elif tool_call.function.name == "Write":
                    func_args = json.loads(tool_call.function.arguments)
                    file_path = func_args["file_path"]
                    content = func_args["content"]
                    with open(file_path, "w") as f:
                        f.write(content)

                elif tool_call.function.name == "Bash":
                    func_args = json.loads(tool_call.function.arguments)
                    command = func_args["command"]
                    
                    result = subprocess.run((command), capture_output=True, text=True, check=True)
                    
                    if result.returncode != 0:
                        content = result.stderr
                    else:
                        content = result.stdout

                #print(content)
                messages_array.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": content,
                })
        
        if choice.finish_reason == "stop":
            break

       
    # TODO: Uncomment the following line to pass the first stage
    print(chat.choices[0].message.content)
                

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    #print("Logs from your program will appear here!", file=sys.stderr)

    


if __name__ == "__main__":
    main()
