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

# Get configuration settings
load_dotenv()
project_endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
model_deployment = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

ai_agent_settings = AzureAIAgentSettings()

policy_agent_name = "policy_pruefungs_agent"
research_agent_name = "recherche_agent"
bookings_agent_name = "buchungs_agent"
booking_agent_instructions = """
Du bist der Buchungs-Agent. Führe die Buchung durch, sobald eine genehmigte Option vorliegt. Bestätige die Buchung und sende eine Bestätigung mit Zusammenfassung über das EmailPlug.
"""

hr_agent_name = "hr_agent"
hr_agent_instructions = """
Du bist der HR-Agent. Du kannst über das Human Resources System Plugin alle Informationen über die Mitarbeitenden, die für die Reisebuchung benötigt werden. Deine Aufgabe ist es, diese Informationen bereitzustellen, wenn der Orchestrierungs-Agent sie anfordert.
"""

WRITER_NAME = "user"

def create_kernel() -> Kernel:
    kernel = Kernel()
    kernel.add_service(
        service=AzureChatCompletion(
            deployment_name=model_deployment,
            endpoint="endpoint",
            api_key="api-key",
        )
    )
    return kernel

class EmailPlugin:
    """A Plugin to simulate email functionality."""

    @kernel_function(description="Sends an email.")
    def send_email(self,
                   to: Annotated[str, "Who to send the email to"],
                   subject: Annotated[str, "The subject of the email."],
                   body: Annotated[str, "The text body of the email."]):
        print("\n--- Email sent ---")
        print("To:", to)
        print("Subject:", subject)
        print(body)
        print("------------------\n")

class HumanResourcesPlugin:
    """A Plugin to mock a connection to a human resources system."""

    @kernel_function(description="Returns personal information of an employee for travel booking.")
    def get_employee_info(self):
        return {
            "name": "Max Mustermann",
            "address": "Musterstraße 1, 80333 München, Deutschland",
            "position": "Senior Consultant",
            "dietary_preferences": "Vegetarian",
            "allergies": "Peanuts",
            "email": "max.mustermann@example.com"
        }
    

def parse_selection_result(result):
    if not result.value:
        return policy_agent_name  # Fallback
    # result.value könnte eine Liste sein oder ein String
    if isinstance(result.value, list):
        return str(result.value[0]).strip()
    else:
        return str(result.value).strip()

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    kernel = create_kernel()

    async with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ) as creds,
        AzureAIAgent.create_client(credential=creds) as project_client,
    ):
        # Reference existing agents
        research_agent_definition = await project_client.agents.get_agent(agent_id="asst_vMGXYaYdFceK3qhvUTG11FNq")
        research_agent = AzureAIAgent(client=project_client, definition=research_agent_definition)

        policy_agent_definition = await project_client.agents.get_agent(agent_id="asst_hsEowHU39xf7DXYFxRJzEgVJ")
        policy_agent = AzureAIAgent(client=project_client, definition=policy_agent_definition)

        # Create booking agent with plugin
        booking_agent_definition = await project_client.agents.create_agent(
            model=model_deployment,
            name=bookings_agent_name,
            instructions=booking_agent_instructions
        )
        booking_agent = AzureAIAgent(
            client=project_client,
            definition=booking_agent_definition,
            plugins=[EmailPlugin()]
        )

        # Create HR agent with plugin
        hr_agent_definition = await project_client.agents.create_agent(
            model=model_deployment,
            name=hr_agent_name,
            instructions=hr_agent_instructions
        )
        hr_agent = AzureAIAgent(
            client=project_client,
            definition=hr_agent_definition,
            plugins=[HumanResourcesPlugin()]
        )

        # Selection function decides next agent based on conversation history
        selection_function = KernelFunctionFromPrompt(
            function_name="selection",
            prompt=f"""
                Entscheide basierend auf dem Gesprächsverlauf, welcher Agent als nächstes handeln soll.
                Verfügbare Agenten:
                - {hr_agent_name}
                - {policy_agent_name}
                - {research_agent_name}
                - {bookings_agent_name}

                Idealer Ablauf: HR > Policy > Recherche > Buchung. Reagiere auf Nutzerfeedback, wenn Recherche scheitert.

                Letzte Nutzer- oder Agenten-Nachricht:
                {{{{$lastmessage}}}}

                Antwort nur den Namen des nächsten Agenten (ohne weitere Kommentare).
            """
        )

        # Termination function checks if booking is confirmed
        termination_function = KernelFunctionFromPrompt(
            function_name="termination_check",
            prompt="""
                Beurteile, ob das Gespräch abgeschlossen ist und die Buchung bestätigt wurde.
                Antwort mit "True" wenn abgeschlossen, sonst "False".
                Letzte Nachrichten:
                {{$chat_history}}
            """
        )

        history_reducer = ChatHistoryTruncationReducer(target_count=10)

        chat = AgentGroupChat(
            agents=[hr_agent, policy_agent, research_agent, booking_agent],
            selection_strategy=KernelFunctionSelectionStrategy(
                initial_agent=policy_agent,
                function=selection_function,
                kernel=kernel,
                result_parser=lambda result: (str(result.value).strip() if result.value else policy_agent_name),
                history_variable_name="lastmessage",
                history_reducer=history_reducer,
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                function=termination_function,
                kernel=kernel,
                history_variable_name="chat_history",
                history_reducer=history_reducer,
                result_parser=lambda r: r.value.strip().lower() == "true"
            )
        )

        print("System bereit. Eingabe starten (oder 'exit', 'reset')")

        while True:
            user_input = input("\nUser > ").strip()
            if not user_input:
                continue
            if user_input.lower() == "exit":
                print("Beende Konversation.")
                break
            if user_input.lower() == "reset":
                await chat.reset()
                print("[Konversation wurde zurückgesetzt]")
                continue

            await chat.add_chat_message(message=user_input)
            try:
                async for response in chat.invoke():
                    if response and response.name:
                        print(f"\n# {response.name.upper()}:\n{response.content}")
            except Exception as e:
                print(f"[Fehler bei Chat-Inferenz: {e}]")

            if chat.is_complete:
                print("\n[Gespräch abgeschlossen. Buchung bestätigt!]")
                break

if __name__ == "__main__":
    asyncio.run(main())
