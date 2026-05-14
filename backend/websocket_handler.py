# """WebSocket handler for real-time voice conversation."""

# import logging

# from fastapi import WebSocket, WebSocketDisconnect

# from .agent import run_agent
# from .voice.stt import transcribe_bytes
# from .voice.tts import synthesize_to_bytes

# log = logging.getLogger("websocket_handler")


# class VoiceWebSocketManager:
#     def __init__(self):
#         self.connections: dict[str, WebSocket] = {}

#     async def connect(self, websocket: WebSocket, session_id: str):
#         await websocket.accept()
#         self.connections[session_id] = websocket
#         log.info(f"Client connected: {session_id}")

#     def disconnect(self, session_id: str):
#         if session_id in self.connections:
#             del self.connections[session_id]
#             log.info(f"Client disconnected: {session_id}")

#     async def handle_voice_stream(self, websocket: WebSocket, session_id: str):
#         try:
#             while True:
#                 data = await websocket.receive_bytes()
#                 if len(data) < 2000:
#                     continue

#                 # Simple VAD
#                 energy = sum(abs(int.from_bytes(data[i:i+2], 'little', signed=True)) 
#                            for i in range(0, len(data), 2)) / (len(data) / 2)

#                 if energy < 1100:   # Adjust this threshold if needed
#                     continue

#                 try:
#                     transcript = await transcribe_bytes(data, suffix=".wav")
#                     transcript = transcript.strip()

#                     if len(transcript) > 5:
#                         await websocket.send_json({"type": "transcript", "text": transcript})

#                         reply = await run_agent(session_id, transcript)

#                         await websocket.send_json({"type": "reply", "text": reply})

#                         audio_bytes = await synthesize_to_bytes(reply)
#                         if audio_bytes:
#                             await websocket.send_bytes(audio_bytes)
#                             await websocket.send_json({"type": "audio_done"})

#                 except Exception as exc:
#                     log.exception("Voice processing error")
#                     await websocket.send_json({"type": "error", "message": str(exc)})

#         except WebSocketDisconnect:
#             self.disconnect(session_id)
#         except Exception as exc:
#             log.exception("WebSocket error")
#             self.disconnect(session_id)


# manager = VoiceWebSocketManager()