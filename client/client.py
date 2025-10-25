#!/usr/bin/env python3
"""
CLIENT - Command-line Tool to Send AI Requests

This is what YOU run to ask questions to the AI models.

USAGE:
    python client.py "What is 2+2?" --model llama2:latest
    python client.py nodes  # See all available nodes

HOW IT WORKS:
1. You send a prompt (question) and which model to use
2. Client sends request to the operator
3. Operator queues the job
4. A node picks up the job and runs it
5. Results stream back in real-time (you see each word as it's generated)
"""

import asyncio
import json
import os
import sys
from typing import Optional

import httpx
import typer


# ============================================================================
# CLI Application
# ============================================================================

app = typer.Typer(help="Distributed Ollama Inference Client")


async def process_payment(client: httpx.AsyncClient, operator_url: str, job_id: str, payment_service_url: str):
    """
    Automatically process payment for completed inference job.

    This function:
    1. Queries the job details from the server
    2. Extracts payment information
    3. Calls payment service to send Concordium payment
    """
    try:
        # Query job details to get payment information
        response = await client.get(f"{operator_url}/jobs/{job_id}")

        if response.status_code != 200:
            typer.secho(
                f"\nWarning: Could not retrieve job details for payment",
                fg=typer.colors.YELLOW
            )
            return

        job_data = response.json()
        payment_info = job_data.get("payment")

        if not payment_info or not payment_info.get("recipient_address"):
            typer.secho(
                f"\nNo payment required for this job",
                fg=typer.colors.BLUE,
                dim=True
            )
            return

        # Display payment information
        amount = payment_info["amount_ccd"]
        recipient = payment_info["recipient_address"]
        node = payment_info.get("recipient_node", "unknown")

        typer.secho(f"\n{'='*60}", fg=typer.colors.CYAN)
        typer.secho(f"Payment Processing", fg=typer.colors.CYAN, bold=True)
        typer.secho(f"{'='*60}", fg=typer.colors.CYAN)
        typer.secho(f"Amount: {amount:.6f} CCD", fg=typer.colors.WHITE)
        typer.secho(f"Recipient Node: {node}", fg=typer.colors.WHITE)
        typer.secho(f"Recipient Address: {recipient}", fg=typer.colors.WHITE, dim=True)
        typer.secho(f"Job ID: {job_id}", fg=typer.colors.WHITE, dim=True)

        # Check if wallet credentials are configured
        sender_key = os.getenv("CONCORDIUM_SENDER_KEY")
        sender_address = os.getenv("CONCORDIUM_SENDER_ADDRESS")

        if not sender_key or not sender_address:
            typer.secho(
                f"\nNote: Set CONCORDIUM_SENDER_KEY and CONCORDIUM_SENDER_ADDRESS to enable automatic payments",
                fg=typer.colors.YELLOW,
                dim=True
            )
            typer.secho(
                f"Example: export CONCORDIUM_SENDER_KEY='your_private_key_hex'",
                fg=typer.colors.YELLOW,
                dim=True
            )
            typer.secho(
                f"         export CONCORDIUM_SENDER_ADDRESS='3sXy...'",
                fg=typer.colors.YELLOW,
                dim=True
            )
            return

        # Send payment via payment service
        typer.secho(f"\nProcessing payment via Concordium payment service...", fg=typer.colors.CYAN)

        payment_payload = {
            "amount": amount,
            "recipient": recipient,
            "memo": job_id,
            "sender_key": sender_key,
            "sender_address": sender_address
        }

        payment_response = await client.post(
            f"{payment_service_url}/pay",
            json=payment_payload,
            timeout=30.0
        )

        if payment_response.status_code == 200:
            result = payment_response.json()
            typer.secho(f"✓ Payment sent successfully!", fg=typer.colors.GREEN, bold=True)
            typer.secho(f"Transaction Hash: {result['transaction_hash']}", fg=typer.colors.GREEN, dim=True)
            typer.secho(f"Explorer: {result['explorer_url']}", fg=typer.colors.BLUE, dim=True)

            # Notify server that payment was successful
            try:
                await client.post(
                    f"{operator_url}/payment-confirmed",
                    json={
                        "job_id": job_id,
                        "transaction_hash": result['transaction_hash'],
                        "amount": amount
                    }
                )
            except Exception as e:
                # Don't fail if notification fails - payment already went through
                pass
        else:
            error_data = payment_response.json()
            typer.secho(f"✗ Payment failed", fg=typer.colors.RED)
            typer.secho(f"Error: {error_data.get('message', 'Unknown error')}", fg=typer.colors.RED, dim=True)

        typer.secho(f"{'='*60}\n", fg=typer.colors.CYAN)

    except httpx.HTTPError as e:
        typer.secho(
            f"\nWarning: Could not connect to payment service at {payment_service_url}",
            fg=typer.colors.YELLOW
        )
        typer.secho(
            f"Make sure the payment service is running: cd payment-service && npm start",
            fg=typer.colors.YELLOW,
            dim=True
        )
    except Exception as e:
        typer.secho(
            f"\nWarning: Payment processing error: {e}",
            fg=typer.colors.YELLOW
        )


