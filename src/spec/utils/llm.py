import asyncio
import random
import time
from functools import wraps
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncAzureOpenAI, AzureOpenAI
from openai.types.chat import ChatCompletion, ParsedChatCompletion
from openai.types.responses.parsed_response import ParsedResponse
from openai.types.responses.response import Response
from pydantic import BaseModel

from spec.config import async_client, client, logger

DEFAULT_TEXT_MODEL = "gpt-4o-mini"


def handle_exception(e: Exception) -> str:
    ERROR_MESSAGES = {
        "APIConnectionError": "⚠️ Issue connecting to our services. Check your network settings, proxy configuration, SSL certificates, or firewall rules.",
        "APITimeoutError": "⚠️ Request timed out. Retry your request after a brief wait and contact us if the issue persists.",
        "AuthenticationError": "⚠️ Your API key or token was invalid, expired, or revoked. Check your API key or token and make sure it is correct and active.",
        "BadRequestError": "⚠️ Your request was malformed or missing some required parameters, such as a token or an input.",
        "ConflictError": "⚠️ The resource was updated by another request. Try to update the resource again and ensure no other requests are trying to update it.",
        "InternalServerError": "⚠️ Issue on our side. Retry your request after a brief wait and contact us if the issue persists.",
        "NotFoundError": "⚠️ Requested resource does not exist. Please check your resource identifier.",
        "PermissionDeniedError": "⚠️ You don't have access to the requested resource. Please verify your API key, organization ID, and resource ID.",
        "RateLimitError": "⚠️ You have hit your assigned rate limit. Please pace your requests.",
        "UnprocessableEntityError": "⚠️ Unable to process the request despite the format being correct. Please try the request again.",
    }

    error_type = type(e).__name__

    if error_type not in ERROR_MESSAGES:
        return e

    if error_type == "BadRequestError":
        try:
            cf_result = e.response.json()["error"]["innererror"].get("content_filter_result", {})
            blocked = [
                f"{cat} (severity: {res.get('severity', 'unknown')})"
                for cat, res in cf_result.items() if res.get("filtered")
            ]
            if blocked:
                return f"⚠️ Your prompt was blocked due to: {', '.join(blocked)}. Please revise and try again or contact admin."
            else:
                return ERROR_MESSAGES.get(error_type)
        except Exception:
            pass
    
    if error_type in ERROR_MESSAGES:    
        return ERROR_MESSAGES.get(error_type)


# define a retry decorator
def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 10,
    errors: tuple = (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise e

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())

                # Sleep for the delay
                time.sleep(delay)

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper


@retry_with_exponential_backoff
def completion_with_backoff(client: AzureOpenAI = client, **kwargs) -> ChatCompletion | ParsedChatCompletion:
    """Generate chat completion with backoff retry logic."""
    if "response_format" in kwargs and kwargs.get("response_format"):
        return client.beta.chat.completions.parse(**kwargs)
    else:
        return client.chat.completions.create(**kwargs)
    
@retry_with_exponential_backoff
def completion_with_backoff_response(client: AzureOpenAI = client, **kwargs) -> ChatCompletion | ParsedChatCompletion:
    """Generate chat completion with backoff retry logic."""
    if "response_format" in kwargs and kwargs.get("response_format"):
        return client.responses.parse(**kwargs)
    else:
        return client.responses.create(**kwargs)

def async_retry_with_exponential_backoff(
    func,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    max_retries: int = 10,
    errors: tuple = (
        openai.RateLimitError,
        openai.APIConnectionError,
        openai.InternalServerError,
    ),
):
    """
    Decorator: retry an *async* function with exponential back-off.
    """

    @wraps(func)
    async def wrapper_async(*args, **kwargs):
        delay = initial_delay
        for attempt in range(1, max_retries + 2):  # +2 để lần cuối raise lỗi
            try:
                return await func(*args, **kwargs)

            except errors as e:
                if attempt > max_retries:
                    raise e

                # tăng delay
                delay *= exponential_base * (1 + jitter * random.random())
                logger.info(f"DELAY: {delay}")
                await asyncio.sleep(delay)

            except Exception as e:
                raise e

    return wrapper_async


@async_retry_with_exponential_backoff
async def acompletion_with_backoff(client: openai.AsyncClient | openai.AsyncAzureOpenAI = async_client,**kwargs,
) -> Response | ParsedResponse:
    if kwargs.get("text_format"):
        return await async_client.responses.parse(**kwargs)
    else:
        return await async_client.responses.create(**kwargs)
    
