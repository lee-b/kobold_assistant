class Participant:
    def get_name(self) -> str:
        raise NotImplementedError()

    async def _on_dialog_event(self, event: 'DialogEvent', history: 'DialogHistory'):
        pass

    async def _run(self, dialog_history):
        raise NotImplementedError()

    async def run(self, dialog_history: 'DialogHistory'):
        dialog_history.add_event_handler(self._on_dialog_event)
        try:
            self._connect_events()
        finally:
            dialog_history.remove_event_handler(self._on_dialog_event)
