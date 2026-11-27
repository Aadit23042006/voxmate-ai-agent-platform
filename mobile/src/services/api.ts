
// Set EXPO_PUBLIC_API_URL in mobile/.env for a physical device.
// Example: http://192.168.1.25:8000
// localhost works for an emulator/simulator on the development machine.

const configuredApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim();

export const API_URL = (
  configuredApiUrl || "http://localhost:8000"
).replace(/\/+$/, "");

export const WS_URL = API_URL
  .replace(/^http:/, "ws:")
  .replace(/^https:/, "wss:");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message = `Request failed: ${status}`
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Extract safe server error details without logging submitted input.
function getSafeErrorDetails(responseText: string): unknown {
  try {
    const parsed = JSON.parse(responseText);

    if (typeof parsed?.detail === "string") {
      return parsed.detail;
    }

    if (Array.isArray(parsed?.detail)) {
      return parsed.detail.map((item: any) => ({
        loc: item?.loc,
        msg: item?.msg,
        type: item?.type,
      }));
    }

    return "Server returned an error response";
  } catch {
    return "Server returned a non-JSON error response";
  }
}

// -----------------------------------------------------------------------------
// Authentication
// -----------------------------------------------------------------------------

async function postCredentials(
  path: string,
  email: string,
  password: string
) {
  let res: Response;

  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
      }),
    });
  } catch {
    console.warn("[VoxMate Auth Diagnostic]", {
      path,
      error: "Network request failed",
    });

    throw new Error("NETWORK_ERROR");
  }

  if (!res.ok) {
    const responseText = await res.text();

    console.warn("[VoxMate Auth Diagnostic]", {
      path,
      status: res.status,
      response: getSafeErrorDetails(responseText),
    });

    throw new ApiError(res.status);
  }

  let data: any;

  try {
    data = await res.json();
  } catch {
    throw new Error("INVALID_AUTH_RESPONSE");
  }

  if (!data?.access_token) {
    throw new Error("INVALID_AUTH_RESPONSE");
  }

  return data as {
    access_token: string;
    token_type?: string;
  };
}

export async function register(email: string, password: string) {
  return postCredentials("/auth/register", email, password);
}

export async function login(email: string, password: string) {
  return postCredentials("/auth/login", email, password);
}

// -----------------------------------------------------------------------------
// Sessions
// -----------------------------------------------------------------------------

export async function createSession(token: string) {
  const res = await fetch(`${API_URL}/sessions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Create session failed: ${res.status}`);
  }

  return res.json() as Promise<{
    session_id: string;
  }>;
}

// -----------------------------------------------------------------------------
// Search History
// -----------------------------------------------------------------------------

export type SearchHistoryItem = {
  id: string;
  query: string;
  answer: string | null;
  sources: {
    title?: string;
    url?: string;
  }[];
  status: string;
  created_at: string;
};

export async function getSearchHistory(token: string) {
  const res = await fetch(`${API_URL}/history/search`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Fetch history failed: ${res.status}`);
  }

  return res.json() as Promise<SearchHistoryItem[]>;
}

export async function deleteSearchHistoryItem(
  token: string,
  id: string
) {
  const res = await fetch(`${API_URL}/history/search/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Delete history item failed: ${res.status}`);
  }

  return res.json() as Promise<{
    deleted: boolean;
  }>;
}

// -----------------------------------------------------------------------------
// Preferences
// -----------------------------------------------------------------------------

export type Preferences = {
  tts_voice: string;
  assistant_name: string;
  tone: "casual" | "formal";
  available_voices: string[];
};

export async function getPreferences(token: string) {
  const res = await fetch(`${API_URL}/account/preferences`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Fetch preferences failed: ${res.status}`);
  }

  return res.json() as Promise<Preferences>;
}

export async function updatePreferences(
  token: string,
  patch: Partial<
    Pick<Preferences, "tts_voice" | "assistant_name" | "tone">
  >
) {
  const res = await fetch(`${API_URL}/account/preferences`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(patch),
  });

  if (!res.ok) {
    throw new Error(`Update preferences failed: ${res.status}`);
  }

  return res.json() as Promise<Preferences>;
}

// -----------------------------------------------------------------------------
// Usage Statistics
// -----------------------------------------------------------------------------

export type UsageStats = {
  total_sessions: number;
  total_messages: number;
  total_tool_calls: number;
  tasks_created: number;
  code_executions: number;
  documents_uploaded: number;
  searches_run: number;
};

export async function getUsageStats(token: string) {
  const res = await fetch(`${API_URL}/account/stats`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Fetch usage stats failed: ${res.status}`);
  }

  return res.json() as Promise<UsageStats>;
}

export async function deleteAllData(token: string) {
  const res = await fetch(`${API_URL}/account/data`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Delete data failed: ${res.status}`);
  }

  return res.json() as Promise<{
    deleted: boolean;
  }>;
}

