import mysql.connector
import requests
import string
import streamlit as st
import subprocess
import sys

# # Try installing mysql-connector-python at runtime
# try:
#     import mysql.connector
# except ImportError:
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python"])

# import mysql.connector
# import streamlit as st

# # Your Streamlit code follows
# st.write("MySQL connector should now be installed!")

# # Check installed packages
# def check_installed_packages():
#     result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
#     st.write("Installed packages:\n", result.stdout)

# check_installed_packages()


# MySQL Database Setup
conn = mysql.connector.connect(
    host="localhost",  
    user="root",      
    password="ash123",      
    database="my_db"  
)
cursor = conn.cursor()

# Create the products table if it doesn't exist
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_name VARCHAR(255) NOT NULL,
        vcpu_count INT NOT NULL,
        base_ram_gb INT NOT NULL,
        base_disk_gb INT NOT NULL,
        max_ram_gb INT NOT NULL,
        register_inr FLOAT NOT NULL,
        renew_inr FLOAT NOT NULL,
        promo_inr FLOAT NOT NULL,
        location VARCHAR(255) NOT NULL,
        delivery_time INT NOT NULL
    )
''')
conn.commit()

# Function to insert or update a product in the products table (case-insensitive)
def insert_or_update_product(product_name, vcpu_count, base_ram_gb, base_disk_gb, max_ram_gb, register_inr, renew_inr, promo_inr, location, delivery_time):
    product_name_lower = product_name.lower()  # Convert to lowercase for case-insensitive matching

    cursor.execute(''' 
        SELECT * FROM products WHERE product_name = %s 
    ''', (product_name_lower,))
    product = cursor.fetchone()

    if product:  # If the product already exists, update its details
        cursor.execute(''' 
            UPDATE products SET vcpu_count = %s, base_ram_gb = %s, base_disk_gb = %s, 
                               max_ram_gb = %s, register_inr = %s, renew_inr = %s, 
                               promo_inr = %s, location = %s, delivery_time = %s
            WHERE product_name = %s
        ''', (vcpu_count, base_ram_gb, base_disk_gb, max_ram_gb, register_inr, renew_inr, promo_inr, location, delivery_time, product_name_lower))
    else:  # If the product doesn't exist, insert a new one
        cursor.execute(''' 
            INSERT INTO products (product_name, vcpu_count, base_ram_gb, base_disk_gb, 
                                  max_ram_gb, register_inr, renew_inr, promo_inr, location, delivery_time) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (product_name_lower, vcpu_count, base_ram_gb, base_disk_gb, max_ram_gb, 
              register_inr, renew_inr, promo_inr, location, delivery_time))

    conn.commit()

# Manually set product data (you can replace or modify these)
insert_or_update_product('VMStandard1', 2, 4, 50, 16, 15000.00, 12000.00, 13500.00, 'Mumbai, India', 3)
insert_or_update_product('VMHighPerformance2', 4, 16, 100, 32, 35000.00, 30000.00, 32500.00, 'Bangalore, India', 5)
insert_or_update_product('VMComputeOptimized', 8, 32, 200, 64, 70000.00, 60000.00, 65000.00, 'Chennai, India', 7)

print("Product details updated successfully!")

# Dify API Key and URL (for external API)
dify_api_key = "app-9oLZBM1eYsA77L1tp3rVYZd9"
url = "https://api.dify.ai/v1/chat-messages"

st.title("Dify Streamlit Chatbot with Product Rate Retrieval")

# Initialize session state if conversation_id and messages are not yet set
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ""  # Empty conversation_id to start fresh

if "messages" not in st.session_state:
    st.session_state.messages = []  # Initialize an empty list to hold chat messages

# Function to insert a message into the database
def insert_message(role, content):
    cursor.execute(''' 
        INSERT INTO messages (role, content) 
        VALUES (%s, %s)
    ''', (role, content))
    conn.commit()

# Function to retrieve all messages from the database
def get_messages():
    cursor.execute('SELECT * FROM messages')
    rows = cursor.fetchall()
    return rows

