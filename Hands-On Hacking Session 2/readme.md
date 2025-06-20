# Hands-On Hack Session 2: Semantic Kernel

In this exercise, you use the Azure AI Agent service in the Azure AI Foundry portal to create a simple agentic workflow.


> **Note**: Some of the technologies used in this exercise are in preview or in active development. You may experience some unexpected behavior, warnings, or errors.


## What are we building ? 🚀


Given that the Travel Booking Agentic System was such a huge success you are tasked with implementing a **Multi-Agent Support System** for Munich Agent Factory GmbH. This system will automate and support for and customer service requests regarding purchased orders by orchestrating multiple specialized agents.

### Your Implementation Requirements

- **Agent Orchestration:** The system must coordinate several specialized agents (e.g., for order status, refunds, and returns).
- **Intent Routing:** User requests must be automatically routed to the correct agent based on intent.
- **Domain Coverage:** The system should support order management and general customer support scenarios.
- **Conversational Interface:** Provide a seamless, user-friendly conversational interface for employees and support staff (e.g., via Gradio).
- **Plugin Integration:** Each agent should be able to call domain-specific plugins (e.g., for checking order status, processing refunds, handling returns).


You drew a first draft on how to solve the problem using the **Handoff Orchestration Pattern** provided by the **Semantic Kernenl SDK**

![Handoff Schema](Media/handoff_schema.png)

### Let's start hacking!

## Setup the local environment

1. Clone this repository to your local machine using your IDE VSC Integration idealy VS Code ;) or directly via the command line:
    ```
   git clone https://github.com/tobiasunterhauser/ai-foundry-agents-workshop
    ```
1. Open a terminal in the project root and setup a virtual python environment:
    ```
    (Windows)
   python -m venv labenv
   ./labenv/Scripts/Activate.ps1

    (Mac)
    python3 -m venv labenv
    source labenv/bin/activate
    ```
