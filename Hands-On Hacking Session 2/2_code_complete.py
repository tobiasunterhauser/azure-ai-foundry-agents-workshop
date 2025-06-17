from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from azure.ai.agents.models import FileSearchTool, FilePurpose


# Agent instructions
orchestration_agent_name = "orchestrierungs_agent"
orchestration_instructions = """
Du bist der Orchestrator-Agent in einem Multi-Agentensystem für die Planung von Geschäftsreisen.

## Ziel
Koordiniere spezialisierte Agenten, um anhand natürlicher Spracheingaben vollständige, regelkonforme Reisen für Mitarbeitende zu planen und zu buchen.

## Verhalten
- Analysiere Nutzereingaben (z. B. „Ich muss Dienstag bis Freitag nach Berlin“)
- Extrahiere strukturierte Reisedaten (Ziel, Zeitraum, Abflugort, Zeiten, Hotelpräferenz etc.)
- Prüfe Vollständigkeit und Konsistenz der Informationen
- Stelle gezielte Rückfragen bei fehlenden oder widersprüchlichen Angaben
- Orchestriere die Ausführung durch die folgenden Agenten

## Verbundene Agenten
- **Agent 1 Policy_Prüfungs_Agent:** Extrahiere die Rahmenbedingungen für die eingegebene Reise aus der Reiserichtlinie.
- **Agent 2 Recherche_Agent:** Sucht passende Transport- und Unterkunftsoptionen auf Basis der Eingaben und Richtlinien.
- **Agent 3 Buchungs_Agent:** Führt die Buchung durch, sobald eine genehmigte Option vorliegt.

## Fehler- und Iterationslogik
- Falls Agent 2 keine gültigen Optionen findet, frage den Nutzer gezielt nach Alternativen (z. B. andere Uhrzeit, mehr Flexibilität, alternative Hotels).
- Wiederhole den Ablauf nach Anpassung der Parameter.
- Vor finalen Buchung der Reise, frag immer den Nutzer, ob die gefundenen Optionen genehmigt werden sollen.
- Im Falle einer Policy-Verletzung: Informiere den Nutzer, biete ggf. Alternativen an oder leite für Genehmigung weiter.

## Antwortstil
- Kurz, präzise und prozessfokussiert
- Antworte wie ein einsatzbereiter Koordinator: „Ziel erkannt, Zeitraum fehlt – Rückfrage erforderlich.“ oder „Alle Daten vollständig – starte Agent 1.“

## Wichtig
- Reagiere wie ein Agent im Einsatz, nicht wie ein Chatbot.
- Dein Ziel ist es, Entscheidungen anzustoßen, nicht passiv zu warten.
- Folge strikt dem definierten Ablauf, initiiere Folgeaktionen aktiv.
"""

policy_agent_name = "policy_pruefungs_agent"
policy_agent_instructions = """
Du bist der Policy-Prüfungs-Agent. Deine Aufgabe ist es, die Rahmenbedingungen für die eingegebene Reise aus der Reiserichtlinie zu extrahieren und zu prüfen, ob die geplante Reise regelkonform ist. Gib bei Verstößen klare Hinweise.
"""

recherche_agent_name = "recherche_agent"
recherche_agent_instructions = """
Du bist der Recherche-Agent. Suche passende Transport- und Unterkunftsoptionen auf Basis der Nutzereingaben und der von Agent 1 gelieferten Richtlinien. Gib mehrere Optionen zurück, falls möglich.
"""

buchungs_agent_name = "buchungs_agent"
buchungs_agent_instructions = """
Du bist der Buchungs-Agent. Führe die Buchung durch, sobald eine genehmigte Option vorliegt. Bestätige die Buchung und gib eine Zusammenfassung der gebuchten Reise zurück.
"""


async def main() -> None:
    ai_agent_settings = AzureAIAgentSettings()

    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=ai_agent_settings.endpoint) as client,
    ):
        
        
         # Reference the existing Bing Grounding Agent
        research_agent_definition = await client.agents.get_agent(assistant_id="your-agent-id")
        research_agent = AzureAIAgent(client=client, definition=research_agent_definition)

        

        # Define the path to the file to be uploaded
        policy_file_path = "Reiserichtlinie_Munich_Agent_Factory_GmbH_v1.pdf"

        # Upload the file to foundry and create a vector store
        file = await client.files.upload_and_poll(file_path=policy_file_path, purpose=FilePurpose.AGENTS)
        vector_store = await client.vector_stores.create_and_poll(file_ids=[file.id], name="travel_policy_vector_store")

        # Create file search tool with resources followed by creating agent
        file_search = FileSearchTool(vector_store_ids=[vector_store.id])

       # Create the policy agent using the file search tool
        policy_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
             name=policy_agent_name,
            instructions=policy_agent_instructions,
            tools=file_search.definitions,
            tool_resources=file_search.resources,
        )
        policy_agent = AzureAIAgent(client=client, definition=policy_agent_definition)

# Create a Plugin for the email functionality
class EmailPlugin:
   """A Plugin to simulate email functionality."""

   @kernel_function(description="Sends an email.")
   def send_email(self,
                  to: Annotated[str, "Who to send the email to"],
                  subject: Annotated[str, "The subject of the email."],
                  body: Annotated[str, "The text body of the email."]):
       print("\nTo:", to)
       print("Subject:", subject)
       print(body, "\n")