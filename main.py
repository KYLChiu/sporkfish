import multiprocessing
import logging


def run_uci():
    logging.info("Running UCI...")
    client = uci_client.UCIClient(uci_client.UCIClient.UCIProtocol.ResponseMode.PRINT)
    while True:
        message = input()
        client.send_command(message)


def run_lichess():
    logging.info("Running Lichess...")
    lichess_client = lichess_bot.LichessBot(token=open("api_token.txt").read())
    lichess_client.run()


if __name__ == "__main__":
    mode = "LICHESS"

    multiprocessing.freeze_support()
    from sporkfish import uci_client, lichess_bot

    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname)s][%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info("----- Sporkfish -----")

    # Should really be an enum but a nice task to move everything to Sporkfish config
    if mode == "LICHESS":
        run_lichess()
    else:
        run_uci()
