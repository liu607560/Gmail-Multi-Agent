from langgraph.graph import END, StateGraph
from .state import GraphState
from .nodes import Nodes

class Workflow():
    def __init__(self):
        # initiate graph state & nodes
        workflow = StateGraph(GraphState)
        nodes = Nodes()
        self.gmail_tools = nodes.gmail_tools

        # define all graph nodes
        workflow.add_node("load_inbox_emails", nodes.load_new_emails)
        workflow.add_node("categorize_email", nodes.categorize_email)
        workflow.add_node("construct_rag_queries", nodes.construct_rag_queries)
        workflow.add_node("retrieve_from_rag", nodes.retrieve_from_rag)
        workflow.add_node("email_writer", nodes.write_draft_email)
        workflow.add_node("email_proofreader", nodes.verify_generated_email)
        workflow.add_node("send_email", nodes.send_email_response)
        workflow.add_node("save_draft", nodes.create_draft_response)
        workflow.add_node("skip_unrelated_email", nodes.skip_unrelated_email)

        # load inbox emails
        workflow.set_entry_point("load_inbox_emails")

        # check if there are emails to process
        workflow.add_conditional_edges(
            "load_inbox_emails",
            nodes.check_new_emails,
            {
                "process": "categorize_email",
                "empty": END
            }
        )

        # route email based on category
        workflow.add_conditional_edges(
            "categorize_email",
            nodes.route_email_based_on_category,
            {
                "product related": "construct_rag_queries",
                "not product related": "email_writer", # Feedback or Complaint
                "unrelated": "skip_unrelated_email"
            }
        )

        # pass constructed queries to RAG chain to retrieve information
        workflow.add_edge("construct_rag_queries", "retrieve_from_rag")
        # give information to writer agent to create draft email
        workflow.add_edge("retrieve_from_rag", "email_writer")
        # proofread the generated draft email
        workflow.add_edge("email_writer", "email_proofreader")
        # check if email is sendable or not, if not rewrite the email
        workflow.add_conditional_edges(
            "email_proofreader",
            nodes.must_rewrite,
            {
                "send": "send_email",
                "rewrite": "email_writer",
                "stop": "save_draft"
            }
        )

        # check if there are still emails to be processed
        workflow.add_conditional_edges(
            "send_email",
            nodes.check_new_emails,
            {
                "process": "categorize_email",
                "empty": END
            }
        )
        workflow.add_conditional_edges(
            "save_draft",
            nodes.check_new_emails,
            {
                "process": "categorize_email",
                "empty": END
            }
        )
        workflow.add_conditional_edges(
            "skip_unrelated_email",
            nodes.check_new_emails,
            {
                "process": "categorize_email",
                "empty": END
            }
        )

        # Compile
        self.app = workflow.compile()
