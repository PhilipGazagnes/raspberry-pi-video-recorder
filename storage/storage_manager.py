class StorageManager:
    def __init__(self, storage_path, max_storage_gb):
        self.storage_path = storage_path
        self.max_storage = max_storage_gb * 1024 * 1024 * 1024

    def get_available_space(self):
        # Check available disk space
        pass

    def cleanup_old_files(self):
        # Remove uploaded files when space is low
        pass

    def generate_filename(self):
        # Create timestamped filename
        pass

    def is_space_available(self):
        # Check if enough space for new recording
        pass
