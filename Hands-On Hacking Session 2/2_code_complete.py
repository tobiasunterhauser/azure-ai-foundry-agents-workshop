import asyncio
import os

from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, ChatHistoryAgentThread, ChatCompletionAgent
from typing import Annotated
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.functions import kernel_function, KernelFunctionFromPrompt
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.filters import FunctionInvocationContext


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

orchestration_agent_instructions = """
Du bist der Orchestrator-Agent in einem Multi-Agentensystem für die Planung von Geschäftsreisen.

## Ziel
Koordiniere spezialisierte Agenten, um anhand natürlicher Spracheingaben vollständige, regelkonforme Reisen für Mitarbeitende zu planen und zu buchen.

## Ablauf

1. **Datenerfassung:**  
    Sobald eine Nutzereingabe eingeht, stelle sicher, dass folgende Informationen vollständig vorliegen:
    - Startort
    - Zielort
    - Hinreisedatum
    - Rückreisedatum
    - Gewünschte Startuhrzeit (Hinreise)
    - Gewünschte Rückreiseuhrzeit (Rückreise)

    Frage gezielt nach, falls eine dieser Angaben fehlt oder unklar ist. Wiederhole die Rückfrage, bis alle Daten vollständig und eindeutig sind.

2. **Policy-Prüfung:**  
    Sobald alle Reisedaten vorliegen, beauftrage den Policy_Prüfungs_Agent, die Reiserichtlinie zu prüfen:
    - Ist eine Flugreise oder nur eine Bahnreise erlaubt?
    - Welche Reiseklasse ist zulässig?

    Warte das Ergebnis ab, gib es aber nur an den Recherche Agent weiter und nicht an den User aus. Fahre erst fort, wenn die Policy-Prüfung abgeschlossen ist.

3. **Recherche:**  
    Beauftrage den Recherche_Agent, passende Transport- und Unterkunftsoptionen auf Basis der Policy-Ergebnisse und Nutzereingaben zu suchen.

4. **Auswahl und Bestätigung:**  
    Präsentiere dem Nutzer die gefundenen Optionen und frage nach einer Auswahl bzw. Bestätigung.

5. **HR-Daten:**  
    Hole die benötigten persönlichen Informationen des Nutzers vom HR Agent ab, um die Buchung abzuschließen. Dies umfasst:
    - Name des Nutzers
    - E-Mail-Adresse des Nutzers

6. **Buchung:**  
    Vor durchfürhugn der Buchung frage nochmal nach einer finalen Bestätigung des Nutzers. Nach Bestätigung durch den Nutzer, beauftrage den Buchungs_Agent mit der Buchung der ausgewählten Option. Die E-Mail-Adresse des Nutzers sowie persönliche Informationen werden vom HR Agent bereitgestellt. Sende die Mail über das EmailPlugin.
## Fehler- und Iterationslogik
- Falls der Recherche_Agent keine gültigen Optionen findet, frage den Nutzer gezielt nach Alternativen (z. B. andere Uhrzeit, mehr Flexibilität, alternative Hotels).
- Wiederhole den Ablauf nach Anpassung der Parameter.
- Im Falle einer Policy-Verletzung: Informiere den Nutzer, biete ggf. Alternativen an oder leite für Genehmigung weiter.

## Antwortstil
- Kurz, präzise und prozessfokussiert
- Antworte wie ein einsatzbereiter Koordinator: „Startort fehlt – Rückfrage erforderlich.“ oder „Alle Daten vollständig – starte Policy-Prüfung.“
- Gib keine Information an den Nutzer aus die für ihn unbedeutend ist, wie z.B. die Namen der Agenten oder deren Aufgaben. Auch die Details der Travelpolicy sind nicht für ihn wichtig. Wichtig ist nur das er in 2 Sätzen sieht was er Buchung kann und das die Recherche entsprechend der Policy durchgeführt wird

## Wichtig
- Reagiere wie ein Agent im Einsatz, nicht wie ein Chatbot.
- Dein Ziel ist es, Entscheidungen anzustoßen, nicht passiv zu warten.
- Folge strikt dem definierten Ablauf, initiiere Folgeaktionen aktiv.
"""


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
    
async def function_invocation_filter(context: FunctionInvocationContext, next):
    """A filter that will be called for each function call in the response."""
    if "messages" not in context.arguments:
        await next(context)
        return
    #print(f"    Agent [{context.function.name}] called with messages: {context.arguments['messages']}")
    await next(context)
    print(f"    Response from agent [{context.function.name}]: {context.result.value}")

async def chat(triage_agent: ChatCompletionAgent, thread: ChatHistoryAgentThread = None) -> bool:
    """
    Continuously prompt the user for input and show the assistant's response.
    Type 'exit' to exit.
    """
    try:
        user_input = input("User:> ")
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting chat...")
        return False

    if user_input.lower().strip() == "exit":
        print("\n\nExiting chat...")
        return False

    response = await triage_agent.get_response(
        messages=user_input,
        thread=thread,
    )

    if response:
        print(f"Agent :> {response}")

    return True

async def main():
    # Create and configure the kernel.
    kernel = Kernel()

    # The filter is used for demonstration purposes to show the function invocation.
    kernel.add_filter("function_invocation", function_invocation_filter)

    ai_agent_settings = AzureAIAgentSettings()

    chat_completion_service = AzureChatCompletion(
    deployment_name="gpt-4.1",  
    api_key="",
    endpoint="", # Used to point to your service
)

    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=ai_agent_settings.endpoint) as project_client,
    ):
        # Reference existing agents
        research_agent_definition = await project_client.agents.get_agent(agent_id="asst_vMGXYaYdFceK3qhvUTG11FNq")
        research_agent = AzureAIAgent(client=project_client, definition=research_agent_definition)

        policy_agent_definition = await project_client.agents.get_agent(agent_id="asst_hsEowHU39xf7DXYFxRJzEgVJ")
        policy_agent = AzureAIAgent(client=project_client, definition=policy_agent_definition)

        # Create booking agent with plugin
        booking_agent_definition = await project_client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
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
            model=ai_agent_settings.model_deployment_name,
            name=hr_agent_name,
            instructions=hr_agent_instructions
        )
        hr_agent = AzureAIAgent(
            client=project_client,
            definition=hr_agent_definition,
            plugins=[HumanResourcesPlugin()]
        )

        orchestration_agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="OrchestrationAgent",
            instructions=orchestration_agent_instructions,
            plugins=[policy_agent, hr_agent, research_agent, booking_agent],
        )
        
        thread = ChatHistoryAgentThread()
        
        print("\nGib deine Reiseanfrage ein (oder 'exit' zum Beenden):")

        chatting = True
        while chatting:
            chatting = await chat(orchestration_agent, thread)



if __name__ == "__main__":
    asyncio.run(main())