async def stream_inference(operator_url: str, model: str, prompt: str, test_mode: bool = False):
    """
    Send a request to the operator and print results as they arrive.

    This function doesn't wait for the entire response - it prints each word
    as soon as it's generated by the AI model (streaming).

    After inference completes, automatically processes payment to the node owner
    (unless in test mode).
    """
    request = {
        "model": model,
        "prompt": prompt
    }

    job_id = None

    try:
        # Open a connection to the operator
        # timeout=300 means wait up to 5 minutes for a response
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Stream mode: get results piece by piece, not all at once
            async with client.stream(
                "POST",
                f"{operator_url}/inference",
                json=request
            ) as response:
                # Extract job_id from response headers
                job_id = response.headers.get("X-Job-ID")
                # Check for errors
                if response.status_code != 200:
                    error_text = await response.aread()
                    typer.secho(
                        f"Error: {response.status_code} - {error_text.decode()}",
                        fg=typer.colors.RED,
                        err=True
                    )
                    raise typer.Exit(1)

                # Read and print the response line by line
                # Each line is a JSON object like: {"token": "Hello", "done": false}
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        # Parse the JSON
                        data = json.loads(line)

                        # First chunk: metadata telling us which node is handling this
                        if data.get("metadata"):
                            typer.secho(
                                f"Node: {data['node_id']}",
                                fg=typer.colors.MAGENTA
                            )
                            typer.secho("Response:", fg=typer.colors.GREEN, bold=True)
                            continue

                        # Error handling
                        if "error" in data:
                            typer.secho(
                                f"\nError: {data['error']}",
                                fg=typer.colors.RED,
                                err=True
                            )
                            raise typer.Exit(1)

                        # Print each word/token as it arrives
                        # end="" means don't add a newline (keep printing on same line)
                        # flush=True means show it immediately
                        if "token" in data and not data.get("done", False):
                            print(data["token"], end="", flush=True)

                        # Done signal - add a final newline and show token counts
                        if data.get("done", False):
                            print()  # New line at the end

                            # Display token counts if available
                            if "token_counts" in data and data["token_counts"]:
                                counts = data["token_counts"]
                                typer.secho(
                                    f"\nTokens: {counts.get('total_tokens', 0)} "
                                    f"(prompt: {counts.get('prompt_tokens', 0)}, "
                                    f"completion: {counts.get('completion_tokens', 0)})",
                                    fg=typer.colors.BLUE,
                                    dim=True
                                )
                            break

                    except json.JSONDecodeError as e:
                        typer.secho(
                            f"\nInvalid JSON response: {line}",
                            fg=typer.colors.RED,
                            err=True
                        )
                        continue

            # After streaming completes, process payment automatically (unless in test mode)
            if job_id and not test_mode:
                # Load payment service URL from config
                try:
                    with open("config.json", "r") as f:
                        config = json.load(f)
                        payment_service_url = config.get("payment_service_url", "http://localhost:3000")
                except:
                    payment_service_url = "http://localhost:3000"

                await process_payment(client, operator_url, job_id, payment_service_url)
            elif job_id and test_mode:
                typer.secho(
                    f"\n[TEST MODE] Payment skipped",
                    fg=typer.colors.YELLOW,
                    dim=True
                )

    except httpx.ConnectError:
        typer.secho(
            f"Error: Could not connect to operator at {operator_url}",
            fg=typer.colors.RED,
            err=True
        )
        typer.secho(
            "Please ensure the operator is running.",
            fg=typer.colors.YELLOW,
            err=True
        )
        raise typer.Exit(1)

    except httpx.TimeoutException:
        typer.secho(
            "\nError: Request timed out",
            fg=typer.colors.RED,
            err=True
        )
        raise typer.Exit(1)

    except Exception as e:
        typer.secho(
            f"\nUnexpected error: {e}",
            fg=typer.colors.RED,
            err=True
        )
        raise typer.Exit(1)


