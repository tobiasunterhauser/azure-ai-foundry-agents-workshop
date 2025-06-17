---
lab:
    title: 'Develop a multi-agent solution with Azure AI Foundry'
    description: 'Learn to configure multiple agents to collaborate using Azure AI Foundry Agent Service'
---

# Develop a multi-agent solution

In this exercise, you'll create a project that orchestrates multiple AI agents using Azure AI Foundry Agent Service. In this exercise, you'll create a quest master agent that is responsible for guiding a party through a dungeon. The party consists of connected AI agents representing a warrior, a healer, and a scout. The quest master agent receives a scenario from the user and delegates tasks to the party members accordingly. Let's get started!

This exercise should take approximately **30** minutes to complete.

## Deploy a model in an Azure AI Foundry project

Let's start by deploying a model in an Azure AI Foundry project.

1. In a web browser, open the [Azure AI Foundry portal](https://ai.azure.com) at `https://ai.azure.com` and sign in using your Azure credentials. Close any tips or quick start panes that are opened the first time you sign in, and if necessary use the **Azure AI Foundry** logo at the top left to navigate to the home page, which looks similar to the following image (close the **Help** pane if it's open):

    ![Screenshot of Azure AI Foundry portal.](./Media/ai-foundry-home.png)

1. In the home page, in the **Explore models and capabilities** section, search for the `gpt-4o` model; which we'll use in our project.
1. In the search results, select the **gpt-4o** model to see its details, and then at the top of the page for the model, select **Use this model**.
1. When prompted to create a project, enter a valid name for your project and expand **Advanced options**.
1. Confirm the following settings for your project:
    - **Azure AI Foundry resource**: *A valid name for your Azure AI Foundry resource*
    - **Subscription**: *Your Azure subscription*
    - **Resource group**: *Create or select a resource group*
    - **Region**: *Select any **AI Services supported location***\*

    > \* Some Azure AI resources are constrained by regional model quotas. In the event of a quota limit being exceeded later in the exercise, there's a possibility you may need to create another resource in a different region.

1. Select **Create** and wait for your project, including the gpt-4 model deployment you selected, to be created.
1. When your project is created, the chat playground will be opened automatically.

    > **Note**: The default TPM setting for this model may be too low for this exercise. A lower TPM helps avoid over-using the quota available in the subscription you are using. 

1. In the navigation pane on the left, select **Models and endpoints** and select your **gpt-4o** deployment.

1. Select **Edit** then increase the **Tokens per Minute Rate Limit**

   > **NOTE**: 40,000 TPM should be sufficient for the data used in this exercise. If your available quota is lower than this, you will be able to complete the exercise but you may need to wait and resubmit prompts if the rate limit is exceeded.

1. In the navigation pane on the left, select **Overview** to see the main page for your project; which looks like this:

    > **Note**: If an *Insufficient permissions** error is displayed, use the **Fix me** button to resolve it.

    ![Screenshot of a Azure AI Foundry project overview page.](./Media/ai-foundry-project.png)

1. Copy the **Azure AI Foundry project endpoint** value to a notepad, as you'll use it to connect to your project in a client application.

## Create an AI Agent client app

Now you're ready to create a client app that defines the agents and instructions. Some code is provided for you in a GitHub repository.

### Prepare the environment

1. Open a new browser tab (keeping the Azure AI Foundry portal open in the existing tab). Then in the new tab, browse to the [Azure portal](https://portal.azure.com) at `https://portal.azure.com`; signing in with your Azure credentials if prompted.

    Close any welcome notifications to see the Azure portal home page.

1. Use the **[\>_]** button to the right of the search bar at the top of the page to create a new Cloud Shell in the Azure portal, selecting a ***PowerShell*** environment with no storage in your subscription.

    The cloud shell provides a command-line interface in a pane at the bottom of the Azure portal. You can resize or maximize this pane to make it easier to work in.

    > **Note**: If you have previously created a cloud shell that uses a *Bash* environment, switch it to ***PowerShell***.

1. In the cloud shell toolbar, in the **Settings** menu, select **Go to Classic version** (this is required to use the code editor).

    **<font color="red">Ensure you've switched to the classic version of the cloud shell before continuing.</font>**

1. In the cloud shell pane, enter the following commands to clone the GitHub repo containing the code files for this exercise (type the command, or copy it to the clipboard and then right-click in the command line and paste as plain text):

    ```
   rm -r ai-agents -f
   git clone https://github.com/MicrosoftLearning/mslearn-ai-agents ai-agents
    ```

    > **Tip**: As you enter commands into the cloud shell, the output may take up a large amount of the screen buffer and the cursor on the current line may be obscured. You can clear the screen by entering the `cls` command to make it easier to focus on each task.

1. When the repo has been cloned, enter the following command to change the working directory to the folder containing the code files and list them all.

    ```
   cd ai-agents/Labfiles/06-build-multi-agent-solution/Python
   ls -a -l
    ```

    The provided files include application code and a file for configuration settings.

### Configure the application settings

1. In the cloud shell command-line pane, enter the following command to install the libraries you'll use:

    ```
   python -m venv labenv
   ./labenv/bin/Activate.ps1
   pip install -r requirements.txt azure-ai-projects
    ```

1. Enter the following command to edit the configuration file that is provided:

    ```
   code .env
    ```

    The file is opened in a code editor.

1. In the code file, replace the **your_project_endpoint** placeholder with the endpoint for your project (copied from the project **Overview** page in the Azure AI Foundry portal), and the **your_model_deployment** placeholder with the name you assigned to your gpt-4o model deployment.

1. After you've replaced the placeholders, use the **CTRL+S** command to save your changes and then use the **CTRL+Q** command to close the code editor while keeping the cloud shell command line open.

### Create AI agents

Now you're ready to create the agents for your multi-agent solution! Let's get started!

1. Enter the following command to edit the **agent_quest.py** file:

    ```
   code agent_quest.py
    ```

1. Review the code in the file, noting that it contains strings for each agent name and instructions.

1. Find the comment **Add references** and add the following code to import the classes you'll need:

    ```python
    # Add references
    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder
    from azure.identity import DefaultAzureCredential
    ```

1. Locate the comment **Create the healer agent on the Azure AI agent service**, and add the following code to create an Azure AI Agent.

    ```python
    # Create the healer agent on the Azure AI agent service
    healer_agent = agents_client.create_agent(
        model=model_deployment,
        name=healer_agent_name,
        instructions=healer_instructions
    )
    ```

    This code creates the agent definition on your Azure AI agents client.

1. Find the comment **Create a connected agent tool for the healer agent**, and add the following code:

    ```python
    # Create a connected agent tool for the healer agent
    healer_agent_tool = ConnectedAgentTool(
        id=healer_agent.id, 
        name=healer_agent_name, 
        description="Responsible for healing party members and addressing injuries."
    )
    ```

    Now let's create the other party member agents.

1. Under the comment **Create the scout agent and connected tool**, and add the following code:
    
    ```python
    # Create the scout agent and connected tool
    scout_agent = agents_client.create_agent(
        model=model_deployment,
        name=scout_agent_name,
        instructions=scout_instructions
    )
    scout_agent_tool = ConnectedAgentTool(
        id=scout_agent.id, 
        name=scout_agent_name, 
        description="Goes ahead of the main party to perform reconnaissance."
    )
    ```

1. Under the comment **Create the warrior agent and connected tool**, and add the following code:
    
    ```python
    # Create the warrior agent and connected tool
    warrior_agent = agents_client.create_agent(
        model=model_deployment,
        name=warrior_agent_name,
        instructions=warrior_instructions
    )
    warrior_agent_tool = ConnectedAgentTool(
        id=warrior_agent.id, 
        name=warrior_agent_name, 
        description="Responds to combat or physical challenges."
    )
    ```


1. Under the comment **Create a main agent with the Connected Agent tools**, and add the following code:
    
    ```python
    # Create a main agent with the Connected Agent tools
    agent = agents_client.create_agent(
        model=model_deployment,
        name="quest_master",
        instructions="""
            You are the Questmaster, the intelligent guide of a three-member adventuring party exploring a short dungeon. 
            Based on the scenario, delegate tasks to the appropriate party member. The current party members are: Warrior, Scout, Healer.
            Only include the party member's response, do not provide an analysis or summary.
        """,
        tools=[
            healer_agent_tool.definitions[0],
            scout_agent_tool.definitions[0],
            warrior_agent_tool.definitions[0]
        ]
    )
    ```

1. Find the comment **Create thread for the chat session**, and add the following code:
    
    ```python
    # Create thread for the chat session
    print("Creating agent thread.")
    thread = agents_client.threads.create()
    ```


1. Under the comment **Create the quest prompt**, and add the following code:
    
    ```python
    prompt = "We find a locked door with strange symbols, and the warrior is limping."
    ```

1. Under the comment **Send a prompt to the agent**, and add the following code:
    
    ```python
    # Send a prompt to the agent
    message = agents_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=prompt,
    )
    ```

1. Under the comment **Create and process Agent run in thread with tools**, and add the following code:
    
    ```python
    # Create and process Agent run in thread with tools
    print("Processing agent thread. Please wait.")
    run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    ```


1. Use the **CTRL+S** command to save your changes to the code file. You can keep it open (in case you need to edit the code to fix any errors) or use the **CTRL+Q** command to close the code editor while keeping the cloud shell command line open.

### Sign into Azure and run the app

Now you're ready to run your code and watch your AI agents collaborate.

1. In the cloud shell command-line pane, enter the following command to sign into Azure.

    ```
   az login
    ```

    **<font color="red">You must sign into Azure - even though the cloud shell session is already authenticated.</font>**

    > **Note**: In most scenarios, just using *az login* will be sufficient. However, if you have subscriptions in multiple tenants, you may need to specify the tenant by using the *--tenant* parameter. See [Sign into Azure interactively using the Azure CLI](https://learn.microsoft.com/cli/azure/authenticate-azure-cli-interactively) for details.

1. When prompted, follow the instructions to open the sign-in page in a new tab and enter the authentication code provided and your Azure credentials. Then complete the sign in process in the command line, selecting the subscription containing your Azure AI Foundry hub if prompted.

1. After you have signed in, enter the following command to run the application:

    ```
   python agent_quest.py
    ```

    You should see some output similar to the following:

    ```output
    Creating agent thread.
    Processing agent thread. Please wait.

    MessageRole.USER:
    We find a locked door with strange symbols, and the warrior is limping.

    MessageRole.AGENT:
    - **Scout:** Decipher the celestial patterns of the strange symbols and determine the sequence to unlock the door. 
    - **Healer:** The warrior's injury has been addressed; moderate strain is relieved through healing magic and restorative salve.
    - **Warrior:** Recovered and ready to assist physically or guard the party as we proceed.

    Cleaning up agents:
    Deleted quest master agent.
    Deleted healer agent.
    Deleted scout agent.
    Deleted warrior agent.
    ```

    You can try modifying the prompt using a different scenario to see how the agents collaborate.

## Clean up

If you've finished exploring Azure AI Agent Service, you should delete the resources you have created in this exercise to avoid incurring unnecessary Azure costs.

1. Return to the browser tab containing the Azure portal (or re-open the [Azure portal](https://portal.azure.com) at `https://portal.azure.com` in a new browser tab) and view the contents of the resource group where you deployed the resources used in this exercise.

1. On the toolbar, select **Delete resource group**.

1. Enter the resource group name and confirm that you want to delete it.