// -----------------------------------------------------------------------------
// Google Integration
// -----------------------------------------------------------------------------

export async function getGoogleConnectUrl(token: string) {
  const res = await fetch(`${API_URL}/integrations/google/connect`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(
      (await res.text()) || `Google connect failed: ${res.status}`
    );
  }

  return res.json() as Promise<{
    authorization_url: string;
  }>;
}

export async function getGoogleStatus(token: string) {
  const res = await fetch(`${API_URL}/integrations/google/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Google status failed: ${res.status}`);
  }

  return res.json() as Promise<{
    connected: boolean;
  }>;
}

// -----------------------------------------------------------------------------
// Push Notifications
// -----------------------------------------------------------------------------

export async function registerPushToken(
  token: string,
  expo_push_token: string,
  platform?: string
) {
  const res = await fetch(
    `${API_URL}/integrations/notifications/device`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        expo_push_token,
        platform,
      }),
    }
  );

  if (!res.ok) {
    const responseText = await res.text();
    let detail = responseText;
    try {
      const parsed = JSON.parse(responseText);
      detail = parsed.detail || parsed.message || responseText;
    } catch {
      // Keep the raw response when it is not JSON.
    }
    throw new Error(
      `Notification registration failed (${res.status}): ${String(detail).slice(0, 240)}`
    );
  }

  return res.json();
}

// -----------------------------------------------------------------------------
// GitHub Integration
// -----------------------------------------------------------------------------

export async function getGitHubStatus(token: string) {
  const res = await fetch(`${API_URL}/integrations/github/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`GitHub status failed: ${res.status}`);
  }

  return res.json() as Promise<{
    connected: boolean;
    login?: string | null;
  }>;
}

export async function connectGitHub(
  token: string,
  githubToken: string
) {
  const res = await fetch(`${API_URL}/integrations/github/connect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      token: githubToken,
    }),
  });

  if (!res.ok) {
    throw new Error(
      (await res.text()) ||
        `GitHub connection failed: ${res.status}`
    );
  }

  return res.json() as Promise<{
    connected: boolean;
    login?: string;
  }>;
}

export async function disconnectGitHub(token: string) {
  const res = await fetch(
    `${API_URL}/integrations/github/disconnect`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!res.ok) {
    throw new Error(`GitHub disconnect failed: ${res.status}`);
  }

  return res.json();
}

// -----------------------------------------------------------------------------
// Platform
// -----------------------------------------------------------------------------

export type CustomAgent = {
  id: string;
  name: string;
  description: string;
  persona: string;
  tool_names: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type MarketplacePlugin = {
  id: string;
  slug: string;
  name: string;
  description: string;
  version: string;
  author: string;
  icon: string;
  category: string;
  featured: boolean;
  tool_names: string[];
  installed: boolean;
};

export type Analytics = {
  sessions: number;
  messages: number;
  tool_calls: number;
  successful_tool_calls: number;
  failed_tool_calls: number;
  avg_tool_latency_ms: number;
  active_custom_agents: number;
  installed_plugins: number;
  agent_runs: number;
  top_tools: {
    tool: string;
    calls: number;
  }[];
};

async function platformFetch(
  token: string,
  path: string,
  init: RequestInit = {}
) {
  const res = await fetch(`${API_URL}/platform${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    throw new Error(
      (await res.text()) ||
        `Platform request failed: ${res.status}`
    );
  }

  return res.json();
}

export const getCustomAgents = (token: string) =>
  platformFetch(token, "/agents") as Promise<CustomAgent[]>;

export const createCustomAgent = (
  token: string,
  body: Omit<CustomAgent, "id" | "created_at" | "updated_at">
) =>
  platformFetch(token, "/agents", {
    method: "POST",
    body: JSON.stringify(body),
  }) as Promise<CustomAgent>;

export const deleteCustomAgent = (
  token: string,
  id: string
) =>
  platformFetch(token, `/agents/${id}`, {
    method: "DELETE",
  });

export const getMarketplacePlugins = (token: string) =>
  platformFetch(token, "/plugins") as Promise<MarketplacePlugin[]>;

export const installPlugin = (token: string, id: string) =>
  platformFetch(token, `/plugins/${id}/install`, {
    method: "POST",
  });

export const uninstallPlugin = (token: string, id: string) =>
  platformFetch(token, `/plugins/${id}/install`, {
    method: "DELETE",
  });

export const getAnalytics = (token: string) =>
  platformFetch(token, "/analytics") as Promise<Analytics>;

export const runMultiAgent = (
  token: string,
  task: string,
  agent_keys?: string[]
) =>
  platformFetch(token, "/multi-agent", {
    method: "POST",
    body: JSON.stringify({
      task,
      agent_keys,
    }),
  });
