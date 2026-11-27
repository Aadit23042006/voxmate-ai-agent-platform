import { useCallback, useEffect, useRef, useState } from "react";
import { createSession } from "../services/api";
import {
  openVoiceSocket,
  sendText,
  sendAudioUtterance,
  sendImageMessage,
  sendFileMessage,
  sendToolConfirmation, sendMeetingStart, sendMeetingEnd,
  VoiceEvent,
} from "../services/websocket";
import { useAudioPlayer, writeBase64ToTempFile } from "../services/audio";

export type TranscriptEntry = {
  role: "user" | "assistant";
  text: string;
  agent?: string;
  sources?: { title?: string; url: string }[];
  image?: { data: string; mimeType: string; filename: string; prompt?: string; provider?: string };
};

export function useVoiceSession(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [ttsUri, setTtsUri] = useState<string | undefined>(undefined);
  const [agentPlan, setAgentPlan] = useState<any | null>(null);
  const [confirmation, setConfirmation] = useState<any | null>(null);
  const [meeting, setMeeting] = useState<any | null>(null);

  // Loads whatever local file ttsUri currently points to. Re-created each
  // time ttsUri changes so a new reply always gets picked up.
  const player = useAudioPlayer(ttsUri);

  useEffect(() => {
    if (ttsUri) {
      player.play();
    }
  }, [ttsUri, player]);

  const connect = useCallback(async () => {
    if (!token) return;
    const { session_id } = await createSession(token);

    let pendingSources: { title?: string; url: string }[] | undefined;

    const handleEvent = (event: VoiceEvent) => {
      if (event.type === "final_transcript") {
        setTranscript((t) => [...t, { role: "user", text: event.data }]);
      } else if (event.type === "tool_result") {
        // search results carry real grounding source URLs — attach them
        // too so the user can see where an answer came from.
        if (event.tool === "search" && Array.isArray(event.result?.sources) && event.result.sources.length) {
          pendingSources = event.result.sources;
        }
      } else if (event.type === "agent_plan") {
        setAgentPlan(event.data);
      } else if (event.type === "tool_confirmation") {
        setConfirmation(event.data);
        setBusy(false);
      } else if (event.type === "agent_text") {
        setTranscript((t) => [
          ...t,
          { role: "assistant", text: event.data, agent: event.agent, sources: pendingSources },
        ]);
        pendingSources = undefined;
      } else if (event.type === "image_generated") {
        setTranscript((t) => {
          if (!t.length) return t;
          const next = [...t];
          const lastIndex = next.length - 1;
          if (next[lastIndex].role === "assistant") {
            next[lastIndex] = {
              ...next[lastIndex],
              image: {
                data: event.data,
                mimeType: event.mime_type,
                filename: event.filename,
                prompt: event.prompt,
                provider: event.provider,
              },
            };
          }
          return next;
        });
      } else if (event.type === "tts_audio_chunk") {
        try {
          const extension = event.mime_type?.includes("wav") ? "wav" : "mp3";
          const uri = writeBase64ToTempFile(event.data, extension);
          setTtsUri(uri);
        } catch (err: any) {
          setBusy(false);
          console.error("VoxMate TTS file/playback preparation failed", err);
        }
      } else if ((event as any).type === "transcript") {
        // Backward compatibility with older backend builds.
        const legacy = event as any;
        if (legacy.text) {
          setTranscript((t) => [...t, { role: "user", text: legacy.text }]);
        }
      } else if ((event as any).type === "ai_utterance") {
        // Backward compatibility with older backend builds.
        const legacy = event as any;
        if (legacy.text) {
          setTranscript((t) => [...t, { role: "assistant", text: legacy.text }]);
        }
        if (legacy.audio) {
          const extension = legacy.mime_type?.includes("wav") ? "wav" : "mp3";
          try {
            setTtsUri(writeBase64ToTempFile(legacy.audio, extension));
          } catch (err) {
            console.error("VoxMate legacy TTS playback preparation failed", err);
          }
        }
      } else if (event.type === "meeting_started") {
        setMeeting({ id: event.meeting_id, title: event.title, status: "recording" });
      } else if (event.type === "meeting_transcript") {
        setTranscript((t) => [...t, { role: "user", text: `Meeting: ${event.data}` }]);
      } else if (event.type === "meeting_result") {
        setMeeting({ ...event.data, status: "completed" });
        setTranscript((t) => [...t, { role: "assistant", text: `Meeting summary:\n${event.data.summary || "Completed."}` }]);
      } else if (event.type === "turn_complete") {
        setBusy(false);
      } else if (event.type === "error") {
        setBusy(false);
        console.error("VoxMate voice error:", event.message);
      }
    };

    const ws = openVoiceSocket(session_id, token, handleEvent);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    wsRef.current = ws;
  }, [token]);

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current) return;
    setBusy(true);
    sendText(wsRef.current, text);
  }, []);

  /** Sends a fully recorded utterance (base64 audio) for the server to
   * transcribe and respond to with real speech. */
  const sendVoiceMessage = useCallback((base64Audio: string, mimeType: string) => {
    if (!wsRef.current) return;
    setBusy(true);
    sendAudioUtterance(wsRef.current, base64Audio, mimeType);
  }, []);

  /** Sends a photo with an optional caption/question about it. */
  const sendImage = useCallback((base64Image: string, mimeType: string, caption: string) => {
    if (!wsRef.current) return;
    setBusy(true);
    sendImageMessage(wsRef.current, base64Image, mimeType, caption);
  }, []);

  /** Sends a document/file with an optional caption. */
  const sendFile = useCallback(
    (base64File: string, mimeType: string, filename: string, caption: string) => {
      if (!wsRef.current) return;
      setBusy(true);
      sendFileMessage(wsRef.current, base64File, mimeType, filename, caption);
    },
    []
  );

  const confirmTool = useCallback((approved: boolean) => {
    if (!wsRef.current || !confirmation?.id) return;
    setBusy(true);
    sendToolConfirmation(wsRef.current, confirmation.id, approved);
    setConfirmation(null);
  }, [confirmation]);

  const startMeeting = useCallback((title = "Voice Meeting") => {
    if (!wsRef.current) return;
    sendMeetingStart(wsRef.current, title);
  }, []);
  const endMeeting = useCallback(() => {
    if (!wsRef.current) return;
    sendMeetingEnd(wsRef.current);
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return {
    connect,
    disconnect,
    sendMessage,
    sendVoiceMessage,
    sendImage,
    sendFile,
    connected,
    transcript,
    busy,
    agentPlan,
    confirmation,
    confirmTool,
    meeting,
    startMeeting,
    endMeeting,
  };
}
