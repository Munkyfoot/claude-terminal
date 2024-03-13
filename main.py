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
    parser.add_argument(
        "--opus", "-o", action="store_true", help="Use opus model for better responses"
    )
    parser.add_argument(
        "--ls",
        "-l",
        action="store_true",
        help="Show Claude all files and directories in the current directory (except those specified in the .gitignore file)",
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Check if an initial query was provided
    has_initial_query = bool(args.query)

    # Create an Agent instance with the specified memory usage
    agent = Agent(
        model="claude-3-opus-20240229" if args.opus else "claude-3-sonnet-20240229",
        use_memory=args.memory,
        view_list_dir=args.ls,
    )

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
