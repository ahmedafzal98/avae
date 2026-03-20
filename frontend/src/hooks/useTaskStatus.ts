"use client";

import { useQueries } from "@tanstack/react-query";
import type { Query } from "@tanstack/react-query";
import { useAuthToken } from "@/lib/auth";
import { getTaskStatus, type TaskStatusResponse } from "@/lib/api";

const TERMINAL_STATUSES = [
  "COMPLETED",
  "FAILED",
  "EXPIRED",
  "PENDING_HUMAN_REVIEW",
  "AWAITING_CLIENT_REMEDIATION",
];

function isTerminal(status: string) {
  return TERMINAL_STATUSES.includes(status);
}

export function useTaskStatuses(taskIds: string[]) {
  const getToken = useAuthToken();

  const queries = useQueries({
    queries: taskIds.map((taskId) => ({
      queryKey: ["taskStatus", taskId],
      queryFn: async (): Promise<TaskStatusResponse> => {
        const token = await getToken();
        return getTaskStatus(taskId, { token });
      },
      refetchInterval: (query: Query<TaskStatusResponse>) => {
        if (query.state.status === "error") return false;
        const data = query.state.data as TaskStatusResponse | undefined;
        if (!data || isTerminal(data.status)) return false;
        return 3000; // Poll every 3s while in progress
      },
      enabled: taskIds.length > 0,
    })),
  });

  return queries;
}