@app.command()
def infer(
    prompt: str = typer.Argument(..., help="The prompt to send to the model"),
    model: str = typer.Option("llama3", "--model", "-m", help="Model name to use"),
    operator: Optional[str] = typer.Option(
        None,
        "--operator",
        "-c",
        help="Operator URL (defaults to config.json)"
    ),
    test: bool = typer.Option(
        False,
        "--test",
        help="Test mode: skip payment requirement (for testing only)"
    ),
):
    """
    Run an inference request through the distributed Ollama network.

    Examples:
        python client.py "Explain quantum entanglement" --model llama3
        python client.py infer "Explain quantum entanglement" --model llama3
        python client.py "test prompt" --model llama3 --test  # Skip payment
    """
    # Check for wallet credentials (unless in test mode)
    if not test:
        sender_key = os.getenv("CONCORDIUM_SENDER_KEY")
        sender_address = os.getenv("CONCORDIUM_SENDER_ADDRESS")

        if not sender_key or not sender_address:
            typer.secho(
                "Error: Wallet credentials required for payment",
                fg=typer.colors.RED,
                bold=True,
                err=True
            )
            typer.secho(
                "\nYou must set your Concordium wallet credentials to use this service:",
                fg=typer.colors.YELLOW,
                err=True
            )
            typer.secho(
                "  export CONCORDIUM_SENDER_KEY='your_private_key_hex'",
                fg=typer.colors.WHITE,
                err=True
            )
            typer.secho(
                "  export CONCORDIUM_SENDER_ADDRESS='4nB44...'",
                fg=typer.colors.WHITE,
                err=True
            )
            typer.secho(
                "\nOr load from .env.local:",
                fg=typer.colors.YELLOW,
                err=True
            )
            typer.secho(
                "  source .env.local",
                fg=typer.colors.WHITE,
                err=True
            )
            typer.secho(
                "\nTo test without payment, use:",
                fg=typer.colors.YELLOW,
                err=True
            )
            typer.secho(
                "  python client.py \"your prompt\" --model llama3 --test",
                fg=typer.colors.WHITE,
                err=True
            )
            raise typer.Exit(1)

    # Load operator URL from config if not provided
    if operator is None:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                operator = config.get("operator_url", "http://localhost:8000")
        except FileNotFoundError:
            typer.secho(
                "Error: config.json not found and no operator URL provided",
                fg=typer.colors.RED,
                err=True
            )
            raise typer.Exit(1)
        except Exception as e:
            typer.secho(
                f"Error reading config.json: {e}",
                fg=typer.colors.RED,
                err=True
            )
            raise typer.Exit(1)

    # Display request info
    typer.secho(f"Model: {model}", fg=typer.colors.CYAN)
    typer.secho(f"Operator: {operator}", fg=typer.colors.CYAN)
    typer.secho(f"Prompt: {prompt}", fg=typer.colors.CYAN)
    if test:
        typer.secho(f"Mode: TEST (payment skipped)", fg=typer.colors.YELLOW, bold=True)
    typer.secho("", fg=typer.colors.CYAN)

    # Run the async stream (node info will be shown when metadata arrives)
    asyncio.run(stream_inference(operator, model, prompt, test_mode=test))


@app.command()
def nodes(
    operator: Optional[str] = typer.Option(
        None,
        "--operator",
        "-c",
        help="Operator URL (defaults to config.json)"
    ),
):
    """
    List all registered nodes and their available models.
    """
    # Load operator URL from config if not provided
    if operator is None:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                operator = config.get("operator_url", "http://localhost:8000")
        except Exception as e:
            typer.secho(f"Error reading config: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    async def fetch_nodes():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{operator}/nodes", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            typer.secho(f"Error fetching nodes: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    data = asyncio.run(fetch_nodes())
    nodes_list = data.get("nodes", [])

    if not nodes_list:
        typer.secho("No nodes registered.", fg=typer.colors.YELLOW)
        return

    typer.secho(f"\nRegistered Nodes ({len(nodes_list)}):\n", fg=typer.colors.GREEN, bold=True)

    for node in nodes_list:
        typer.secho(f"Node ID: {node['node_id']}", fg=typer.colors.CYAN, bold=True)
        typer.secho(f"  URL: {node['url']}", fg=typer.colors.WHITE)
        typer.secho(f"  Models: {', '.join(node['models'])}", fg=typer.colors.WHITE)
        typer.secho(f"  Last Seen: {node['last_seen']}", fg=typer.colors.WHITE)
        print()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Make "infer" the default command if no command is specified
    # This allows: python client.py "prompt" instead of python client.py infer "prompt"
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # Check if first arg is a known command or help flag
        if first_arg not in ["infer", "nodes", "--help", "-h", "--version"]:
            # If it starts with a dash, it's likely a flag, so prepend "infer"
            # If it doesn't start with dash, it's likely a prompt, so prepend "infer"
            sys.argv.insert(1, "infer")

    app()
