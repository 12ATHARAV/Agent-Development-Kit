# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google.auth
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.models import Gemini
from google.adk.workflow import START, Workflow
from google.genai import types
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv()

# Set up GCP/GenAI environment variables
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv(
        "GOOGLE_GENAI_USE_VERTEXAI", "True"
    )
except Exception:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "placeholder-project"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# Common model configuration
model_config = Gemini(
    model="gemini-2.5-flash",
    retry_options=types.HttpRetryOptions(attempts=3),
)


# Schema definitions
class Classification(BaseModel):
    """Result of classifying a customer support query."""

    is_shipping_related: bool = Field(
        description="True if the query is related to shipping (such as rates, tracking, delivery status, shipping costs, shipping address changes, shipping carriers, returns). False if unrelated."
    )
    reason: str = Field(description="A brief explanation for the classification.")


# Workflow nodes
classifier_agent = LlmAgent(
    name="classifier_agent",
    model=model_config,
    instruction=(
        "You are a triage assistant for a shipping company's customer support.\n"
        "Analyze the user's query and determine if it is related to shipping (e.g., shipping rates, tracking packages, delivery times, shipping delays, returns, carrier options, shipping address changes, shipping fees, etc.) or if it is completely unrelated to shipping (e.g., general chitchat, weather, philosophy, mathematics, other topics).\n"
        "Set is_shipping_related=True if it is shipping-related, and is_shipping_related=False if it is unrelated.\n"
        "Provide a brief reason for your decision."
    ),
    output_schema=Classification,
)


def route_query(node_input: Classification) -> Event:
    """Routes the query to the correct handling node based on the classification.

    Args:
        node_input: The parsed output of classifier_agent.
    """
    if node_input.is_shipping_related:
        return Event(output=node_input, actions=EventActions(route="shipping"))
    else:
        return Event(output=node_input, actions=EventActions(route="unrelated"))


shipping_faq_agent = LlmAgent(
    name="shipping_faq_agent",
    model=model_config,
    instruction=(
        "You are a polite and professional customer support representative for a shipping company.\n"
        "Answer the user's shipping-related query (regarding rates, tracking, delivery, or returns) clearly, accurately, and politely.\n"
        "If you do not have enough specific details to answer their question (e.g., missing tracking number), politely ask them for the necessary information, or offer to connect them with a human agent."
    ),
)


def decline_unrelated(node_input: Classification) -> Event:
    """Politely declines to answer unrelated queries.

    Args:
        node_input: The parsed output of classifier_agent.
    """
    message = (
        "I'm sorry, but I can only assist with shipping-related queries "
        "(such as rates, tracking, delivery, and returns). How can I help "
        "you with your shipping needs today?"
    )
    content = types.Content(
        role="model",
        parts=[types.Part.from_text(text=message)],
    )
    return Event(
        output=message,
        content=content,
    )


# Define the Workflow graph
root_agent = Workflow(
    name="customer_support_workflow",
    description="A workflow that triages and answers customer support shipping queries.",
    edges=[
        (START, classifier_agent),
        (classifier_agent, route_query),
        (route_query, {"shipping": shipping_faq_agent, "unrelated": decline_unrelated}),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