1. Install necassary packages int othe virtual environment:

    ```
    pip install python-dotenv azure-identity semantic-kernel[azure] 

    ````

1. Open the **.env** file and  replace the **your_project_endpoint** placeholder with the endpoint for your project (copied from the project **Overview** page in the Azure AI Foundry portal), and the **your_model_deployment** placeholder with the name you assigned to your gpt-4o model deployment.

1. After you've replaced the placeholders, use the **CTRL+S** command to save your changes and then use the **CTRL+Q** command to close the code editor while keeping the cloud shell command line open.

**You are now ready to go!**
 

## Start Coding 🧑‍💻

Now you're ready to create the agents for your multi-agent solution! Let's get started!

1. Open the **code.py** file

1. Find the comment **Add references** and add the following code to import the classes you'll need:

    ```python
    from azure.identity.aio import DefaultAzureCredential
    from semantic_kernel.agents import Agent, HandoffOrchestration, OrchestrationHandoffs, AzureAIAgent, AzureAIAgentSettings
    from semantic_kernel.agents.runtime import InProcessRuntime
    from semantic_kernel.contents import (
        AuthorRole,
        ChatMessageContent,
        FunctionCallContent,
        FunctionResultContent,
        StreamingChatMessageContent,
    )
    from semantic_kernel.functions import kernel_function
    ```
Note how this time we are referencing **only the semantic_kernel SDK** and not the Foundry SDK

1. Locate the comment **Create the support agent in Azure AI Foundry** and add the following code: 

    ```python
    support_agent_definition = await project_client.agents.create_agent(
        model=ai_agent_settings.model_deployment_name,
        name="SupportAgent",
        instructions="Handle customer support requests and triage them to the appropriate agents.",
        description="A customer support agent that triages issues."
    )
    ```
This creates the Agent with the defined properties in AI Foundry

    
1. Locate the comment right underneath **Create the created support agent as an AzureAIAgent instance** and add the following code
    
    ```python
    support_agent = AzureAIAgent(
        client=project_client,
        definition=support_agent_definition
    )
    ```
This instantiates an AzureAIAgent instance of the created Foundry Agent. This allows to invoke the agent in Semantic Kernel Orchestration Patterns and call kernel function plugins. [See Full Documentation](https://learn.microsoft.com/en-us/python/api/semantic-kernel/semantic_kernel.agents.azureaiagent?view=semantic-kernel-python)

1. Locate the comment **Define the plugin for handling order-related tasks** and add the following code. 
    ```python
    class OrderStatusPlugin:
    @kernel_function
    def check_order_status(self, order_id: str) -> str:
        """Check the status of an order."""
        # Simulate checking the order status
        return f"Order {order_id} is shipped and will arrive in 2-3 days."
    ```

1. Locate the comment **Create the Order Status agent** and create the Agent that calls the OrderStatus Plugin:
    
    ```python
    order_status_agent_definition = await project_client.agents.create_agent(
        model=ai_agent_settings.model_deployment_name,
        name="OrderStatusAgent",
        description="A customer support agent that checks order status.",
        instructions="Handle order status requests."
    )
    order_status_agent = AzureAIAgent(
        client=project_client,
        definition=order_status_agent_definition,
        plugins=[OrderStatusPlugin()]
    )
    ```
1. Locate the comment **Define the plugin for handling refunds**. Observe how the **OrderStatusPlugin** was created. And create a similar Plugin named **OrderRefundPlugin**  that checks if a specific order id is eligible for refund. Be creative. The return statement should look something like this:

    ```python
        return f"Refund for order {order_id} has been processed successfully."
    ```

1. Locate the comment **Create the Refund agent**. Observe how the order_status Agent was created and Create the **refund_agent**. Don't forget to call your **OrderRefundPlugin**. User the following parameter:
    
    ```python
    name="RefundAgent",
    description="A customer support agent that handles refunds.",
    instructions="Handle refund requests."
    ```
1. Locate the comment **Define plugin for handling order returns** and create the **OrderReturnPlugin**

1. Locate the comment **Create the Order Return agent**. And create the **order_return_agent**  using the following parameter:

    ```python
    name="OrderReturnAgent",
    description="A customer support agent that handles order returns.",
    instructions="Handle order return requests."
    ```

1. Locateh the logic for the Agent handoffs at the comment **Define the handoff relationships between agents**  and add the following code: 

    ```python
    handoffs = (
        OrchestrationHandoffs()
        .add_many(
            source_agent=support_agent.name,
            target_agents={
                refund_agent.name: "Transfer to this agent if the issue is refund related",
                order_status_agent.name: "Transfer to this agent if the issue is order status related",
                order_return_agent.name: "Transfer to this agent if the issue is order return related",
            },
        )
        .add(
            source_agent=refund_agent.name,
            target_agent=support_agent.name,
            description="Transfer to this agent if the issue is not refund related",
        )
        .add(
            source_agent=order_status_agent.name,
            target_agent=support_agent.name,
            description="Transfer to this agent if the issue is not order status related",
        )
        .add(
            source_agent=order_return_agent.name,
            target_agent=support_agent.name,
            description="Transfer to this agent if the issue is not order return related",
        )
    )
    ```

1. Locate the comment **Create the handoff orchestration with the agents and handoffs** and add the following code:

    ```python
    handoff_orchestration = HandoffOrchestration(
        members=agents,
        handoffs=handoffs,
        streaming_agent_response_callback=streaming_agent_response_callback,
        human_response_function=human_response_function,
    )
    ```

1. Use the **CTRL+S** command to save your changes to the code file.

1. Run the code by entering the following command in the terminal: 
    
    ```
   python code.py
    ```

    **Congrats! You can now interact with the Agent Orchestration in the terminal**


1. Check in the AI Foundry Portal the 4 Agents that have been created.


# Next Step (Optional)
In the previous exercise, you may have noticed that managing a multi-agent workflow using only prompt engineering can be challenging, imprecise, and often results in high token usage. Semantic Kernel provides built-in orchestration patterns, such as Handoff, to address these issues and streamline agent coordination.

**Reflect on your experience:**  
Consider the challenges you faced when building the Agentic Solution for Booking Business Travel—such as intent routing, agent coordination, and maintaining clarity in responses.

**Your task:**  
Revisit your previous Travel Booking Agentic Solution and enhance it by applying the Handoff orchestration pattern from Semantic Kernel. Specifically:

- Identify the specialized agents involved in the travel booking scenario (e.g., booking agent, policy lookup agent, approval agent).
- Define clear handoff rules between these agents based on user intent or workflow requirements.
- Implement the orchestration logic using Semantic Kernel’s Handoff pattern to automate agent collaboration and improve the overall user experience.

> **Goal:**  
> Refactor your travel booking solution to leverage agent handoffs, making the workflow more robust, efficient, and easier to maintain.

Once complete, test your updated solution and observe how the orchestration improves agent collaboration and response quality.

## Overview of all Semantic Kernel Orchestration Patterns

| Pattern     | Description                                                                 | Typical Use Case                                               |
|-------------|-----------------------------------------------------------------------------|----------------------------------------------------------------|
| [Concurrent](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/concurrent) | Broadcasts a task to all agents, collects results independently.             | Parallel analysis, independent subtasks, ensemble decision making. |
| [Sequential](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/sequential) | Passes the result from one agent to the next in a defined order.               | Step-by-step workflows, pipelines, multi-stage processing.     |
| [Handoff](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/handoff)    | Dynamically passes control between agents based on context or rules.           | Dynamic workflows, escalation, fallback, or expert handoff scenarios. |
| [Group Chat](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/group-chat) | All agents participate in a group conversation, coordinated by a group manager. | Brainstorming, collaborative problem solving, consensus building. |
| [Magentic](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/magentic)   | Group chat-like orchestration inspired by [MagenticOne](https://magenticone.com/). | Complex, generalist multi-agent collaboration.                 |

