class TextIO:
    async def on_text_received(self, text: str):
        raise NotImplementedError()

    async def send_text(self, text: str):
        raise NotImplementedError()

    async def run(self):
        raise NotImplementedError()
