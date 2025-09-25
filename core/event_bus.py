from queue import Queue


class EventBus:
    def __init__(self):
        self.subscribers = {}
        self.event_queue = Queue()

    def subscribe(self, event_type, callback):
        # Register event handlers
        pass

    def publish(self, event_type, data):
        # Send events to subscribers
        pass
