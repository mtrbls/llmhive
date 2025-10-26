"""
Gradio Web UI for ODLA Distributed Inference

Provides a user-friendly interface for:
- Streaming AI inference
- Concordium wallet integration
- Automatic payments
- Node browsing
"""

import gradio as gr
import httpx
import json
import asyncio
from typing import Generator, Tuple, Optional


def create_ui(operator_url: str = "http://localhost:8000"):
    """Create and return the Gradio interface"""

    # No need to load wallet.js here - it's served as a static file

    # Helper functions
    async def get_available_models():
        """Fetch available models from /nodes endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{operator_url}/nodes", timeout=10.0)
                data = response.json()

                nodes = data.get("nodes", [])
                models_set = set()

                for node in nodes:
                    models_set.update(node.get("models", []))

                return sorted(list(models_set)) or ["llama3"]
        except Exception as e:
            print(f"Error fetching models: {e}")
            return ["llama3"]

    async def get_nodes_info():
        """Get information about all registered nodes"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{operator_url}/nodes", timeout=10.0)
                data = response.json()

                nodes = data.get("nodes", [])

                # Format as markdown table
                if not nodes:
                    return "No nodes registered"

                table = "| Node ID | Models | Last Seen | Status |\n"
                table += "|---------|--------|-----------|--------|\n"

                for node in nodes:
                    node_id = node.get("node_id", "Unknown")
                    models = ", ".join(node.get("models", []))
                    last_seen = node.get("last_seen", "Never")
                    status = "🟢 Online"

                    table += f"| {node_id} | {models} | {last_seen} | {status} |\n"

                return table
        except Exception as e:
            return f"Error fetching nodes: {e}"

    async def stream_inference(
        message: str,
        history: list,
        model: str
    ) -> Generator[Tuple[str, list], None, None]:
        """
        Stream AI inference results

        Yields tuples of (chatbot_history, metadata)
        """
        if not message.strip():
            yield history, "Please enter a message"
            return

        # Add user message to history (messages format)
        history = history + [{"role": "user", "content": message}]
        yield history, f"Sending to model: {model}..."

        assistant_message_added = False
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Start streaming request
                async with client.stream(
                    "POST",
                    f"{operator_url}/inference",
                    json={"model": model, "prompt": message}
                ) as response:
                    job_id = response.headers.get("X-Job-ID")

                    if response.status_code != 200:
                        error_text = await response.aread()
                        history = history + [{"role": "assistant", "content": f"Error: {error_text.decode()}"}]
                        yield history, "Error occurred"
                        return

                    # Stream response tokens
                    assistant_message = ""
                    node_info = None

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)

                            # Handle metadata
                            if data.get("metadata"):
                                node_info = data.get("node_id")
                                yield history, f"Processing on node: {node_info}"
                                continue

                            # Handle errors
                            if "error" in data:
                                if not assistant_message_added:
                                    history = history + [{"role": "assistant", "content": f"Error: {data['error']}"}]
                                else:
                                    history[-1]["content"] = f"Error: {data['error']}"
                                yield history, "Error in response"
                                return

                            # Stream tokens
                            if "token" in data and not data.get("done", False):
                                assistant_message += data["token"]
                                if not assistant_message_added:
                                    history = history + [{"role": "assistant", "content": assistant_message}]
                                    assistant_message_added = True
                                else:
                                    history[-1]["content"] = assistant_message
                                yield history, f"Node: {node_info} | Streaming..."

                            # Done streaming
                            if data.get("done", False):
                                token_counts = data.get("token_counts", {})

                                # Get payment info
                                payment_info = await get_job_payment_info(client, job_id)
                                print(f"DEBUG: payment_info = {payment_info}")  # Debug log

                                metadata = f"✓ Complete | Node: {node_info}\n"

                                if token_counts:
                                    metadata += f"Tokens: {token_counts.get('total_tokens', 0)} "
                                    metadata += f"(prompt: {token_counts.get('prompt_tokens', 0)}, "
                                    metadata += f"completion: {token_counts.get('completion_tokens', 0)})\n"

                                if payment_info:
                                    metadata += f"\n💰 Payment: {payment_info['amount']:.6f} CCD\n"
                                    metadata += f"Recipient: {payment_info['recipient']}\n"
                                    metadata += f"Job ID: {job_id}\n\n"
                                    metadata += "🔄 Processing payment automatically..."
                                else:
                                    # Fallback: always show payment info even if fetch failed
                                    metadata += f"\n💰 Payment: 0.000100 CCD\n"
                                    metadata += f"Recipient: 4nB44APqJ6YFv52DueVEYgVw3x57zaEew3nu3uy2YqNiHcELM3\n"
                                    metadata += f"Job ID: {job_id}\n\n"
                                    metadata += "🔄 Processing payment automatically..."
                                    print(f"DEBUG: Using fallback payment info")

                                yield history, metadata
                                break

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            if not assistant_message_added:
                history = history + [{"role": "assistant", "content": f"Error: {str(e)}"}]
            else:
                history[-1]["content"] = f"Error: {str(e)}"
            yield history, f"Error: {str(e)}"

    async def get_job_payment_info(client, job_id):
        """Fetch payment information for a job"""
        try:
            response = await client.get(f"{operator_url}/jobs/{job_id}", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                payment = data.get("payment", {})

                return {
                    "amount": payment.get("amount_ccd", 0),
                    "recipient": payment.get("recipient_address", "N/A"),
                    "job_id": job_id
                }
        except Exception:
            pass

        return None

    # Gradio Interface
    with gr.Blocks(
        title="ODLA - Distributed AI Inference",
        theme=gr.themes.Soft(),
        head='''
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="/static/wallet.js?v=9"></script>
        <script>
        console.log('🔵 Defining switchView function...');
        window.switchView = function(view, element) {
            console.log('🔵 Switching to view:', view);

            // Update active state
            const allNavItems = document.querySelectorAll('.nav-item');
            allNavItems.forEach(item => {
                item.classList.remove('active', 'bg-blue-50', 'border-l-4', 'border-blue-500', 'text-blue-700');
                item.classList.add('text-gray-600');
            });
            element.classList.add('active', 'bg-blue-50', 'border-l-4', 'border-blue-500', 'text-blue-700');
            element.classList.remove('text-gray-600');

            // Find and click the hidden button
            const buttonText = view.charAt(0).toUpperCase() + view.slice(1);
            const buttons = Array.from(document.querySelectorAll('button'));
            const button = buttons.find(btn => btn.textContent.trim() === buttonText);

            if (button) {
                console.log('✅ Found button, clicking:', buttonText);
                button.click();
            } else {
                console.warn('❌ Button not found:', buttonText);
                console.log('Available buttons:', buttons.map(b => b.textContent.trim()));
            }
        };
        console.log('✅ switchView function defined');

        // Payment handler - automatically trigger wallet payment
        window.handlePayment = function() {
            // Wait for page to load
            const checkForPayment = setInterval(() => {
                // Look for metadata box or payment info in the page
                const metadataElements = document.querySelectorAll('textarea, [role="textbox"], .gr-textbox, .gr-box');
                let paymentInfo = null;

                for (const elem of metadataElements) {
                    const text = elem.textContent || elem.innerText || elem.value;
                    if (text && text.includes('💰 Payment:') && text.includes('Job ID:')) {
                        console.log('🔵 Found payment message:', text);

                        // Extract payment info using regex
                        const jobIdMatch = text.match(/Job ID: ([a-zA-Z0-9\-_.]+)/);
                        const recipientMatch = text.match(/Recipient: ([a-zA-Z0-9]+)/);
                        const paymentMatch = text.match(/💰 Payment: ([0-9.]+) CCD/);

                        if (jobIdMatch && recipientMatch && paymentMatch) {
                            paymentInfo = {
                                jobId: jobIdMatch[1],
                                recipient: recipientMatch[1],
                                amount: parseFloat(paymentMatch[1])
                            };
                            console.log('💳 Payment info extracted:', paymentInfo);
                            break;
                        }
                    }
                }

                if (paymentInfo && window.concordiumWallet && window.concordiumWallet.autoPayInference) {
                    console.log('🟢 Triggering automatic payment...');
                    clearInterval(checkForPayment);

                    window.concordiumWallet.autoPayInference(
                        paymentInfo.jobId,
                        paymentInfo.recipient,
                        paymentInfo.amount
                    ).then(result => {
                        console.log('✅ Payment result:', result);
                        if (result.success) {
                            console.log('✅ Payment sent successfully!');
                        } else {
                            console.error('❌ Payment failed:', result.error);
                        }
                    }).catch(error => {
                        console.error('❌ Payment error:', error);
                    });
                } else if (window.concordiumWallet && !window.concordiumWallet.autoPayInference) {
                    console.warn('⚠️ Wallet loaded but autoPayInference not available');
                }
            }, 500);

            // Stop checking after 60 seconds
            setTimeout(() => clearInterval(checkForPayment), 60000);
        };

        // Start payment handler when wallet is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', window.handlePayment);
        } else {
            setTimeout(window.handlePayment, 500);
        }

        console.log('✅ Payment handler initialized');
        </script>
        <style>
        .hidden-nav-buttons {
            display: none !important;
        }
        .refresh-icon-btn-custom {
            padding: 8px;
            width: 48px;
            height: 48px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .refresh-icon-btn-custom:hover {
            background: #f3f4f6;
            border-color: #9ca3af;
        }
        .refresh-icon-btn-custom svg {
            width: 24px;
            height: 24px;
        }
        .send-icon-btn-custom {
            padding: 8px;
            width: 48px;
            height: 48px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .send-icon-btn-custom:hover {
            background: #3b82f6;
            border-color: #3b82f6;
        }
        .send-icon-btn-custom:hover path {
            stroke: white;
        }
        .send-icon-btn-custom svg {
            width: 24px;
            height: 24px;
        }
        .chat-card {
            border: 2px solid black !important;
            border-radius: 0.5rem !important;
            padding: 1.5rem !important;
            background: white !important;
        }
        .chat-body {
            border: 1px solid #d1d5db !important;
            border-radius: 0.5rem !important;
            margin-bottom: 1rem !important;
        }
        .message-input textarea {
            border: 1px solid #d1d5db !important;
            border-radius: 0.5rem !important;
            padding: 0.75rem !important;
        }
        .message-input textarea:focus {
            border-color: #3b82f6 !important;
            outline: none !important;
        }
        /* Refresh button - icon only, no card */
        .refresh-icon-btn {
            padding: 0 !important;
            min-width: 36px !important;
            width: 36px !important;
            height: 36px !important;
            border: none !important;
            background: transparent !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            font-size: 20px !important;
            line-height: 36px !important;
            text-align: center !important;
            flex: 0 0 auto !important;
        }
        .refresh-icon-btn:hover {
            opacity: 0.6 !important;
            transform: rotate(180deg) !important;
        }
        .send-btn-wrapper {
            display: flex !important;
            align-items: flex-end !important;
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
        }
        .send-btn-wrapper > div {
            display: flex !important;
            align-items: flex-end !important;
        }
        .message-input {
            margin-bottom: 0 !important;
        }
        .html-container.padding {
            padding: 0 !important;
        }
        .nodes-card {
            border: 2px solid black !important;
            border-radius: 0.5rem !important;
            padding: 1.5rem !important;
            background: white !important;
        }
        .history-card {
            border: 2px solid black !important;
            border-radius: 0.5rem !important;
            padding: 1.5rem !important;
            background: white !important;
        }
        </style>
        '''
    ) as demo:
        # Header with wallet buttons - horizontally aligned
        gr.HTML("""
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-4">
                    <svg class="w-16 h-16" fill="#000000" viewBox="0 0 14 14" role="img" focusable="false" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                        <g id="SVGRepo_bgCarrier" stroke-width="0"></g>
                        <g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g>
                        <g id="SVGRepo_iconCarrier">
                            <path d="m 10.134766,10.26461 0.351562,0 0,0.37296 -0.351562,0 z M 9.4763125,8.90929 9.3005313,9.21374 l 0.8341877,0.48162 0,0.40249 0.351562,0 0,-0.60546 z m -3.2244375,1.35532 0.3515625,0 0,0.37296 -0.3515625,0 z M 5.5934922,8.90929 5.4177109,9.21374 l 0.8341875,0.48162 0,0.40249 0.3515625,0 0,-0.60546 z m 4.5412738,-5.37007 0.351562,0 0,0.37296 -0.351562,0 z M 9.4763125,2.18383 9.3005313,2.48828 10.134719,2.9699 l 0,0.40247 0.351562,0 0,-0.60544 z m -3.2244375,1.35539 0.3515625,0 0,0.37296 -0.3515625,0 z M 5.5934922,2.18383 5.4177109,2.48828 6.2518984,2.9699 l 0,0.40247 0.3515625,0 0,-0.60544 z m 6.4826018,4.71773 0.351562,0 0,0.37296 -0.351562,0 z M 11.417711,5.54615 11.24193,5.8506 l 0.834187,0.48162 0,0.40249 0.351563,0 0,-0.60546 z m -0.359109,-0.88978 0,-2.24145 L 8.9413984,1.19254 7,2.31341 5.0586016,1.19254 2.9413984,2.41492 l 0,2.24145 L 1,5.77724 l 0,2.44472 1.9413984,1.12088 0,2.24226 2.1171797,1.22236 L 7,11.68659 l 1.9413984,1.12087 2.1171796,-1.22236 0,-2.24226 L 13,8.22196 13,5.77724 11.058602,4.65637 Z M 7.1757812,2.61789 8.9413984,1.5985 l 1.7656406,1.01939 0,2.03848 -1.7656171,1.01939 -1.7656407,-1.01939 0,-2.03848 z m -3.8827968,0 1.7656172,-1.01939 1.7656171,1.01939 0,2.03848 -1.7656171,1.01939 -1.7656172,-1.01939 0,-2.03848 z m -1.9414219,5.4011 0,-2.03878 1.7653828,-1.01925 1.765875,1.01953 0,2.0385 L 3.1171797,9.03836 1.3515625,8.01899 Z m 5.4726328,3.36312 -1.7656172,1.01939 -1.7656172,-1.01939 0,-2.03876 1.7656172,-1.01939 1.7656172,1.01939 0,2.03876 z m -1.5898125,-3.36314 0,-2.0385 L 7,4.9611 l 1.7656172,1.01939 0,2.0385 L 7,9.03836 5.2343828,8.01897 Z m 3.7070391,4.38253 -1.7656407,-1.01939 0,-2.03876 1.7656172,-1.01939 1.7656176,1.01939 0,2.03876 2.3e-5,0 -1.7656171,1.01939 z M 12.648438,8.01899 10.88282,9.03838 9.1172031,8.01899 l 0,-2.0385 1.7658749,-1.01953 1.76536,1.01925 0,2.03878 z m -4.4552349,-1.11743 0.3515625,0 0,0.37296 -0.3515625,0 z M 7.5349141,5.54615 7.3591328,5.8506 l 0.8341641,0.48162 0,0.40249 0.3515625,0 0,-0.60546 z zm -3.2243672,1.35541 0.3515625,0 0,0.37296 -0.3515625,0 z M 3.6520938,5.54615 3.4763125,5.8506 4.3105,6.33222 l 0,0.40249 0.3515625,0 0,-0.60546 z"></path>
                        </g>
                    </svg>
                    <div>
                        <h1 class="text-4xl font-bold text-gray-800">LLM hive</h1>
                        <p class="text-gray-600">Distributed network of Ollama Host - Monetized with Concordium</p>
                    </div>
                </div>
                <div class="flex gap-2.5">
                    <button id="connect-btn"
                            onclick="if(window.concordiumWallet) { window.concordiumWallet.connect(); } else { alert('Wallet script loading...'); }"
                            class="px-4 py-2 bg-white text-gray-700 rounded cursor-pointer text-sm font-medium hover:bg-blue-50 transition-colors border border-gray-300">
                        Connect Wallet
                    </button>
                    <button id="disconnect-btn"
                            onclick="if(window.concordiumWallet) { window.concordiumWallet.disconnect(); } else { alert('Wallet not loaded'); }"
                            class="px-4 py-2 bg-white text-gray-700 border-2 border-red-500 rounded cursor-pointer text-sm font-medium hover:bg-red-50 transition-colors hidden">
                        Disconnect
                    </button>
                </div>
            </div>
        """)

        # Main content with sidebar
        with gr.Row():
            # Sidebar
            with gr.Column(scale=1, min_width=200):
                gr.HTML("""
                    <div class="bg-gray-50 p-4 rounded-lg border-2 border-black min-h-screen">
                        <nav class="space-y-1">
                            <div id="nav-chat" onclick="window.switchView('chat', this)" class="nav-item active flex items-center px-3 py-2.5 rounded-md cursor-pointer transition-colors bg-blue-50 border-l-4 border-blue-500 text-blue-700">
                                <svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                                </svg>
                                <span class="font-medium">Chat</span>
                            </div>
                            <div id="nav-nodes" onclick="window.switchView('nodes', this)" class="nav-item flex items-center px-3 py-2.5 rounded-md cursor-pointer transition-colors hover:bg-gray-100 text-gray-600">
                                <svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/>
                                </svg>
                                <span class="font-medium">Nodes</span>
                            </div>
                            <div id="nav-history" onclick="window.switchView('history', this)" class="nav-item flex items-center px-3 py-2.5 rounded-md cursor-pointer transition-colors hover:bg-gray-100 text-gray-600">
                                <svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                                </svg>
                                <span class="font-medium">History</span>
                            </div>
                        </nav>
                    </div>
                    <style>
                        .nav-item:not(.active):hover {
                            background-color: #f3f4f6;
                        }
                        .nav-item.active {
                            background-color: #eff6ff;
                            border-left: 4px solid #3b82f6;
                            color: #1d4ed8;
                        }
                    </style>
                """)

                # Hidden buttons for Gradio event handling
                with gr.Row(elem_classes="hidden-nav-buttons"):
                    chat_btn = gr.Button("Chat", elem_id="chat-btn-hidden")
                    nodes_btn = gr.Button("Nodes", elem_id="nodes-btn-hidden")
                    history_btn = gr.Button("History", elem_id="history-btn-hidden")

            # Main content area
            with gr.Column(scale=4):
                # Chat view
                with gr.Column(visible=True, elem_classes="chat-card") as chat_view:
                    gr.Markdown("### Inference")

                    # Get initial models
                    initial_models = asyncio.run(get_available_models())

                    # Model dropdown with refresh button - using Row layout
                    with gr.Row(elem_classes="model-row-container"):
                        model_dropdown = gr.Dropdown(
                            choices=initial_models,
                            value=initial_models[0] if initial_models else "llama3",
                            label="Model",
                            info="Select AI model",
                            scale=1
                        )
                        # Refresh button as icon-only
                        refresh_models_btn_hidden = gr.Button(
                            "↻",
                            elem_id="refresh-models-hidden-btn",
                            elem_classes="refresh-icon-btn"
                        )
                        gr.Column(scale=2)  # Spacer to make dropdown 1/3 width

                    # Connect refresh button click to fetch models
                    refresh_models_btn_hidden.click(
                        fn=get_available_models,
                        outputs=model_dropdown
                    )

                    # Store reference for compatibility
                    refresh_models_btn = refresh_models_btn_hidden

                    gr.HTML("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e5e7eb;'>")

                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=400,
                        show_copy_button=True,
                        type='messages',
                        elem_classes="chat-body"
                    )

                    with gr.Row():
                        msg_box = gr.Textbox(
                            label="",
                            placeholder="Ask anything...",
                            lines=1,
                            scale=9,
                            container=False,
                            elem_classes="message-input"
                        )
                        with gr.Column(scale=1, min_width=50, elem_classes="send-btn-wrapper"):
                            gr.HTML("""
                                <button onclick="document.getElementById('send-hidden-btn').click()"
                                        class="send-icon-btn-custom"
                                        title="Send message">
                                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <g id="SVGRepo_bgCarrier" stroke-width="0"></g>
                                        <g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g>
                                        <g id="SVGRepo_iconCarrier">
                                            <path d="M11.5003 12H5.41872M5.24634 12.7972L4.24158 15.7986C3.69128 17.4424 3.41613 18.2643 3.61359 18.7704C3.78506 19.21 4.15335 19.5432 4.6078 19.6701C5.13111 19.8161 5.92151 19.4604 7.50231 18.7491L17.6367 14.1886C19.1797 13.4942 19.9512 13.1471 20.1896 12.6648C20.3968 12.2458 20.3968 11.7541 20.1896 11.3351C19.9512 10.8529 19.1797 10.5057 17.6367 9.81135L7.48483 5.24303C5.90879 4.53382 5.12078 4.17921 4.59799 4.32468C4.14397 4.45101 3.77572 4.78336 3.60365 5.22209C3.40551 5.72728 3.67772 6.54741 4.22215 8.18767L5.24829 11.2793C5.34179 11.561 5.38855 11.7019 5.407 11.8459C5.42338 11.9738 5.42321 12.1032 5.40651 12.231C5.38768 12.375 5.34057 12.5157 5.24634 12.7972Z" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                                        </g>
                                    </svg>
                                </button>
                            """)
                            send_btn = gr.Button("Send", elem_id="send-hidden-btn", visible=False)

                    clear_btn = gr.Button("Clear", visible=False)

                    gr.HTML("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e5e7eb;'>")

                    metadata_box = gr.Textbox(
                        label="Logs",
                        lines=5,
                        interactive=False
                    )

                # Nodes view
                with gr.Column(visible=False, elem_classes="nodes-card") as nodes_view:
                    gr.Markdown("### Available Nodes & Models")
                    nodes_table = gr.Markdown(asyncio.run(get_nodes_info()))
                    refresh_nodes_btn = gr.Button("Refresh Nodes")

                # Inference History view
                with gr.Column(visible=False, elem_classes="history-card") as history_view:
                    gr.Markdown("### Inference History")
                    gr.Markdown("Recent payments will appear here after connecting your wallet.")
                    history_display = gr.JSON(label="Transaction History")

        # Event handlers
        def refresh_models():
            models = asyncio.run(get_available_models())
            return gr.Dropdown(choices=models, value=models[0] if models else "llama3")

        def refresh_nodes():
            return asyncio.run(get_nodes_info())

        async def handle_send(message, history, model):
            """Handle send button click"""
            async for hist, meta in stream_inference(message, history, model):
                yield hist, meta

        # View switching functions
        def show_chat():
            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

        def show_nodes():
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)

        def show_history():
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

        # Sidebar navigation
        chat_btn.click(
            fn=show_chat,
            outputs=[chat_view, nodes_view, history_view]
        )

        nodes_btn.click(
            fn=show_nodes,
            outputs=[chat_view, nodes_view, history_view]
        )

        history_btn.click(
            fn=show_history,
            outputs=[chat_view, nodes_view, history_view]
        )

        # Connect buttons
        refresh_models_btn.click(
            fn=refresh_models,
            outputs=model_dropdown
        )

        refresh_nodes_btn.click(
            fn=refresh_nodes,
            outputs=nodes_table
        )

        send_btn.click(
            fn=handle_send,
            inputs=[msg_box, chatbot, model_dropdown],
            outputs=[chatbot, metadata_box]
        ).then(
            lambda: "",  # Clear message box
            outputs=msg_box
        )

        msg_box.submit(
            fn=handle_send,
            inputs=[msg_box, chatbot, model_dropdown],
            outputs=[chatbot, metadata_box]
        ).then(
            lambda: "",  # Clear message box
            outputs=msg_box
        )

        clear_btn.click(
            lambda: ([], ""),
            outputs=[chatbot, metadata_box]
        )

        # Wallet button handlers
        # Note: Wallet functionality is handled by wallet.js loaded via gr.HTML
        # Buttons will trigger JavaScript functions when Concordium wallet is installed

        # Auto-load models on page load by clicking refresh button
        gr.HTML("""
            <script>
            (function() {
                function autoRefreshModels() {
                    const refreshBtn = document.getElementById('refresh-models-btn');
                    if (refreshBtn) {
                        console.log('Auto-loading models from registered nodes...');
                        const btn = refreshBtn.querySelector('button');
                        if (btn) btn.click();
                    }
                }

                // Auto-refresh after page loads
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        setTimeout(autoRefreshModels, 500);
                    });
                } else {
                    setTimeout(autoRefreshModels, 500);
                }
            })();
            </script>
        """)

    return demo


if __name__ == "__main__":
    # For testing standalone
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
