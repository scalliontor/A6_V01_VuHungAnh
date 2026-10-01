class SpeechService:
    """Prototype speech to text: input is an already transcribed string."""

    def transcribe(self, audio_input):
        if not isinstance(audio_input, str) or not audio_input.strip():
            raise ValueError("Provide a nonempty simulated transcript")
        return audio_input.strip()
