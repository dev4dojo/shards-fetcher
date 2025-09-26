class FetchError(Exception):
    def __init__(self, url: str, message: str):
        super().__init__(f"Error fetching {url}: {message}")
        self.url = url
        self.message = message
