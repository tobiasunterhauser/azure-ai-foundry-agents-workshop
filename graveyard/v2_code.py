import asyncio
import os

from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AgentGroupChat
from typing import Annotated
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.functions import kernel_function, KernelFunctionFromPrompt
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer

# Load environment variables
load_dotenv()

project_endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
model_deployment = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

# Agent instructions
triage_agent_name = "TriageAgent"
triage_agent_instructions = """
Du bist der TriageAgent für Support-Tickets.
- Analysiere das eingehende Support-Ticket.
- Kategorisiere das Problem (z.B. "Technisch", "Rechnung", "Allgemeine Anfrage").
- Bestimme die Priorität (z.B. "Hoch", "Mittel", "Niedrig").
- Gib eine kurze Zusammenfassung und die Klassifikation zurück.
- Wenn das Problem dringend oder kritisch ist, markiere es entsprechend.
- Antworte nur mit der Analyse, keine Lösungsvorschläge.
"""

knowledge_agent_name = "KnowledgeAgent"
knowledge_agent_instructions = """
Du bist der KnowledgeAgent.
- Nutze die Klassifikation und den Inhalt des Tickets.
- Suche passende FAQ-Einträge oder Lösungsvorschläge.
- Gib mehrere Optionen zurück, falls möglich.
- Fasse die gefundenen Informationen klar zusammen.
- Keine neuen Klassifikationen oder Bewertungen vornehmen.
"""

response_agent_name = "ResponseAgent"
response_agent_instructions = """
Du bist der ResponseAgent.
- Erstelle eine höfliche, klare Antwort basierend auf den Eingaben von TriageAgent und KnowledgeAgent.
- Stelle sicher, dass die Antwort alle relevanten Punkte anspricht.
- Falls noch Informationen fehlen oder Unsicherheiten bestehen, frage nach.
- Keine technischen Details, sondern kundenorientierte Kommunikation.
- Sende bei erfolgreicher Antwort eine Bestätigung per E-Mail.
"""

class EmailPlugin:
    """A Plugin to simulate sending emails."""

    async def send_email(self, to: str, subject: str, body: str):
        print("\n--- Mock Email Sending ---")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print("--- End of Email ---\n")

def create_kernel() -> Kernel:
    """Creates a Kernel instance with an Azure OpenAI ChatCompletion service."""
    kernel = Kernel()
    kernel.add_service(service=AzureChatCompletion(deployment_name=model_deployment, endpoint="https://t-tobiasu-7828-resource.openai.azure.com/", api_key="AHWkbvvaYjaTyCOKBdFJs9D6LJIGxUR8eaU8TeqXAQExzSJIKIyYJQQJ99BFACfhMk5XJ3w3AAAAACOGZSMP"))
    return kernel

async def main():
     # Create a single kernel instance for all agents.
    kernel = create_kernel()


    # Create Azure credentials and AI Agent client
    async with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True) as creds,
        AzureAIAgent.create_client(
            credential=creds
        ) as project_client,
    ):

        # Register agents dynamically
        triage_def = await project_client.agents.create_agent(
            model=model_deployment,
            name=triage_agent_name,
            instructions=triage_agent_instructions,
        )
        triage_agent = AzureAIAgent(client=project_client, definition=triage_def)

        knowledge_def = await project_client.agents.create_agent(
            model=model_deployment,
            name=knowledge_agent_name,
            instructions=knowledge_agent_instructions,
        )
        knowledge_agent = AzureAIAgent(client=project_client, definition=knowledge_def)

        response_def = await project_client.agents.create_agent(
            model=model_deployment,
            name=response_agent_name,
            instructions=response_agent_instructions,
        )
        # Attach EmailPlugin to response agent
        response_agent = AzureAIAgent(
            client=project_client,
            definition=response_def,
            plugins=[EmailPlugin()]
        )

        # Selection function: who answers next based on last message
        selection_prompt = f"""
            Given the last RESPONSE, pick the next agent to respond.
            Agents: {triage_agent_name}, {knowledge_agent_name}, {response_agent_name}

            Rules:
            - If RESPONSE is from user, next is {triage_agent_name}.
            - If RESPONSE is from {triage_agent_name}, next is {knowledge_agent_name}.
            - If RESPONSE is from {knowledge_agent_name}, next is {response_agent_name}.
            - If RESPONSE is from {response_agent_name}, next is {triage_agent_name} or end.

            RESPONSE:
            {{{{$lastmessage}}}}
        """

        selection_function = KernelFunctionFromPrompt(
            function_name="agent_selection",
            prompt=selection_prompt,
        )

        chat = AgentGroupChat(
            agents=[triage_agent, knowledge_agent, response_agent],
            selection_strategy=KernelFunctionSelectionStrategy(
                initial_agent=triage_agent,
                function=selection_function,
                kernel=kernel,
                result_parser=lambda r: str(r.value[0]).strip(),
                history_variable_name="lastmessage",
                history_reducer=ChatHistoryTruncationReducer(target_count=5)
            )
        )

        print("Support Ticket Demo with Azure AI Agents ready. Type your ticket description or 'exit' to quit.")

        while True:
            user_input = input("User > ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue

            await chat.add_chat_message(user_input)

            # Run the AgentGroupChat orchestration
            try:
                async for response in chat.invoke():
                    if response and response.name:
                        print(f"\n# {response.name}:\n{response.content}")

                        # Example of plugin usage: send email after ResponseAgent answers
                        if response.name == response_agent_name:
                            # Call plugin method mock send_email (you can customize recipient)
                            await response_agent.invoke_plugin_function_async(
                                "send_email",
                                to="customer@example.com",
                                subject="Ihre Support Anfrage",
                                body=response.content,
                            )
            except Exception as e:
                print(f"[Error during chat invocation: {e}]")

            chat.is_complete = False


if __name__ == "__main__":
    asyncio.run(main())
