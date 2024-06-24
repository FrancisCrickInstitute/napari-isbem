import os
from queue import Queue

from qtpy.QtWidgets import QErrorMessage
import math
import psutil
from qtpy.QtCore import QObject, Signal


class Trigger(QObject):
    """A custom QObject for receiving notifications and commands from threads.
    The trigger signal is emitted by calling signal.emit(). The queue can
    be used to send commands: queue.put(cmd) puts a cmd into the
    queue, and queue.get() reads the cmd and empties the queue.
    """
    signal = Signal()
    queue = Queue()

    def transmit(self, req):
        """Transmit a single command."""
        self.queue.put(req)
        self.signal.emit()


def display_qt_error(parent, error):
        """Handle when an error occurs

        Show the error in an error message window.
        """
        em = QErrorMessage(parent)
        em.showMessage(str(error))
        
        
def is_multiple(a, b):
    """
    Returns True if b is a multiple of a, False otherwise.
    """
    ratio = a / b
    return math.isclose(ratio, round(ratio))


def log_memory_usage():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 ** 2} MB")


def log_memory_usage():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 ** 2} MB")
    
    
