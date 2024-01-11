import time
from multiprocessing import Value, Lock


class Statistics:
    """A class for tracking statistics related to node visits."""

    def __init__(self, nodes_visited: Value):
        """
        Initialize the Statistics object.

        Attributes:
        - nodes_visited (Value): The number of nodes visited. Shared across processes.
        """
        self.nodes_visited = nodes_visited

    def increment(self, count: int = 1) -> None:
        """
        Increment the nodes_visited count.

        Parameters:
        - count (int): The number of nodes to increment the count by. Default is 1.
        """
        self.nodes_visited += count

    def reset(self) -> None:
        """
        Reset the statistics by setting nodes_visited to 0 and updating start_time to the current time.
        """
        self.nodes_visited = 0
