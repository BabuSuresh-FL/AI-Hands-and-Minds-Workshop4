import streamlit as st
import boto3
import json
import time
from botocore.config import Config
from botocore.exceptions import ReadTimeoutError, ClientError

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Bank of Mars - AI Assistant", page_icon="🤖", layout="centered")

st.title("🤖 Bank of Mars - AI Assistant")
st.write("Ask your queries and get responses from your AI Assistant")

# Input fields for AWS credentials (only needed once per session)
with st.sidebar:
    st.header("🔒 AWS Credentials")
    aws_access_key = st.text_input("AWS Access Key ID", type="password")
    aws_secret_key = st.text_input("AWS Secret Access Key", type="password")
    aws_region = st.text_input("AWS Region", value="us-east-1")
    agent_id = st.text_input("Supervisor Agent ID")
    agent_alias_id = st.text_input("Agent Alias ID")
    
    # Advanced settings
    st.header("⚙️ Advanced Settings")
    timeout_seconds = st.slider("Request Timeout (seconds)", 60, 600, 300)
    max_retries = st.slider("Max Retries", 1, 5, 3)

# User query
user_query = st.text_area("💬 Enter your query:", height=100)

def create_bedrock_client(access_key, secret_key, region, timeout_sec, retries):
    """Create Bedrock client with proper timeout configuration"""
    config = Config(
        read_timeout=timeout_sec,
        connect_timeout=60,
        retries={
            'max_attempts': retries,
            'mode': 'adaptive'
        }
    )
    
    return boto3.client(
        "bedrock-agent-runtime",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=config
    )

def invoke_agent_with_retry(client, agent_id, alias_id, query, max_attempts=3):
    """Invoke agent with retry logic"""
    for attempt in range(max_attempts):
        try:
            st.info(f"🔄 Attempt {attempt + 1}/{max_attempts} - Processing your request...")
            
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=f"streamlit-session-{int(time.time())}",
                inputText=query
            )
            return response
            
        except ReadTimeoutError:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                st.warning(f"⏱️ Request timed out. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                st.error("❌ Request timed out after all retry attempts")
                return None
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['ThrottlingException', 'ServiceUnavailableException'] and attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                st.warning(f"⏱️ Service temporarily unavailable. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                st.error(f"❌ AWS Error: {str(e)}")
                return None
                
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    return None

def process_streaming_response(response):
    """Process streaming response with proper error handling and fixed text formatting"""
    if not response:
        return
    
    output_text = ""
    
    # Create a container for the response with proper styling
    st.markdown("**🤖 AI Assistant Response:**")
    response_container = st.empty()
    
    try:
        # Create a progress bar for visual feedback
        progress_bar = st.progress(0)
        chunk_count = 0
        
        for event in response["completion"]:
            if "chunk" in event:
                chunk_bytes = event["chunk"].get("bytes", b"")
                if chunk_bytes:
                    chunk_text = chunk_bytes.decode("utf-8")
                    output_text += chunk_text
                    
                    # FIXED: Use st.text() instead of markdown to preserve formatting
                    # This prevents markdown interpretation and displays text as-is
                    with response_container.container():
                        st.text(output_text)
                    
                    chunk_count += 1
                    # Update progress (arbitrary - since we don't know total chunks)
                    progress_bar.progress(min(chunk_count * 5, 100))
                    
                    # Small delay to make streaming visible
                    time.sleep(0.1)
        
        # Clear progress bar when done
        progress_bar.empty()
        
        if not output_text:
            st.warning("⚠️ No response received from the agent")
        else:
            st.success("✅ Response completed successfully!")
            
            # Optional: Also display in a code block for better readability
            with st.expander("📋 Response in formatted view"):
                st.code(output_text, language=None)
            
    except Exception as e:
        st.error(f"❌ Error processing response: {str(e)}")

if st.button("Send to AI Assistant"):
    if not all([aws_access_key, aws_secret_key, aws_region, agent_id, agent_alias_id, user_query]):
        st.error("⚠️ Please fill in all fields and enter a query.")
    else:
        try:
            # Show processing indicator
            with st.spinner('🔧 Initializing AI Assistant...'):
                # Create Bedrock client with timeout configuration
                client = create_bedrock_client(
                    aws_access_key, 
                    aws_secret_key, 
                    aws_region,
                    timeout_seconds,
                    max_retries
                )
                
                # Test connection
                st.info("🔗 Testing connection to AWS Bedrock...")
                
            # Invoke agent with retry logic
            with st.spinner('🤖 AI Assistant is processing your query...'):
                response = invoke_agent_with_retry(
                    client, 
                    agent_id, 
                    agent_alias_id, 
                    user_query,
                    max_retries
                )
            
            # Process the streaming response
            if response:
                st.info("📡 Receiving response...")
                process_streaming_response(response)
            
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            st.info("💡 Try increasing the timeout value in Advanced Settings or check your AWS credentials.")

# Add helpful information
with st.expander("ℹ️ Troubleshooting Tips"):
    st.markdown("""
    **If you're experiencing timeouts:**
    - Increase the timeout value in Advanced Settings (try 600 seconds for complex queries)
    - Check your internet connection stability
    - Verify your AWS credentials are correct
    - Ensure the Agent ID and Alias ID are valid
    - Try simpler queries first to test connectivity
    
    **If the agent is not responding:**
    - Make sure your Bedrock agent is deployed and active
    - Check that your AWS account has proper permissions for Bedrock
    - Verify the agent is in the same region as specified
    """)

# Session state to maintain conversation history (optional)
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []