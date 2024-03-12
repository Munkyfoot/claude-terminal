import argparse

from utils import USER_STYLE_PREFIX, Agent, PrintStyle

if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Chat with an AI.")

    # Add arguments
    parser.add_argument("query", nargs="*", default=None, help="Optional initial query")
    parser.add_argument(
        "--memory", "-m", action="store_true", help="Use history to improve responses"
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Check if an initial query was provided
    has_initial_query = bool(args.query)

    # Create an Agent instance with the specified memory usage
    agent = Agent(use_memory=args.memory)

    while True:
        try:
            if has_initial_query:
                # If an initial query was provided, use it as the first query
                query = " ".join(args.query)
                print(f"{USER_STYLE_PREFIX}> {query}{PrintStyle.RESET.value}")
                has_initial_query = False
            else:
                # Prompt the user for input
                query = input(f"{USER_STYLE_PREFIX}> ")
                if query.lower() in ["exit", "quit"] or query == "":
                    break
                print(PrintStyle.RESET.value, end="")

            # Run the agent with the user's query
            response = agent.run(query)

        except KeyboardInterrupt:
            # Handle keyboard interruption (Ctrl+C)
            # Clear the line and any styles and continue
            print("\033[K", end="\r")
            break

        except Exception as e:
            # Handle any other exceptions
            print(f"Error (user): {e}")
            continue

    # Clear any styles before exiting
    print(PrintStyle.RESET.value, end="")
