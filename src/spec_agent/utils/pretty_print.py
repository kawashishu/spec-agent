from typing import List

from agents import TResponseInputItem


def pretty_message(messages: list):
    """
    Prints the messages in a readable format, including tool calls and outputs.

    Args:
        messages (list): List of message dictionaries.
    """

    for idx, message in enumerate(messages, start=1):
        role = message.get("role", "N/A")
        content = message.get("content", "N/A")
        is_deleted = message.get("deleted", False)
        if is_deleted:
            print(f"Message {idx}: [DELETED]")
        else:
            print(f"Message {idx}:")

        # Capitalize the first letter of role
        print(f"{role.capitalize()}: {content[:3000]}")

        print("-" * 50)

def pretty_context(context: List[TResponseInputItem]):
    """Print chat context in a simple, readable way."""
    idx = 1
    i = 0
    while i < len(context):
        item = context[i]
        role = item.get("role")
        if role == "user":
            print(f"\n{idx}. \033[94mUser\033[0m: {item['content']}".strip())
            idx += 1
        elif role == "assistant":
            content = item.get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "output_text":
                        text = c.get("text", "")
                        print(f"\n{idx}. \033[92mAssistant\033[0m: {text[:300]}...".strip())
                        idx += 1
            elif isinstance(content, str):
                print(f"\n{idx}. \033[92mAssistant\033[0m: {content[:300]}...".strip())
                idx += 1
        elif item.get("type") == "function_call":
            # Print tool call and its output if available
            if i + 1 < len(context) and context[i + 1].get("type") == "function_call_output":
                output = context[i + 1].get("output", "")
                short_output = output[:300] + "..." if len(output) > 300 else output
                print(f"\n{idx}. \033[93mTool\033[0m: {item.get('name')} - {short_output}".strip())
                idx += 1
                i += 1
        i += 1
