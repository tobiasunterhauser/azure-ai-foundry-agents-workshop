import os
from dotenv import load_dotenv

# Add references


# Clear the console
os.system('cls' if os.name=='nt' else 'clear')

# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Create the agents client


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

with agents_client:

    # Reference the existing Bing Grounding Agent
    recherche_agent = agents_client.get_agent(
        agent_id="Recherche_Agent_ID" # Replace with actual ID of the Bing Grounding Agent
    )


    # Create the Booking Agent

    
    # Define the path to the file to be uploaded
    policy_file_path = "Reiserichtlinie_Munich_Agent_Factory_GmbH_v1.pdf"

    # Upload the travel policy file to foundry and create a vector store
   

    # Create file search tool with resources followed by creating agent
   

    # Create the policy agent using the file search tool
  

    # Create the connected agent tools for all 3 agents
    # Note: The connected agent tools are used to connect the agents to the orchestrator agent
    policy_agent_tool = ConnectedAgentTool(
        id=policy_agent.id,
        name=policy_agent_name,
        description="Prüft die Reiserichtlinie für die geplante Reise."
    )

    # add recherche_agent_tool
    

    # add buchungs_agent_tool 


    # Create the Orchestrator Agent
    # This agent will coordinate the other agents based on user input
    

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