# Function to retrieve product details from the database (case-insensitive)
def get_product_details(product_name):
    cursor.execute('''
        SELECT product_name, vcpu_count, base_ram_gb, base_disk_gb, max_ram_gb, register_inr, renew_inr, promo_inr, location, delivery_time 
        FROM products WHERE LOWER(product_name) = LOWER(%s)
    ''', (product_name,))
    product = cursor.fetchone()
    if product:
        return product  # Return all product details as a tuple
    else:
        return None  # Return None if the product is not found

# Function to load the response from the assistant (chatbot)
def load_response(prompt):
    headers = {
        'Authorization': f'Bearer {dify_api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "inputs": {},
        "query": prompt,
        "response_mode": "blocking",
        "conversation_id": st.session_state.conversation_id,
        "user": "aianytime",
        "files": []
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        response_data = response.json()

        full_response = response_data.get('answer', 'No answer provided')

        new_conversation_id = response_data.get('conversation_id', st.session_state.conversation_id)
        st.session_state.conversation_id = new_conversation_id

        return full_response

    except requests.exceptions.RequestException as e:
        if e.response:
            st.error(f"HTTP Status Code: {e.response.status_code}")
            st.error(f"Response Content: {e.response.text}")
        else:
            st.error(f"An error occurred: {e}")
        return "An error occurred while fetching the response."

# Function to handle product price query in the chat
def handle_product_price_query(query):
    # Look for product-related query with "price" and either "of" or "for"
    if 'price' in query.lower() and ('of' in query.lower() or 'for' in query.lower()):
        # Check for both "of" and "for" and split accordingly
        if 'of' in query.lower():
            product_name = query.split('of')[-1].strip()
        elif 'for' in query.lower():
            product_name = query.split('for')[-1].strip()

        # Remove punctuation (like ? or ! at the end) from the product_name
        product_name = product_name.translate(str.maketrans('', '', string.punctuation))

        # Convert the product_name to lowercase for case-insensitive matching
        product_name_lower = product_name.lower()

        product = get_product_details(product_name_lower)
        if product:
            # Format product details with <br> for line breaks in Markdown
            response = (f"**Product Name**: {product[0]}<br>"
                        f"**VCpu Count**: {product[1]}<br>"
                        f"**Base RAM**: {product[2]} GB<br>"
                        f"**Base Disk**: {product[3]} GB<br>"
                        f"**Max RAM**: {product[4]} GB<br>"
                        f"**Price (Register)**: ₹{product[5]:,.2f}<br>"
                        f"**Price (Renewal)**: ₹{product[6]:,.2f}<br>"
                        f"**Price (Promo)**: ₹{product[7]:,.2f}<br>"
                        f"**Location**: {product[8]}<br>"
                        f"**Delivery Time**: {product[9]} days")
            return response
        else:
            return f"Sorry, I couldn't find the price or details for the product '{product_name}'."
    else:
        return None  # Not a price query, let the chatbot handle it

# Display previous chat messages from the database
messages = get_messages()
for message in messages:
    with st.chat_message(message[1]):
        # Render each message with Markdown (supporting <br> for line breaks)
        st.markdown(message[2], unsafe_allow_html=True)

# Get user input (question)
prompt = st.chat_input("Ask me anything, or ask for product prices!")

if prompt:
    # Display user input
    with st.chat_message("user"):
        st.markdown(prompt)
    insert_message('user', prompt)

    # Check if the query is related to product price
    product_price_response = handle_product_price_query(prompt)
    if product_price_response:
        # If it's a product price query, respond directly
        with st.chat_message("assistant"):
            st.markdown(product_price_response, unsafe_allow_html=True)
        insert_message('assistant', product_price_response)
    else:
        # Handle as a normal chatbot query
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("**Gimme a minute ...** ⏳")

            full_response = load_response(prompt)

            message_placeholder.markdown(full_response)

            insert_message('assistant', full_response)

    # Refresh session state messages to reflect new data
    st.session_state.messages = get_messages()
