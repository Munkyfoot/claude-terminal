import argparse

from utils import USER_STYLE_PREFIX, Agent, PrintStyle

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat with an AI.")
    parser.add_argument("query", nargs="*", default=None, help="Optional initial query")
    parser.add_argument(
        "--memory", "-m", action="store_true", help="Use history to improve responses"
    )

    args = parser.parse_args()

    has_initial_query = bool(args.query)

    agent = Agent(use_memory=args.memory)

    while True:
        try:
            if has_initial_query:
                query = " ".join(args.query)
                print(f"{USER_STYLE_PREFIX}> {query}{PrintStyle.RESET.value}")
                has_initial_query = False
            else:
                query = input(f"{USER_STYLE_PREFIX}> ")
                if query.lower() in ["exit", "quit"] or query == "":
                    break
                print(PrintStyle.RESET.value, end="")
            response = agent.run(query)
        except KeyboardInterrupt:
            # Clear the line and any styles and continue
            print("\033[K", end="\r")
            break
        except Exception as e:
            print(f"Error (user): {e}")
            continue

    # Clear any styles
    print(PrintStyle.RESET.value, end="")
