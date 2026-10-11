from colorama import Fore, Style
from src.graph import Workflow
from dotenv import load_dotenv
import os
import time
from copy import deepcopy
import google.auth
from google.auth.transport.requests import AuthorizedSession

# Load all env variables
load_dotenv()

# config 
config = {'recursion_limit': 100}

initial_state = {
    "emails": [],
    "current_email": {
      "id": "",
      "threadId": "",
      "messageId": "",
      "references": "",
      "sender": "",
      "subject": "",
      "body": ""
    },
    "email_category": "",
    "generated_email": "",
    "rag_queries": [],
    "retrieved_documents": "",
    "writer_messages": [],
    "sendable": False,
    "trials": 0
}

def main():
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "project-bd082cfe-bd29-4ca6-936")
    topic = f"projects/{project}/topics/{os.getenv('GMAIL_PUBSUB_TOPIC', 'gmail-notifications')}"
    subscription = f"projects/{project}/subscriptions/{os.getenv('GMAIL_PUBSUB_SUBSCRIPTION', 'gmail-notifications-sub')}"
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    workflow = Workflow()
    endpoint = f"https://pubsub.googleapis.com/v1/{subscription}"
    renew_at = 0
    print("Waiting for Gmail notifications. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                if time.monotonic() >= renew_at:
                    watch = workflow.gmail_tools.watch_inbox(topic)
                    renew_at = time.monotonic() + min(
                        86400, max(60, int(watch["expiration"]) / 1000 - time.time() - 3600)
                    )
                    print("Gmail watch enabled / renewed.")
                response = session.post(
                    endpoint + ":pull", json={"maxMessages": 1}, timeout=90
                )
                response.raise_for_status()
                messages = response.json().get("receivedMessages", [])
                if not messages:
                    time.sleep(1)
                    continue
                ack_ids = [message["ackId"] for message in messages]
                response = session.post(
                    endpoint + ":modifyAckDeadline",
                    json={"ackIds": ack_ids, "ackDeadlineSeconds": 600}, timeout=30,
                )
                response.raise_for_status()
                for output in workflow.app.stream(deepcopy(initial_state), config):
                    for key, update in output.items():
                        if key == "load_inbox_emails" and not update.get("emails"):
                            continue
                        print(Fore.CYAN + f"Finished running: {key}:" + Style.RESET_ALL)
                        print()
                response = session.post(
                    endpoint + ":acknowledge", json={"ackIds": ack_ids}, timeout=30
                )
                response.raise_for_status()
            except Exception as error:
                print(Fore.RED + f"Notification processing failed: {error}" + Style.RESET_ALL)
                time.sleep(30)
    except KeyboardInterrupt:
        print("\nEmail automation stopped.")
    finally:
        session.close()


if __name__ == "__main__":
    main()

