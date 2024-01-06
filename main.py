import multiprocessing


def run_uci():
    print("Running UCI...")
    client = uci_client.UCIClient(uci_communicator.ResponseMode.PRINT)
    while True:
        message = input()
        client.send_command(message)


def run_lichess():
    print("Running Lichess...")
    lichess_client = lichess_bot.LichessBot(token=open("api_token.txt").read())
    lichess_client.run()


if __name__ == "__main__":
    mode = "LICHESS"

    multiprocessing.freeze_support()
    from sporkfish import uci_client, uci_communicator, lichess_bot

    if mode == "LICHESS":
        run_lichess()
    else:
        run_uci()