class LLM:
    """
    A class to handle text and embedding generation using Azure OpenAI services.

    This class provides both synchronous and asynchronous methods for generating
    text completions and embeddings, supporting structured output parsing and streaming.
    """

    client: AzureOpenAI = client
    async_client: AsyncAzureOpenAI = async_client

    @classmethod
    async def async_generate(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = DEFAULT_TEXT_MODEL,
        response_format: Optional[BaseModel] = None,
        stream: bool = False,
        **args,
    ) -> Any:
        """
        Asynchronously generate text or structured output.

        Parameters:
            messages (List[Dict[str, str]]): The conversation messages for generation.
            model (Optional[str]): The model to use for generation. Defaults to DEFAULT_TEXT_MODEL.
            response_format (Optional[BaseModel]): A Pydantic model to parse structured responses.
            stream (bool): Whether to stream the response. Defaults to False.
            **args: Additional arguments passed to the OpenAI client.

        Returns:
            Any: The generated response, either as text or structured output.

        Raises:
            ValueError: If response_format is provided with streaming enabled.
            Exception: If an error occurs during generation.
        """
        if response_format and stream:
            raise ValueError("Streaming with response_format is not supported.")

        try:
            if response_format:
                # Non-streaming structured output
                response = await cls.async_client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    response_format=response_format,
                    **args,
                )
                parsed_output = response.choices[0].message.parsed
                logger.info("Structured output generated successfully (async).")
                return parsed_output
            else:
                if stream:
                    # Streaming text output
                    return cls._async_stream_response(messages, model=model, **args)
                else:
                    # Non-streaming text output
                    response = await cls.async_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.0,
                        **args,
                    )
                    text = response.choices[0].message.content
                    # logger.info("Text generated successfully (async).")
                    return text
        except Exception as e:
            logger.error(f"Error generating output (async): {str(e)}")
            raise

    @classmethod
    async def _async_stream_response(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = DEFAULT_TEXT_MODEL,
        **args,
    ):
        """
        Internal method to handle streaming responses asynchronously.

        Parameters:
            messages (List[Dict[str, str]]): The conversation messages for generation.
            model (Optional[str]): The model to use for generation. Defaults to DEFAULT_TEXT_MODEL.
            **args: Additional arguments passed to the OpenAI client.

        Yields:
            str: Chunks of text as they are received.

        Raises:
            Exception: If an error occurs during streaming.
        """
        try:
            response_iter = await cls.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                stream=True,
                **args,
            )

            async for chunk in response_iter:
                if chunk is not None and len(chunk.choices) < 1:
                    continue
                if not chunk.choices[0].delta.content:
                    continue
                yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error generating streaming output (async): {str(e)}")
            raise

    @classmethod
    def generate(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = DEFAULT_TEXT_MODEL,
        response_format: Optional[BaseModel] = None,
        temperature: Optional[float] = 0.0,
        **args,
    ) -> Any:
        """
        Synchronously generate text or structured output.

        Parameters:
            messages (List[Dict[str, str]]): The conversation messages for generation.
            model (Optional[str]): The model to use for generation. Defaults to DEFAULT_TEXT_MODEL.
            response_format (Optional[BaseModel]): A Pydantic model to parse structured responses.
            **args: Additional arguments passed to the OpenAI client.

        Returns:
            Any: The generated response, either as text or structured output.

        Raises:
            Exception: If an error occurs during generation.
        """
        try:
            if "o1" in model and not response_format:
                response = cls.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **args,
                )
                text = response.choices[0].message.content
                # logger.info("Text generated successfully (sync).")
                return text

            elif response_format:
                response = cls.client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    **args,
                )
                parsed_output = response.choices[0].message.parsed
                # logger.info("Structured output generated successfully (sync).")
                return parsed_output
            else:
                response = cls.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    **args,
                )
                text = response.choices[0].message.content
                # logger.info("Text generated successfully (sync).")
                return text
        except Exception as e:
            logger.error(f"Error generating output (sync): {str(e)}")
            raise

    @classmethod
    async def async_embedding(
        cls,
        text: str,
        model: Optional[str] = "text-embedding-3-large",
        **args,
    ) -> List[float]:
        """
        Asynchronously generate embeddings for the given text.

        Parameters:
            text (str): The input text to generate embeddings for.
            model (Optional[str]): The model to use for embeddings. Defaults to "text-embedding-3-large".
            **args: Additional arguments passed to the OpenAI client.

        Returns:
            List[float]: The generated embedding as a list of floats.

        Raises:
            Exception: If an error occurs during embedding generation.
        """
        try:
            response = await cls.async_client.embeddings.create(
                input=text, model=model, **args
            )
            embedding = response.data[0].embedding
            logger.info("Embedding generated successfully (async).")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embeddings (async): {str(e)}")
            raise

    @classmethod
    def embedding(
        cls,
        text: str,
        model: Optional[str] = "text-embedding-3-small",
        **args,
    ) -> List[float]:
        """
        text-embedding-3-small: 1536
        text-embedding-3-large: 3072

        Synchronously generate embeddings for the given text.

        Parameters:
            text (str): The input text to generate embeddings for.
            model (Optional[str]): The model to use for embeddings. Defaults to "text-embedding-3-large".
            **args: Additional arguments passed to the OpenAI client.

        Returns:
            List[float]: The generated embedding as a list of floats.

        Raises:
            Exception: If an error occurs during embedding generation.
        """
        try:
            response = cls.client.embeddings.create(input=text, model=model, **args)
            embedding = response.data[0].embedding
            # logger.info("Embedding generated successfully (sync).")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embeddings (sync): {str(e)}")
            raise

