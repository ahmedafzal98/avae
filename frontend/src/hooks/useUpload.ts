"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuthToken } from "@/lib/auth";
import { uploadFiles, type UploadResponse } from "@/lib/api";
import type { AuditTarget } from "@/types/audit-target";

export interface UploadParams {
  files: File[];
  auditTarget: AuditTarget;
  userId?: number;
  prompt?: string;
  /** When set, single-file remediation upload for AWAITING_CLIENT_REMEDIATION checkpoint (Task 4.8) */
  remediationForCheckpointId?: string | null;
}

export function useUpload() {
  const getToken = useAuthToken();

  return useMutation({
    mutationFn: async ({
      files,
      auditTarget,
      userId = 1,
      prompt,
      remediationForCheckpointId,
    }: UploadParams): Promise<UploadResponse> => {
      const token = await getToken();
      return uploadFiles(files, {
        auditTarget,
        userId,
        prompt,
        token,
        remediationForCheckpointId,
      });
    },
  });
}
