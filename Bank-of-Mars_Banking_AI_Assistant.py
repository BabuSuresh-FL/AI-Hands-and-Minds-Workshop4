import streamlit as st
import boto3
import json

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Bank of Mars - AI Assistant", page_icon="🤖", layout="centered")

st.title("🤖 Bank of Mars - AI Assistant")
st.write("Ask your queries and get responses from your AI Assistant")

# Input fields for AWS credentials (only needed once per session)
with st.sidebar:
    st.header("🔑 AWS Credentials")
    aws_access_key = st.text_input("AWS Access Key ID", type="password")
    aws_secret_key = st.text_input("AWS Secret Access Key", type="password")
    aws_region = st.text_input("AWS Region", value="us-east-1")
    agent_id = st.text_input("Supervisor Agent ID")  # Replace with your agent ID
    agent_alias_id = st.text_input("Agent Alias ID")  # Replace with your alias ID

# User query
user_query = st.text_area("💬 Enter your query:", height=100)

if st.button("Send to AI Assistant"):
    if not all([aws_access_key, aws_secret_key, aws_region, agent_id, agent_alias_id, user_query]):
        st.error("⚠️ Please fill in all fields and enter a query.")
    else:
        try:
            # ---------------------------
            # Boto3 Bedrock Agent Runtime client
            # ---------------------------
            client = boto3.client(
                "bedrock-agent-runtime",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region,
            )

            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId="streamlit-session",
                inputText=user_query
            )

            # The response has streaming chunks
            output_text = ""
            for event in response["completion"]:
                if "chunk" in event:
                    chunk_text = event["chunk"]["bytes"].decode("utf-8")
                    output_text += chunk_text
                    st.write(chunk_text)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
