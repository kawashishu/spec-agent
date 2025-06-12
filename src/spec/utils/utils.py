import glob
import json
import os

import tiktoken

from .s3 import S3


def save_txt(file_path: str, content: str):
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
    except Exception as e:
        print(f"error when saving file: {e}")


def load_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"error when loading file: {e}")
        return ""


def load_txt_from_folder(folder_path: str) -> dict:
    txt_files = glob.glob(
        os.path.join(folder_path, "*.txt")
    )  # Lấy tất cả các file .txt
    data = {}

    for file_path in txt_files:
        file_name = os.path.basename(file_path)  # Lấy tên file
        data[file_name] = load_txt(file_path)

    return data


def load_json(file_path):
    """Load data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, file_path):
    """Save data to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_jsonl(file_path):
    """Load data from a JSONL file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def save_jsonl(data, file_path):
    """Save data to a JSONL file."""
    with open(file_path, "w", encoding="utf-8") as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def save_messages(messages: list, filename: str = None, folder: str = None, s3: S3 = None):
    """
    Saves the messages list to a JSON file. The filename is automatically generated
    using the current time in Vietnam timezone if not provided.

    Args:
        messages (list): List of message dictionaries.
        filename (str, optional): Custom filename. If None, use timestamp-based filename.
    """
    try:
        filepath = os.path.join(folder, filename)
        print("filepath: ",filepath)
        if s3 is not None:
            try:
                json_str = json.dumps(messages, indent=4, ensure_ascii=False)
                # Tải nội dung JSON lên S3
                s3.s3_client.put_object(
                    Body=json_str.encode("utf-8"),
                    Bucket=s3.bucket_name,
                    Key=filepath
                )
            except Exception as e:
                raise RuntimeError(f"Failed to save messages to S3: {e}")

    except Exception as e:
        print(f"Failed to save messages: {e}")

def num_tokens_from_text(string: str, encoding_name: str = "o200k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def num_tokens_from_messages(messages, model="gpt-4o-mini-2024-07-18"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06"
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0125.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4o-mini" in model:
        print("Warning: gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-mini-2024-07-18.")
        return num_tokens_from_messages(messages, model="gpt-4o-mini-2024-07-18")
    elif "gpt-4o" in model:
        print("Warning: gpt-4o and gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-2024-08-06.")
        return num_tokens_from_messages(messages, model="gpt-4o-2024-08-06")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}."""
        )
    num_tokens = 0
    for message in messages:
        if message.get("deleted", False) == True:
            continue
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens
