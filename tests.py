import threading
import time
import io
import sys

def thread_b(output_stream):
    for i in range(5):
        print(f"[Thread B] Message {i}", file=output_stream)
        time.sleep(0.5)

def main():
    buffer = io.StringIO()
    t = threading.Thread(target=thread_b, args=(buffer,))
    t.start()

    for i in range(5):
        print(f"[Main Thread] Message {i}")
        time.sleep(0.5)

    t.join()

    print("\n[Thread B Output]")
    print(buffer.getvalue())

if __name__ == "__main__":
    main()
