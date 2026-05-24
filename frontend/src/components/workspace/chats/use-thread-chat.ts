"use client";

import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { fetch as fetchWithAuth } from "@/core/api/fetcher";
import { getLangGraphBaseURL } from "@/core/config";
import { uuid } from "@/core/utils/uuid";

/**
 * Verifies that a thread exists on the backend.
 * Inspired by Open WebUI's getChatById pattern: if the chat/thread is not
 * found (404), the caller should redirect to a new conversation instead of
 * letting the LangGraph SDK crash with an error cascade.
 */
async function threadExistsOnBackend(threadId: string): Promise<boolean> {
  try {
    const baseUrl = getLangGraphBaseURL();
    const res = await fetchWithAuth(
      `${baseUrl}/threads/${encodeURIComponent(threadId)}`,
      { method: "GET" },
    );
    // 404 = thread not in checkpointer  treat as non-existent
    // Any other status (200, 5xx, etc.)  assume exists to avoid spurious redirects
    if (res.status === 404) return false;
    return true;
  } catch {
    // Network error: treat as existing to avoid redirect loops
    return true;
  }
}

export function useThreadChat() {
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const pathname = usePathname();
  const router = useRouter();

  const searchParams = useSearchParams();
  const [threadId, setThreadId] = useState(() => {
    return threadIdFromPath === "new" ? uuid() : threadIdFromPath;
  });

  const [isNewThread, setIsNewThread] = useState(
    () => threadIdFromPath === "new",
  );

  // Track which thread IDs we have already validated so we only fire the
  // backend check once per unique thread_id (not on every re-render).
  const validatedThreadRef = useRef<string | null>(null);

  useEffect(() => {
    if (pathname.endsWith("/new")) {
      setIsNewThread(true);
      setThreadId(uuid());
      return;
    }
    // Guard: after history.replaceState updates the URL from /chats/new to
    // /chats/{UUID}, Next.js useParams may still return the stale "new" value
    // because replaceState does not trigger router updates. Avoid propagating
    // this invalid thread ID to downstream hooks (e.g. useStream), which would
    // cause a 422 from LangGraph Server.
    if (threadIdFromPath === "new") {
      return;
    }
    setIsNewThread(false);
    setThreadId(threadIdFromPath);

    // --- Open WebUI-inspired thread validation ---
    // On initial load of /workspace/chats/{thread_id}, verify the thread
    // still exists in the backend checkpointer.  If it returns 404 we
    // redirect to /workspace/chats/new instead of letting useStream receive
    // the 404 and trigger the error cascade that caused DeerFlow to always
    // return to the chat page (issue: GET /api/langgraph/threads/{id}  404
    //  SDK onError  isNewThread flip  redirect loop).
    if (validatedThreadRef.current !== threadIdFromPath) {
      validatedThreadRef.current = threadIdFromPath;
      void threadExistsOnBackend(threadIdFromPath).then((exists) => {
        if (!exists) {
          // Same pattern as Open WebUI Chat.svelte:
          // getChatById returns null  goto("/")
          router.replace("/workspace/chats/new");
        }
      });
    }
  }, [pathname, threadIdFromPath, router]);

  const isMock = searchParams.get("mock") === "true";
  return { threadId, setThreadId, isNewThread, setIsNewThread, isMock };
}
