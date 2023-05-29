import argparse
import sys
import time

from kobold_assistant.mumble import MumbleClient

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('server_address', default='localhost')
    parser.add_argument('port', default=64738, type=int)
    parser.add_argument('username', default='test')
    parser.add_argument('password', default='test')
    parser.add_argument('audio_file', help="Path to the audio file (WAV format) that will be sent to the server.")

    args = parser.parse_args()

    # Create the client
    c_and_c_users = ['lb', 'lbphone']
    print(f"Waiting for commands from {c_and_c_users!r}")
    client = MumbleClient(args.server_address, args.port, args.username, args.password, c_and_c_users)

    while True:
        # Listen for 5 seconds
        client.start_receive_text()
        time.sleep(5)
        client.stop_receive_text()

        print("Recognized text:", client.get_recognized_text())

        # Then switch and send for 5 seconds
        client.start_send_audio(args.audio_file)
        time.sleep(5)
        client.stop_send_audio()

    # To close the client, call the close method
    # client.close()  # Remember to use this if you ever break the infinite loop


if __name__ == "__main__":
    sys.exit(main())
