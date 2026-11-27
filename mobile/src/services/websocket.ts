
import { WS_URL } from "./api";

export type VoiceEvent =
  | { type: "final_transcript"; data: string }
  | { type: "agent_text"; data: string; agent?: string }
  | { type: "tool_call"; tool: string }
  | {
      type: "tool_result";
      tool: string;
      result: any;
      status?: string;
      latency_ms?: number;
      call_id?: string;
    }
  | {
      type: "tts_audio_chunk";
      data: string;
      mime_type: string;
    }
  | {
      type: "image_generated";
      data: string;
      mime_type: string;
      filename: string;
      prompt?: string;
      provider?: string;
    }
  | { type: "turn_complete"; latency_ms: number }
  | { type: "agent_plan"; data: any }
  | {
      type: "tool_confirmation";
      data: {
        id: string;
        tool: string;
        arguments: any;
        reason?: string;
      };
    }
  | {
      type: "meeting_started";
      meeting_id: string;
      title: string;
    }
  | {
      type: "meeting_transcript";
      meeting_id: string;
      data: string;
    }
  | { type: "meeting_result"; data: any }
  | { type: "error"; message: string };

// Server compatibility events accepted from older backend builds.
export type LegacyVoiceEvent =
  | {
      type: "transcript";
      text: string;
      session_id?: string;
    }
  | {
      type: "ai_utterance";
      text: string;
      audio?: string;
      mime_type?: string;
      audio_format?: string;
      session_id?: string;
    };

/**
 * Opens an authenticated voice WebSocket connection.
 */
export function openVoiceSocket(
  sessionId: string,
  token: string,
  onEvent: (event: VoiceEvent) => void
): WebSocket {
  const ws = new WebSocket(
    `${WS_URL}/ws/voice/${sessionId}?token=${encodeURIComponent(token)}`
  );

  ws.onmessage = (msg) => {
    try {
      const event = JSON.parse(msg.data) as VoiceEvent;
      onEvent(event);
    } catch {
      // Ignore malformed WebSocket frames.
    }
  };

  return ws;
}

/**
 * Sends a text message to the AI orchestrator.
 */
export function sendText(ws: WebSocket, text: string): void {
  ws.send(
    JSON.stringify({
      type: "text_utterance",
      text,
    })
  );
}

/**
 * Sends one complete recorded audio utterance.
 * Audio must already be base64-encoded.
 * mimeType should match the actual recording format.
 */
export function sendAudioUtterance(
  ws: WebSocket,
  base64Audio: string,
  mimeType: string = "audio/m4a"
): void {
  ws.send(
    JSON.stringify({
      type: "audio_utterance",
      data: base64Audio,
      mime_type: mimeType,
    })
  );
}

/**
 * Sends a base64-encoded image with an optional caption.
 */
export function sendImageMessage(
  ws: WebSocket,
  base64Image: string,
  mimeType: string,
  caption: string
): void {
  ws.send(
    JSON.stringify({
      type: "image_message",
      data: base64Image,
      mime_type: mimeType,
      caption,
    })
  );
}

/**
 * Sends a base64-encoded document or file with an optional caption.
 */
export function sendFileMessage(
  ws: WebSocket,
  base64File: string,
  mimeType: string,
  filename: string,
  caption: string
): void {
  ws.send(
    JSON.stringify({
      type: "file_message",
      data: base64File,
      mime_type: mimeType,
      filename,
      caption,
    })
  );
}

/**
 * Approves or rejects a pending tool confirmation.
 */
export function sendToolConfirmation(
  ws: WebSocket,
  approvalId: string,
  approved: boolean
): void {
  ws.send(
    JSON.stringify({
      type: "tool_confirmation",
      approval_id: approvalId,
      approved,
    })
  );
}

/**
 * Starts a voice meeting.
 */
export function sendMeetingStart(
  ws: WebSocket,
  title: string = "Voice Meeting"
): void {
  ws.send(
    JSON.stringify({
      type: "meeting_start",
      title,
    })
  );
}

/**
 * Ends the current voice meeting.
 */
export function sendMeetingEnd(ws: WebSocket): void {
  ws.send(
    JSON.stringify({
      type: "meeting_end",
    })
  );
}
