import os
from dotenv import load_dotenv
# Add references
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder, FileSearchTool, FilePurpose
from azure.identity import DefaultAzureCredential

# Clear the console
os.system('cls' if os.name=='nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Create the agents client
agents_client = AgentsClient(endpoint=project_endpoint, credential=DefaultAzureCredential())

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

recherche_agent_name = "reise-recherche_agent"
recherche_agent_instructions = """
Du bist der Recherche-Agent. Suche passende Transport- und Unterkunftsoptionen auf Basis der Nutzereingaben und der von Agent 1 gelieferten Richtlinien. Gib mehrere Optionen zurück, falls möglich.
"""

buchungs_agent_name = "buchungs_agent"
buchungs_agent_instructions = """
Du bist der Buchungs-Agent. Führe die Buchung durch, sobald eine genehmigte Option vorliegt. Bestätige die Buchung und gib eine Zusammenfassung der gebuchten Reise zurück.
"""

with agents_client:

    # Reference the existing Bing Grounding Agent
    recherche_agent = agents_client.get_agent(
        agent_id="Recherche_Agent_ID" # Replace with actual ID of the Bing Grounding Agent
    )


    # Create the Booking Agent
    buchungs_agent = agents_client.create_agent(
        model=model_deployment,
        name=buchungs_agent_name,
        instructions=buchungs_agent_instructions
    )

    
    # Define the path to the file to be uploaded
    policy_file_path = "Resources/Reiserichtlinie_Munich_Agent_Factory_GmbH_v1.pdf"

    # Upload the file to foundry and create a vector store
    file = agents_client.files.upload_and_poll(file_path=policy_file_path, purpose=FilePurpose.AGENTS)
    vector_store = agents_client.vector_stores.create_and_poll(file_ids=[file.id], name="travel_policy_vector_store")

    # Create file search tool with resources followed by creating agent
    file_search = FileSearchTool(vector_store_ids=[vector_store.id])

    # Create the policy agent using the file search tool
    policy_agent = agents_client.create_agent(
        model=model_deployment,
        name=policy_agent_name,
        instructions=policy_agent_instructions,
        tools=file_search.definitions,
        tool_resources=file_search.resources,
    )

    # Create the connected agent tools for all 3 agents
    # Note: The connected agent tools are used to connect the agents to the orchestrator agent
    policy_agent_tool = ConnectedAgentTool(
        id=policy_agent.id,
        name=policy_agent_name,
        description="Prüft die Reiserichtlinie für die geplante Reise."
    )
    
    recherche_agent_tool = ConnectedAgentTool(
        id=recherche_agent.id,
        name=recherche_agent_name,
        description="Sucht Transport- und Unterkunftsoptionen."
    )

    buchungs_agent_tool = ConnectedAgentTool(
        id=buchungs_agent.id,
        name=buchungs_agent_name,
        description="Bucht genehmigte Reiseoptionen."
    )

    # Create the Orchestrator Agent
    # This agent will coordinate the other agents based on user input
    orchestrator_agent = agents_client.create_agent(
        model=model_deployment,
        name=orchestration_agent_name,
        instructions=orchestration_instructions,
        tools=[
            policy_agent_tool.definitions[0],
            recherche_agent_tool.definitions[0],
            buchungs_agent_tool.definitions[0]
        ]
    )

    print(f"Orchestrator-Agent '{orchestration_agent_name}' und verbundene Agenten wurden erfolgreich erstellt.")

    # === Thread for Terminal Interaction ===
    thread = agents_client.threads.create()
    print("\nGib deine Reiseanfrage ein (oder 'exit' zum Beenden):")
    while True:
        user_input = input("> ")
        if user_input.strip().lower() == "exit":
            break

        agents_client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=user_input,
        )

        print("Verarbeite Anfrage...")
        run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=orchestrator_agent.id)
        if run.status == "failed":
            print(f"Run fehlgeschlagen: {run.last_error}")
            continue

        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for message in messages:
            if message.text_messages:
                last_msg = message.text_messages[-1]
                print(f"{message.role}:\n{last_msg.text.value}\n")

    # Aufräumen
    # print("Lösche Agenten...")
    agents_client.delete_agent(orchestrator_agent.id)
    agents_client.delete_agent(policy_agent.id)
    agents_client.delete_agent(buchungs_agent.id)
    print("Alle Agenten wieder gelöscht.")