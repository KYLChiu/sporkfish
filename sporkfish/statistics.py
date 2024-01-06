import time
from multiprocessing import Value


class Statistics:
    """A class for tracking statistics related to node visits."""

    def __init__(self, nodes_visited: Value):
        """
        Initialize the Statistics object.

        Attributes:
        - nodes_visited (int): The number of nodes visited.
        - start_time (float): The time when the Statistics object was created.
        """
        self.nodes_visited = nodes_visited
        self.start_time = time.time()

    def increment(self, count: int = 1) -> None:
        """
        Increment the nodes_visited count.

        Parameters:
        - count (int): The number of nodes to increment the count by. Default is 1.
        """
        # Not entirely accurate as not atomic, but will do for now
        self.nodes_visited.value += count

    def nodes_per_second(self) -> float:
        """
        Calculate and return the nodes visited per second.

        Returns:
        - float: Nodes per second. If no nodes have been visited or the elapsed time is 0, returns 0.
        """
        elapsed_time = time.time() - self.start_time
        return self.nodes_visited.value / elapsed_time if elapsed_time > 0 else 0

    def reset(self) -> None:
        """
        Reset the statistics by setting nodes_visited to 0 and updating start_time to the current time.
        """
        self.nodes_visited.value = 0
        self.start_time = time.time()
