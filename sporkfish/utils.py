import time
import sys
import traceback


def run_timed(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time
        print(f"{func.__name__} took {execution_time:.5f} seconds to run.")
        return result

    return wrapper


def run_with_except_msg(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Caught exception: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise

    return wrapper
